#!/usr/bin/env python3

import os
import sys
import requests
import time
import logging
import subprocess
import ast
import re
from typing import Dict, List
from splitapiclient.main import get_client
from pytimeparse import parse as parse_duration

try:
    import esprima
except ImportError:
    esprima = None

try:
    import javalang
except ImportError:
    javalang = None

try:
    from git import Repo
except ImportError:
    Repo = None

try:
    import tree_sitter
except ImportError:
    tree_sitter = None

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ErrorMessageFormatter:
    """Provides comprehensive, actionable error messages with troubleshooting guidance"""

    @staticmethod
    def format_flag_removal_error(
        flag_name: str, tag_name: str, files_with_flag: List[str] = None
    ) -> str:
        """Format error message for flags marked for removal"""
        message = f"""
╔══════════════════════════════════════════════════════════════════════
║ ❌ FEATURE FLAG REMOVAL REQUIRED
╠══════════════════════════════════════════════════════════════════════
║ Flag: '{flag_name}'
║ Issue: Flag has removal tag '{tag_name}'
║ 
║ 🔧 REQUIRED ACTIONS:
║ 1. Remove all references to '{flag_name}' from your code
║ 2. Clean up any related configuration or documentation
║ 3. Consider the impact on users and gradual rollout strategy
║ 
║ 📁 FILES CONTAINING THIS FLAG:"""

        if files_with_flag:
            for file_path in files_with_flag:
                message += f"\n║    • {file_path}"
        else:
            message += f"\n║    • (Run git grep '{flag_name}' to locate all references)"

        message += """
║ 
║ 💡 HELPFUL COMMANDS:
║    git grep -n "{flag}" --exclude-dir=node_modules
║    rg "{flag}" --type js --type java --type py
║ 
║ 📖 DOCUMENTATION:
║    Best Practices: https://developer.harness.io/docs/feature-management-experimentation/getting-started/overview/manage-the-feature-flag-lifecycle/
╚══════════════════════════════════════════════════════════════════════""".format(
            flag=flag_name
        )

        return message

    @staticmethod
    def format_flag_count_error(
        current_count: int, max_allowed: int, flags_in_code: List[str]
    ) -> str:
        """Format error message for flag count limit exceeded"""
        excess_count = current_count - max_allowed
        return f"""
╔══════════════════════════════════════════════════════════════════════
║ ❌ FEATURE FLAG COUNT LIMIT EXCEEDED
╠══════════════════════════════════════════════════════════════════════
║ Current Flags: {current_count}
║ Maximum Allowed: {max_allowed}
║ Excess Count: {excess_count}
║ 
║ 🔧 REQUIRED ACTIONS:
║ 1. Remove {excess_count} feature flag(s) from your code
║ 2. Consider consolidating similar flags
║ 3. Remove unused or deprecated flags
║ 
║ 📋 ALL FLAGS IN CODE:
║    {chr(10).join([f'    • {flag}' for flag in sorted(flags_in_code)])}
║ 
║ 💡 STRATEGIES TO REDUCE FLAG COUNT:
║    • Identify flags at 100% rollout for removal
║    • Combine similar feature toggles
║    • Remove experiment flags after conclusion
║    • Archive flags not used in production
║ 
║ 📖 GOVERNANCE GUIDE:
║    Flag Management: https://developer.harness.io/docs/feature-management-experimentation/getting-started/overview/manage-the-feature-flag-lifecycle/
╚══════════════════════════════════════════════════════════════════════"""

    @staticmethod
    def format_stale_flag_error(
        flag_name: str,
        threshold: str,
        last_activity: str,
        flag_type: str = "modified",
    ) -> str:
        """Format error message for stale flags"""
        return f"""
╔══════════════════════════════════════════════════════════════════════
║ ❌ STALE FEATURE FLAG DETECTED
╠══════════════════════════════════════════════════════════════════════
║ Flag: '{flag_name}'
║ Issue: Flag hasn't been {flag_type} in {threshold}
║ Last Activity: {last_activity}
║ 
║ 🔧 REQUIRED ACTIONS:
║ 1. Review if this flag is still needed
║ 2. If needed, add 'permanent' tag to exclude from stale checks
║ 3. If not needed, plan removal strategy
║ 4. Update flag configuration if actively used
║ 
║ 🏷️  TO MARK AS PERMANENT:
║    • Add tag 'permanent' or 'keep' in Harness UI
║    • This will exclude it from future stale flag checks
║ 
║ 🗑️  TO REMOVE SAFELY:
║    1. Verify flag is not actively used in production
║    2. Check traffic metrics and user impact
║    3. Plan gradual removal if needed
║    4. Remove from code and Harness configuration
║ 
║ 📊 CHECK FLAG USAGE:
║    • Review analytics in Harness dashboard
║    • Check production traffic patterns
║    • Verify with product/engineering teams
║ 
║ 📖 RESOURCES:
║    Flag Lifecycle: https://developer.harness.io/docs/feature-management-experimentation/getting-started/overview/manage-the-feature-flag-lifecycle/
╚══════════════════════════════════════════════════════════════════════"""

    @staticmethod
    def format_api_error(
        error_type: str, details: str, suggestions: List[str]
    ) -> str:
        """Format error message for API connectivity issues"""
        suggestion_text = "\n".join(
            [
                f"║    {i+1}. {suggestion}"
                for i, suggestion in enumerate(suggestions)
            ]
        )

        return f"""
╔══════════════════════════════════════════════════════════════════════
║ ❌ HARNESS API CONNECTION ERROR
╠══════════════════════════════════════════════════════════════════════
║ Error Type: {error_type}
║ Details: {details}
║ 
║ 🔧 TROUBLESHOOTING STEPS:
{suggestion_text}
║ 
║ 🔑 VERIFY CREDENTIALS:
║    • Check HARNESS_API_TOKEN is valid and not expired
║    • Verify HARNESS_ACCOUNT_ID is correct
║    • Confirm HARNESS_PROJECT_ID exists
║ 
║ 🌐 NETWORK DIAGNOSTICS:
║    curl -H "x-api-key: $HARNESS_API_TOKEN" \\
║         https://app.harness.io/ng/api/projects
║ 
║ 📖 HARNESS API DOCS:
║    Authentication: https://developer.harness.io/docs/platform/automation/api/api-permissions-reference
║    Getting Started: https://developer.harness.io/docs/platform/automation/api/api-quickstart
╚══════════════════════════════════════════════════════════════════════"""

    @staticmethod
    def format_configuration_error(
        missing_vars: List[str], optional_vars: List[str] = None
    ) -> str:
        """Format error message for configuration issues"""
        required_text = "\n".join([f"║    • {var}" for var in missing_vars])
        optional_text = ""
        if optional_vars:
            optional_text = f"""
║ 
║ 🔧 OPTIONAL CONFIGURATION:
║    These can enhance functionality:
{chr(10).join([f'║    • {var}' for var in optional_vars])}"""

        return f"""
╔══════════════════════════════════════════════════════════════════════
║ ❌ CONFIGURATION ERROR
╠══════════════════════════════════════════════════════════════════════
║ Missing required environment variables
║ 
║ 🔑 REQUIRED VARIABLES:
{required_text}{optional_text}
║ 
║ 
║ 🚀 FOR DRONE/HARNESS CI:
║    steps:
║    - name: feature-flag-check
║      image: your-registry/feature-flag-ci-plugin
║      settings:
║        harness_api_token:
║          from_secret: harness_token
║ 
╚══════════════════════════════════════════════════════════════════════"""


