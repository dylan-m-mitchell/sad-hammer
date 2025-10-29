"""Deprecated test module for sessionful remove_unit; replaced by stateless tests.

This module is kept as a shim so older test suites that reference the file
won't fail import. All active tests use `test_api_remove_unit_stateless.py`.
"""

import pytest


def pytest_configure(config):
    pytest.skip("sessionful tests removed; use stateless tests", allow_module_level=True)
