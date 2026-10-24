"""Deterministic dice for repeatable engine tests and saved games.

A game stores only a seed and a cursor.  Each die is derived from
``SHA-256(seed:cursor:sides)`` which means:

* a saved game can be continued exactly where it stopped;
* replaying the same actions produces the same rolls;
* no global random state is touched; and
* the result does not depend on the Python version's random implementation.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Tuple, Union

_DICE_RE = re.compile(r"^\s*(?P<count>\d*)\s*[dD]\s*(?P<sides>\d+)\s*(?P<modifier>[+-]\s*\d+)?\s*$")
_MAX_DICE = 100
_MIN_SIDES = 2
_MAX_SIDES = 1000


class DiceError(ValueError):
    """Raised when a dice expression or dice state is invalid."""


@dataclass(frozen=True)
class DiceState:
    """Serializable position in a deterministic dice stream."""

    seed: int
    cursor: int = 0

    def __post_init__(self) -> None:
        if self.cursor < 0:
            raise DiceError("cursor must not be negative")

    def to_dict(self) -> Dict[str, int]:
        return {"seed": self.seed, "cursor": self.cursor}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DiceState":
        try:
            return cls(seed=int(payload["seed"]), cursor=int(payload["cursor"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise DiceError(f"invalid dice state: {exc}") from exc


@dataclass(frozen=True)
class DiceRoll:
    """The result of one dice expression."""

    expression: str
    rolls: Tuple[int, ...]
    modifier: int = 0
    total: int = 0

    def __post_init__(self) -> None:
        if self.total == 0 and self.rolls:
            object.__setattr__(self, "total", sum(self.rolls) + self.modifier)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expression": self.expression,
            "rolls": list(self.rolls),
            "modifier": self.modifier,
            "total": self.total,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DiceRoll":
        try:
            return cls(
                expression=str(payload["expression"]),
                rolls=tuple(int(v) for v in payload["rolls"]),
                modifier=int(payload.get("modifier", 0)),
                total=int(payload.get("total", 0)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DiceError(f"invalid dice roll: {exc}") from exc


class Dice:
    """A small deterministic roller.

    The object is intentionally mutable so an owning game state can advance its
    cursor after an action.  ``state`` always returns a serializable snapshot.
    """

    def __init__(self, state: Union[DiceState, int] = 0) -> None:
        if isinstance(state, int):
            state = DiceState(seed=state)
        if not isinstance(state, DiceState):
            raise TypeError("Dice requires a DiceState or integer seed")
        self._state = state

    @property
    def state(self) -> DiceState:
        return self._state

    @property
    def seed(self) -> int:
        return self._state.seed

    @property
    def cursor(self) -> int:
        return self._state.cursor

    def _draw(self, sides: int) -> int:
        if sides < _MIN_SIDES or sides > _MAX_SIDES:
            raise DiceError(f"die sides must be between {_MIN_SIDES} and {_MAX_SIDES}")
        payload = f"{self._state.seed}:{self._state.cursor}:D{sides}".encode("utf-8")
        digest = hashlib.sha256(payload).digest()
        value = int.from_bytes(digest[:8], "big")
        self._state = DiceState(seed=self._state.seed, cursor=self._state.cursor + 1)
        return value % sides + 1

    def d(self, sides: int) -> int:
        """Roll a single die with the given number of sides."""

        return self._draw(sides)

    def d3(self) -> int:
        return self._draw(3)

    def d6(self) -> int:
        return self._draw(6)

    def roll(self, expression: str) -> DiceRoll:
        """Roll an expression such as ``D6``, ``2D6+1`` or ``D3``."""

        if not isinstance(expression, str):
            raise DiceError("dice expression must be a string")
        match = _DICE_RE.match(expression)
        if not match:
            raise DiceError(f"unsupported dice expression: {expression!r}")
        count_text = match.group("count")
        count = int(count_text) if count_text else 1
        sides = int(match.group("sides"))
        modifier_text = match.group("modifier")
        modifier = int(modifier_text.replace(" ", "")) if modifier_text else 0
        if count < 1 or count > _MAX_DICE:
            raise DiceError(f"dice count must be between 1 and {_MAX_DICE}")
        rolls = tuple(self._draw(sides) for _ in range(count))
        return DiceRoll(
            expression=expression.strip(),
            rolls=rolls,
            modifier=modifier,
            total=sum(rolls) + modifier,
        )

    def roll_many(self, expressions: Iterable[str]) -> List[DiceRoll]:
        return [self.roll(expression) for expression in expressions]


def stable_fraction(seed: int, key: str) -> float:
    """Return a deterministic float in ``[0, 1)`` for non-dice tie-breaking.

    This is useful for AI personality noise without advancing the game's dice
    cursor.  The same seed and key always produce the same value.
    """

    if not isinstance(key, str):
        raise TypeError("key must be a string")
    payload = f"{seed}:tiebreak:{key}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big") / float(1 << 64)