def extract_flags_ast_javascript(content: str) -> List[str]:
    """Extract feature flags from JavaScript using AST parsing"""
    if not esprima:
        return []

    try:
        tree = esprima.parseScript(content)
        variables = {}
        flags = []

        def walk_node(node):
            if hasattr(node, "type"):
                # Variable declarations: const FLAG_NAME = "my-flag" or const FLAG_ARRAY = ["flag1", "flag2"]
                if getattr(node, "type") == "VariableDeclaration":
                    for decl in getattr(node, "declarations", []):
                        if (
                            hasattr(decl, "id")
                            and getattr(decl.id, "type", None) == "Identifier"
                            and hasattr(decl, "init")
                        ):
                            var_name = decl.id.name

                            # Handle string literal variables
                            if getattr(
                                decl.init, "type", None
                            ) == "Literal" and isinstance(
                                getattr(decl.init, "value", None), str
                            ):
                                variables[var_name] = decl.init.value

                            # Handle array literal variables: const FLAG_ARRAY = ["flag1", "flag2"]
                            elif (
                                getattr(decl.init, "type", None)
                                == "ArrayExpression"
                            ):
                                array_values = []
                                for element in getattr(
                                    decl.init, "elements", []
                                ):
                                    if getattr(
                                        element, "type", None
                                    ) == "Literal" and isinstance(
                                        getattr(element, "value", None), str
                                    ):
                                        array_values.append(element.value)
                                if (
                                    array_values
                                ):  # Only store if we found string values
                                    variables[var_name] = array_values

                # Method calls: getTreatment(FLAG_NAME) - extract all string arguments
                elif getattr(node, "type") == "CallExpression":
                    callee = getattr(node, "callee", None)
                    if (
                        callee
                        and getattr(callee, "type", None) == "MemberExpression"
                        and hasattr(callee, "property")
                        and getattr(callee.property, "name", None)
                        in [
                            "getTreatment",
                            "treatment",
                            "getTreatmentWithConfig",
                            "getTreatments",
                            "getTreatmentsWithConfig",
                        ]
                    ):
                        # Extract all string arguments - safer approach for different SDK signatures
                        for arg in getattr(node, "arguments", []):
                            if getattr(
                                arg, "type", None
                            ) == "Literal" and isinstance(
                                getattr(arg, "value", None), str
                            ):
                                flags.append(arg.value)
                            elif (
                                getattr(arg, "type", None) == "Identifier"
                                and getattr(arg, "name", None) in variables
                            ):
                                var_value = variables[arg.name]
                                if isinstance(var_value, str):
                                    flags.append(var_value)
                                elif isinstance(var_value, list):
                                    flags.extend(
                                        var_value
                                    )  # Add all flags from array variable
                            elif (
                                getattr(arg, "type", None) == "ArrayExpression"
                            ):
                                # Handle array literals: ['flag1', 'flag2', 'flag3']
                                for element in getattr(arg, "elements", []):
                                    if getattr(
                                        element, "type", None
                                    ) == "Literal" and isinstance(
                                        getattr(element, "value", None), str
                                    ):
                                        flags.append(element.value)
                                    elif (
                                        getattr(element, "type", None)
                                        == "Identifier"
                                        and getattr(element, "name", None)
                                        in variables
                                    ):
                                        flags.append(variables[element.name])

            # Recursively walk child nodes
            if hasattr(node, "__dict__"):
                for key, value in node.__dict__.items():
                    if hasattr(value, "type"):
                        walk_node(value)
                    elif isinstance(value, list):
                        for item in value:
                            if hasattr(item, "type"):
                                walk_node(item)

        walk_node(tree)
        return list(set(flags))

    except Exception as e:
        logger.debug(f"JavaScript AST parsing failed: {e}")
        return []


