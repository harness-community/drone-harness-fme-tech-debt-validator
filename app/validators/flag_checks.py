"""Feature flag validation checks."""

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
                        tag_details = []
                        try:
                            if hasattr(tags, "map"):
                                for tag in tags:
                                    tag_attrs = dir(tag)
                                    tag_details.append(f"attrs: {[attr for attr in tag_attrs if not attr.startswith('_')]}")
                                    # Try different possible attribute names
                                    name = (
                                        getattr(tag, "name", None)
                                        or getattr(tag, "tag", None)
                                        or getattr(tag, "label", None)
                                        or getattr(tag, "value", None)
                                        or str(tag)
                                    )
                                    tag_names.append(name if name else "")
                            else:
                                for tag in tags:
                                    tag_attrs = dir(tag)
                                    tag_details.append(f"attrs: {[attr for attr in tag_attrs if not attr.startswith('_')]}")
                                    # Try different possible attribute names
                                    name = (
                                        getattr(tag, "name", None)
                                        or getattr(tag, "tag", None)
                                        or getattr(tag, "label", None)
                                        or getattr(tag, "value", None)
                                        or str(tag)
                                    )
                                    tag_names.append(name if name else "")
                        except Exception as e:
                            tag_names = ["<unable to read tags>"]
                            tag_details = [f"<error: {e}>"]
                        logger.debug(f"Flag '{flag}': tag names = {tag_names}")
                        logger.debug(f"Flag '{flag}': tag details = {tag_details}")

                if tags:
                    try:
                        # Check if tags have the removal tag
                        removal_tag_found = None
                        if hasattr(tags, "map") and hasattr(tags, "any"):
                            # Use built-in methods if available
                            for removal_tag in self.remove_these_flags_tag.lower().split(","):

                                def get_tag_name(tag):
                                    return (
                                        getattr(tag, "name", None)
                                        or getattr(tag, "tag", None)
                                        or getattr(tag, "label", None)
                                        or getattr(tag, "value", None)
                                        or str(tag)
                                        or ""
                                    ).lower()

                                if tags.map(get_tag_name).any(lambda tag: tag == removal_tag.strip()):
                                    removal_tag_found = removal_tag.strip()
                                    break
                        else:
                            # Fallback for list-like tags
                            for tag in tags:
                                # Try different possible attribute names
                                tag_name = (
                                    getattr(tag, "name", None)
                                    or getattr(tag, "tag", None)
                                    or getattr(tag, "label", None)
                                    or getattr(tag, "value", None)
                                    or str(tag)
                                )
                                if tag_name and tag_name.lower() in [t.strip() for t in self.remove_these_flags_tag.lower().split(",")]:
                                    removal_tag_found = tag_name
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
