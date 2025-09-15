"""Threshold-based validation checks for feature flags."""

import logging
import time
import datetime
from typing import Dict, List
from pytimeparse import parse as parse_duration
from formatters import ErrorMessageFormatter

logger = logging.getLogger(__name__)


class ThresholdValidator:
    """Handles threshold-based validation checks for stale flags."""

    def __init__(self, config: Dict[str, str]):
        self.permanent_flags_tag = config.get("permanent_flags_tag", "")
        self.flag_last_modified_threshold = config.get("flag_last_modified_threshold", "-1")
        self.flag_last_traffic_threshold = config.get("flag_last_traffic_threshold", "-1")
        self.flag_at_100_percent_last_modified_threshold = config.get("flag_at_100_percent_last_modified_threshold", "-1")
        self.flag_at_100_percent_last_traffic_threshold = config.get("flag_at_100_percent_last_traffic_threshold", "-1")
        self.debug = config.get("debug", False)

        if self.debug:
            logger.debug("=== ThresholdValidator Configuration ===")
            logger.debug(f"Permanent flags tag: '{self.permanent_flags_tag}'")
            status = "(DISABLED)" if self.flag_last_modified_threshold == "-1" else "(ENABLED)"
            logger.debug(f"Flag last modified threshold: '{self.flag_last_modified_threshold}' {status}")

            status = "(DISABLED)" if self.flag_last_traffic_threshold == "-1" else "(ENABLED)"
            logger.debug(f"Flag last traffic threshold: '{self.flag_last_traffic_threshold}' {status}")

            status = "(DISABLED)" if self.flag_at_100_percent_last_modified_threshold == "-1" else "(ENABLED)"
            logger.debug(f"100% flag last modified threshold: '{self.flag_at_100_percent_last_modified_threshold}' {status}")

            status = "(DISABLED)" if self.flag_at_100_percent_last_traffic_threshold == "-1" else "(ENABLED)"
            logger.debug(f"100% flag last traffic threshold: '{self.flag_at_100_percent_last_traffic_threshold}' {status}")
            logger.debug("=========================================")

    def _check_flag_threshold(
        self,
        flags_in_code: List[str],
        meta_flag_data: Dict,
        flag_data: List,
        threshold_value: str,
        attribute_name: str,
        check_100_percent: bool = False,
    ) -> bool:
        """Generic helper for checking flag thresholds based on timestamps"""
        if self.debug:
            logger.debug(f"Starting threshold check: attribute={attribute_name}, threshold={threshold_value}, check_100_percent={check_100_percent}")
            logger.debug(f"Checking {len(flags_in_code)} flags: {flags_in_code}")

        if threshold_value == "-1":
            if self.debug:
                logger.debug("Threshold check skipped (not configured)")
            return True  # Skip check if not configured

        # Parse duration string (e.g., "90d 10h 30m") to seconds
        threshold_seconds = parse_duration(threshold_value)
        if threshold_seconds is None:
            logger.warning(f"Invalid duration format: {threshold_value}")
            return True

        threshold_timestamp = time.time() - threshold_seconds
        if self.debug:
            logger.debug(f"Threshold parsed: {threshold_value} = {threshold_seconds} seconds = timestamp {threshold_timestamp}")

        failed_flags = []

        for flag in flags_in_code:
            if self.debug:
                logger.debug(f"Checking flag '{flag}' against threshold")

            # Skip permanent flags - fast dictionary lookup with safe access
            if self._is_permanent_flag(flag, meta_flag_data):
                if self.debug:
                    logger.debug(f"Flag '{flag}' has permanent tag, skipping threshold check")
                logger.info(f"Feature flag {flag} has a permanent tag")
                continue

            # Find flag detail with safe name access
            flag_detail = None
            for detail in flag_data:
                if getattr(detail, "name", None) == flag:
                    flag_detail = detail
                    break

            if self.debug:
                logger.debug(f"Flag '{flag}': detail found = {flag_detail is not None}")

            if flag_detail:
                # Get the timestamp attribute dynamically
                timestamp = getattr(flag_detail, attribute_name, None)
                if self.debug:
                    logger.debug(f"Flag '{flag}': Raw {attribute_name} value = {timestamp} (type: {type(timestamp)})")

                    # Check if timestamp needs conversion from milliseconds to seconds
                    if isinstance(timestamp, int) and timestamp > 1e10:  # Likely milliseconds
                        timestamp_seconds = timestamp // 1000
                        logger.debug(f"Flag '{flag}': Converting from milliseconds: {timestamp} -> {timestamp_seconds}")
                        timestamp = timestamp_seconds

                    timestamp_readable = (
                        datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S") if isinstance(timestamp, int) else "N/A"
                    )
                    threshold_readable = datetime.datetime.fromtimestamp(threshold_timestamp).strftime("%Y-%m-%d %H:%M:%S")
                    logger.debug(f"Flag '{flag}': {attribute_name} = {timestamp} ({timestamp_readable})")
                    logger.debug(f"Flag '{flag}': threshold = {threshold_timestamp} ({threshold_readable})")
                    logger.debug(f"Flag '{flag}': is_stale = {isinstance(timestamp, int) and timestamp < threshold_timestamp}")

                # Convert milliseconds to seconds if needed
                if isinstance(timestamp, int) and timestamp > 1e10:
                    timestamp = timestamp // 1000

                if isinstance(timestamp, int) and timestamp < threshold_timestamp and not check_100_percent:
                    # Format last activity time
                    last_activity = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                    flag_type = "modified" if attribute_name == "lastUpdateTime" else "receiving traffic"

                    if self.debug:
                        logger.debug(f"Flag '{flag}': threshold violation detected (last {flag_type}: {last_activity})")

                    # Add to failed flags list instead of returning immediately
                    failed_flags.append(
                        {
                            "flag": flag,
                            "threshold_value": threshold_value,
                            "last_activity": last_activity,
                            "flag_type": flag_type,
                            "is_100_percent": False,
                        }
                    )

                elif isinstance(timestamp, int) and timestamp < threshold_timestamp and check_100_percent:
                    if self._is_flag_at_100_percent(flag, flag_data):
                        # Format last activity time
                        last_activity = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                        flag_type = "modified" if attribute_name == "last_update_time" else "receiving traffic"

                        if self.debug:
                            logger.debug(f"Flag '{flag}': 100% flag threshold violation detected (last {flag_type}: {last_activity})")

                        # Add to failed flags list instead of returning immediately
                        failed_flags.append(
                            {
                                "flag": flag,
                                "threshold_value": threshold_value,
                                "last_activity": last_activity,
                                "flag_type": flag_type,
                                "is_100_percent": True,
                            }
                        )

                    elif self.debug:
                        logger.debug(f"Flag '{flag}': not at 100%, skipping 100% threshold check")

        # Report all failures after checking all flags
        if failed_flags:
            # Log summary first
            logger.error(f"\n📊 THRESHOLD CHECK SUMMARY: Found {len(failed_flags)} stale flag(s)")

            for failure in failed_flags:
                if failure["is_100_percent"]:
                    error_msg = ErrorMessageFormatter.format_100_percent_flag_error(
                        failure["flag"], failure["threshold_value"], failure["last_activity"], failure["flag_type"]
                    )
                else:
                    error_msg = ErrorMessageFormatter.format_stale_flag_error(
                        failure["flag"], failure["threshold_value"], failure["last_activity"], failure["flag_type"]
                    )
                logger.error(error_msg)

            # Log final summary
            regular_flags = [f["flag"] for f in failed_flags if not f["is_100_percent"]]
            hundred_percent_flags = [f["flag"] for f in failed_flags if f["is_100_percent"]]

            summary_parts = []
            if regular_flags:
                summary_parts.append(f"{len(regular_flags)} stale flag(s): {', '.join(regular_flags)}")
            if hundred_percent_flags:
                summary_parts.append(f"{len(hundred_percent_flags)} 100% flag(s): {', '.join(hundred_percent_flags)}")

            logger.error(f"⚠️  TOTAL ISSUES: {' | '.join(summary_parts)}")

            return False

        return True

    def check_all_thresholds_consolidated(self, flags_in_code: List[str], meta_flag_data: Dict, flag_data: List) -> bool:
        """Comprehensive threshold check that combines all threshold types and reports consolidated results"""
        if self.debug:
            logger.debug("Starting consolidated threshold check for all flag types")

        all_failed_flags = {}  # flag_name -> {issues: [], details: {}}

        # Check each threshold type and collect all failures
        threshold_checks = [
            ("Modified Threshold", self.flag_last_modified_threshold, "last_update_time", False),
            ("Traffic Threshold", self.flag_last_traffic_threshold, "last_traffic_received_at", False),
            ("100% Modified Threshold", self.flag_at_100_percent_last_modified_threshold, "last_update_time", True),
            ("100% Traffic Threshold", self.flag_at_100_percent_last_traffic_threshold, "last_traffic_received_at", True),
        ]

        for check_name, threshold_value, attribute_name, check_100_percent in threshold_checks:
            if threshold_value == "-1":
                if self.debug:
                    logger.debug(f"Skipping {check_name} (not configured)")
                continue

            if self.debug:
                logger.debug(f"Running {check_name} with threshold {threshold_value}")

            # Run threshold check and collect failures
            failed_flags = self._run_single_threshold_check(
                flags_in_code, meta_flag_data, flag_data, threshold_value, attribute_name, check_100_percent
            )

            # Consolidate failures by flag name
            for failure in failed_flags:
                flag_name = failure["flag"]
                if flag_name not in all_failed_flags:
                    all_failed_flags[flag_name] = {"issues": [], "is_100_percent": failure["is_100_percent"], "flag": flag_name}

                all_failed_flags[flag_name]["issues"].append(
                    {
                        "check_name": check_name,
                        "threshold": threshold_value,
                        "last_activity": failure["last_activity"],
                        "flag_type": failure["flag_type"],
                    }
                )

        # Generate consolidated reports
        if all_failed_flags:
            self._report_consolidated_failures(all_failed_flags)
            return False

        return True

    def _run_single_threshold_check(
        self, flags_in_code: List[str], meta_flag_data: Dict, flag_data: List, threshold_value: str, attribute_name: str, check_100_percent: bool
    ) -> List[Dict]:
        """Run a single threshold check and return failures without logging errors"""
        from pytimeparse import parse as parse_duration
        import time

        threshold_seconds = parse_duration(threshold_value)
        if threshold_seconds is None:
            return []

        threshold_timestamp = time.time() - threshold_seconds
        failed_flags = []

        for flag in flags_in_code:
            # Skip permanent flags
            if self._is_permanent_flag(flag, meta_flag_data):
                continue  # Skip this flag entirely

            # Find flag detail
            flag_detail = None
            for detail in flag_data:
                if getattr(detail, "name", None) == flag:
                    flag_detail = detail
                    break

            if flag_detail:
                timestamp = getattr(flag_detail, attribute_name, None)

                # Convert milliseconds to seconds if needed
                if isinstance(timestamp, int) and timestamp > 1e10:
                    timestamp = timestamp // 1000

                if isinstance(timestamp, int) and timestamp < threshold_timestamp:
                    # For 100% checks, verify the flag is actually at 100%
                    if check_100_percent and not self._is_flag_at_100_percent(flag, flag_data):
                        continue

                    last_activity = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                    flag_type = "modified" if attribute_name == "last_update_time" else "receiving traffic"

                    failed_flags.append({"flag": flag, "last_activity": last_activity, "flag_type": flag_type, "is_100_percent": check_100_percent})

        return failed_flags

    def _report_consolidated_failures(self, all_failed_flags: Dict):
        """Generate consolidated reports for all threshold failures"""
        logger.error(f"\n📊 CONSOLIDATED THRESHOLD REPORT: {len(all_failed_flags)} flag(s) with violations")

        for flag_name, flag_info in all_failed_flags.items():
            issues = flag_info["issues"]
            is_100_percent = flag_info["is_100_percent"]

            # Build issue summary
            issue_lines = []
            for issue in issues:
                issue_lines.append(f"║   • {issue['check_name']}: {issue['threshold']} (last {issue['flag_type']}: {issue['last_activity']})")

            status = "100% allocation + stale" if is_100_percent else "Stale flag"
            icon = "⚠️" if is_100_percent else "❌"

            consolidated_msg = f"""
╔══════════════════════════════════════════════════════════════════════
║ {icon} CONSOLIDATED THRESHOLD VIOLATIONS
╠══════════════════════════════════════════════════════════════════════
║ Flag: '{flag_name}'
║ Status: {status}
║ Violations: {len(issues)} threshold(s) failed
║
║ 🚨 FAILED CHECKS:
{chr(10).join(issue_lines)}
║
║ 🔧 RECOMMENDED ACTION:"""

            # Add action recommendations based on flag type
            if is_100_percent:
                consolidated_msg += """
║    • REMOVE FLAG: At 100% allocation - can be safely removed
║    • CLEAN UP CODE: Replace flag checks with direct implementation"""
            else:
                consolidated_msg += """
║    • REVIEW FLAG: Add permanent tag if needed, or plan removal
║    • UPDATE CONFIG: Modify flag settings if actively used"""

            consolidated_msg += f"""
║
║ 💡 SEARCH COMMANDS:
║    git grep -n "{flag_name}" --exclude-dir=node_modules
║    rg "{flag_name}" --type js --type java --type py
║
║ 📖 RESOURCES:
║    Flag Lifecycle: https://developer.harness.io/docs/feature-management-experimentation/getting-started/overview/manage-the-feature-flag-lifecycle/
╚══════════════════════════════════════════════════════════════════════"""

            logger.error(consolidated_msg)

        # Final summary
        regular_flags = [name for name, info in all_failed_flags.items() if not info["is_100_percent"]]
        hundred_percent_flags = [name for name, info in all_failed_flags.items() if info["is_100_percent"]]

        summary_parts = []
        if regular_flags:
            summary_parts.append(f"{len(regular_flags)} stale: {', '.join(regular_flags)}")
        if hundred_percent_flags:
            summary_parts.append(f"{len(hundred_percent_flags)} at 100%: {', '.join(hundred_percent_flags)}")

        logger.error(f"⚠️  SUMMARY: {' | '.join(summary_parts)}")

    def _is_permanent_flag(self, flag: str, meta_flag_data: Dict) -> bool:
        """Check if flag is marked as permanent."""
        if not self.permanent_flags_tag:
            return False

        meta_flag = meta_flag_data.get(flag)
        if not meta_flag:
            return False

        tags = getattr(meta_flag, "_tags", None)
        if not tags:
            return False

        permanent_tag_names = [tag.strip().lower() for tag in self.permanent_flags_tag.split(",") if tag.strip()]
        if not permanent_tag_names:
            return False

        try:
            for tag in tags:
                tag_name = getattr(tag, "name", None)
                if tag_name and tag_name.lower() in permanent_tag_names:
                    return True
        except Exception as e:
            if self.debug:
                logger.debug(f"Error checking permanent tags for flag {flag}: {e}")

        return False

    def _is_flag_at_100_percent(self, flag: str, flag_data: List) -> bool:
        """Check if a flag is at 100% traffic allocation"""
        if self.debug:
            logger.debug(f"Checking if flag '{flag}' is at 100% traffic allocation")
        try:
            for flag_detail in flag_data:
                if getattr(flag_detail, "name", None) == flag:
                    # Safely check traffic allocation
                    traffic_allocation = getattr(flag_detail, "_traffic_allocation", None)
                    if self.debug:
                        logger.debug(f"Flag '{flag}': traffic allocation = {traffic_allocation}")
                    if traffic_allocation != 100:
                        if self.debug:
                            logger.debug(f"Flag '{flag}': traffic allocation is not 100%, continuing")
                        continue

                    # Safely check rules
                    rules = getattr(flag_detail, "_rules", None)
                    default_rule = getattr(flag_detail, "_default_rule", None)

                    if self.debug:
                        logger.debug(f"Flag '{flag}': rules = {rules}, default_rule = {default_rule is not None}")

                    # Check if rules is empty and default rule has 100% allocation
                    if rules == [] and default_rule is not None:
                        if self.debug:
                            logger.debug(f"Flag '{flag}': checking default rule with {len(default_rule)} items")
                        try:
                            # default_rule is a list of DefaultRule objects, each with treatment and size
                            for rule_item in default_rule:
                                rule_size = getattr(rule_item, "_size", 0)
                                rule_treatment = getattr(rule_item, "_treatment", None)
                                if self.debug:
                                    logger.debug(f"Flag '{flag}': default rule item - treatment: {rule_treatment}, size: {rule_size}")
                                if rule_size == 100:
                                    if self.debug:
                                        logger.debug(f"Flag '{flag}': found 100% default rule")
                                    return True
                            if self.debug:
                                logger.debug(f"Flag '{flag}': no 100% default rules found")
                        except Exception as e:
                            logger.debug(f"Error checking default rule for flag {flag}: {e}")
                            continue

                    # Check if first rule has 100% allocation
                    if rules and len(rules) > 0:
                        first_rule = rules[0]
                        rule_allocation = getattr(first_rule, "allocation", None)
                        if self.debug:
                            logger.debug(f"Flag '{flag}': first rule allocation = {rule_allocation}")
                        if rule_allocation == 100:
                            if self.debug:
                                logger.debug(f"Flag '{flag}': first rule has 100% allocation")
                            return True

            if self.debug:
                logger.debug(f"Flag '{flag}': not at 100% traffic allocation")
            return False

        except Exception as e:
            logger.warning(f"Error checking if flag {flag} is at 100%: {e}")
            return False

    def check_last_modified_threshold(self, flags_in_code: List[str], meta_flag_data: Dict, flag_data: List) -> bool:
        """Check if any flags were modified beyond the threshold duration"""
        return self._check_flag_threshold(
            flags_in_code,
            meta_flag_data,
            flag_data,
            self.flag_last_modified_threshold,
            "last_update_time",
        )

    def check_last_traffic_threshold(self, flags_in_code: List[str], meta_flag_data: Dict, flag_data: List) -> bool:
        """Check if any flags have not received traffic beyond the threshold duration"""
        return self._check_flag_threshold(
            flags_in_code,
            meta_flag_data,
            flag_data,
            self.flag_last_traffic_threshold,
            "last_traffic_received_at",
        )

    def check_last_modified_threshold_100_percent(self, flags_in_code: List[str], meta_flag_data: Dict, flag_data: List) -> bool:
        """Check if any 100% flags were modified beyond the threshold duration"""
        return self._check_flag_threshold(
            flags_in_code,
            meta_flag_data,
            flag_data,
            self.flag_last_modified_threshold,
            "last_update_time",
            check_100_percent=True,
        )

    def check_last_traffic_threshold_100_percent(self, flags_in_code: List[str], meta_flag_data: Dict, flag_data: List) -> bool:
        """Check if any 100% flags have not received traffic beyond the threshold duration"""
        return self._check_flag_threshold(
            flags_in_code,
            meta_flag_data,
            flag_data,
            self.flag_last_traffic_threshold,
            "last_traffic_received_at",
            check_100_percent=True,
        )
