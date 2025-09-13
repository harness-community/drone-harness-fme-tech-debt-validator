"""C# feature flag extraction using lexical parsing with regex fallback."""

import logging
import re
from typing import List

try:
    from pygments.lexers import get_lexer_by_name
    from pygments.token import Token
except ImportError:
    get_lexer_by_name = None
    Token = None

logger = logging.getLogger(__name__)


def extract_flags_ast_csharp(content: str) -> List[str]:
    """Extract feature flags from C# using lexical parsing with pygments"""
    if not get_lexer_by_name or not Token:
        # Fallback to regex if pygments is not available
        return _extract_flags_csharp_regex_fallback(content)

    try:
        return _extract_flags_csharp_lexical(content)
    except Exception as e:
        logger.debug(f"Lexical C# parsing failed: {e}")
        # Fallback to regex on any error
        return _extract_flags_csharp_regex_fallback(content)


def _extract_flags_csharp_lexical(content: str) -> List[str]:
    """Extract feature flags from C# using pygments lexical parsing"""
    csharp_lexer = get_lexer_by_name('csharp')
    tokens = list(csharp_lexer.get_tokens(content))

    variables = {}
    flags = []
    i = 0

    while i < len(tokens):
        token_type, value = tokens[i]

        # Variable declarations: string flagName = "value";
        if (token_type == Token.Keyword.Type and value == "string") or (token_type == Token.Keyword and value == "var"):
            # Look for variable assignment pattern
            j = i + 1
            var_name = None

            # Skip whitespace to find variable name
            while j < len(tokens) and tokens[j][1].strip() == '':
                j += 1

            if j < len(tokens) and tokens[j][0] in [Token.Name, Token.Name.Variable]:
                var_name = tokens[j][1]
                j += 1

                # Look for assignment operator
                while j < len(tokens) and tokens[j][1].strip() in ['', '=']:
                    j += 1

                # Look for string literal value
                if j < len(tokens) and tokens[j][0] == Token.Literal.String:
                    var_value = tokens[j][1].strip('"\'')
                    if var_name and var_value:
                        variables[var_name] = var_value

        # Method calls: look for GetTreatment methods
        elif (token_type in [Token.Name, Token.Name.Function] and "GetTreatment" in value):
            # Found a GetTreatment method, now look for the opening parenthesis
            j = i + 1
            while j < len(tokens) and tokens[j][1].strip() in ['', '.']:
                j += 1

            # Should find opening parenthesis
            if j < len(tokens) and tokens[j][1] == '(':
                # Extract all string literals until closing parenthesis
                paren_count = 1
                j += 1

                while j < len(tokens) and paren_count > 0:
                    t_type, t_value = tokens[j]

                    if t_value == '(':
                        paren_count += 1
                    elif t_value == ')':
                        paren_count -= 1
                    elif t_type == Token.Literal.String:
                        # Remove quotes from string literal
                        clean_string = t_value.strip('"\'')
                        if clean_string:
                            flags.append(clean_string)
                    elif t_type in [Token.Name, Token.Name.Variable] and t_value in variables:
                        # Variable reference
                        flags.append(variables[t_value])

                    j += 1

        i += 1

    return list(set(flags))


def _extract_flags_csharp_regex_fallback(content: str) -> List[str]:
    """Regex-based fallback for C# flag extraction"""
    variables = {}
    flags = []

    # Simple variable assignment pattern: string varName = "value";
    var_pattern = r'string\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*["\']([^"\']+)["\'];'
    var_matches = re.findall(var_pattern, content)
    for var_name, var_value in var_matches:
        variables[var_name] = var_value

    # GetTreatment calls with string literals - extract all string arguments (including plural forms)
    # Find all GetTreatment method calls first, then extract all string literals from each
    method_pattern = r'(?:^|[^a-zA-Z])GetTreatments?(?:WithConfig)?(?:Async)?\s*\([^)]+\)'
    for method_match in re.finditer(method_pattern, content):
        method_call = method_match.group(0)
        # Extract all string literals from this specific method call
        string_pattern = r'["\']([^"\']+)["\']'
        strings = re.findall(string_pattern, method_call)
        flags.extend(strings)

    # GetTreatment calls with variables - extract all variable arguments
    var_usage_pattern = r"GetTreatments?(?:WithConfig)?(?:Async)?\([^)]*\b([a-zA-Z_][a-zA-Z0-9_]*)\b[^)]*\)"
    var_usage_matches = re.findall(var_usage_pattern, content)
    for var_name in var_usage_matches:
        if var_name in variables:
            flags.append(variables[var_name])

    # Handle List<string> initialization patterns: new List<string> { "flag1", "flag2" }
    # Extract from both variable declarations and method calls
    list_patterns = [
        # In GetTreatment method calls
        r"GetTreatments?(?:WithConfig)?(?:Async)?\s*\([^)]*new\s+List<string>\s*\{([^}]+)\}",
        # In variable declarations: List<string> flagList = new List<string> { "flag1", "flag2" };
        r"List<string>\s+\w+\s*=\s*new\s+List<string>\s*\{([^}]+)\}",
        # Static readonly declarations: readonly List<string> FlagList = new List<string> { "flag1", "flag2" };
        r"readonly\s+List<string>\s+\w+\s*=\s*new\s+List<string>\s*\{([^}]+)\}",
        # Var declarations: var flagList = new List<string> { "flag1", "flag2" };
        r"var\s+\w+\s*=\s*new\s+List<string>\s*\{([^}]+)\}",
    ]

    for list_pattern in list_patterns:
        list_matches = re.findall(list_pattern, content)
        for list_content in list_matches:
            # Extract individual string literals from the list
            string_pattern = r'["\']([^"\']+)["\']'
            string_matches = re.findall(string_pattern, list_content)
            flags.extend(string_matches)

    # Handle Java Arrays.asList patterns: Arrays.asList("flag1", "flag2")
    arrays_aslist_pattern = r"Arrays\.asList\s*\(([^)]+)\)"
    arrays_matches = re.findall(arrays_aslist_pattern, content)
    for arrays_content in arrays_matches:
        # Extract individual string literals from Arrays.asList
        string_pattern = r'["\']([^"\']+)["\']'
        string_matches = re.findall(string_pattern, arrays_content)
        flags.extend(string_matches)

    return list(set(flags))
