"""Explainable, rules-based utility AI.

The policy never invents an action.  It scores the actions the system says are
legal, applies an aggression/personality profile, and returns its reasoning.
That keeps the AI honest: if the rules module rejects an action, the AI cannot
select it in the first place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.engine.core.dice import stable_fraction
from backend.engine.core.models import GameState, Side
from backend.engine.core.session import GameSession
from backend.engine.systems.base import GameAction, GameSystem, IllegalActionError


@dataclass(frozen=True)
class AggressionProfile:
    """Weights that shape an AI player's style without changing the rules."""

    name: str
    objective_focus: float = 1.0
    damage_focus: float = 1.0
    risk_tolerance: float = 0.5
    cover_focus: float = 1.0
    mobility: float = 1.0
    noise: float = 0.0
    description: str = ""

    def weights(self) -> Dict[str, float]:
        return {
            "objective_focus": self.objective_focus,
            "damage_focus": self.damage_focus,
            "risk_tolerance": self.risk_tolerance,
            "cover_focus": self.cover_focus,
            "mobility": self.mobility,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "objective_focus": self.objective_focus,
            "damage_focus": self.damage_focus,
            "risk_tolerance": self.risk_tolerance,
            "cover_focus": self.cover_focus,
            "mobility": self.mobility,
            "noise": self.noise,
            "description": self.description,
        }


PROFILES: Dict[str, AggressionProfile] = {
    "aggressive": AggressionProfile(
        name="aggressive",
        objective_focus=0.8,
        damage_focus=1.5,
        risk_tolerance=0.85,
        cover_focus=0.5,
        mobility=1.2,
        noise=0.35,
        description="Pushes for damage and board pressure; accepts more risk.",
    ),
    "balanced": AggressionProfile(
        name="balanced",
        objective_focus=1.2,
        damage_focus=1.1,
        risk_tolerance=0.5,
        cover_focus=1.0,
        mobility=1.0,
        noise=0.25,
        description="Trades damage and objective play evenly.",
    ),
    "cautious": AggressionProfile(
        name="cautious",
        objective_focus=1.35,
        damage_focus=0.8,
        risk_tolerance=0.25,
        cover_focus=1.6,
        mobility=0.8,
        noise=0.15,
        description="Protects units, uses cover and only takes good fights.",
    ),
}


def get_profile(name: str) -> AggressionProfile:
    key = str(name).strip().lower()
    if key not in PROFILES:
        options = ", ".join(sorted(PROFILES))
        raise ValueError(f"unknown AI profile {name!r}; choose one of: {options}")
    return PROFILES[key]


@dataclass
class ScoredAction:
    action: GameAction
    score: float
    base_score: float
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.to_dict(),
            "score": round(self.score, 4),
            "base_score": round(self.base_score, 4),
            "reason": self.reason,
        }


@dataclass
class Decision:
    side: Side
    profile: str
    action: GameAction
    score: float
    base_score: float
    reason: str
    alternatives: List[ScoredAction] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "side": self.side.value,
            "profile": self.profile,
            "action": self.action.to_dict(),
            "score": round(self.score, 4),
            "base_score": round(self.base_score, 4),
            "reason": self.reason,
            "alternatives": [item.to_dict() for item in self.alternatives],
        }


class UtilityAI:
    """Score the system's legal actions and pick the best one."""

    def __init__(
        self,
        system: GameSystem,
        profile: AggressionProfile = PROFILES["balanced"],
        *,
        top_alternatives: int = 4,
    ) -> None:
        self.system = system
        self.profile = profile
        self.top_alternatives = max(0, int(top_alternatives))

    def score_actions(self, state: GameState, side: Optional[Side] = None) -> List[ScoredAction]:
        side = Side.parse(side or state.active_side)
        weights = self.profile.weights()
        scored: List[ScoredAction] = []
        for action in self.system.legal_actions(state):
            base = float(self.system.evaluate_action(state, action, side, weights))
            noise = (
                stable_fraction(state.dice.seed, action.key()) * self.profile.noise
                if self.profile.noise
                else 0.0
            )
            reason = self.system.explain_action(state, action, side)
            scored.append(
                ScoredAction(
                    action=action,
                    score=base + noise,
                    base_score=base,
                    reason=reason,
                )
            )
        scored.sort(key=lambda item: (-item.score, item.action.key()))
        return scored

    def choose(self, state: GameState, side: Optional[Side] = None) -> Optional[Decision]:
        side = Side.parse(side or state.active_side)
        scored = self.score_actions(state, side)
        if not scored:
            return None
        best = scored[0]
        return Decision(
            side=side,
            profile=self.profile.name,
            action=best.action,
            score=best.score,
            base_score=best.base_score,
            reason=best.reason,
            alternatives=scored[1 : 1 + self.top_alternatives],
        )


def run_ai_turn(
    session: GameSession,
    profile: AggressionProfile,
    *,
    max_actions: int = 100,
    top_alternatives: int = 2,
) -> List[Decision]:
    """Play one complete AI turn, one legal action at a time.

    The loop stops as soon as the active side changes or the game ends, so it
    is safe to call for either side in an AI-vs-AI demo.
    """

    if max_actions < 1:
        raise ValueError("max_actions must be at least 1")
    starting_side = session.state.active_side
    decisions: List[Decision] = []
    policy = UtilityAI(session.system, profile, top_alternatives=top_alternatives)
    while (
        not session.is_terminal()
        and session.state.active_side is starting_side
        and len(decisions) < max_actions
    ):
        decision = policy.choose(session.state)
        if decision is None:
            break
        try:
            session.apply(decision.action)
        except IllegalActionError:
            # A policy bug should be loud in development, but stopping is safer
            # than corrupting a saved game.  Tests assert this never happens.
            raise
        decisions.append(decision)
    return decisions