def extract_flags_ast_java(content: str) -> List[str]:
    """Extract feature flags from Java using AST parsing"""
    if not javalang:
        return []

    try:
        tree = javalang.parse.parse(content)
        variables = {}
        flags = []

        for path, node in tree:
            # Variable declarations: String FLAG_NAME = "my-flag"; or List<String> flags = Arrays.asList("flag1", "flag2");
            if isinstance(node, javalang.tree.VariableDeclarator):
                if (
                    isinstance(node.initializer, javalang.tree.Literal)
                    and isinstance(node.initializer.value, str)
                    and node.initializer.value.startswith('"')
                    and node.initializer.value.endswith('"')
                ):
                    # Remove quotes from string literal
                    flag_value = node.initializer.value[1:-1]
                    variables[node.name] = flag_value
                elif isinstance(
                    node.initializer, javalang.tree.MethodInvocation
                ):
                    # Handle Arrays.asList("flag1", "flag2") in variable declarations
                    if (
                        hasattr(node.initializer, "member")
                        and node.initializer.member == "asList"
                        and hasattr(node.initializer, "qualifier")
                        and isinstance(node.initializer.qualifier, str)
                        and node.initializer.qualifier == "Arrays"
                    ):
                        array_values = []
                        for list_arg in node.initializer.arguments:
                            if isinstance(
                                list_arg, javalang.tree.Literal
                            ) and isinstance(list_arg.value, str):
                                flag_value = (
                                    list_arg.value[1:-1]
                                    if list_arg.value.startswith('"')
                                    else list_arg.value
                                )
                                array_values.append(flag_value)
                        if array_values:
                            variables[node.name] = array_values

            # Method calls: client.getTreatment(FLAG_NAME) - extract all string arguments
            elif isinstance(node, javalang.tree.MethodInvocation):
                if node.member in [
                    "getTreatment",
                    "treatment",
                    "getTreatmentWithConfig",
                    "getTreatments",
                    "getTreatmentsWithConfig",
                ]:
                    # Extract all string arguments - safer approach for different SDK signatures
                    for arg in node.arguments:
                        if isinstance(
                            arg, javalang.tree.Literal
                        ) and isinstance(arg.value, str):
                            # Remove quotes from string literal
                            flag_value = (
                                arg.value[1:-1]
                                if arg.value.startswith('"')
                                else arg.value
                            )
                            flags.append(flag_value)
                        elif (
                            isinstance(arg, javalang.tree.MemberReference)
                            and arg.member in variables
                        ):
                            var_value = variables[arg.member]
                            if isinstance(var_value, str):
                                flags.append(var_value)
                            elif isinstance(var_value, list):
                                flags.extend(
                                    var_value
                                )  # Add all flags from array variable
                        elif isinstance(arg, javalang.tree.MethodInvocation):
                            # Handle Arrays.asList("flag1", "flag2", "flag3")
                            if (
                                hasattr(arg, "member")
                                and arg.member == "asList"
                            ):
                                # Check for Arrays.asList pattern - qualifier can be a string
                                is_arrays_aslist = False
                                if hasattr(arg, "qualifier"):
                                    if (
                                        isinstance(arg.qualifier, str)
                                        and arg.qualifier == "Arrays"
                                    ):
                                        is_arrays_aslist = True
                                    elif (
                                        isinstance(
                                            arg.qualifier,
                                            javalang.tree.MemberReference,
                                        )
                                        and arg.qualifier.member == "Arrays"
                                    ):
                                        is_arrays_aslist = True
                                    elif (
                                        hasattr(arg.qualifier, "value")
                                        and arg.qualifier.value == "Arrays"
                                    ):
                                        is_arrays_aslist = True

                                if is_arrays_aslist:
                                    for list_arg in arg.arguments:
                                        if isinstance(
                                            list_arg, javalang.tree.Literal
                                        ) and isinstance(list_arg.value, str):
                                            flag_value = (
                                                list_arg.value[1:-1]
                                                if list_arg.value.startswith(
                                                    '"'
                                                )
                                                else list_arg.value
                                            )
                                            flags.append(flag_value)
                        elif isinstance(arg, javalang.tree.ArrayCreator):
                            # Handle array literals: new String[]{"flag1", "flag2", "flag3"} (fallback)
                            if hasattr(arg, "initializer") and hasattr(
                                arg.initializer, "initializers"
                            ):
                                for element in arg.initializer.initializers:
                                    if isinstance(
                                        element, javalang.tree.Literal
                                    ) and isinstance(element.value, str):
                                        flag_value = (
                                            element.value[1:-1]
                                            if element.value.startswith('"')
                                            else element.value
                                        )
                                        flags.append(flag_value)

        return list(set(flags))

    except Exception as e:
        logger.debug(f"Java AST parsing failed: {e}")
        return []


