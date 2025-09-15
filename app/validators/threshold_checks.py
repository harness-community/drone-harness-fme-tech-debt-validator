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

        for flag in flags_in_code:
            if self.debug:
                logger.debug(f"Checking flag '{flag}' against threshold")

            # Skip permanent flags - fast dictionary lookup with safe access
            meta_flag = meta_flag_data.get(flag)
            if meta_flag:
                tags = getattr(meta_flag, "_tags", None)
                if tags:
                    try:
                        permanent_tag_names = [tag.strip().lower() for tag in self.permanent_flags_tag.split(",") if tag.strip()]
                        is_permanent = False

                        for tag in tags:
                            tag_name = getattr(tag, "name", None)
                            if tag_name and tag_name.lower() in permanent_tag_names:
                                is_permanent = True
                                break

                        if is_permanent:
                            if self.debug:
                                logger.debug(f"Flag '{flag}' has permanent tag, skipping threshold check")
                            logger.info(f"Feature flag {flag} has a permanent tag")
                            continue
                    except Exception as e:
                        logger.debug(f"Error checking permanent tags for flag {flag}: {e}")
                        # Continue with threshold check if tag checking fails

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
                    timestamp_readable = (
                        datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S") if isinstance(timestamp, int) else "N/A"
                    )
                    threshold_readable = datetime.datetime.fromtimestamp(threshold_timestamp).strftime("%Y-%m-%d %H:%M:%S")
                    logger.debug(f"Flag '{flag}': {attribute_name} = {timestamp} ({timestamp_readable})")
                    logger.debug(f"Flag '{flag}': threshold = {threshold_timestamp} ({threshold_readable})")
                    logger.debug(f"Flag '{flag}': is_stale = {isinstance(timestamp, int) and timestamp < threshold_timestamp}")

                if isinstance(timestamp, int) and timestamp < threshold_timestamp and not check_100_percent:
                    # Format last activity time
                    last_activity = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                    flag_type = "modified" if attribute_name == "lastUpdateTime" else "receiving traffic"

                    if self.debug:
                        logger.debug(f"Flag '{flag}': threshold violation detected (last {flag_type}: {last_activity})")

                    error_msg = ErrorMessageFormatter.format_stale_flag_error(flag, threshold_value, last_activity, flag_type)
                    logger.error(error_msg)
                    return False
                elif isinstance(timestamp, int) and timestamp < threshold_timestamp and check_100_percent:
                    if self._is_flag_at_100_percent(flag, flag_data):
                        # Format last activity time
                        last_activity = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                        flag_type = "modified" if attribute_name == "lastUpdateTime" else "receiving traffic"

                        if self.debug:
                            logger.debug(f"Flag '{flag}': 100% flag threshold violation detected (last {flag_type}: {last_activity})")

                        error_msg = ErrorMessageFormatter.format_stale_flag_error(flag, threshold_value, last_activity, flag_type)
                        logger.error(error_msg)
                        return False
                    elif self.debug:
                        logger.debug(f"Flag '{flag}': not at 100%, skipping 100% threshold check")

        return True

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

                    # Check if rules is empty and default rule has 100% bucket
                    if rules == [] and default_rule is not None:
                        buckets = getattr(default_rule, "buckets", None)
                        if buckets is not None:
                            try:
                                # Safely check if any bucket has size 100
                                if hasattr(buckets, "any"):
                                    result = buckets.any(lambda bucket: getattr(bucket, "size", 0) == 100)
                                    if self.debug:
                                        logger.debug(f"Flag '{flag}': bucket check result = {result}")
                                    return result
                                else:
                                    # If buckets is a list, iterate manually
                                    for bucket in buckets:
                                        bucket_size = getattr(bucket, "size", 0)
                                        if self.debug:
                                            logger.debug(f"Flag '{flag}': bucket size = {bucket_size}")
                                        if bucket_size == 100:
                                            if self.debug:
                                                logger.debug(f"Flag '{flag}': found 100% bucket")
                                            return True
                            except Exception as e:
                                logger.debug(f"Error checking buckets for flag {flag}: {e}")
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
