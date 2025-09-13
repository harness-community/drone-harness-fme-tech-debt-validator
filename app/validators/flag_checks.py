"""Feature flag validation checks."""

import json
import logging
from typing import Dict, List
from formatters import ErrorMessageFormatter

logger = logging.getLogger(__name__)


class FlagValidator:
    """Handles feature flag governance validation checks."""

    def __init__(self, config: Dict[str, str]):
        self.remove_these_flags_tag = config.get("remove_these_flags_tag", "")
        self.max_flags_in_project = config.get("max_flags_in_project", "-1")
        self.debug = config.get("debug", False)

    def check_removal_tags(self, flags_in_code: List[str], meta_flag_data: Dict, flag_file_mapping: Dict[str, List[str]]) -> bool:
        """Check if any flags in code have removal tags."""
        if self.debug:
            logger.debug(f"Starting removal tag check for {len(flags_in_code)} flags: {flags_in_code}")
            logger.debug(f"Removal tags to check: {self.remove_these_flags_tag}")

        for flag in flags_in_code:
            # Fast dictionary lookup
            flagMeta = meta_flag_data.get(flag)

            if self.debug:
                logger.debug(f"Checking flag '{flag}': metadata found = {flagMeta is not None}")

            if flagMeta:
                # Safely access tags
                tags = getattr(flagMeta, "_tags", None)
                if self.debug:
                    logger.debug(f"Flag '{flag}': tags found = {tags is not None}")
                    if tags:
                        tag_names = []
                        try:
                            if hasattr(tags, "map"):
                                for tag in tags:
                                    # Try different possible attribute names
                                    name = (
                                        getattr(tag, "name", None)
                                        or getattr(tag, "tag", None)
                                        or getattr(tag, "label", None)
                                        or getattr(tag, "value", None)
                                        or str(tag)
                                    )

                                    # If name looks like JSON, try to parse it
                                    if name and isinstance(name, str) and name.startswith("{") and name.endswith("}"):
                                        try:
                                            # Replace single quotes with double quotes for valid JSON
                                            json_str = name.replace("'", '"')
                                            parsed_tag = json.loads(json_str)
                                            actual_name = parsed_tag.get("name", name)
                                            tag_names.append(actual_name)
                                        except (json.JSONDecodeError, AttributeError):
                                            tag_names.append(name if name else "")
                                    else:
                                        tag_names.append(name if name else "")
                            else:
                                for tag in tags:
                                    # Try different possible attribute names
                                    name = (
                                        getattr(tag, "name", None)
                                        or getattr(tag, "tag", None)
                                        or getattr(tag, "label", None)
                                        or getattr(tag, "value", None)
                                        or str(tag)
                                    )

                                    # If name looks like JSON, try to parse it
                                    if name and isinstance(name, str) and name.startswith("{") and name.endswith("}"):
                                        try:
                                            # Replace single quotes with double quotes for valid JSON
                                            json_str = name.replace("'", '"')
                                            parsed_tag = json.loads(json_str)
                                            actual_name = parsed_tag.get("name", name)
                                            tag_names.append(actual_name)
                                        except (json.JSONDecodeError, AttributeError):
                                            tag_names.append(name if name else "")
                                    else:
                                        tag_names.append(name if name else "")
                        except Exception as e:
                            tag_names = ["<unable to read tags>"]
                            if self.debug:
                                logger.debug(f"Flag '{flag}': unable to read tags: {e}")
                        logger.debug(f"Flag '{flag}': tag names = {tag_names}")

                if tags:
                    try:
                        # Check if tags have the removal tag
                        removal_tag_found = None
                        if self.debug:
                            logger.debug(f"Flag '{flag}': checking removal tags, configured removal tags: '{self.remove_these_flags_tag}'")

                        # Simple iteration through tags since they don't have map/any methods
                        for tag in tags:
                            # Try different possible attribute names
                            tag_name = (
                                getattr(tag, "name", None)
                                or getattr(tag, "tag", None)
                                or getattr(tag, "label", None)
                                or getattr(tag, "value", None)
                                or str(tag)
                            )

                            # If tag_name looks like JSON, try to parse it
                            if tag_name and isinstance(tag_name, str) and tag_name.startswith("{") and tag_name.endswith("}"):
                                try:
                                    # Replace single quotes with double quotes for valid JSON
                                    json_str = tag_name.replace("'", '"')
                                    parsed_tag = json.loads(json_str)
                                    actual_tag_name = parsed_tag.get("name", tag_name)
                                except (json.JSONDecodeError, AttributeError):
                                    actual_tag_name = tag_name
                            else:
                                actual_tag_name = tag_name

                            if self.debug:
                                logger.debug(f"Flag '{flag}': comparing tag '{actual_tag_name}' against removal tags")

                            if actual_tag_name and actual_tag_name.lower() in [t.strip() for t in self.remove_these_flags_tag.lower().split(",")]:
                                removal_tag_found = actual_tag_name
                                if self.debug:
                                    logger.debug(f"Flag '{flag}': found matching removal tag '{actual_tag_name}'")
                                break

                        if removal_tag_found:
                            files_with_flag = flag_file_mapping.get(flag, [])
                            if self.debug:
                                logger.debug(f"Flag '{flag}': removal tag '{removal_tag_found}' found, files: {files_with_flag}")
                            error_msg = ErrorMessageFormatter.format_flag_removal_error(flag, removal_tag_found, files_with_flag)
                            logger.error(error_msg)
                            return False
                        elif self.debug:
                            logger.debug(f"Flag '{flag}': no removal tags found")

                    except Exception as e:
                        logger.debug(f"Error checking removal tags for flag {flag}: {e}")
                        continue
        return True

    def check_flag_count_limit(self, flags_in_code: List[str]) -> bool:
        """Check if flag count exceeds the configured limit."""
        if self.debug:
            logger.debug(f"Starting flag count check: {len(flags_in_code)} flags found, limit: {self.max_flags_in_project}")

        if int(self.max_flags_in_project) > -1 and len(flags_in_code) > int(self.max_flags_in_project):
            if self.debug:
                logger.debug(f"Flag count limit exceeded: {len(flags_in_code)} > {self.max_flags_in_project}")
            error_msg = ErrorMessageFormatter.format_flag_count_error(
                len(flags_in_code),
                int(self.max_flags_in_project),
                flags_in_code,
            )
            logger.error(error_msg)
            return False
        elif self.debug:
            logger.debug("Flag count check passed")
        return True
