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

        if self.debug:
            logger.debug("=== FlagValidator Configuration ===")
            logger.debug(
                f"Remove these flags tags: '{self.remove_these_flags_tag}' {'(DISABLED)' if not self.remove_these_flags_tag else '(ENABLED)'}"
            )
            logger.debug(f"Max flags in project: '{self.max_flags_in_project}' {'(DISABLED)' if self.max_flags_in_project == '-1' else '(ENABLED)'}")
            logger.debug("====================================")

    def _extract_tag_name(self, tag) -> str:
        """Extract tag name from tag object with JSON parsing support."""
        tag_name = getattr(tag, "name", None) or getattr(tag, "tag", None) or getattr(tag, "label", None) or getattr(tag, "value", None) or str(tag)

        # Handle JSON-formatted tag names
        if tag_name and isinstance(tag_name, str) and tag_name.startswith("{") and tag_name.endswith("}"):
            try:
                json_str = tag_name.replace("'", '"')
                parsed_tag = json.loads(json_str)
                return parsed_tag.get("name", tag_name)
            except (json.JSONDecodeError, AttributeError):
                return tag_name

        return tag_name if tag_name else ""

    def _extract_all_tag_names(self, tags) -> List[str]:
        """Extract all tag names from tags collection."""
        tag_names = []
        try:
            for tag in tags:
                tag_names.append(self._extract_tag_name(tag))
        except Exception as e:
            if self.debug:
                logger.debug(f"Unable to read tags: {e}")
            return ["<unable to read tags>"]
        return tag_names

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
                    try:
                        # Extract all tag names using the helper method
                        tag_names = self._extract_all_tag_names(tags)
                        if self.debug:
                            logger.debug(f"Flag '{flag}': tag names = {tag_names}")

                        # Check if tags have the removal tag
                        removal_tag_found = None
                        if self.debug:
                            logger.debug(f"Flag '{flag}': checking removal tags, configured removal tags: '{self.remove_these_flags_tag}'")

                        removal_tags = [t.strip().lower() for t in self.remove_these_flags_tag.lower().split(",") if t.strip()]

                        for tag_name in tag_names:
                            if self.debug:
                                logger.debug(f"Flag '{flag}': comparing tag '{tag_name}' against removal tags")

                            if tag_name and tag_name.lower() in removal_tags:
                                removal_tag_found = tag_name
                                if self.debug:
                                    logger.debug(f"Flag '{flag}': found matching removal tag '{tag_name}'")
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
