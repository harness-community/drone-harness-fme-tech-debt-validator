"""C# feature flag extraction using tree-sitter AST parsing with regex fallback."""

import logging
import os
import re
from typing import List

try:
    import tree_sitter
except ImportError:
    tree_sitter = None

logger = logging.getLogger(__name__)


def extract_flags_ast_csharp(content: str) -> List[str]:
    """Extract feature flags from C# using tree-sitter AST parsing"""
    if not tree_sitter:
        # Fallback to regex if tree-sitter is not available
        return _extract_flags_csharp_regex_fallback(content)

    try:
        # Try to set up tree-sitter C# parser
        Language = tree_sitter.Language

        # Try to load the C# language from the cloned repository
        csharp_grammar_path = os.path.join(os.getcwd(), "tree-sitter-c-sharp")
        if not os.path.exists(csharp_grammar_path):
            # Fallback to regex if grammar not available
            return _extract_flags_csharp_regex_fallback(content)

        # Build and load C# language
        try:
            csharp_language = Language.build_library("build/csharp.so", [csharp_grammar_path])
            csharp = Language(csharp_language, "c_sharp")
        except Exception:
            # If building fails, fallback to regex
            return _extract_flags_csharp_regex_fallback(content)

        # Create parser and parse content
        parser = tree_sitter.Parser()
        parser.set_language(csharp)
        tree = parser.parse(bytes(content, "utf8"))

        variables = {}
        flags = []

        def walk_tree(node):
            # Variable declarations: string flagName = "value";
            if node.type == "variable_declaration":
                for child in node.children:
                    if child.type == "variable_declarator":
                        var_name = None
                        var_value = None
                        for declarator_child in child.children:
                            if declarator_child.type == "identifier":
                                var_name = content[declarator_child.start_byte : declarator_child.end_byte]
                            elif declarator_child.type == "equals_value_clause":
                                for value_child in declarator_child.children:
                                    if value_child.type == "string_literal":
                                        # Remove quotes from string literal
                                        var_value = content[value_child.start_byte + 1 : value_child.end_byte - 1]

                        if var_name and var_value:
                            variables[var_name] = var_value

            # Method invocations: client.GetTreatment("flag")
            elif node.type == "invocation_expression":
                method_name = None
                # Find method name
                for child in node.children:
                    if child.type == "member_access_expression":
                        for member_child in child.children:
                            if member_child.type == "identifier":
                                method_name = content[member_child.start_byte : member_child.end_byte]
                    elif child.type == "identifier":
                        method_name = content[child.start_byte : child.end_byte]

                # Check if this is a feature flag method (including plural forms and async variants)
                if method_name and ("GetTreatment" in method_name or "Treatment" in method_name):
                    # Extract arguments
                    for child in node.children:
                        if child.type == "argument_list":
                            for arg_child in child.children:
                                if arg_child.type == "argument":
                                    for arg_value in arg_child.children:
                                        if arg_value.type == "string_literal":
                                            # Extract string literal value (remove quotes)
                                            flag_value = content[arg_value.start_byte + 1 : arg_value.end_byte - 1]
                                            flags.append(flag_value)
                                        elif arg_value.type == "identifier":
                                            # Variable reference for single flags
                                            var_name = content[arg_value.start_byte : arg_value.end_byte]
                                            if var_name in variables:
                                                flags.append(variables[var_name])
                                        elif arg_value.type == "object_creation_expression":
                                            # Handle: new List<string> { "flag1", "flag2" }
                                            for creation_child in arg_value.children:
                                                if creation_child.type == "initializer_expression":
                                                    for init_child in creation_child.children:
                                                        if init_child.type == "string_literal":
                                                            flag_value = content[init_child.start_byte + 1 : init_child.end_byte - 1]
                                                            flags.append(flag_value)

            # Recursively walk children
            for child in node.children:
                walk_tree(child)

        walk_tree(tree.root_node)
        return list(set(flags))

    except Exception as e:
        logger.debug(f"Tree-sitter C# AST parsing failed: {e}")
        # Fallback to regex on any error
        return _extract_flags_csharp_regex_fallback(content)


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
    # More precise pattern to avoid false positives
    direct_pattern = r'(?:^|[^a-zA-Z])GetTreatments?(?:WithConfig)?(?:Async)?\s*\([^)]*?["\']([^"\']+?)["\']'
    direct_matches = re.findall(direct_pattern, content)
    flags.extend(direct_matches)

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
