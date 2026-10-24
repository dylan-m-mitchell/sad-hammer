"""Structured events emitted by systems and stored in the game log."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional


@dataclass
class Event:
    """A serializable, human-readable record of something that happened.

    Systems create events without worrying about sequence numbers.  The
    ``GameSession`` stamps sequence, round, phase and side before appending the
    event to the state log.
    """

    kind: str
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    seq: int = 0
    round: int = 0
    phase: str = ""
    side: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "message": self.message,
            "data": self.data,
            "seq": self.seq,
            "round": self.round,
            "phase": self.phase,
            "side": self.side,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Event":
        data = payload.get("data", {})
        if not isinstance(data, dict):
            raise ValueError("event data must be an object")
        return cls(
            kind=str(payload["kind"]),
            message=str(payload.get("message", "")),
            data=dict(data),
            seq=int(payload.get("seq", 0)),
            round=int(payload.get("round", 0)),
            phase=str(payload.get("phase", "")),
            side=(str(payload["side"]) if payload.get("side") is not None else None),
        )


def make_event(kind: str, message: str = "", **data: Any) -> Event:
    """Convenience constructor for system code."""

    return Event(kind=kind, message=message, data=data)
