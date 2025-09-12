"""Threshold-based validation checks for feature flags."""

import logging
import time
import datetime
from typing import Dict, List
from pytimeparse import parse as parse_duration
from ..formatters import ErrorMessageFormatter

logger = logging.getLogger(__name__)


class ThresholdValidator:
    """Handles threshold-based validation checks for stale flags."""
    
    def __init__(self, config: Dict[str, str]):
        self.permanent_flags_tag = config.get("permanent_flags_tag", "")
        self.flag_last_modified_threshold = config.get("flag_last_modified_threshold", "-1")
        self.flag_last_traffic_threshold = config.get("flag_last_traffic_threshold", "-1")
        self.flag_at_100_percent_last_modified_threshold = config.get("flag_at_100_percent_last_modified_threshold", "-1")
        self.flag_at_100_percent_last_traffic_threshold = config.get("flag_at_100_percent_last_traffic_threshold", "-1")

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
        if threshold_value == "-1":
            return True  # Skip check if not configured

        # Parse duration string (e.g., "90d 10h 30m") to seconds
        threshold_seconds = parse_duration(threshold_value)
        if threshold_seconds is None:
            logger.warning(f"Invalid duration format: {threshold_value}")
            return True

        threshold_timestamp = time.time() - threshold_seconds

        for flag in flags_in_code:
            # Skip permanent flags - fast dictionary lookup with safe access
            meta_flag = meta_flag_data.get(flag)
            if meta_flag:
                tags = getattr(meta_flag, "_tags", None)
                if tags:
                    try:
                        is_permanent = False
                        if hasattr(tags, "map") and hasattr(tags, "any"):
                            # Use built-in methods if available
                            is_permanent = tags.map(
                                lambda tag: getattr(tag, "name", "").lower()
                            ).any(
                                lambda tag: tag
                                in self.permanent_flags_tag.lower().split(",")
                            )
                        else:
                            # Fallback for list-like tags
                            for tag in tags:
                                tag_name = getattr(tag, "name", "")
                                if (
                                    tag_name.lower()
                                    in self.permanent_flags_tag.lower().split(
                                        ","
                                    )
                                ):
                                    is_permanent = True
                                    break

                        if is_permanent:
                            logger.info(
                                f"Feature flag {flag} has a permanent tag"
                            )
                            continue
                    except Exception as e:
                        logger.debug(
                            f"Error checking permanent tags for flag {flag}: {e}"
                        )
                        # Continue with threshold check if tag checking fails

            # Find flag detail with safe name access
            flag_detail = None
            for detail in flag_data:
                if getattr(detail, "name", None) == flag:
                    flag_detail = detail
                    break

            if flag_detail:
                # Get the timestamp attribute dynamically
                timestamp = getattr(flag_detail, attribute_name, None)
                if (
                    isinstance(timestamp, int)
                    and timestamp < threshold_timestamp
                    and not check_100_percent
                ):
                    # Format last activity time
                    last_activity = datetime.datetime.fromtimestamp(
                        timestamp
                    ).strftime("%Y-%m-%d %H:%M:%S")
                    flag_type = (
                        "modified"
                        if attribute_name == "lastUpdateTime"
                        else "receiving traffic"
                    )

                    error_msg = ErrorMessageFormatter.format_stale_flag_error(
                        flag, threshold_value, last_activity, flag_type
                    )
                    logger.error(error_msg)
                    return False
                elif (
                    isinstance(timestamp, int)
                    and timestamp < threshold_timestamp
                    and check_100_percent
                ):
                    if self._is_flag_at_100_percent(flag, flag_data):
                        # Format last activity time
                        last_activity = datetime.datetime.fromtimestamp(
                            timestamp
                        ).strftime("%Y-%m-%d %H:%M:%S")
                        flag_type = (
                            "modified"
                            if attribute_name == "lastUpdateTime"
                            else "receiving traffic"
                        )

                        error_msg = (
                            ErrorMessageFormatter.format_stale_flag_error(
                                flag, threshold_value, last_activity, flag_type
                            )
                        )
                        logger.error(error_msg)
                        return False

        return True

    def _is_flag_at_100_percent(self, flag: str, flag_data: List) -> bool:
        """Check if a flag is at 100% traffic allocation"""
        try:
            for flag_detail in flag_data:
                if getattr(flag_detail, "name", None) == flag:
                    # Safely check traffic allocation
                    traffic_allocation = getattr(
                        flag_detail, "_traffic_allocation", None
                    )
                    if traffic_allocation != 100:
                        continue

                    # Safely check rules
                    rules = getattr(flag_detail, "_rules", None)
                    default_rule = getattr(flag_detail, "_default_rule", None)

                    # Check if rules is empty and default rule has 100% bucket
                    if rules == [] and default_rule is not None:
                        buckets = getattr(default_rule, "buckets", None)
                        if buckets is not None:
                            try:
                                # Safely check if any bucket has size 100
                                if hasattr(buckets, "any"):
                                    return buckets.any(
                                        lambda bucket: getattr(
                                            bucket, "size", 0
                                        )
                                        == 100
                                    )
                                else:
                                    # If buckets is a list, iterate manually
                                    for bucket in buckets:
                                        if getattr(bucket, "size", 0) == 100:
                                            return True
                            except Exception as e:
                                logger.debug(
                                    f"Error checking buckets for flag {flag}: {e}"
                                )
                                continue

                    # Check if first rule has 100% allocation
                    if rules and len(rules) > 0:
                        first_rule = rules[0]
                        rule_allocation = getattr(
                            first_rule, "allocation", None
                        )
                        if rule_allocation == 100:
                            return True

            return False

        except Exception as e:
            logger.warning(f"Error checking if flag {flag} is at 100%: {e}")
            return False

    def check_last_modified_threshold(
        self, 
        flags_in_code: List[str], 
        meta_flag_data: Dict, 
        flag_data: List
    ) -> bool:
        """Check if any flags were modified beyond the threshold duration"""
        return self._check_flag_threshold(
            flags_in_code,
            meta_flag_data,
            flag_data,
            self.flag_last_modified_threshold,
            "lastUpdateTime",
        )

    def check_last_traffic_threshold(
        self, 
        flags_in_code: List[str], 
        meta_flag_data: Dict, 
        flag_data: List
    ) -> bool:
        """Check if any flags have not received traffic beyond the threshold duration"""
        return self._check_flag_threshold(
            flags_in_code,
            meta_flag_data,
            flag_data,
            self.flag_last_traffic_threshold,
            "lastTrafficRecievedAt",
        )

    def check_last_modified_threshold_100_percent(
        self, 
        flags_in_code: List[str], 
        meta_flag_data: Dict, 
        flag_data: List
    ) -> bool:
        """Check if any 100% flags were modified beyond the threshold duration"""
        return self._check_flag_threshold(
            flags_in_code,
            meta_flag_data,
            flag_data,
            self.flag_last_modified_threshold,
            "lastUpdateTime",
            check_100_percent=True,
        )

    def check_last_traffic_threshold_100_percent(
        self, 
        flags_in_code: List[str], 
        meta_flag_data: Dict, 
        flag_data: List
    ) -> bool:
        """Check if any 100% flags have not received traffic beyond the threshold duration"""
        return self._check_flag_threshold(
            flags_in_code,
            meta_flag_data,
            flag_data,
            self.flag_last_traffic_threshold,
            "lastTrafficRecievedAt",
            check_100_percent=True,
        )