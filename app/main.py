#!/usr/bin/env python3

import os
import sys
import logging
from typing import Dict, List

from formatters import ErrorMessageFormatter
from utils import HarnessApiClient, GitCodeAnalyzer
from validators import FlagValidator, ThresholdValidator

# Configure logging
debug_enabled = os.getenv("PLUGIN_DEBUG", "false").lower() in ("true", "1", "yes")
log_level = logging.DEBUG if debug_enabled else logging.INFO
logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CITestRunner:
    """Orchestrates feature flag CI testing workflow."""

    def __init__(self):
        # Extract configuration from environment
        self.config = self._extract_config()

        # Validate required configuration
        if not self._validate_configuration():
            sys.exit(1)

        # Initialize components
        self.harness_client = HarnessApiClient(self.config)
        self.code_analyzer = GitCodeAnalyzer(self.config)
        self.flag_validator = FlagValidator(self.config)
        self.threshold_validator = ThresholdValidator(self.config)

        # Initialize data - will be populated by separate method calls
        if not self.harness_client.fetch_flags():
            logger.error("Failed to fetch flags from Harness - cannot proceed with testing")
            sys.exit(1)

        # Get code changes and analyze for flags
        self.code_changes = self.code_analyzer.get_code_changes()
        self.flags_in_code = self.code_analyzer.analyze_code_for_flags(self.code_changes)

        if not self.flags_in_code:
            logger.info("No feature flags found in code changes")

    def _extract_config(self) -> Dict[str, str]:
        """Extract configuration from environment variables."""
        return {
            "commit_before": os.getenv("DRONE_COMMIT_BEFORE", "HEAD"),
            "commit_after": os.getenv("DRONE_COMMIT_AFTER", "HEAD"),
            "api_base_url": os.getenv("API_BASE_URL", "https://app.harness.io"),
            "harness_token": os.getenv("PLUGIN_HARNESS_API_TOKEN", "none"),
            "harness_account": os.getenv("HARNESS_ACCOUNT_ID", "none"),
            "harness_org": os.getenv("HARNESS_ORG_ID", "none"),
            "harness_project": os.getenv("HARNESS_PROJECT_ID", "none"),
            "production_environment_name": os.getenv("PLUGIN_PRODUCTION_ENVIRONMENT_NAME", "Production"),
            "permanent_flags_tag": os.getenv("PLUGIN_TAG_PERMANENT_FLAGS", ""),
            "remove_these_flags_tag": os.getenv("PLUGIN_TAG_REMOVE_THESE_FLAGS", ""),
            "max_flags_in_project": os.getenv("PLUGIN_MAX_FLAGS_IN_PROJECT", "-1"),
            "flag_last_modified_threshold": os.getenv("PLUGIN_FLAG_LAST_MODIFIED_THRESHOLD", "-1"),
            "flag_last_traffic_threshold": os.getenv("PLUGIN_FLAG_LAST_TRAFFIC_THRESHOLD", "-1"),
            "flag_at_100_percent_last_modified_threshold": os.getenv("PLUGIN_FLAG_AT_100_PERCENT_LAST_MODIFIED_THRESHOLD", "-1"),
            "flag_at_100_percent_last_traffic_threshold": os.getenv("PLUGIN_FLAG_AT_100_PERCENT_LAST_TRAFFIC_THRESHOLD", "-1"),
            "debug": os.getenv("PLUGIN_DEBUG", "false").lower() in ("true", "1", "yes"),
        }

    def _validate_configuration(self) -> bool:
        """Validate required environment variables and configuration"""
        missing_required = []
        optional_vars = []

        # Check required variables for Harness API
        harness_vars = {
            "PLUGIN_HARNESS_API_TOKEN": self.config["harness_token"],
            "HARNESS_ACCOUNT_ID": self.config["harness_account"],
            "HARNESS_PROJECT_ID": self.config["harness_project"],
        }

        # Check required variables for Drone CI
        drone_vars = {
            "DRONE_COMMIT_BEFORE": self.config["commit_before"],
            "DRONE_COMMIT_AFTER": self.config["commit_after"],
        }

        for var_name, var_value in harness_vars.items():
            if var_value == "none" or not var_value:
                missing_required.append(var_name)

        for var_name, var_value in drone_vars.items():
            if var_value == "HEAD":  # Default value means not set
                missing_required.append(var_name)

        # List optional variables for user information
        if self.config["remove_these_flags_tag"] == "":
            optional_vars.append("PLUGIN_TAG_REMOVE_THESE_FLAGS (for tag-based flag removal)")

        if self.config["permanent_flags_tag"] == "":
            optional_vars.append("PLUGIN_TAG_PERMANENT_FLAGS (to exclude flags from stale checks)")

        if self.config["max_flags_in_project"] == "-1":
            optional_vars.append("PLUGIN_MAX_FLAGS_IN_PROJECT (for flag count limits)")

        if self.config["flag_last_modified_threshold"] == "-1":
            optional_vars.append("PLUGIN_FLAG_LAST_MODIFIED_THRESHOLD (for stale flag detection)")

        if self.config["flag_last_traffic_threshold"] == "-1":
            optional_vars.append("PLUGIN_FLAG_LAST_TRAFFIC_THRESHOLD (for unused flag detection)")

        if self.config["flag_at_100_percent_last_modified_threshold"] == "-1":
            optional_vars.append("PLUGIN_FLAG_AT_100_PERCENT_LAST_MODIFIED_THRESHOLD (for 100% flag staleness)")

        if self.config["flag_at_100_percent_last_traffic_threshold"] == "-1":
            optional_vars.append("PLUGIN_FLAG_AT_100_PERCENT_LAST_TRAFFIC_THRESHOLD (for 100% flag traffic)")

        if missing_required:
            error_msg = ErrorMessageFormatter.format_configuration_error(missing_required, optional_vars)
            logger.error(error_msg)
            return False

        return True

    def _run_test(self, test_method, test_name: str, test_results: List[Dict]) -> bool:
        """Helper method to run a single test and handle logging/results"""
        try:
            success = test_method()
            if success:
                logger.info(f"✅ {test_name} passed")
                test_results.append({"test": test_name, "success": True})
            else:
                logger.error(f"❌ {test_name} failed")
                test_results.append({"test": test_name, "success": False})
            return success
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {e}")
            test_results.append({"test": test_name, "success": False, "error": str(e)})
            return False

    def run_tests(self) -> bool:
        """Run all tests and return overall success status"""
        logger.info("Starting CI test run...")
        logger.info("Configuration:")
        logger.info(f"  API Base URL: {self.config['api_base_url']}")
        logger.info(f"  Feature Flags in Code: {self.flags_in_code}")
        logger.info(f"  Feature Flags in Harness: {len(self.harness_client.flag_data)} total")
        logger.info(f"  Commit Hashes: {self.config['commit_before']} -> {self.config['commit_after']}")

        test_results = []
        all_tests_passed = True

        # Define all tests to run
        tests = [
            (
                lambda: self.flag_validator.check_removal_tags(
                    self.flags_in_code, self.harness_client.meta_flag_data, self.code_analyzer.flag_file_mapping
                ),
                "Feature Flag removal tag check",
            ),
            (
                lambda: self.flag_validator.check_flag_count_limit(self.flags_in_code),
                "Feature Flag count check",
            ),
            (
                lambda: self.threshold_validator.check_last_modified_threshold(
                    self.flags_in_code, self.harness_client.meta_flag_data, self.harness_client.flag_data
                ),
                "Feature Flag last modified threshold check",
            ),
            (
                lambda: self.threshold_validator.check_last_traffic_threshold(
                    self.flags_in_code, self.harness_client.meta_flag_data, self.harness_client.flag_data
                ),
                "Feature Flag last traffic threshold check",
            ),
            (
                lambda: self.threshold_validator.check_last_modified_threshold_100_percent(
                    self.flags_in_code, self.harness_client.meta_flag_data, self.harness_client.flag_data
                ),
                "Feature Flag last modified threshold check for 100 percent flags",
            ),
            (
                lambda: self.threshold_validator.check_last_traffic_threshold_100_percent(
                    self.flags_in_code, self.harness_client.meta_flag_data, self.harness_client.flag_data
                ),
                "Feature Flag last traffic threshold check for 100 percent flags",
            ),
        ]

        # Run all tests
        for test_method, test_name in tests:
            if not self._run_test(test_method, test_name, test_results):
                all_tests_passed = False

        # Print summary
        logger.info("=" * 50)
        logger.info("TEST SUMMARY")
        logger.info("=" * 50)

        passed_tests = sum(1 for result in test_results if result["success"])
        total_tests = len(test_results)

        logger.info(f"All Tests: {passed_tests}/{total_tests} passed")
        logger.info(f"Overall Result: {'✅ PASS' if all_tests_passed else '❌ FAIL'}")

        return all_tests_passed


def main():
    """Main entry point for the CI test script"""
    logger.info("CI Test Runner starting...")

    runner = CITestRunner()
    success = runner.run_tests()

    if success:
        logger.info("All tests passed! Exiting with code 0")
        sys.exit(0)
    else:
        logger.error("One or more tests failed! Exiting with code 1")
        sys.exit(1)


if __name__ == "__main__":
    main()
