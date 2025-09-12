"""JavaScript/TypeScript feature flag extraction using AST parsing."""

import logging
from typing import List

try:
    import esprima
except ImportError:
    esprima = None

logger = logging.getLogger(__name__)


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