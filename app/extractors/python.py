"""Python feature flag extraction using AST parsing."""

import ast
import logging
import textwrap
from typing import List

logger = logging.getLogger(__name__)


def extract_flags_ast_python(content: str) -> List[str]:
    """Extract feature flags from Python using AST parsing"""
    try:
        # Handle indented code by dedenting it first
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