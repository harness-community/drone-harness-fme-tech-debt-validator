"""Regex-based feature flag extraction fallback for all languages."""

import re
from typing import List


def extract_flags_regex(content: str) -> List[str]:
    """Extract feature flags using regex patterns (fallback method)"""
    patterns = [
        # Extract string literals from getTreatment method calls (including plural forms)
        # More precise patterns to avoid false positives
        r'(?:^|[^a-zA-Z])(?:get_?)?[Tt]reatments?(?:_?[Ww]ith_?[Cc]onfig(?:_?[Aa]sync)?)?\s*\([^)]*?["\']([^"\']+?)["\']',
        r'(?:^|[^a-zA-Z])GetTreatments?(?:WithConfig(?:Async)?)?\s*\([^)]*?["\']([^"\']+?)["\']',
    ]

    flags = []
    for pattern in patterns:
        matches = re.findall(pattern, content, re.DOTALL)
        flags.extend(matches)

    # Handle array/list patterns for multiple flags
    array_patterns = [
        # JavaScript/TypeScript: ['flag1', 'flag2']
        r'\[([^\]]*?["\'][^"\']+["\'][^\]]*?)\]',
        # Python: ['flag1', 'flag2']
        r'\[([^\]]*?["\'][^"\']+["\'][^\]]*?)\]',
        # Java: Arrays.asList("flag1", "flag2")
        r'Arrays\.asList\s*\(([^)]*?["\'][^"\']+["\'][^)]*?)\)',
        # Java: new String[]{"flag1", "flag2"} (fallback)
        r'new\s+String\[\]\s*\{([^}]*?["\'][^"\']+["\'][^}]*?)\}',
        # C#: new List<string> { "flag1", "flag2" } (only in GetTreatment calls)
        r'GetTreatments?(?:WithConfig)?(?:Async)?\s*\([^)]*new\s+List<string>\s*\{([^}]*?["\'][^"\']+["\'][^}]*?)\}',
        # C#: var declarations with List<string>
        r'var\s+\w+\s*=\s*new\s+List<string>\s*\{([^}]*?["\'][^"\']+["\'][^}]*?)\}',
        # C#: List<string> declarations
        r'List<string>\s+\w+\s*=\s*new\s+List<string>\s*\{([^}]*?["\'][^"\']+["\'][^}]*?)\}',
    ]

    for pattern in array_patterns:
        array_matches = re.findall(pattern, content, re.DOTALL)
        for array_content in array_matches:
            # Extract individual string literals from array content
            string_pattern = r'["\']([^"\']+)["\']'
            string_matches = re.findall(string_pattern, array_content)
            flags.extend(string_matches)

    return list(set(flags))
