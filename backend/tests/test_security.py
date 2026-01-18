"""Tests for security hardening - code sanitization and filesystem escape prevention."""

import pytest

from app.services.code_validator import (
    CodeValidator,
    ValidationResult,
    check_filesystem_escape,
    get_code_validator,
)


@pytest.mark.asyncio
async def test_code_sanitization():
    """Test that submitted code is properly sanitized and validated."""
    validator = get_code_validator()

    # Test 1: Valid code should pass
    valid_code = """
# Simple maze solving code
result = look()
if result['north'] != 'wall':
    move('north')
elif result['east'] != 'wall':
    move('east')
"""
    result = validator.validate(valid_code)
    assert result.is_valid is True
    assert len(result.errors) == 0

    # Test 2: Blocked imports should fail
    blocked_import_code = """
import os
os.system('rm -rf /')
"""
    result = validator.validate(blocked_import_code)
    assert result.is_valid is False
    assert any("Blocked import" in e for e in result.errors)

    # Test 3: Subprocess should be blocked
    subprocess_code = """
import subprocess
subprocess.run(['cat', '/etc/passwd'])
"""
    result = validator.validate(subprocess_code)
    assert result.is_valid is False
    assert any("Blocked import" in e or "subprocess" in e.lower() for e in result.errors)

    # Test 4: exec/eval should be blocked
    exec_code = """
exec("print('hello')")
"""
    result = validator.validate(exec_code)
    assert result.is_valid is False
    assert any("exec" in e.lower() for e in result.errors)

    # Test 5: __import__ should be blocked
    import_code = """
os = __import__('os')
os.system('ls')
"""
    result = validator.validate(import_code)
    assert result.is_valid is False
    assert any("__import__" in e for e in result.errors)

    # Test 6: Socket imports should be blocked
    socket_code = """
import socket
s = socket.socket()
s.connect(('evil.com', 80))
"""
    result = validator.validate(socket_code)
    assert result.is_valid is False
    assert any("Blocked import" in e for e in result.errors)

    # Test 7: Dangerous attribute access should be blocked
    attr_code = """
x = ''
x.__class__.__bases__[0].__subclasses__()
"""
    result = validator.validate(attr_code)
    assert result.is_valid is False
    assert any("attribute" in e.lower() for e in result.errors)

    # Test 8: Syntax errors should be caught
    syntax_error_code = """
def foo(
    print("incomplete")
"""
    result = validator.validate(syntax_error_code)
    assert result.is_valid is False
    assert any("Syntax error" in e for e in result.errors)

    # Test 9: open() function should be caught
    open_code = """
with open('/etc/passwd', 'r') as f:
    print(f.read())
"""
    result = validator.validate(open_code)
    assert result.is_valid is False

    # Test 10: from import should be blocked
    from_import_code = """
from subprocess import call
call(['ls'])
"""
    result = validator.validate(from_import_code)
    assert result.is_valid is False
    assert any("Blocked import" in e for e in result.errors)


