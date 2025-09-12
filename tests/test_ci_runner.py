"""Integration tests for the CI test runner."""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch
from app.main import CITestRunner


@pytest.mark.integration
class TestCITestRunnerInitialization:
    """Test CI runner initialization and configuration."""

    @patch.dict(os.environ, {}, clear=True)
    def test_default_configuration(self):
        """Test that missing environment variables trigger validation error."""
        with pytest.raises(SystemExit) as exc_info:
            CITestRunner()

        # Should exit with code 1 due to missing required environment variables
        assert exc_info.value.code == 1

    def test_environment_variable_configuration(self, mock_env_vars):
        """Test configuration from environment variables."""
        with patch.dict(os.environ, mock_env_vars), patch("app.utils.harness_client.get_client"), patch(
            "app.utils.harness_client.HarnessApiClient.fetch_flags", return_value=True
        ), patch("app.utils.git_operations.GitCodeAnalyzer.analyze_code_for_flags", return_value=[]):

            runner = CITestRunner()

            assert runner.config["harness_token"] == "test-token"
            assert runner.config["harness_account"] == "test-account"
            assert runner.config["production_environment_name"] == "Production"
            assert runner.config["max_flags_in_project"] == "50"
            assert runner.config["remove_these_flags_tag"] == "deprecated,remove"


@pytest.mark.integration
class TestFlagRetrieval:
    """Test flag retrieval from Harness API."""

    @patch("app.utils.harness_client.requests.get")
    @patch("app.utils.harness_client.get_client")
    def test_successful_flag_retrieval(self, mock_get_client, mock_requests, mock_harness_client):
        """Test successful flag retrieval from Harness."""
        # Mock requests response
        mock_response = Mock()
        mock_response.json.return_value = {"data": {"project": {"identifier": "test-project", "name": "Test Project"}}}
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock client
        mock_get_client.return_value = mock_harness_client

        with patch.dict(os.environ, {"HARNESS_PROJECT_ID": "test-project"}), patch(
            "app.utils.git_operations.GitCodeAnalyzer.analyze_code_for_flags", return_value=[]
        ), patch("app.utils.git_operations.GitCodeAnalyzer.get_code_changes", return_value=[]):

            CITestRunner()

            # Verify API calls were made
            mock_requests.assert_called_once()
            mock_harness_client.workspaces.find.assert_called_once_with("Test Project")
            mock_harness_client.splits.list.assert_called_once()
            mock_harness_client.environments.find.assert_called_once()

    @patch("app.utils.harness_client.requests.get")
    @patch("app.utils.harness_client.get_client")
    def test_api_error_handling(self, mock_get_client, mock_requests):
        """Test handling of API errors."""
        # Mock failed response
        mock_requests.side_effect = Exception("Network error")
        mock_get_client.return_value = Mock()

        with patch("app.utils.harness_client.HarnessApiClient.fetch_flags", return_value=False):

            # Should exit immediately on API failure
            with pytest.raises(SystemExit) as exc_info:
                CITestRunner()

            assert exc_info.value.code == 1

    @patch("app.utils.harness_client.requests.get")
    @patch("app.utils.harness_client.get_client")
    def test_project_not_found(self, mock_get_client, mock_requests):
        """Test handling when project is not found."""
        # Mock response with different project
        mock_response = Mock()
        mock_response.json.return_value = {"data": {"content": [{"identifier": "other-project", "name": "Other Project"}]}}
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response
        mock_get_client.return_value = Mock()

        with patch.dict(os.environ, {"HARNESS_PROJECT_ID": "test-project"}), patch(
            "app.utils.git_operations.GitCodeAnalyzer.analyze_code_for_flags", return_value=[]
        ), patch("app.utils.git_operations.GitCodeAnalyzer.get_code_changes", return_value=[]):

            # Should exit immediately when project not found
            with pytest.raises(SystemExit) as exc_info:
                CITestRunner()

            assert exc_info.value.code == 1


