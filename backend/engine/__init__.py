"""Sad Hammer rules engine.

The engine is deliberately independent of the legacy Flask API and card-driven
simulator.  It provides a deterministic, serializable game state plus a small
system interface that AoS 4th and Warhammer 40,000 11th can implement.
"""

from backend.engine.core.models import SCHEMA_VERSION, Side

__all__ = ["SCHEMA_VERSION", "Side"]
__version__ = "0.1.0"
