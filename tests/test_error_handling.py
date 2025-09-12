"""Tests for error handling and edge cases."""

import pytest
import requests
import time
import subprocess
from unittest.mock import Mock, patch, MagicMock
from app.main import CITestRunner


@pytest.mark.unit
class TestNetworkErrorHandling:
    """Test network and API error handling."""

    @patch("app.main.requests.get")
    @patch("app.main.get_client")
    def test_connection_timeout(self, mock_get_client, mock_requests):
        """Test handling of connection timeouts."""
        mock_requests.side_effect = requests.exceptions.Timeout("Connection timeout")
        mock_get_client.return_value = Mock()

        with patch.object(
            CITestRunner, "get_feature_flags_in_code", return_value=True
        ), patch.object(CITestRunner, "get_code_changes", return_value=[]):

            runner = CITestRunner()

            # Should handle timeout gracefully
            assert runner.flag_data == []
            assert runner.metaFlagData == {}

    @patch("app.main.requests.get")
    @patch("app.main.get_client")
    def test_connection_error(self, mock_get_client, mock_requests):
        """Test handling of connection errors."""
        mock_requests.side_effect = requests.exceptions.ConnectionError(
            "Network unreachable"
        )
        mock_get_client.return_value = Mock()

        with patch.object(
            CITestRunner, "get_feature_flags_in_code", return_value=True
        ), patch.object(CITestRunner, "get_code_changes", return_value=[]):

            runner = CITestRunner()

            # Should handle connection error gracefully
            assert runner.flag_data == []
            assert runner.metaFlagData == {}

    @patch("app.main.requests.get")
    @patch("app.main.get_client")
    def test_http_error(self, mock_get_client, mock_requests):
        """Test handling of HTTP errors."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )
        mock_requests.return_value = mock_response
        mock_get_client.return_value = Mock()

        with patch.object(
            CITestRunner, "get_feature_flags_in_code", return_value=True
        ), patch.object(CITestRunner, "get_code_changes", return_value=[]):

            runner = CITestRunner()

            # Should handle HTTP error gracefully
            assert runner.flag_data == []

    @patch("app.main.requests.get")
    @patch("app.main.get_client")
    def test_invalid_json_response(self, mock_get_client, mock_requests):
        """Test handling of invalid JSON responses."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("No JSON object could be decoded")
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response
        mock_get_client.return_value = Mock()

        with patch.object(
            CITestRunner, "get_feature_flags_in_code", return_value=True
        ), patch.object(CITestRunner, "get_code_changes", return_value=[]):

            runner = CITestRunner()

            # Should handle invalid JSON gracefully
            assert runner.flag_data == []

    @patch("app.main.requests.get")
    @patch("app.main.get_client")
    def test_unexpected_response_structure(self, mock_get_client, mock_requests):
        """Test handling of unexpected response structure."""
        mock_response = Mock()
        mock_response.json.return_value = {"unexpected": "structure"}
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response
        mock_get_client.return_value = Mock()

        with patch.object(
            CITestRunner, "get_feature_flags_in_code", return_value=True
        ), patch.object(CITestRunner, "get_code_changes", return_value=[]):

            runner = CITestRunner()

            # Should handle unexpected structure gracefully
            assert runner.flag_data == []


@pytest.mark.unit
class TestSafeDataAccess:
    """Test safe data access patterns."""

    def test_missing_flag_attributes(self):
        """Test handling of missing flag attributes."""
        with patch("app.main.get_client"), patch.object(
            CITestRunner, "get_flags", return_value=True
        ), patch.object(CITestRunner, "get_feature_flags_in_code", return_value=True):

            runner = CITestRunner()
            runner.flags_in_code = ["test-flag"]

            # Create flag detail with missing attributes
            flag_detail = Mock()
            flag_detail.name = "test-flag"
            # Missing _traffic_allocation attribute
            del flag_detail._traffic_allocation
            runner.flag_data = [flag_detail]

            # Should not crash
            result = runner._is_flag_at_100_percent("test-flag")
            assert result is False

    def test_none_default_rule(self):
        """Test handling of None default rule."""
        with patch("app.main.get_client"), patch.object(
            CITestRunner, "get_flags", return_value=True
        ), patch.object(CITestRunner, "get_feature_flags_in_code", return_value=True):

            runner = CITestRunner()
            runner.flags_in_code = ["test-flag"]

            # Create flag detail with None default rule
            flag_detail = Mock()
            flag_detail.name = "test-flag"
            flag_detail._traffic_allocation = 100
            flag_detail._rules = []
            flag_detail._default_rule = None
            runner.flag_data = [flag_detail]

            # Should not crash
            result = runner._is_flag_at_100_percent("test-flag")
            assert result is False

    def test_missing_tag_attributes(self):
        """Test handling of missing tag attributes."""
        with patch("app.main.get_client"), patch.object(
            CITestRunner, "get_flags", return_value=True
        ), patch.object(CITestRunner, "get_feature_flags_in_code", return_value=True):

            runner = CITestRunner()
            runner.flags_in_code = ["test-flag"]
            runner.remove_these_flags_tag = "deprecated"

            # Create flag meta with tags but missing name attribute
            tag_mock = Mock()
            del tag_mock.name  # Remove name attribute

            flag_meta = Mock()
            flag_meta._tags = [tag_mock]
            runner.metaFlagData = {"test-flag": flag_meta}

            # Should handle gracefully
            result = runner.check_if_flags_have_remove_these_tags()
            assert result is True

    def test_threshold_check_with_missing_attributes(self):
        """Test threshold checking with missing timestamp attributes."""
        with patch("app.main.get_client"), patch.object(
            CITestRunner, "get_flags", return_value=True
        ), patch.object(CITestRunner, "get_feature_flags_in_code", return_value=True):

            runner = CITestRunner()
            runner.flags_in_code = ["test-flag"]
            runner.flag_last_modified_threshold = "30d"

            # Create flag detail without timestamp
            flag_detail = Mock()
            flag_detail.name = "test-flag"
            # Missing lastUpdateTime attribute
            del flag_detail.lastUpdateTime
            runner.flag_data = [flag_detail]
            runner.metaFlagData = {}

            # Should handle gracefully
            result = runner.check_flag_last_modified_threshold()
            assert result is True


