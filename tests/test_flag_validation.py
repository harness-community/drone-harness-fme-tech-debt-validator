"""Tests for flag validation functionality."""

import pytest
from unittest.mock import Mock
from app.validators.flag_checks import FlagValidator
from tests.test_utils import create_mock_flag_meta


@pytest.mark.unit
class TestFlagValidator:
    """Test FlagValidator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"remove_these_flags_tag": "deprecated,remove", "max_flags_in_project": "5", "debug": True}
        self.validator = FlagValidator(self.config)

    def test_tag_extraction_with_simple_tags(self):
        """Test tag extraction with simple tag names."""
        # Create mock tags with simple names - configure the name attribute properly
        tag1 = Mock()
        tag1.name = "permanent"
        tag2 = Mock()
        tag2.name = "remove"
        tag3 = Mock()
        tag3.name = "frontend"

        mock_tags = [tag1, tag2, tag3]

        # Test the tag extraction method
        tag_names = self.validator._extract_all_tag_names(mock_tags)

        assert "permanent" in tag_names
        assert "remove" in tag_names
        assert "frontend" in tag_names
        assert len(tag_names) == 3

    def test_tag_extraction_with_json_tags(self):
        """Test tag extraction with JSON-formatted tag names."""
        # Create mock tags with JSON names
        tag1 = Mock()
        tag1.name = '{"name": "permanent", "color": "blue"}'
        tag2 = Mock()
        tag2.name = "{'name': 'remove', 'color': 'red'}"
        tag3 = Mock()
        tag3.name = "simple-tag"

        mock_tags = [tag1, tag2, tag3]

        tag_names = self.validator._extract_all_tag_names(mock_tags)

        assert "permanent" in tag_names
        assert "remove" in tag_names
        assert "simple-tag" in tag_names

    def test_tag_extraction_with_alternative_attributes(self):
        """Test tag extraction with various attribute names."""
        # Mock tags with different attribute names
        tag1 = Mock()
        tag1.name = None
        tag1.tag = "deprecated"
        tag1.label = None
        tag1.value = None

        tag2 = Mock()
        tag2.name = None
        tag2.tag = None
        tag2.label = "remove"
        tag2.value = None

        tag3 = Mock()
        tag3.name = None
        tag3.tag = None
        tag3.label = None
        tag3.value = "frontend"

        tag_names = self.validator._extract_all_tag_names([tag1, tag2, tag3])

        assert "deprecated" in tag_names
        assert "remove" in tag_names
        assert "frontend" in tag_names

    def test_tag_extraction_error_handling(self):
        """Test tag extraction with error conditions."""

        # Mock tags that will cause exceptions during iteration
        def problematic_iterable():
            raise Exception("Tag error")
            yield

        tag_names = self.validator._extract_all_tag_names(problematic_iterable())

        assert tag_names == ["<unable to read tags>"]

    def test_removal_tag_detection_positive(self):
        """Test detection of flags with removal tags."""
        # Create flag metadata with removal tag
        flag_meta_data = {"test-flag": create_mock_flag_meta("test-flag", ["frontend", "remove"])}

        result = self.validator.check_removal_tags(["test-flag"], flag_meta_data, {"test-flag": ["test.js"]})

        assert result is False  # Should fail when removal tag found

    def test_removal_tag_detection_negative(self):
        """Test that flags without removal tags pass."""
        # Create flag metadata without removal tag
        flag_meta_data = {"test-flag": create_mock_flag_meta("test-flag", ["frontend", "permanent"])}

        result = self.validator.check_removal_tags(["test-flag"], flag_meta_data, {"test-flag": ["test.js"]})

        assert result is True  # Should pass when no removal tag

    def test_removal_tag_case_insensitive(self):
        """Test that removal tag detection is case insensitive."""
        # Test various case combinations
        flag_meta_data = {
            "flag1": create_mock_flag_meta("flag1", ["REMOVE"]),
            "flag2": create_mock_flag_meta("flag2", ["Deprecated"]),
            "flag3": create_mock_flag_meta("flag3", ["permanent"]),
        }

        # Configure with lowercase removal tags
        validator = FlagValidator({"remove_these_flags_tag": "remove,deprecated", "max_flags_in_project": "10", "debug": False})

        # flag1 should fail (REMOVE matches remove)
        result1 = validator.check_removal_tags(["flag1"], flag_meta_data, {})
        assert result1 is False

        # flag3 should pass (permanent doesn't match)
        result3 = validator.check_removal_tags(["flag3"], flag_meta_data, {})
        assert result3 is True

    def test_flag_count_limit_exceeded(self):
        """Test flag count limit enforcement."""
        flags = ["flag1", "flag2", "flag3", "flag4", "flag5", "flag6"]

        result = self.validator.check_flag_count_limit(flags)

        assert result is False  # Should fail with 6 flags (limit is 5)

    def test_flag_count_limit_within_bounds(self):
        """Test flag count within limits."""
        flags = ["flag1", "flag2", "flag3"]

        result = self.validator.check_flag_count_limit(flags)

        assert result is True  # Should pass with 3 flags (limit is 5)

    def test_flag_count_limit_disabled(self):
        """Test flag count limit when disabled."""
        validator = FlagValidator({"remove_these_flags_tag": "", "max_flags_in_project": "-1", "debug": False})  # Disabled

        flags = ["flag1", "flag2", "flag3", "flag4", "flag5", "flag6", "flag7", "flag8"]

        result = validator.check_flag_count_limit(flags)

        assert result is True  # Should pass when limit is disabled

    def test_empty_flags_list(self):
        """Test validation with empty flags list."""
        result = self.validator.check_removal_tags([], {}, {})
        assert result is True

        result = self.validator.check_flag_count_limit([])
        assert result is True

    def test_missing_flag_metadata(self):
        """Test handling of flags with missing metadata."""
        # Flag exists in code but not in metadata
        result = self.validator.check_removal_tags(["missing-flag"], {}, {"missing-flag": ["test.js"]})  # Empty metadata

        assert result is True  # Should pass when metadata is missing

    def test_flags_without_tags(self):
        """Test handling of flags with no tags."""
        flag_meta = Mock()
        flag_meta._tags = None  # No tags

        flag_meta_data = {"test-flag": flag_meta}

        result = self.validator.check_removal_tags(["test-flag"], flag_meta_data, {"test-flag": ["test.js"]})

        assert result is True  # Should pass when no tags exist


@pytest.mark.unit
class TestTagExtractionHelpers:
    """Test tag extraction helper methods in isolation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = FlagValidator({"remove_these_flags_tag": "remove", "max_flags_in_project": "5", "debug": False})

    def test_extract_tag_name_simple(self):
        """Test simple tag name extraction."""
        tag = Mock()
        tag.name = "simple-tag"
        tag.tag = None
        tag.label = None
        tag.value = None
        result = self.validator._extract_tag_name(tag)
        assert result == "simple-tag"

    def test_extract_tag_name_fallback_attributes(self):
        """Test tag name extraction with fallback attributes."""
        # Test 'tag' attribute fallback
        tag = Mock()
        tag.name = None
        tag.tag = "fallback-tag"
        tag.label = None
        tag.value = None
        result = self.validator._extract_tag_name(tag)
        assert result == "fallback-tag"

        # Test 'label' attribute fallback
        tag = Mock()
        tag.name = None
        tag.tag = None
        tag.label = "label-tag"
        tag.value = None
        result = self.validator._extract_tag_name(tag)
        assert result == "label-tag"

        # Test 'value' attribute fallback
        tag = Mock()
        tag.name = None
        tag.tag = None
        tag.label = None
        tag.value = "value-tag"
        result = self.validator._extract_tag_name(tag)
        assert result == "value-tag"

    def test_extract_tag_name_json_parsing(self):
        """Test JSON tag name parsing."""
        # Valid JSON with double quotes
        tag = Mock()
        tag.name = '{"name": "json-tag", "color": "blue"}'
        result = self.validator._extract_tag_name(tag)
        assert result == "json-tag"

        # Valid JSON with single quotes (converted to double)
        tag = Mock()
        tag.name = "{'name': 'single-quote-tag', 'color': 'red'}"
        result = self.validator._extract_tag_name(tag)
        assert result == "single-quote-tag"

        # Invalid JSON should return original string
        tag = Mock()
        tag.name = '{"invalid": json}'
        result = self.validator._extract_tag_name(tag)
        assert result == '{"invalid": json}'

    def test_extract_tag_name_str_fallback(self):
        """Test string conversion fallback."""
        tag = Mock()
        tag.name = None
        tag.tag = None
        tag.label = None
        tag.value = None
        tag.__str__ = Mock(return_value="str-tag")

        result = self.validator._extract_tag_name(tag)
        assert result == "str-tag"