def extract_flags_ast_python(content: str) -> List[str]:
    """Extract feature flags from Python using AST parsing"""
    try:
        # Handle indented code by dedenting it first
        import textwrap

        content = textwrap.dedent(content)
        tree = ast.parse(content)
        variables = {}
        flags = []

        for node in ast.walk(tree):
            # Variable assignments: FLAG_NAME = "my-flag" or FLAG_LIST = ["flag1", "flag2"]
            if isinstance(node, ast.Assign):
                if len(node.targets) == 1 and isinstance(
                    node.targets[0], ast.Name
                ):
                    var_name = node.targets[0].id

                    # Handle string literal assignments
                    if isinstance(node.value, ast.Constant) and isinstance(
                        node.value.value, str
                    ):
                        variables[var_name] = node.value.value

                    # Handle list literal assignments: FLAG_LIST = ["flag1", "flag2"]
                    elif isinstance(node.value, ast.List):
                        array_values = []
                        for element in node.value.elts:
                            if isinstance(
                                element, ast.Constant
                            ) and isinstance(element.value, str):
                                array_values.append(element.value)
                        if (
                            array_values
                        ):  # Only store if we found string values
                            variables[var_name] = array_values

            # Method calls: client.getTreatment(FLAG_NAME) - extract all string arguments
            elif isinstance(node, ast.Call):
                # Handle both attribute calls and direct calls
                method_name = None
                if isinstance(node.func, ast.Attribute):
                    method_name = node.func.attr
                elif isinstance(node.func, ast.Name):
                    method_name = node.func.id

                if method_name in [
                    "getTreatment",
                    "get_treatment",
                    "treatment",
                    "get_treatment_with_config",
                    "getTreatments",
                    "get_treatments",
                    "get_treatments_with_config",
                ]:
                    # Extract all string arguments - safer approach for different SDK signatures
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and isinstance(
                            arg.value, str
                        ):
                            flags.append(arg.value)
                        elif isinstance(arg, ast.Name) and arg.id in variables:
                            var_value = variables[arg.id]
                            if isinstance(var_value, str):
                                flags.append(var_value)
                            elif isinstance(var_value, list):
                                flags.extend(
                                    var_value
                                )  # Add all flags from list variable
                        elif isinstance(arg, ast.List):
                            # Handle list literals: ['flag1', 'flag2', 'flag3']
                            for element in arg.elts:
                                if isinstance(
                                    element, ast.Constant
                                ) and isinstance(element.value, str):
                                    flags.append(element.value)
                                elif (
                                    isinstance(element, ast.Name)
                                    and element.id in variables
                                ):
                                    flags.append(variables[element.id])

        return list(set(flags))

    except Exception as e:
        logger.debug(f"Python AST parsing failed: {e}")
        return []


def extract_flags_ast_csharp(content: str) -> List[str]:
    """Extract feature flags from C# using tree-sitter AST parsing"""
    if not tree_sitter:
        # Fallback to regex if tree-sitter is not available
        return _extract_flags_csharp_regex_fallback(content)

    try:
        # Try to set up tree-sitter C# parser
        Language = tree_sitter.Language

        # Try to load the C# language from the cloned repository
        import os

        csharp_grammar_path = os.path.join(os.getcwd(), "tree-sitter-c-sharp")
        if not os.path.exists(csharp_grammar_path):
            # Fallback to regex if grammar not available
            return _extract_flags_csharp_regex_fallback(content)

        # Build and load C# language
        try:
            csharp_language = Language.build_library(
                "build/csharp.so", [csharp_grammar_path]
            )
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
                                var_name = content[
                                    declarator_child.start_byte : declarator_child.end_byte
                                ]
                            elif (
                                declarator_child.type == "equals_value_clause"
                            ):
                                for value_child in declarator_child.children:
                                    if value_child.type == "string_literal":
                                        # Remove quotes from string literal
                                        var_value = content[
                                            value_child.start_byte
                                            + 1 : value_child.end_byte
                                            - 1
                                        ]

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
                                method_name = content[
                                    member_child.start_byte : member_child.end_byte
                                ]
                    elif child.type == "identifier":
                        method_name = content[
                            child.start_byte : child.end_byte
                        ]

                # Check if this is a feature flag method (including plural forms and async variants)
                if method_name and (
                    "GetTreatment" in method_name or "Treatment" in method_name
                ):
                    # Extract arguments
                    for child in node.children:
                        if child.type == "argument_list":
                            for arg_child in child.children:
                                if arg_child.type == "argument":
                                    for arg_value in arg_child.children:
                                        if arg_value.type == "string_literal":
                                            # Extract string literal value (remove quotes)
                                            flag_value = content[
                                                arg_value.start_byte
                                                + 1 : arg_value.end_byte
                                                - 1
                                            ]
                                            flags.append(flag_value)
                                        elif arg_value.type == "identifier":
                                            # Variable reference for single flags
                                            var_name = content[
                                                arg_value.start_byte : arg_value.end_byte
                                            ]
                                            if var_name in variables:
                                                flags.append(
                                                    variables[var_name]
                                                )
                                        elif (
                                            arg_value.type
                                            == "object_creation_expression"
                                        ):
                                            # Handle: new List<string> { "flag1", "flag2" }
                                            for (
                                                creation_child
                                            ) in arg_value.children:
                                                if (
                                                    creation_child.type
                                                    == "initializer_expression"
                                                ):
                                                    for (
                                                        init_child
                                                    ) in (
                                                        creation_child.children
                                                    ):
                                                        if (
                                                            init_child.type
                                                            == "string_literal"
                                                        ):
                                                            flag_value = content[
                                                                init_child.start_byte
                                                                + 1 : init_child.end_byte
                                                                - 1
                                                            ]
                                                            flags.append(
                                                                flag_value
                                                            )

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
    var_pattern = (
        r'string\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*["\']([^"\']+)["\'];'
    )
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


