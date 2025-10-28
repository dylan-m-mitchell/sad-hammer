#!/usr/bin/env python3
"""Backend server wrapper that ensures imports resolve when running from the
`backend/` package directory. It reuses the existing top-level `api_server.app`.

Run with:

    python backend/server.py

This assumes your virtualenv is activated.
"""
import os
import sys

# Put the repository root on sys.path so api_server and other modules import
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.api_server import app

if __name__ == '__main__':
    # bind to 0.0.0.0 so the container is reachable from other containers (nginx)
    app.run(host='0.0.0.0', port=5000, debug=True)
