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

    def _filter_valid_flags(self, flags_in_code: List[str]) -> List[str]:
        """Filter flags_in_code to only include actual flags that exist in Harness.

        This removes non-flag arguments like user IDs that are also extracted
        from flag evaluation method calls.
        """
        valid_flags = []

        # Get all known flag names from both meta data and flag data
        known_flag_names = set()

        # Add flags from meta flag data (if available)
        if hasattr(self.harness_client, "meta_flag_data") and self.harness_client.meta_flag_data:
            known_flag_names.update(self.harness_client.meta_flag_data.keys())

        # Add flags from flag data (if available) - flag_data is a list of objects
        if hasattr(self.harness_client, "flag_data") and self.harness_client.flag_data:
            for flag_obj in self.harness_client.flag_data:
                flag_name = getattr(flag_obj, "name", None)
                if flag_name:
                    known_flag_names.add(flag_name)

        # Filter flags_in_code to only include known flags
        for flag in flags_in_code:
            if flag in known_flag_names:
                valid_flags.append(flag)
            else:
                logger.debug(f"Filtering out non-flag argument: '{flag}'")

        logger.info(f"Filtered flags: {len(flags_in_code)} total -> {len(valid_flags)} valid flags")
        return valid_flags

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

        # Filter flags to only include actual flags (removes user IDs and other arguments)
        filtered_flags = self._filter_valid_flags(self.flags_in_code)
        logger.info(f"  Validated Feature Flags: {filtered_flags}")

        if debug_enabled:
            logger.debug("=== Test Configuration Summary ===")
            logger.debug(f"Flag removal tags: '{self.config.get('remove_these_flags_tag', 'NOT SET')}'")
            logger.debug(f"Permanent flags tags: '{self.config.get('permanent_flags_tag', 'NOT SET')}'")
            logger.debug(f"Max flags in project: '{self.config.get('max_flags_in_project', 'NOT SET')}'")
            logger.debug(f"Flag last modified threshold: '{self.config.get('flag_last_modified_threshold', 'NOT SET')}'")
            logger.debug(f"Flag last traffic threshold: '{self.config.get('flag_last_traffic_threshold', 'NOT SET')}'")
            logger.debug(f"100% flag modified threshold: '{self.config.get('flag_at_100_percent_last_modified_threshold', 'NOT SET')}'")
            logger.debug(f"100% flag traffic threshold: '{self.config.get('flag_at_100_percent_last_traffic_threshold', 'NOT SET')}'")
            logger.debug("===================================")

        test_results = []
        all_tests_passed = True

        # Define all tests to run - use filtered_flags instead of self.flags_in_code
        tests = [
            (
                lambda: self.flag_validator.check_removal_tags(
                    filtered_flags, self.harness_client.meta_flag_data, self.code_analyzer.flag_file_mapping
                ),
                "Feature Flag removal tag check",
            ),
            (
                lambda: self.flag_validator.check_flag_count_limit(filtered_flags),
                "Feature Flag count check",
            ),
            (
                lambda: self.threshold_validator.check_all_thresholds_consolidated(
                    filtered_flags, self.harness_client.meta_flag_data, self.harness_client.flag_data
                ),
                "Feature Flag comprehensive threshold check",
            ),
        ]

        # Run all tests
        if debug_enabled:
            logger.debug(f"=== Running {len(tests)} Tests ===")
            for i, (_, test_name) in enumerate(tests, 1):
                logger.debug(f"{i}. {test_name}")
            logger.debug("===============================")

        for test_method, test_name in tests:
            if debug_enabled:
                logger.debug(f"Starting test: {test_name}")
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