class CITestRunner:
    def __init__(self):
        self.commit_before = os.getenv("DRONE_COMMIT_BEFORE", "HEAD")
        self.commit_after = os.getenv("DRONE_COMMIT_AFTER", "HEAD")
        self.code_changes = self.get_code_changes()
        self.api_base_url = os.getenv("API_BASE_URL", "https://app.harness.io")
        self.harness_token = os.getenv("HARNESS_API_TOKEN", "none")
        self.harness_account = os.getenv("HARNESS_ACCOUNT_ID", "none")
        self.harness_project = os.getenv("HARNESS_PROJECT_ID", "none")
        self.production_environment_name = os.getenv(
            "PLUGIN_PRODUCTION_ENVIRONMENT_NAME", "Production"
        )
        self.permanent_flags_tag = os.getenv("PLUGIN_TAG_PERMANENT_FLAGS", "")
        self.remove_these_flags_tag = os.getenv(
            "PLUGIN_TAG_REMOVE_THESE_FLAGS", ""
        )
        self.max_flags_in_project = os.getenv(
            "PLUGIN_MAX_FLAGS_IN_PROJECT", "-1"
        )
        self.flag_last_modified_threshold = os.getenv(
            "PLUGIN_FLAG_LAST_MODIFIED_THRESHOLD", "-1"
        )
        self.flag_last_traffic_threshold = os.getenv(
            "PLUGIN_FLAG_LAST_TRAFFIC_THRESHOLD", "-1"
        )
        self.flag_at_100_percent_last_modified_threshold = os.getenv(
            "PLUGIN_FLAG_AT_100_PERCENT_LAST_MODIFIED_THRESHOLD", "-1"
        )
        self.flag_at_100_percent_last_traffic_threshold = os.getenv(
            "PLUGIN_FLAG_AT_100_PERCENT_LAST_TRAFFIC_THRESHOLD", "-1"
        )

        # Validate required configuration
        if not self._validate_configuration():
            sys.exit(1)

        self.flag_data = []
        self.metaFlagData = {}  # Dictionary for fast flag lookup by name
        self.flags_in_code = []
        self.client = get_client(
            harness_mode=True,
            harness_token=self.harness_token,
            account_identifier=self.harness_account,
        )

        # Initialize data - will be populated by separate method calls
        if not self.get_flags():
            logger.error(
                "Failed to fetch flags from Harness - some tests may not work correctly"
            )

        if not self.get_feature_flags_in_code():
            logger.error(
                "Failed to analyze code for flags - some tests may not work correctly"
            )

    def _validate_configuration(self) -> bool:
        """Validate required environment variables and configuration"""
        missing_required = []
        optional_vars = []

        # Check required variables for Harness API
        harness_vars = {
            "HARNESS_API_TOKEN": self.harness_token,
            "HARNESS_ACCOUNT_ID": self.harness_account,
            "HARNESS_PROJECT_ID": self.harness_project,
        }

        # Check required variables for Drone CI
        drone_vars = {
            "DRONE_COMMIT_BEFORE": self.commit_before,
            "DRONE_COMMIT_AFTER": self.commit_after,
        }

        for var_name, var_value in harness_vars.items():
            if var_value == "none" or not var_value:
                missing_required.append(var_name)

        for var_name, var_value in drone_vars.items():
            if var_value == "HEAD":  # Default value means not set
                missing_required.append(var_name)

        # List optional variables for user information
        if self.remove_these_flags_tag == "":
            optional_vars.append(
                "PLUGIN_TAG_REMOVE_THESE_FLAGS (for tag-based flag removal)"
            )

        if self.permanent_flags_tag == "":
            optional_vars.append(
                "PLUGIN_TAG_PERMANENT_FLAGS (to exclude flags from stale checks)"
            )

        if self.max_flags_in_project == "-1":
            optional_vars.append(
                "PLUGIN_MAX_FLAGS_IN_PROJECT (for flag count limits)"
            )

        if self.flag_last_modified_threshold == "-1":
            optional_vars.append(
                "PLUGIN_FLAG_LAST_MODIFIED_THRESHOLD (for stale flag detection)"
            )

        if self.flag_last_traffic_threshold == "-1":
            optional_vars.append(
                "PLUGIN_FLAG_LAST_TRAFFIC_THRESHOLD (for unused flag detection)"
            )

        if self.flag_at_100_percent_last_modified_threshold == "-1":
            optional_vars.append(
                "PLUGIN_FLAG_AT_100_PERCENT_LAST_MODIFIED_THRESHOLD (for 100% flag staleness)"
            )

        if self.flag_at_100_percent_last_traffic_threshold == "-1":
            optional_vars.append(
                "PLUGIN_FLAG_AT_100_PERCENT_LAST_TRAFFIC_THRESHOLD (for 100% flag traffic)"
            )

        if missing_required:
            error_msg = ErrorMessageFormatter.format_configuration_error(
                missing_required, optional_vars
            )
            logger.error(error_msg)
            return False

        return True

    def get_flags(self):
        try:
            # Fetch projects with timeout and error handling
            url = f"{self.api_base_url}/ng/api/projects?accountIdentifier={self.harness_account}"
            headers = {"x-api-key": self.harness_token}

            logger.info(f"Fetching projects from Harness API: {url}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()  # Raises HTTPError for bad responses

            try:
                projects_data = response.json()
            except ValueError as e:
                logger.error(f"Invalid JSON response from Harness API: {e}")
                return False

            # Validate response structure
            if (
                not isinstance(projects_data, dict)
                or "data" not in projects_data
            ):
                logger.error("Unexpected response structure from Harness API")
                return False

            if "content" not in projects_data.get("data", {}):
                logger.error("No 'content' field in projects response")
                return False

            # Find the target project
            harness_project = None
            for project in projects_data["data"]["content"]:
                if project.get("identifier") == self.harness_project:
                    harness_project = project
                    break

            if not harness_project:
                logger.error(
                    f"Project '{self.harness_project}' not found in account '{self.harness_account}'"
                )
                return False

            logger.info(
                f"Found project: {harness_project.get('name', 'Unknown')}"
            )

            # Get workspace and flag data with error handling
            try:
                workspace = self.client.workspaces.find(
                    harness_project["name"]
                )
                if not workspace:
                    logger.error(
                        f"Workspace not found for project: {harness_project['name']}"
                    )
                    return False

                logger.info(f"Found workspace: {workspace.id}")

                metaFlagDefs = self.client.splits.list(workspace.id)
                # Convert to dictionary for faster lookups by flag name
                self.metaFlagData = {flag.name: flag for flag in metaFlagDefs}
                logger.info(
                    f"Loaded {len(self.metaFlagData)} flag definitions"
                )

                environments = self.client.environments.list(workspace.id)

                production_env_found = False
                for environment in environments:
                    if (
                        environment.get("name")
                        == self.production_environment_name
                    ):
                        production_env_found = True
                        logger.info(
                            f"Found production environment: {environment.get('name')}"
                        )

                        flagDefs = self.client.split_definitions.list(
                            workspace.id, environment.id
                        )
                        for flagDef in flagDefs:
                            self.flag_data.append(flagDef)

                        logger.info(
                            f"Loaded {len(self.flag_data)} production flag configurations"
                        )
                        break

                if not production_env_found:
                    logger.warning(
                        f"Production environment '{self.production_environment_name}' not found"
                    )

            except Exception as e:
                logger.error(f"Error accessing Harness Split.io client: {e}")
                return False

            return True

        except requests.exceptions.Timeout:
            error_msg = ErrorMessageFormatter.format_api_error(
                "Connection Timeout",
                "Request to Harness API timed out after 30 seconds",
                [
                    "Check your network connectivity",
                    "Verify firewall settings allow HTTPS to app.harness.io",
                    "Try running the curl command manually to test connectivity",
                    "Check if Harness API is experiencing downtime",
                ],
            )
            logger.error(error_msg)
            return False
        except requests.exceptions.ConnectionError:
            error_msg = ErrorMessageFormatter.format_api_error(
                "Network Connection Error",
                "Cannot establish connection to Harness API",
                [
                    "Check internet connectivity",
                    "Verify DNS resolution for app.harness.io",
                    "Check proxy settings if behind corporate firewall",
                    "Try accessing https://app.harness.io in browser",
                ],
            )
            logger.error(error_msg)
            return False
        except requests.exceptions.HTTPError as e:
            status_code = getattr(e.response, "status_code", "Unknown")
            error_suggestions = []

            if status_code == 401:
                error_suggestions = [
                    "Verify HARNESS_API_TOKEN is correct and not expired",
                    "Check if token has required permissions for Feature Flags",
                    "Generate a new API token from Harness UI if needed",
                ]
            elif status_code == 403:
                error_suggestions = [
                    "API token lacks permissions for this project",
                    "Verify HARNESS_ACCOUNT_ID and HARNESS_PROJECT_ID are correct",
                    "Check token permissions in Harness Access Control",
                ]
            elif status_code == 404:
                error_suggestions = [
                    "Verify project exists and IDs are correct",
                    "Check if project has Feature Flags enabled",
                    "Confirm account/org/project hierarchy is correct",
                ]
            else:
                error_suggestions = [
                    "Check Harness API status page for known issues",
                    "Retry the operation after a brief delay",
                    "Contact Harness support if problem persists",
                ]

            error_msg = ErrorMessageFormatter.format_api_error(
                f"HTTP {status_code} Error", str(e), error_suggestions
            )
            logger.error(error_msg)
            return False
        except requests.exceptions.RequestException as e:
            error_msg = ErrorMessageFormatter.format_api_error(
                "Request Error",
                str(e),
                [
                    "Check if all required environment variables are set",
                    "Verify API endpoint URL is correct",
                    "Check request format and headers",
                    "Review network configuration",
                ],
            )
            logger.error(error_msg)
            return False
        except Exception as e:
            error_msg = ErrorMessageFormatter.format_api_error(
                "Unexpected Error",
                str(e),
                [
                    "Check all environment variables are properly set",
                    "Verify Python dependencies are installed correctly",
                    "Enable debug logging for more details",
                    "Report this issue if it persists",
                ],
            )
            logger.error(error_msg)
            return False

    def get_code_changes(self) -> List[str]:
        """Get list of changed files between commits using Harness Code Repository API"""
        try:
            # Try Harness Code API first
            repo_name = os.getenv("DRONE_REPO_NAME") # os.getenv("HARNESS_REPO_NAME") or os.getenv("DRONE_REPO_NAME")
            api_token = self.harness_token
            account_id = self.harness_account
            
            if repo_name and api_token and account_id:
                url = f"{self.api_base_url}/code/api/v1/repos/{repo_name}/diff/{self.commit_before}...{self.commit_after}"
                headers = {
                    "x-api-key": api_token,
                    "Harness-Account": account_id
                }
                
                logger.info(f"Fetching changes from Harness API: {self.commit_before}...{self.commit_after}")
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                # Handle both array response and object with 'files' key
                if isinstance(data, list):
                    changed_files = [file['path'] for file in data]
                else:
                    changed_files = [file['path'] for file in data.get('files', [])]
                
                logger.info(f"Found {len(changed_files)} changed files via Harness API")
                return changed_files
            
            # Fallback to GitPython/subprocess
            logger.warning("Harness API credentials not available, falling back to local git")
            if Repo is None:
                logger.error("GitPython not available, falling back to subprocess")
                result = subprocess.run(
                    [
                        "git",
                        "diff",
                        "--name-only",
                        self.commit_before,
                        self.commit_after,
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                changed_files = (
                    result.stdout.strip().split("\n")
                    if result.stdout.strip()
                    else []
                )
            else:
                repo = Repo('.')
                diff_output = repo.git.diff('--name-only', self.commit_before, self.commit_after)
                changed_files = diff_output.strip().split('\n') if diff_output.strip() else []
            
            logger.info(
                f"Found {len(changed_files)} changed files between {self.commit_before} and {self.commit_after}"
            )
            return changed_files
        except Exception as e:
            logger.error(f"Failed to get code changes: {e}")
            return []

    def get_feature_flags_in_code(self) -> bool:
        """Search for feature flags using AST parsing with regex fallback"""
        feature_flags = []
        self.flag_file_mapping = {}  # Track which files contain which flags

        # Get all changed files and analyze them
        for file_path in self.code_changes:
            try:
                # Read the current content of the file
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()

                # Determine parsing method based on file extension
                file_flags = []
                if file_path.endswith(".js") or file_path.endswith(".jsx"):
                    file_flags = extract_flags_ast_javascript(file_content)
                    method = "JavaScript AST"
                elif file_path.endswith(".java"):
                    file_flags = extract_flags_ast_java(file_content)
                    method = "Java AST"
                elif file_path.endswith(".py"):
                    file_flags = extract_flags_ast_python(file_content)
                    method = "Python AST"
                elif file_path.endswith(".cs"):
                    file_flags = extract_flags_ast_csharp(file_content)
                    method = "C# AST"
                else:
                    file_flags = extract_flags_regex(file_content)
                    method = "Regex"

                # If AST parsing failed or returned nothing, fall back to regex
                if not file_flags and method != "Regex":
                    file_flags = extract_flags_regex(file_content)
                    method += " (fallback to Regex)"

                if file_flags:
                    logger.info(
                        f"Found {len(file_flags)} flags in {file_path} using {method}: {file_flags}"
                    )
                    feature_flags.extend(file_flags)

                    # Track which files contain which flags
                    for flag in file_flags:
                        if flag not in self.flag_file_mapping:
                            self.flag_file_mapping[flag] = []
                        self.flag_file_mapping[flag].append(file_path)
                else:
                    logger.debug(
                        f"No flags found in {file_path} using {method}"
                    )

            except (FileNotFoundError, UnicodeDecodeError) as e:
                logger.warning(f"Could not read file {file_path}: {e}")
                continue

        # Remove duplicates
        feature_flags = list(set(feature_flags))
        logger.info(
            f"Total unique feature flags found: {len(feature_flags)} - {feature_flags}"
        )
        self.flags_in_code = feature_flags
        return True

    def check_if_flags_have_remove_these_tags(self) -> bool:
        for flag in self.flags_in_code:
            # Fast dictionary lookup
            flagMeta = self.metaFlagData.get(flag)

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
                            files_with_flag = self.flag_file_mapping.get(
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

    def check_if_flag_count_exceeds_limit(self) -> bool:
        if int(self.max_flags_in_project) > -1 and len(
            self.flags_in_code
        ) > int(self.max_flags_in_project):
            error_msg = ErrorMessageFormatter.format_flag_count_error(
                len(self.flags_in_code),
                int(self.max_flags_in_project),
                self.flags_in_code,
            )
            logger.error(error_msg)
            return False
        return True

    def _check_flag_threshold(
        self,
        threshold_value: str,
        attribute_name: str,
        error_message_template: str,
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

        for flag in self.flags_in_code:
            # Skip permanent flags - fast dictionary lookup with safe access
            meta_flag = self.metaFlagData.get(flag)
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
            for detail in self.flag_data:
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
                    import datetime

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
                    if self._is_flag_at_100_percent(flag):
                        # Format last activity time
                        import datetime

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

    def check_flag_last_modified_threshold(self) -> bool:
        """Check if any flags were modified beyond the threshold duration"""
        return self._check_flag_threshold(
            self.flag_last_modified_threshold,
            "lastUpdateTime",
            "Feature flag {flag} was last modified {threshold} ago (threshold exceeded)",
        )

    def check_flag_last_traffic_recieved_threshold(self) -> bool:
        """Check if any flags have not received traffic beyond the threshold duration"""
        return self._check_flag_threshold(
            self.flag_last_traffic_threshold,
            "lastTrafficRecievedAt",
            "Feature flag {flag} has not received traffic in {threshold} (threshold exceeded)",
        )

    def _is_flag_at_100_percent(self, flag: str) -> bool:
        """Check if a flag is at 100% traffic allocation"""
        try:
            for flag_detail in self.flag_data:
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

    def check_flag_last_modified_threshold_100_percent(self) -> bool:
        """Check if any flags were modified beyond the threshold duration"""
        return self._check_flag_threshold(
            self.flag_last_modified_threshold,
            "lastUpdateTime",
            "Feature flag {flag} is 100 percent one treatment and was last modified {threshold} ago (threshold exceeded)",
            check_100_percent=True,
        )

    def check_flag_last_traffic_recieved_threshold_100_percent(self) -> bool:
        """Check if any flags have not received traffic beyond the threshold duration"""
        return self._check_flag_threshold(
            self.flag_last_traffic_threshold,
            "lastTrafficRecievedAt",
            "Feature flag {flag} is 100 percent one treatment and has not received traffic in {threshold} (threshold exceeded)",
            check_100_percent=True,
        )

    def _run_test(
        self, test_method, test_name: str, test_results: List[Dict]
    ) -> bool:
        """Helper method to run a single test and handle logging/results"""
        try:
            success = test_method()
            if success:
                logger.info(f"✅ {test_name} passed")
                test_results.append({"test": test_name, "success": True})
            else:
                logger.error(f"❌ {test_name} failed")
            return success
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {e}")
            return False

    def run_tests(self) -> bool:
        """Run all tests and return overall success status"""
        logger.info("Starting CI test run...")
        logger.info("Configuration:")
        logger.info(f"  API Base URL: {self.api_base_url}")
        logger.info(f"  Feature Flags in Code: {self.flags_in_code}")
        logger.info(f"  Feature Flags in Harness: {self.flag_data}")
        logger.info(
            f"  Commit Hashes: {self.commit_before} -> {self.commit_after}"
        )

        test_results = []
        all_tests_passed = True

        # Define all tests to run
        tests = [
            (
                self.check_if_flags_have_remove_these_tags,
                "feature flag removal tag check",
            ),
            (
                self.check_if_flag_count_exceeds_limit,
                "feature flag count check",
            ),
            (
                self.check_flag_last_modified_threshold,
                "feature flag last modified threshold check",
            ),
            (
                self.check_flag_last_traffic_recieved_threshold,
                "feature flag last traffic threshold check",
            ),
            (
                self.check_flag_last_modified_threshold_100_percent,
                "feature flag last modified threshold check for 100 percent flags",
            ),
            (
                self.check_flag_last_traffic_recieved_threshold_100_percent,
                "feature flag last traffic threshold check for 100 percent flags",
            ),
        ]

        # Run all tests
        for test_method, test_name in tests:
            if not self._run_test(test_method, test_name, test_results):
                all_tests_passed = False

        # Print summary
        logger.info("\n" + "=" * 50)
        logger.info("TEST SUMMARY")
        logger.info("=" * 50)

        passed_tests = sum(1 for result in test_results if result["success"])
        total_tests = len(test_results)

        logger.info(f"All Tests: {passed_tests}/{total_tests} passed")
        logger.info(
            f"Overall Result: {'✅ PASS' if all_tests_passed else '❌ FAIL'}"
        )

        return all_tests_passed


def main():
    """Main entry point for the CI test script"""
    logger.info("CI Test Runner starting...")

    runner = CITestRunner()
    success = runner.run_tests()

    if success:
        logger.info("All tests passed! Exiting with code 0")
        sys.exit(0)
    else:
        logger.error("One or more tests failed! Exiting with code 1")
        sys.exit(1)


if __name__ == "__main__":
    main()
