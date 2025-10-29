#!/usr/bin/env python3
"""Compatibility shim for tests that load `reference_card_decks.py` from repo root.

The canonical module lives at `backend/reference_card_decks.py`. Re-export
the symbols expected by tests for backward compatibility.
"""

from backend.reference_card_decks import (
    battleplan_deck,
    battle_tactic_deck,
    tactic_to_actions,
    objective_action_deck,
)

__all__ = [
    'battleplan_deck',
    'battle_tactic_deck',
    'tactic_to_actions',
    'objective_action_deck',
]
