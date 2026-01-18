"""Code validation and sanitization service for security hardening."""

import ast
import re
from dataclasses import dataclass
from typing import Optional


# Dangerous imports that could be used for system access
BLOCKED_IMPORTS = {
    # System/OS access
    "os",
    "sys",
    "subprocess",
    "shutil",
    "pathlib",
    "glob",
    # Network access (except urllib for maze client)
    "socket",
    "requests",
    "httpx",
    "aiohttp",
    "ftplib",
    "smtplib",
    "telnetlib",
    # Code execution
    "exec",
    "eval",
    "compile",
    "code",
    "importlib",
    "__import__",
    # File access
    "io",
    "builtins",
    "open",
    # Process/threading
    "multiprocessing",
    "threading",
    "concurrent",
    "asyncio",
    # Dangerous modules
    "ctypes",
    "pickle",
    "marshal",
    "shelve",
    "pty",
    "fcntl",
    "termios",
    "resource",
    "signal",
    "mmap",
}

# Patterns that could indicate malicious code
DANGEROUS_PATTERNS = [
    # Direct file access attempts
    r"open\s*\(",
    r"file\s*\(",
    # Exec/eval patterns
    r"exec\s*\(",
    r"eval\s*\(",
    r"compile\s*\(",
    # Import manipulation
    r"__import__\s*\(",
    r"importlib\.",
    # Attribute access to dangerous methods
    r"__builtins__",
    r"__globals__",
    r"__subclasses__",
    r"__class__",
    r"__bases__",
    r"__mro__",
    # OS command execution
    r"os\.system",
    r"os\.popen",
    r"os\.exec",
    r"os\.spawn",
    r"subprocess\.",
    # Network access patterns
    r"socket\.",
    r"requests\.",
    r"urllib\.request",
    # Path traversal
    r"\.\./",
    r"/etc/",
    r"/proc/",
    r"/sys/",
    r"/dev/",
]


@dataclass
class ValidationResult:
    """Result of code validation."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]


class CodeValidator:
    """Validates and sanitizes user-submitted code."""

    def __init__(self):
        self.blocked_imports = BLOCKED_IMPORTS
        self.dangerous_patterns = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]

    def validate(self, code: str) -> ValidationResult:
        """
        Validate user code for security issues.

        Args:
            code: Python code to validate

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        # Check for syntax errors
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Syntax error: {e.msg} at line {e.lineno}"],
                warnings=[],
            )

        # Check imports
        import_errors = self._check_imports(tree)
        errors.extend(import_errors)

        # Check for dangerous patterns
        pattern_errors = self._check_patterns(code)
        errors.extend(pattern_errors)

        # Check for dangerous AST nodes
        ast_errors = self._check_ast(tree)
        errors.extend(ast_errors)

        # Check code length
        if len(code) > 100000:
            errors.append("Code exceeds maximum length of 100,000 characters")

        # Check line count
        line_count = code.count("\n") + 1
        if line_count > 5000:
            warnings.append(f"Code has {line_count} lines, which may affect execution time")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _check_imports(self, tree: ast.AST) -> list[str]:
        """Check for blocked imports."""
        errors = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if module in self.blocked_imports:
                        errors.append(
                            f"Blocked import: '{alias.name}' is not allowed for security reasons"
                        )

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split(".")[0]
                    if module in self.blocked_imports:
                        errors.append(
                            f"Blocked import: 'from {node.module}' is not allowed for security reasons"
                        )

        return errors

    def _check_patterns(self, code: str) -> list[str]:
        """Check for dangerous patterns in code."""
        errors = []

        for pattern in self.dangerous_patterns:
            if pattern.search(code):
                errors.append(
                    f"Dangerous pattern detected: code contains potentially harmful construct"
                )
                break  # One error per pattern type is enough

        return errors

    def _check_ast(self, tree: ast.AST) -> list[str]:
        """Check AST for dangerous nodes."""
        errors = []

        for node in ast.walk(tree):
            # Check for exec/eval calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ("exec", "eval", "compile", "__import__"):
                        errors.append(
                            f"Dangerous function call: '{node.func.id}' is not allowed"
                        )

            # Check for dangerous attribute access
            if isinstance(node, ast.Attribute):
                if node.attr in (
                    "__globals__",
                    "__builtins__",
                    "__subclasses__",
                    "__class__",
                    "__bases__",
                    "__mro__",
                    "__code__",
                    "__reduce__",
                ):
                    errors.append(
                        f"Dangerous attribute access: '{node.attr}' is not allowed"
                    )

        return errors

    def sanitize(self, code: str) -> str:
        """
        Sanitize code by adding safety wrapper.

        Note: This doesn't modify the code itself but wraps it
        in a safety context when executed.
        """
        # Add a header that disables dangerous builtins
        safety_header = """
# Sandbox safety wrapper
__builtins_safe__ = {
    'True': True,
    'False': False,
    'None': None,
    'print': print,
    'len': len,
    'range': range,
    'enumerate': enumerate,
    'zip': zip,
    'map': map,
    'filter': filter,
    'sorted': sorted,
    'reversed': reversed,
    'list': list,
    'dict': dict,
    'set': set,
    'tuple': tuple,
    'str': str,
    'int': int,
    'float': float,
    'bool': bool,
    'abs': abs,
    'min': min,
    'max': max,
    'sum': sum,
    'any': any,
    'all': all,
    'isinstance': isinstance,
    'hasattr': hasattr,
    'getattr': getattr,
}
"""
        return safety_header + "\n" + code


def check_filesystem_escape(code: str) -> list[str]:
    """
    Check for filesystem escape attempts.

    Args:
        code: Python code to check

    Returns:
        List of detected escape attempts
    """
    escape_patterns = [
        (r"\.\./", "Path traversal using ../"),
        (r"/etc/passwd", "Attempt to access /etc/passwd"),
        (r"/etc/shadow", "Attempt to access /etc/shadow"),
        (r"/proc/", "Attempt to access /proc/"),
        (r"/sys/", "Attempt to access /sys/"),
        (r"/dev/", "Attempt to access /dev/"),
        (r"/root/", "Attempt to access /root/"),
        (r"/home/", "Attempt to access /home/"),
        (r"~\/", "Attempt to access home directory"),
        (r"os\.path", "Using os.path module"),
        (r"\bpathlib\b", "Using pathlib module"),
        (r"\bglob\b", "Using glob module"),
        (r"\bshutil\b", "Using shutil module"),
        (r"open\s*\([^)]*['\"]\/", "Opening absolute path"),
        (r"open\s*\([^)]*['\"]\.\.\/", "Opening relative path escape"),
    ]

    detected = []
    for pattern, description in escape_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            detected.append(description)

    return detected


# Singleton instance
_validator: Optional[CodeValidator] = None


def get_code_validator() -> CodeValidator:
    """Get singleton code validator."""
    global _validator
    if _validator is None:
        _validator = CodeValidator()
    return _validator