@pytest.mark.unit
class TestFileHandlingErrors:
    """Test file handling error scenarios."""

    def test_file_not_found(self):
        """Test handling of missing files."""
        with patch("app.main.get_client"), patch.object(
            CITestRunner, "get_flags", return_value=True
        ), patch.object(
            CITestRunner, "get_code_changes", return_value=["missing_file.js"]
        ):

            runner = CITestRunner()

            # Should handle missing file gracefully
            result = runner.get_feature_flags_in_code()
            assert result is True
            assert runner.flags_in_code == []

    def test_unicode_decode_error(self):
        """Test handling of unicode decode errors."""
        import tempfile

        # Create file with invalid UTF-8
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"\xff\xfe invalid utf-8")
            temp_file = f.name

        try:
            with patch("app.main.get_client"), patch.object(
                CITestRunner, "get_flags", return_value=True
            ), patch.object(CITestRunner, "get_code_changes", return_value=[temp_file]):

                runner = CITestRunner()

                # Should handle decode error gracefully
                result = runner.get_feature_flags_in_code()
                assert result is True
                # Should have logged warning but continued
        finally:
            import os

            os.unlink(temp_file)

    def test_git_command_failure(self):
        """Test handling of git command failures."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")

            with patch("app.main.get_client"), patch.object(
                CITestRunner, "get_flags", return_value=True
            ), patch.object(
                CITestRunner, "get_feature_flags_in_code", return_value=True
            ):

                runner = CITestRunner()
                changes = runner.get_code_changes()

                # Should return empty list on git failure
                assert changes == []


@pytest.mark.unit
class TestEdgeCaseValues:
    """Test edge case values and boundary conditions."""

    def test_empty_environment_variables(self):
        """Test handling of empty environment variables."""
        with patch.dict(
            "os.environ",
            {
                "HARNESS_API_TOKEN": "",
                "HARNESS_ACCOUNT_ID": "",
                "PLUGIN_MAX_FLAGS_IN_PROJECT": "",
            },
        ), patch("app.main.get_client"), patch.object(
            CITestRunner, "get_flags", return_value=True
        ), patch.object(
            CITestRunner, "get_feature_flags_in_code", return_value=True
        ):

            runner = CITestRunner()

            # Should handle empty values gracefully
            assert runner.harness_token == ""
            assert runner.harness_account == ""
            assert runner.max_flags_in_project == ""

    def test_invalid_duration_format(self):
        """Test handling of invalid duration formats."""
        with patch("app.main.get_client"), patch.object(
            CITestRunner, "get_flags", return_value=True
        ), patch.object(CITestRunner, "get_feature_flags_in_code", return_value=True):

            runner = CITestRunner()
            runner.flag_last_modified_threshold = "invalid-duration"
            runner.flags_in_code = ["test-flag"]
            runner.metaFlagData = {}

            # Should handle invalid duration gracefully
            result = runner.check_flag_last_modified_threshold()
            assert result is True

    def test_zero_flag_count_limit(self):
        """Test flag count limit of zero."""
        with patch("app.main.get_client"), patch.object(
            CITestRunner, "get_flags", return_value=True
        ), patch.object(CITestRunner, "get_feature_flags_in_code", return_value=True):

            runner = CITestRunner()
            runner.flags_in_code = ["test-flag"]
            runner.max_flags_in_project = "0"

            # Should fail with any flags when limit is 0
            result = runner.check_if_flag_count_exceeds_limit()
            assert result is False

    def test_very_old_timestamps(self):
        """Test handling of very old timestamps."""
        with patch("app.main.get_client"), patch.object(
            CITestRunner, "get_flags", return_value=True
        ), patch.object(CITestRunner, "get_feature_flags_in_code", return_value=True):

            runner = CITestRunner()
            runner.flags_in_code = ["test-flag"]
            runner.flag_last_modified_threshold = "1d"

            # Very old timestamp (year 1970)
            flag_detail = Mock()
            flag_detail.name = "test-flag"
            flag_detail.lastUpdateTime = 0
            runner.flag_data = [flag_detail]
            runner.metaFlagData = {}

            # Should detect as stale
            result = runner.check_flag_last_modified_threshold()
            assert result is False

    def test_future_timestamps(self):
        """Test handling of future timestamps."""
        with patch("app.main.get_client"), patch.object(
            CITestRunner, "get_flags", return_value=True
        ), patch.object(CITestRunner, "get_feature_flags_in_code", return_value=True):

            runner = CITestRunner()
            runner.flags_in_code = ["test-flag"]
            runner.flag_last_modified_threshold = "1d"

            # Future timestamp
            future_time = int(time.time()) + 86400  # 1 day in future
            flag_detail = Mock()
            flag_detail.name = "test-flag"
            flag_detail.lastUpdateTime = future_time
            runner.flag_data = [flag_detail]
            runner.metaFlagData = {}

            # Should pass (not considered stale)
            result = runner.check_flag_last_modified_threshold()
            assert result is True


@pytest.mark.unit
class TestExceptionHandling:
    """Test exception handling in various scenarios."""

    def test_client_initialization_failure(self):
        """Test handling of client initialization failure."""
        with patch("app.main.get_client") as mock_get_client:
            mock_get_client.side_effect = Exception("Client initialization failed")

            with patch.object(
                CITestRunner, "get_feature_flags_in_code", return_value=True
            ):
                # Should raise the exception (not handled at this level)
                with pytest.raises(Exception, match="Client initialization failed"):
                    CITestRunner()

    def test_tag_processing_exception(self):
        """Test handling of exceptions during tag processing."""
        with patch("app.main.get_client"), patch.object(
            CITestRunner, "get_flags", return_value=True
        ), patch.object(CITestRunner, "get_feature_flags_in_code", return_value=True):

            runner = CITestRunner()
            runner.flags_in_code = ["test-flag"]
            runner.remove_these_flags_tag = "deprecated"

            # Create flag meta with tags that raise exception
            flag_meta = Mock()
            flag_meta._tags = Mock()
            flag_meta._tags.map.side_effect = Exception("Tag processing error")
            runner.metaFlagData = {"test-flag": flag_meta}

            # Should handle exception gracefully
            result = runner.check_if_flags_have_remove_these_tags()
            assert result is True

    def test_100_percent_check_exception(self):
        """Test handling of exceptions during 100% check."""
        with patch("app.main.get_client"), patch.object(
            CITestRunner, "get_flags", return_value=True
        ), patch.object(CITestRunner, "get_feature_flags_in_code", return_value=True):

            runner = CITestRunner()

            # Create flag detail that raises exception
            flag_detail = Mock()
            flag_detail.name = "test-flag"
            flag_detail._traffic_allocation = Mock(
                side_effect=Exception("Allocation error")
            )
            runner.flag_data = [flag_detail]

            # Should handle exception gracefully
            result = runner._is_flag_at_100_percent("test-flag")
            assert result is False

    def test_test_execution_exception(self):
        """Test handling of exceptions during test execution."""
        with patch("app.main.get_client"), patch.object(
            CITestRunner, "get_flags", return_value=True
        ), patch.object(CITestRunner, "get_feature_flags_in_code", return_value=True):

            runner = CITestRunner()

            # Mock a test method that raises exception
            def failing_test():
                raise Exception("Test execution error")

            test_results = []
            result = runner._run_test(failing_test, "failing test", test_results)

            # Should handle exception and return False
            assert result is False
            assert len(test_results) == 0  # No result added on exception


@pytest.mark.unit
class TestBoundaryConditions:
    """Test boundary conditions and limits."""

    def test_maximum_file_count(self):
        """Test handling of large number of changed files."""
        large_file_list = [f"file_{i}.js" for i in range(1000)]

        with patch("app.main.get_client"), patch.object(
            CITestRunner, "get_flags", return_value=True
        ), patch.object(CITestRunner, "get_code_changes", return_value=large_file_list):

            # Mock file reading to avoid actual file I/O
            with patch("builtins.open", side_effect=FileNotFoundError):
                runner = CITestRunner()
                result = runner.get_feature_flags_in_code()

                # Should handle large file count gracefully
                assert result is True

    def test_very_large_flag_names(self):
        """Test handling of very large flag names."""
        large_flag = "x" * 10000  # Very long flag name

        code = f'client.getTreatment("{large_flag}");'

        from app.main import extract_flags_ast_javascript

        flags = extract_flags_ast_javascript(code)

        # Should handle large flag names
        assert large_flag in flags

    def test_many_flags_in_single_file(self):
        """Test handling of many flags in a single file."""
        # Create code with many flag calls
        flag_calls = [f'client.getTreatment("flag_{i}");' for i in range(100)]
        code = "\n".join(flag_calls)

        from app.main import extract_flags_ast_javascript

        flags = extract_flags_ast_javascript(code)

        # Should extract all flags
        assert len(flags) == 100
        for i in range(100):
            assert f"flag_{i}" in flags
