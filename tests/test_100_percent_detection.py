"""Tests for 100% flag detection logic using proper Split.io API structure."""

import pytest
from unittest.mock import Mock
from app.validators.threshold_checks import ThresholdValidator
from tests.test_utils import (
    create_mock_flag_meta,
    create_mock_100_percent_flag_detail,
    create_mock_100_percent_flag_with_rules,
    create_mock_mixed_treatment_flag,
    create_mock_rule_with_buckets,
    create_mock_flag_detail,
)


@pytest.mark.unit
class TestOneHundredPercentDetection:
    """Test 100% flag detection with proper Split.io API structure."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"permanent_flags_tag": "permanent", "flag_last_modified_threshold": "90d", "debug": True}
        self.validator = ThresholdValidator(self.config)

    def test_100_percent_flag_no_rules_default_only(self):
        """Test 100% detection for flag with no rules, only default rule."""
        flag_detail = create_mock_100_percent_flag_detail("test-flag", "enabled")

        result = self.validator._is_flag_at_100_percent("test-flag", [flag_detail])
        assert result is True

    def test_100_percent_flag_with_consistent_rules(self):
        """Test 100% detection for flag with rules that all have same treatment."""
        flag_detail = create_mock_100_percent_flag_with_rules("test-flag", "enabled", num_rules=3)

        result = self.validator._is_flag_at_100_percent("test-flag", [flag_detail])
        assert result is True

    def test_not_100_percent_mixed_treatments(self):
        """Test that flags with mixed treatments are NOT considered 100%."""
        flag_detail = create_mock_mixed_treatment_flag("test-flag")

        result = self.validator._is_flag_at_100_percent("test-flag", [flag_detail])
        assert result is False

    def test_not_100_percent_traffic_allocation(self):
        """Test that flags without 100% traffic allocation are not 100%."""
        flag_detail = create_mock_flag_detail("test-flag", traffic_allocation=50)

        result = self.validator._is_flag_at_100_percent("test-flag", [flag_detail])
        assert result is False

    def test_100_percent_split_bucket_not_100_percent(self):
        """Test that rules with split buckets are NOT considered 100%."""
        flag_detail = Mock()
        flag_detail.name = "test-flag"
        flag_detail._traffic_allocation = 100

        # Create rule with split buckets (50/50)
        rule = create_mock_rule_with_buckets([{"treatment": "enabled", "size": 50}, {"treatment": "disabled", "size": 50}])
        flag_detail._rules = [rule]

        # Default rule
        default_rule_item = Mock()
        default_rule_item._size = 100
        default_rule_item._treatment = "enabled"
        flag_detail._default_rule = [default_rule_item]

        result = self.validator._is_flag_at_100_percent("test-flag", [flag_detail])
        assert result is False

    def test_100_percent_partial_allocation_rule(self):
        """Test that rules with partial allocation are NOT considered 100%."""
        flag_detail = Mock()
        flag_detail.name = "test-flag"
        flag_detail._traffic_allocation = 100

        # Create rule with only 80% allocation
        rule = create_mock_rule_with_buckets([{"treatment": "enabled", "size": 80}])
        flag_detail._rules = [rule]

        # Default rule
        default_rule_item = Mock()
        default_rule_item._size = 100
        default_rule_item._treatment = "enabled"
        flag_detail._default_rule = [default_rule_item]

        result = self.validator._is_flag_at_100_percent("test-flag", [flag_detail])
        assert result is False

    def test_100_percent_no_default_rule_not_100_percent(self):
        """Test that flags with rules but no default rule are NOT 100%."""
        flag_detail = Mock()
        flag_detail.name = "test-flag"
        flag_detail._traffic_allocation = 100

        # Create rule with 100% allocation
        rule = create_mock_rule_with_buckets([{"treatment": "enabled", "size": 100}])
        flag_detail._rules = [rule]

        # No default rule
        flag_detail._default_rule = []

        result = self.validator._is_flag_at_100_percent("test-flag", [flag_detail])
        assert result is False

    def test_100_percent_default_rule_not_100_percent(self):
        """Test that flags with rules but default rule not 100% are NOT 100%."""
        flag_detail = Mock()
        flag_detail.name = "test-flag"
        flag_detail._traffic_allocation = 100

        # Create rule with 100% allocation
        rule = create_mock_rule_with_buckets([{"treatment": "enabled", "size": 100}])
        flag_detail._rules = [rule]

        # Default rule with only 50% allocation
        default_rule_item = Mock()
        default_rule_item._size = 50
        default_rule_item._treatment = "enabled"
        flag_detail._default_rule = [default_rule_item]

        result = self.validator._is_flag_at_100_percent("test-flag", [flag_detail])
        assert result is False

    def test_100_percent_complex_scenario_all_consistent(self):
        """Test complex scenario with multiple rules all having consistent treatment."""
        flag_detail = Mock()
        flag_detail.name = "test-flag"
        flag_detail._traffic_allocation = 100

        # Create multiple rules all with "premium" treatment
        rules = [
            create_mock_rule_with_buckets([{"treatment": "premium", "size": 100}]),  # Premium users
            create_mock_rule_with_buckets([{"treatment": "premium", "size": 100}]),  # Beta users
            create_mock_rule_with_buckets([{"treatment": "premium", "size": 100}]),  # Enterprise users
        ]
        flag_detail._rules = rules

        # Default rule also has "premium" treatment
        default_rule_item = Mock()
        default_rule_item._size = 100
        default_rule_item._treatment = "premium"
        flag_detail._default_rule = [default_rule_item]

        result = self.validator._is_flag_at_100_percent("test-flag", [flag_detail])
        assert result is True

    def test_100_percent_complex_scenario_inconsistent_treatments(self):
        """Test complex scenario with rules having different treatments."""
        flag_detail = Mock()
        flag_detail.name = "test-flag"
        flag_detail._traffic_allocation = 100

        # Create rules with different treatments
        rules = [
            create_mock_rule_with_buckets([{"treatment": "premium", "size": 100}]),  # Premium users get premium
            create_mock_rule_with_buckets([{"treatment": "standard", "size": 100}]),  # Basic users get standard
            create_mock_rule_with_buckets([{"treatment": "premium", "size": 100}]),  # Enterprise users get premium
        ]
        flag_detail._rules = rules

        # Default rule
        default_rule_item = Mock()
        default_rule_item._size = 100
        default_rule_item._treatment = "premium"
        flag_detail._default_rule = [default_rule_item]

        result = self.validator._is_flag_at_100_percent("test-flag", [flag_detail])
        assert result is False

    def test_flag_not_found(self):
        """Test behavior when flag is not found in flag_data."""
        flag_detail = create_mock_100_percent_flag_detail("other-flag", "enabled")

        result = self.validator._is_flag_at_100_percent("missing-flag", [flag_detail])
        assert result is False

    def test_error_handling_malformed_buckets(self):
        """Test error handling with malformed bucket data."""
        flag_detail = Mock()
        flag_detail.name = "test-flag"
        flag_detail._traffic_allocation = 100

        # Create rule with malformed buckets that will cause exceptions
        rule = Mock()
        rule._buckets = [Mock(side_effect=Exception("Bucket error"))]
        flag_detail._rules = [rule]

        # Default rule
        default_rule_item = Mock()
        default_rule_item._size = 100
        default_rule_item._treatment = "enabled"
        flag_detail._default_rule = [default_rule_item]

        # Should not crash and return False
        result = self.validator._is_flag_at_100_percent("test-flag", [flag_detail])
        assert result is False


@pytest.mark.unit
class TestOneHundredPercentIntegrationWithThresholds:
    """Integration tests for 100% detection with threshold validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            "permanent_flags_tag": "permanent",
            "flag_at_100_percent_last_modified_threshold": "1s",  # Very short
            "flag_at_100_percent_last_traffic_threshold": "1s",
            "debug": True,
        }
        self.validator = ThresholdValidator(self.config)

    def test_100_percent_threshold_check_integration(self):
        """Test that 100% flags are properly identified in threshold checks."""
        # Create flag metadata
        flag_meta_data = {
            "regular-flag": create_mock_flag_meta("regular-flag", ["frontend"]),
            "hundred-percent-flag": create_mock_flag_meta("hundred-percent-flag", ["backend"]),
        }

        # Create flag data - one 100%, one not
        old_timestamp = 1000000000  # Very old timestamp
        flag_data = [
            create_mock_flag_detail("regular-flag", lastUpdateTime=old_timestamp, traffic_allocation=50),
            create_mock_100_percent_flag_detail("hundred-percent-flag", "enabled", lastUpdateTime=old_timestamp),
        ]

        flags_in_code = ["regular-flag", "hundred-percent-flag"]

        # Run 100% modified threshold check
        failed_flags = self.validator._run_single_threshold_check(flags_in_code, flag_meta_data, flag_data, "1s", "last_update_time", True)

        # Only the 100% flag should be in failed flags
        failed_flag_names = [f["flag"] for f in failed_flags]
        assert "hundred-percent-flag" in failed_flag_names
        assert "regular-flag" not in failed_flag_names  # Not 100%, so excluded from 100% check
        assert len(failed_flags) == 1