@pytest.mark.asyncio
async def test_filesystem_escape():
    """Test prevention of filesystem escape and malicious imports."""
    # Test 1: Path traversal should be detected
    traversal_code = """
path = "../../../etc/passwd"
"""
    escapes = check_filesystem_escape(traversal_code)
    assert len(escapes) > 0
    assert any("traversal" in e.lower() for e in escapes)

    # Test 2: /etc/passwd access should be detected
    passwd_code = """
path = "/etc/passwd"
"""
    escapes = check_filesystem_escape(passwd_code)
    assert len(escapes) > 0
    assert any("passwd" in e.lower() for e in escapes)

    # Test 3: /proc access should be detected
    proc_code = """
path = "/proc/self/environ"
"""
    escapes = check_filesystem_escape(proc_code)
    assert len(escapes) > 0
    assert any("/proc" in e.lower() for e in escapes)

    # Test 4: /dev access should be detected
    dev_code = """
path = "/dev/random"
"""
    escapes = check_filesystem_escape(dev_code)
    assert len(escapes) > 0
    assert any("/dev" in e.lower() for e in escapes)

    # Test 5: Home directory access should be detected
    home_code = """
path = "/home/user/.ssh/id_rsa"
"""
    escapes = check_filesystem_escape(home_code)
    assert len(escapes) > 0
    assert any("home" in e.lower() for e in escapes)

    # Test 6: pathlib should be detected
    pathlib_code = """
from pathlib import Path
p = Path("/etc/passwd")
"""
    escapes = check_filesystem_escape(pathlib_code)
    assert len(escapes) > 0
    assert any("pathlib" in e.lower() for e in escapes)

    # Test 7: os.path should be detected
    ospath_code = """
import os
path = os.path.join("/", "etc", "passwd")
"""
    escapes = check_filesystem_escape(ospath_code)
    assert len(escapes) > 0
    assert any("os.path" in e.lower() for e in escapes)

    # Test 8: glob should be detected
    glob_code = """
import glob
files = glob.glob('/etc/*')
"""
    escapes = check_filesystem_escape(glob_code)
    assert len(escapes) > 0
    assert any("glob" in e.lower() for e in escapes)

    # Test 9: shutil should be detected
    shutil_code = """
import shutil
shutil.copy('/etc/passwd', '/tmp/passwd')
"""
    escapes = check_filesystem_escape(shutil_code)
    assert len(escapes) > 0
    assert any("shutil" in e.lower() for e in escapes)

    # Test 10: Clean code should not trigger false positives
    clean_code = """
# Simple maze solving code
result = look()
move('north')
print("Moving north")
"""
    escapes = check_filesystem_escape(clean_code)
    assert len(escapes) == 0


class TestCodeValidator:
    """Additional tests for the code validator."""

    def test_multiple_blocked_imports(self):
        """Test code with multiple blocked imports."""
        validator = CodeValidator()
        code = """
import os
import sys
import subprocess
"""
        result = validator.validate(code)
        assert result.is_valid is False
        # Should detect all blocked imports
        assert len(result.errors) >= 3

    def test_nested_import(self):
        """Test nested module imports."""
        validator = CodeValidator()
        code = """
import os.path
"""
        result = validator.validate(code)
        assert result.is_valid is False

    def test_allowed_stdlib(self):
        """Test that safe stdlib modules are allowed."""
        validator = CodeValidator()
        code = """
import json
import math
import random
import collections
import itertools
import functools
import operator
import string
import re
import datetime
import time
import copy
import heapq
import bisect

# Use them
data = json.dumps({'key': 'value'})
x = math.sqrt(16)
r = random.randint(1, 10)
"""
        result = validator.validate(code)
        assert result.is_valid is True

    def test_code_length_limit(self):
        """Test that overly long code is rejected."""
        validator = CodeValidator()
        code = "x = 1\n" * 200000  # Very long code
        result = validator.validate(code)
        assert result.is_valid is False
        assert any("length" in e.lower() for e in result.errors)

    def test_sanitize_adds_wrapper(self):
        """Test that sanitize adds safety wrapper."""
        validator = CodeValidator()
        code = "print('hello')"
        sanitized = validator.sanitize(code)
        assert "__builtins_safe__" in sanitized
        assert code in sanitized

    def test_ctypes_blocked(self):
        """Test that ctypes is blocked."""
        validator = CodeValidator()
        code = """
import ctypes
"""
        result = validator.validate(code)
        assert result.is_valid is False

    def test_pickle_blocked(self):
        """Test that pickle is blocked."""
        validator = CodeValidator()
        code = """
import pickle
"""
        result = validator.validate(code)
        assert result.is_valid is False

    def test_multiprocessing_blocked(self):
        """Test that multiprocessing is blocked."""
        validator = CodeValidator()
        code = """
import multiprocessing
"""
        result = validator.validate(code)
        assert result.is_valid is False

    def test_threading_blocked(self):
        """Test that threading is blocked."""
        validator = CodeValidator()
        code = """
import threading
"""
        result = validator.validate(code)
        assert result.is_valid is False
