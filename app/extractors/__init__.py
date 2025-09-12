"""Flag extraction modules for different programming languages."""

from .javascript import extract_flags_ast_javascript
from .java import extract_flags_ast_java
from .python import extract_flags_ast_python
from .csharp import extract_flags_ast_csharp
from .regex_fallback import extract_flags_regex

__all__ = [
    'extract_flags_ast_javascript',
    'extract_flags_ast_java', 
    'extract_flags_ast_python',
    'extract_flags_ast_csharp',
    'extract_flags_regex'
]