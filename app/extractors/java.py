"""Java feature flag extraction using AST parsing."""

import logging
from typing import List

try:
    import javalang
except ImportError:
    javalang = None

logger = logging.getLogger(__name__)


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
                elif isinstance(node.initializer, javalang.tree.MethodInvocation):
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
                            if isinstance(list_arg, javalang.tree.Literal) and isinstance(list_arg.value, str):
                                flag_value = list_arg.value[1:-1] if list_arg.value.startswith('"') else list_arg.value
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
                        if isinstance(arg, javalang.tree.Literal) and isinstance(arg.value, str):
                            # Remove quotes from string literal
                            flag_value = arg.value[1:-1] if arg.value.startswith('"') else arg.value
                            flags.append(flag_value)
                        elif isinstance(arg, javalang.tree.MemberReference) and arg.member in variables:
                            var_value = variables[arg.member]
                            if isinstance(var_value, str):
                                flags.append(var_value)
                            elif isinstance(var_value, list):
                                flags.extend(var_value)  # Add all flags from array variable
                        elif isinstance(arg, javalang.tree.MethodInvocation):
                            # Handle Arrays.asList("flag1", "flag2", "flag3")
                            if hasattr(arg, "member") and arg.member == "asList":
                                # Check for Arrays.asList pattern - qualifier can be a string
                                is_arrays_aslist = False
                                if hasattr(arg, "qualifier"):
                                    if isinstance(arg.qualifier, str) and arg.qualifier == "Arrays":
                                        is_arrays_aslist = True
                                    elif (
                                        isinstance(
                                            arg.qualifier,
                                            javalang.tree.MemberReference,
                                        )
                                        and arg.qualifier.member == "Arrays"
                                    ):
                                        is_arrays_aslist = True
                                    elif hasattr(arg.qualifier, "value") and arg.qualifier.value == "Arrays":
                                        is_arrays_aslist = True

                                if is_arrays_aslist:
                                    for list_arg in arg.arguments:
                                        if isinstance(list_arg, javalang.tree.Literal) and isinstance(list_arg.value, str):
                                            flag_value = list_arg.value[1:-1] if list_arg.value.startswith('"') else list_arg.value
                                            flags.append(flag_value)
                        elif isinstance(arg, javalang.tree.ArrayCreator):
                            # Handle array literals: new String[]{"flag1", "flag2", "flag3"} (fallback)
                            if hasattr(arg, "initializer") and hasattr(arg.initializer, "initializers"):
                                for element in arg.initializer.initializers:
                                    if isinstance(element, javalang.tree.Literal) and isinstance(element.value, str):
                                        flag_value = element.value[1:-1] if element.value.startswith('"') else element.value
                                        flags.append(flag_value)

        return list(set(flags))

    except Exception as e:
        logger.debug(f"Java AST parsing failed: {e}")
        return []