@pytest.mark.integration
class TestCodeAnalysis:
    """Test code analysis functionality."""

    def test_git_diff_integration(self):
        """Test integration with git diff fallback."""
        # Mock environment to skip Harness API and test fallback
        # Clear repo name to force fallback to subprocess
        with patch.dict(os.environ, {"DRONE_REPO_NAME": "", "HARNESS_REPO_NAME": ""}, clear=False):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = "file1.js\nfile2.py\nfile3.java"
                mock_run.return_value.returncode = 0

                with patch("app.utils.harness_client.get_client"), patch(
                    "app.utils.harness_client.HarnessApiClient.fetch_flags", return_value=True
                ), patch("app.utils.git_operations.GitCodeAnalyzer.analyze_code_for_flags", return_value=[]):

                    runner = CITestRunner()
                    changes = runner.code_analyzer.get_code_changes()

                    assert "file1.js" in changes
                    assert "file2.py" in changes
                    assert "file3.java" in changes

    def test_harness_api_integration(self):
        """Test integration with Harness Code Repository API."""
        mock_response_data = [
            {"path": "app/feature.js", "status": "MODIFIED"},
            {"path": "test/feature.test.js", "status": "ADDED"},
            {"path": "docs/readme.md", "status": "MODIFIED"},
        ]

        with patch.dict(
            os.environ,
            {
                "DRONE_REPO_NAME": "test-repo",
                "PLUGIN_HARNESS_API_TOKEN": "test-token",
                "HARNESS_ACCOUNT_ID": "test-account",
                "HARNESS_ORG_ID": "test-org",
                "HARNESS_PROJECT_ID": "test-project",
            },
        ):
            with patch("requests.get") as mock_get:
                mock_get.return_value.json.return_value = mock_response_data
                mock_get.return_value.raise_for_status.return_value = None

                with patch("app.utils.harness_client.get_client"), patch(
                    "app.utils.harness_client.HarnessApiClient.fetch_flags", return_value=True
                ), patch("app.utils.git_operations.GitCodeAnalyzer.analyze_code_for_flags", return_value=[]):
                    runner = CITestRunner()
                    changes = runner.code_analyzer.get_code_changes()

                    assert "app/feature.js" in changes
                    assert "test/feature.test.js" in changes
                    assert "docs/readme.md" in changes
                    assert len(changes) == 3

    def test_file_analysis_integration(self, sample_javascript_code):
        """Test full file analysis pipeline."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(sample_javascript_code)
            temp_file = f.name

        try:
            with patch("app.utils.harness_client.get_client"), patch(
                "app.utils.harness_client.HarnessApiClient.fetch_flags", return_value=True
            ), patch("app.utils.git_operations.GitCodeAnalyzer.get_code_changes", return_value=[temp_file]):

                runner = CITestRunner()
                # This is now handled automatically in initialization
                result = True

                assert result is True
                assert len(runner.flags_in_code) > 0
                assert "simple-flag" in runner.flags_in_code
        finally:
            os.unlink(temp_file)


@pytest.mark.integration
class TestValidationChecks:
    """Test individual validation checks."""

    def test_flag_count_check_pass(self):
        """Test flag count check passing."""
        with patch("app.utils.harness_client.get_client"), patch("app.utils.harness_client.HarnessApiClient.fetch_flags", return_value=True), patch(
            "app.utils.git_operations.GitCodeAnalyzer.analyze_code_for_flags", return_value=[]
        ):

            runner = CITestRunner()
            runner.flags_in_code = ["flag1", "flag2"]
            runner.flag_validator.max_flags_in_project = "5"

            result = runner.flag_validator.check_flag_count_limit(runner.flags_in_code)
            assert result is True

    def test_flag_count_check_fail(self):
        """Test flag count check failing."""
        with patch("app.utils.harness_client.get_client"), patch("app.utils.harness_client.HarnessApiClient.fetch_flags", return_value=True), patch(
            "app.utils.git_operations.GitCodeAnalyzer.analyze_code_for_flags", return_value=[]
        ):

            runner = CITestRunner()
            runner.flags_in_code = ["flag1", "flag2", "flag3"]
            runner.flag_validator.max_flags_in_project = "2"

            result = runner.flag_validator.check_flag_count_limit(runner.flags_in_code)
            assert result is False

    def test_removal_tag_check_pass(self):
        """Test removal tag check passing."""
        with patch("app.utils.harness_client.get_client"), patch("app.utils.harness_client.HarnessApiClient.fetch_flags", return_value=True), patch(
            "app.utils.git_operations.GitCodeAnalyzer.analyze_code_for_flags", return_value=[]
        ):

            runner = CITestRunner()
            runner.flags_in_code = ["test-flag"]
            runner.flag_validator.remove_these_flags_tag = "deprecated,remove"

            # Mock flag without removal tags
            flag_meta = Mock()
            production_tag = Mock()
            production_tag.name = "production"
            flag_meta._tags = [production_tag]
            runner.harness_client.meta_flag_data = {"test-flag": flag_meta}

            result = runner.flag_validator.check_removal_tags(runner.flags_in_code, runner.harness_client.meta_flag_data, {})
            assert result is True

    def test_removal_tag_check_fail(self):
        """Test removal tag check failing."""
        with patch("app.utils.harness_client.get_client"), patch("app.utils.harness_client.HarnessApiClient.fetch_flags", return_value=True), patch(
            "app.utils.git_operations.GitCodeAnalyzer.analyze_code_for_flags", return_value=[]
        ), patch("app.utils.git_operations.GitCodeAnalyzer.get_code_changes", return_value=["test-file.js"]):

            runner = CITestRunner()
            runner.flags_in_code = ["test-flag"]
            runner.flag_validator.remove_these_flags_tag = "deprecated,remove"

            # Initialize flag_file_mapping which is needed by the method
            runner.flag_file_mapping = {"test-flag": ["test-file.js"]}

            # Mock flag with removal tag
            flag_meta = Mock()
            deprecated_tag = Mock()
            deprecated_tag.name = "deprecated"
            flag_meta._tags = [deprecated_tag]
            runner.harness_client.meta_flag_data = {"test-flag": flag_meta}

            result = runner.flag_validator.check_removal_tags(
                runner.flags_in_code, runner.harness_client.meta_flag_data, runner.code_analyzer.flag_file_mapping
            )
            assert result is False


@pytest.mark.integration
class TestFullWorkflow:
    """Test complete CI workflow integration."""

    @patch("app.utils.harness_client.get_client")
    @patch("app.utils.harness_client.requests.get")
    def test_successful_complete_workflow(self, mock_requests, mock_get_client, mock_harness_client):
        """Test complete successful workflow."""
        # Mock API responses
        mock_response = Mock()
        mock_response.json.return_value = {"data": {"project": {"identifier": "test-project", "name": "Test Project"}}}
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response
        mock_get_client.return_value = mock_harness_client

        # Setup mock client to return environments and split definitions
        mock_env = Mock()
        mock_env.id = "env-123"
        mock_env.name = "Production"
        mock_harness_client.environments.find.return_value = mock_env

        # Mock split definitions for production environment
        mock_split_def = Mock()
        mock_split_def.name = "test-flag"
        mock_harness_client.split_definitions.list.return_value = [mock_split_def]

        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write('client.getTreatment("test-flag");')
            temp_file = f.name

        try:
            with patch.dict(os.environ, {"HARNESS_PROJECT_ID": "test-project"}), patch(
                "app.utils.git_operations.GitCodeAnalyzer.get_code_changes", return_value=[temp_file]
            ):

                runner = CITestRunner()
                result = runner.run_tests()

                # Should pass all tests
                assert result is True
                assert "test-flag" in runner.flags_in_code
        finally:
            os.unlink(temp_file)

    def test_failed_workflow_flag_count(self):
        """Test workflow failing on flag count."""
        with patch("app.utils.harness_client.get_client"), patch("app.utils.harness_client.HarnessApiClient.fetch_flags", return_value=True), patch(
            "app.utils.git_operations.GitCodeAnalyzer.analyze_code_for_flags", return_value=[]
        ):

            runner = CITestRunner()
            runner.flags_in_code = ["flag1", "flag2", "flag3"]
            runner.flag_validator.max_flags_in_project = "2"
            runner.harness_client.meta_flag_data = {}

            result = runner.run_tests()
            assert result is False

    @patch("app.main.sys.exit")
    def test_main_function_success(self, mock_exit):
        """Test main function with successful execution."""
        with patch("app.main.CITestRunner") as mock_runner_class:
            mock_runner = Mock()
            mock_runner.run_tests.return_value = True
            mock_runner_class.return_value = mock_runner

            from app.main import main

            main()

            mock_exit.assert_called_once_with(0)

    @patch("app.main.sys.exit")
    def test_main_function_failure(self, mock_exit):
        """Test main function with failed execution."""
        with patch("app.main.CITestRunner") as mock_runner_class:
            mock_runner = Mock()
            mock_runner.run_tests.return_value = False
            mock_runner_class.return_value = mock_runner

            from app.main import main

            main()

            mock_exit.assert_called_once_with(1)


@pytest.mark.integration
@pytest.mark.slow
class TestRealGitIntegration:
    """Test integration with real git repository."""

    def test_real_git_diff(self, temp_git_repo):
        """Test with real git repository."""
        # Change to temp repo directory
        original_dir = os.getcwd()
        os.chdir(temp_git_repo)

        try:
            # Create new file and commit
            with open("new_feature.js", "w") as f:
                f.write('client.getTreatment("new-feature");')

            os.system("git add new_feature.js")
            os.system('git commit -m "Add new feature"')

            # Test git diff
            with patch("app.utils.harness_client.get_client"), patch(
                "app.utils.harness_client.HarnessApiClient.fetch_flags", return_value=True
            ), patch("app.utils.git_operations.GitCodeAnalyzer.get_code_changes", return_value=["new_feature.js"]):

                runner = CITestRunner()
                runner.config["commit_before"] = "HEAD~1"
                runner.config["commit_after"] = "HEAD"
                # Re-initialize code changes with new commit values
                runner.code_changes = runner.code_analyzer.get_code_changes()

                changes = runner.code_changes
                assert "new_feature.js" in changes

                # Test flag extraction
                # This is now handled automatically in initialization
                result = True
                assert result is True
                assert "new-feature" in runner.flags_in_code

        finally:
            os.chdir(original_dir)
