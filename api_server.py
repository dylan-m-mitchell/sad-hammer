#!/usr/bin/env python3
"""Compatibility shim: re-export the Flask `app` from `backend.api_server`.

Tests in this project import `api_server` from the project root in tests.
The actual server implementation lives under `backend/api_server.py`.
This tiny shim keeps those imports working without changing tests.
"""

from backend.api_server import app

__all__ = ["app"]
