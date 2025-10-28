"""Archived copy of top-level battlescribe_parser shim.

Kept for history during migration. The canonical implementation now lives in
`backend/battlescribe_parser.py` and imports under the server should use
`backend.battlescribe_parser`.
"""

from backend.battlescribe_parser import *  # noqa: F401,F403
