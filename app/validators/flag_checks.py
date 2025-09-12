"""Feature flag validation checks."""

import logging
from typing import Dict, List
from ..formatters import ErrorMessageFormatter

logger = logging.getLogger(__name__)


class FlagValidator:
    """Handles feature flag governance validation checks."""
    
    def __init__(self, config: Dict[str, str]):
        self.remove_these_flags_tag = config.get("remove_these_flags_tag", "")
        self.max_flags_in_project = config.get("max_flags_in_project", "-1")
        
    def check_removal_tags(
        self, 
        flags_in_code: List[str], 
        meta_flag_data: Dict, 
        flag_file_mapping: Dict[str, List[str]]
    ) -> bool:
        """Check if any flags in code have removal tags."""
        for flag in flags_in_code:
            # Fast dictionary lookup
            flagMeta = meta_flag_data.get(flag)

            if flagMeta:
                # Safely access tags
                tags = getattr(flagMeta, "_tags", None)
                if tags:
                    try:
                        # Check if tags have the removal tag
                        removal_tag_found = None
                        if hasattr(tags, "map") and hasattr(tags, "any"):
                            # Use built-in methods if available
                            for (
                                removal_tag
                            ) in self.remove_these_flags_tag.lower().split(
                                ","
                            ):
                                if tags.map(
                                    lambda tag: getattr(
                                        tag, "name", ""
                                    ).lower()
                                ).any(lambda tag: tag == removal_tag.strip()):
                                    removal_tag_found = removal_tag.strip()
                                    break
                        else:
                            # Fallback for list-like tags
                            for tag in tags:
                                tag_name = getattr(tag, "name", "")
                                if tag_name.lower() in [
                                    t.strip()
                                    for t in self.remove_these_flags_tag.lower().split(
                                        ","
                                    )
                                ]:
                                    removal_tag_found = tag_name
                                    break

                        if removal_tag_found:
                            files_with_flag = flag_file_mapping.get(
                                flag, []
                            )
                            error_msg = ErrorMessageFormatter.format_flag_removal_error(
                                flag, removal_tag_found, files_with_flag
                            )
                            logger.error(error_msg)
                            return False

                    except Exception as e:
                        logger.debug(
                            f"Error checking removal tags for flag {flag}: {e}"
                        )
                        continue
        return True

    def check_flag_count_limit(self, flags_in_code: List[str]) -> bool:
        """Check if flag count exceeds the configured limit."""
        if int(self.max_flags_in_project) > -1 and len(
            flags_in_code
        ) > int(self.max_flags_in_project):
            error_msg = ErrorMessageFormatter.format_flag_count_error(
                len(flags_in_code),
                int(self.max_flags_in_project),
                flags_in_code,
            )
            logger.error(error_msg)
            return False
        return True