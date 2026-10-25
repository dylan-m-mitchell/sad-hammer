"""Stateless table companion for Age of Sigmar 4th.

The table planner turns two rosters into a round of physical-table
instructions.  It tracks no board, positions, wounds or distances: it only
uses unit profiles and doctrine, then tells the player what to measure, move
and roll.  Nothing in this package imports the digital board engine.
"""

from backend.table.planner import build_plan
from backend.table.rosters import (
    Roster,
    RosterParseError,
    TableUnit,
    TableWeapon,
    parse_roster,
    starter_rosters,
)

__all__ = [
    "Roster",
    "RosterParseError",
    "TableUnit",
    "TableWeapon",
    "build_plan",
    "parse_roster",
    "starter_rosters",
]
