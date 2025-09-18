"""Tests for threshold validation functionality."""

import pytest
from unittest.mock import Mock
from app.validators.threshold_checks import ThresholdValidator
from tests.test_utils import create_mock_flag_meta, create_mock_flag_detail, create_mock_100_percent_flag_detail


@pytest.mark.unit
class TestThresholdValidator:
    """Test ThresholdValidator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            "permanent_flags_tag": "permanent,keep",
            "flag_last_modified_threshold": "90d",
            "flag_last_traffic_threshold": "30d",
            "flag_at_100_percent_last_modified_threshold": "30d",
            "flag_at_100_percent_last_traffic_threshold": "7d",
            "debug": True,
        }
        self.validator = ThresholdValidator(self.config)

    def test_permanent_flag_detection_positive(self):
        """Test detection of flags with permanent tags."""
        flag_meta_data = {"test-flag": create_mock_flag_meta("test-flag", ["frontend", "permanent"])}

        result = self.validator._is_permanent_flag("test-flag", flag_meta_data)
        assert result is True

    def test_permanent_flag_detection_negative(self):
        """Test that flags without permanent tags are not marked as permanent."""
        flag_meta_data = {"test-flag": create_mock_flag_meta("test-flag", ["frontend", "deprecated"])}

        result = self.validator._is_permanent_flag("test-flag", flag_meta_data)
        assert result is False

    def test_permanent_flag_case_insensitive(self):
        """Test that permanent flag detection is case insensitive."""
        flag_meta_data = {
            "flag1": create_mock_flag_meta("flag1", ["PERMANENT"]),
            "flag2": create_mock_flag_meta("flag2", ["Keep"]),
            "flag3": create_mock_flag_meta("flag3", ["deprecated"]),
        }

        assert self.validator._is_permanent_flag("flag1", flag_meta_data) is True
        assert self.validator._is_permanent_flag("flag2", flag_meta_data) is True
        assert self.validator._is_permanent_flag("flag3", flag_meta_data) is False

    def test_permanent_flag_with_no_config(self):
        """Test permanent flag detection when no permanent tags are configured."""
        validator = ThresholdValidator({"permanent_flags_tag": "", "flag_last_modified_threshold": "90d", "debug": False})

        flag_meta_data = {"test-flag": create_mock_flag_meta("test-flag", ["permanent"])}

        result = validator._is_permanent_flag("test-flag", flag_meta_data)
        assert result is False

    def test_permanent_flags_excluded_from_threshold_checks(self):
        """Test that permanent flags are excluded from threshold checks."""
        # Create flag metadata - one permanent, one not
        flag_meta_data = {
            "permanent-flag": create_mock_flag_meta("permanent-flag", ["permanent"]),
            "regular-flag": create_mock_flag_meta("regular-flag", ["frontend"]),
        }

        # Create old flag details that would normally fail threshold checks
        old_timestamp = 1000000000  # Very old timestamp
        flag_data = [
            create_mock_flag_detail("permanent-flag", lastUpdateTime=old_timestamp),
            create_mock_flag_detail("regular-flag", lastUpdateTime=old_timestamp),
        ]

        flags_in_code = ["permanent-flag", "regular-flag"]

        # Run threshold check
        result = self.validator.check_all_thresholds_consolidated(flags_in_code, flag_meta_data, flag_data)

        # Should fail because regular-flag is old, but permanent-flag should be skipped
        assert result is False

    def test_permanent_flags_excluded_from_single_threshold_check(self):
        """Test that permanent flags are excluded from single threshold checks."""
        # Create flag metadata
        flag_meta_data = {
            "permanent-flag": create_mock_flag_meta("permanent-flag", ["permanent"]),
            "regular-flag": create_mock_flag_meta("regular-flag", ["frontend"]),
        }

        # Create old flag details
        old_timestamp = 1000000000  # Very old timestamp
        flag_data = [
            create_mock_flag_detail("permanent-flag", lastUpdateTime=old_timestamp),
            create_mock_flag_detail("regular-flag", lastUpdateTime=old_timestamp),
        ]

        flags_in_code = ["permanent-flag", "regular-flag"]

        # Run single threshold check
        failed_flags = self.validator._run_single_threshold_check(flags_in_code, flag_meta_data, flag_data, "90d", "last_update_time", False)

        # Only regular-flag should be in failed flags, permanent-flag should be excluded
        assert len(failed_flags) == 1
        assert failed_flags[0]["flag"] == "regular-flag"

    def test_multiple_permanent_tags(self):
        """Test permanent flag detection with multiple configured permanent tags."""
        validator = ThresholdValidator({"permanent_flags_tag": "permanent,keep,core,critical", "flag_last_modified_threshold": "90d", "debug": False})

        flag_meta_data = {
            "flag1": create_mock_flag_meta("flag1", ["permanent"]),
            "flag2": create_mock_flag_meta("flag2", ["keep"]),
            "flag3": create_mock_flag_meta("flag3", ["core"]),
            "flag4": create_mock_flag_meta("flag4", ["critical"]),
            "flag5": create_mock_flag_meta("flag5", ["deprecated"]),
        }

        assert validator._is_permanent_flag("flag1", flag_meta_data) is True
        assert validator._is_permanent_flag("flag2", flag_meta_data) is True
        assert validator._is_permanent_flag("flag3", flag_meta_data) is True
        assert validator._is_permanent_flag("flag4", flag_meta_data) is True
        assert validator._is_permanent_flag("flag5", flag_meta_data) is False

    def test_permanent_flag_with_missing_metadata(self):
        """Test permanent flag detection with missing metadata."""
        result = self.validator._is_permanent_flag("missing-flag", {})
        assert result is False

    def test_permanent_flag_with_no_tags(self):
        """Test permanent flag detection when flag has no tags."""
        flag_meta = Mock()
        flag_meta._tags = None

        flag_meta_data = {"test-flag": flag_meta}

        result = self.validator._is_permanent_flag("test-flag", flag_meta_data)
        assert result is False

    def test_permanent_flag_tag_extraction_error_handling(self):
        """Test permanent flag detection with tag extraction errors."""
        # Create a problematic tag that will cause an exception
        problematic_tag = Mock()
        problematic_tag.name = Mock(side_effect=Exception("Tag error"))

        flag_meta = Mock()
        flag_meta._tags = [problematic_tag]

        flag_meta_data = {"test-flag": flag_meta}

        # Should not crash and return False
        result = self.validator._is_permanent_flag("test-flag", flag_meta_data)
        assert result is False


@pytest.mark.unit
class TestPermanentFlagIntegration:
    """Integration tests for permanent flag handling across all threshold types."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            "permanent_flags_tag": "permanent",
            "flag_last_modified_threshold": "1s",  # Very short to ensure failure
            "flag_last_traffic_threshold": "1s",
            "flag_at_100_percent_last_modified_threshold": "1s",
            "flag_at_100_percent_last_traffic_threshold": "1s",
            "debug": True,
        }
        self.validator = ThresholdValidator(self.config)

    def test_permanent_flags_excluded_from_all_threshold_types(self):
        """Test that permanent flags are excluded from all 4 threshold check types."""
        # Create mixed flags - some permanent, some not
        flag_meta_data = {
            "permanent-flag-1": create_mock_flag_meta("permanent-flag-1", ["permanent"]),
            "permanent-flag-2": create_mock_flag_meta("permanent-flag-2", ["permanent", "frontend"]),
            "regular-flag-1": create_mock_flag_meta("regular-flag-1", ["frontend"]),
            "regular-flag-2": create_mock_flag_meta("regular-flag-2", ["backend"]),
        }

        # Create very old flag details (would fail all threshold checks)
        very_old_timestamp = 1000000000  # Very old timestamp
        flag_data = [
            create_mock_100_percent_flag_detail(
                "permanent-flag-1", "on", lastUpdateTime=very_old_timestamp, lastTrafficReceivedAt=very_old_timestamp
            ),
            create_mock_100_percent_flag_detail(
                "permanent-flag-2", "on", lastUpdateTime=very_old_timestamp, lastTrafficReceivedAt=very_old_timestamp
            ),
            create_mock_flag_detail("regular-flag-1", lastUpdateTime=very_old_timestamp, lastTrafficReceivedAt=very_old_timestamp),
            create_mock_100_percent_flag_detail("regular-flag-2", "on", lastUpdateTime=very_old_timestamp, lastTrafficReceivedAt=very_old_timestamp),
        ]

        flags_in_code = ["permanent-flag-1", "permanent-flag-2", "regular-flag-1", "regular-flag-2"]

        # Run comprehensive threshold check
        result = self.validator.check_all_thresholds_consolidated(flags_in_code, flag_meta_data, flag_data)

        # Should fail because regular flags are old, but permanent flags should be excluded
        assert result is False

        # Test individual threshold types to ensure permanent flags are excluded from each

        # Test Modified Threshold
        failed_flags = self.validator._run_single_threshold_check(flags_in_code, flag_meta_data, flag_data, "1s", "last_update_time", False)
        failed_flag_names = [f["flag"] for f in failed_flags]
        assert "permanent-flag-1" not in failed_flag_names
        assert "permanent-flag-2" not in failed_flag_names
        assert "regular-flag-1" in failed_flag_names
        assert "regular-flag-2" in failed_flag_names

        # Test Traffic Threshold
        failed_flags = self.validator._run_single_threshold_check(flags_in_code, flag_meta_data, flag_data, "1s", "last_traffic_received_at", False)
        failed_flag_names = [f["flag"] for f in failed_flags]
        assert "permanent-flag-1" not in failed_flag_names
        assert "permanent-flag-2" not in failed_flag_names
        assert "regular-flag-1" in failed_flag_names
        assert "regular-flag-2" in failed_flag_names

        # Test 100% Modified Threshold
        failed_flags = self.validator._run_single_threshold_check(flags_in_code, flag_meta_data, flag_data, "1s", "last_update_time", True)
        failed_flag_names = [f["flag"] for f in failed_flags]
        assert "permanent-flag-1" not in failed_flag_names
        assert "permanent-flag-2" not in failed_flag_names
        # regular-flag-2 should fail (it's at 100% and old)
        assert "regular-flag-2" in failed_flag_names

        # Test 100% Traffic Threshold
        failed_flags = self.validator._run_single_threshold_check(flags_in_code, flag_meta_data, flag_data, "1s", "last_traffic_received_at", True)
        failed_flag_names = [f["flag"] for f in failed_flags]
        assert "permanent-flag-1" not in failed_flag_names
        assert "permanent-flag-2" not in failed_flag_names
        # regular-flag-2 should fail (it's at 100% and no recent traffic)
        assert "regular-flag-2" in failed_flag_names
