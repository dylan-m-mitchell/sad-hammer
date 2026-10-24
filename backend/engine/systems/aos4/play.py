"""Player-facing orchestration for the Age of Sigmar 4th slice.

The rules module intentionally knows nothing about HTTP or React.  This module
turns a :class:`GameSession` into a small, presentation-ready match: it filters
legal actions to the human side, runs the AI until the human is needed again,
and builds the board view consumed by the web client.

Keeping this layer separate from the Flask routes means the complete
human-vs-AI loop can be tested without a browser or a running server.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from backend.engine.ai.policy import (
    AggressionProfile,
    Decision,
    get_profile,
    run_ai_until_human,
)
from backend.engine.core.events import Event
from backend.engine.core.models import GameState, Side, Unit
from backend.engine.core.session import GameSession
from backend.engine.systems.aos4.combat import unit_edge_distance
from backend.engine.systems.aos4.datapack import FactionPack, Mission
from backend.engine.systems.aos4.system import Aos4System
from backend.engine.systems.base import GameAction, IllegalActionError

ACTION_GROUP_ORDER: Tuple[str, ...] = (
    "deploy",
    "move",
    "run",
    "retreat",
    "shoot",
    "charge",
    "fight",
    "command",
    "end_deployment",
    "end_phase",
)

ACTION_GROUP_LABELS = {
    "deploy": "Deployment",
    "move": "Move",
    "run": "Run",
    "retreat": "Retreat",
    "shoot": "Shoot",
    "charge": "Charge",
    "fight": "Fight",
    "command": "Command",
    "end_deployment": "Deployment",
    "end_phase": "Phase",
}

COMMAND_LABELS = {
    "rally": "Rally",
    "all_out_attack": "All-out Attack",
    "all_out_defence": "All-out Defence",
}


class MatchError(ValueError):
    """Raised when a player action is not valid for the current match."""


def _round(value: float) -> float:
    return round(float(value), 2)


def _is_inside_objective(state: GameState, point: Any) -> Optional[str]:
    for objective in state.objectives:
        if objective.contains(point):
            return objective.name
    return None


def _is_in_cover(state: GameState, point: Any) -> bool:
    return any(feature.cover and feature.contains(point) for feature in state.terrain)


def _nearest_enemy(state: GameState, unit: Unit) -> Optional[Unit]:
    enemies = state.alive_units_for(unit.side.other)
    if not enemies:
        return None
    return min(enemies, key=lambda enemy: unit.position.distance_to(enemy.position))


class Aos4Match:
    """A single human-vs-AI AoS 4th game."""

    def __init__(self, session: GameSession, profile: AggressionProfile) -> None:
        system = session.system
        if not isinstance(system, Aos4System):
            raise MatchError("Aos4Match requires an AoS 4th game session")
        self.session = session
        self.system: Aos4System = system
        self.profile = profile
        self._decision_descriptions: Dict[int, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Construction and persistence

    @classmethod
    def create(
        cls,
        *,
        seed: int = 0,
        mission: str = "contested-ground",
        player_pack: str = "stormcast-starter",
        ai_pack: str = "skaven-starter",
        max_rounds: Optional[int] = None,
        skip_deployment: bool = True,
        ai_profile: str = "balanced",
        game_id: str = "",
    ) -> "Aos4Match":
        profile = get_profile(ai_profile)
        system = Aos4System()
        options: Dict[str, Any] = {
            "mission": mission,
            "player_pack": player_pack,
            "ai_pack": ai_pack,
            "skip_deployment": bool(skip_deployment),
        }
        if max_rounds is not None:
            options["max_rounds"] = int(max_rounds)
        if game_id:
            options["game_id"] = str(game_id)
        session = GameSession.new(system, seed=int(seed), **options)
        session.state.metadata["seed"] = int(seed)
        session.state.metadata["ai_profile"] = profile.name
        return cls(session, profile)

    @classmethod
    def from_state(
        cls,
        payload: Mapping[str, Any],
        *,
        ai_profile: Optional[str] = None,
        game_id: Optional[str] = None,
    ) -> "Aos4Match":
        system = Aos4System()
        session = GameSession.from_dict(system, dict(payload))
        if game_id:
            session.state.game_id = str(game_id)
        session.ensure_valid()
        stored_profile = session.state.metadata.get("ai_profile")
        profile_name = ai_profile or stored_profile or "balanced"
        profile = get_profile(str(profile_name))
        session.state.metadata["ai_profile"] = profile.name
        return cls(session, profile)

    @property
    def game_id(self) -> str:
        return self.session.state.game_id

    def state_dict(self) -> Dict[str, Any]:
        return self.session.state.to_dict()

    # ------------------------------------------------------------------
    # Player actions

    def player_actions(self) -> List[Dict[str, Any]]:
        """Annotated legal actions owned by the human side."""

        actions = self.system.legal_actions_for(self.session.state, Side.PLAYER)
        entries = [self.describe_action(action) for action in actions]
        entries.sort(
            key=lambda entry: (
                (
                    ACTION_GROUP_ORDER.index(entry["group"])
                    if entry["group"] in ACTION_GROUP_ORDER
                    else 99
                ),
                entry["actor_number"] or 99,
                entry.get("distance") if entry.get("distance") is not None else 0.0,
                entry["label"],
                entry["id"],
            )
        )
        return entries

    def describe_action(
        self,
        action: GameAction,
        state: Optional[GameState] = None,
    ) -> Dict[str, Any]:
        state = state or self.session.state
        unit = state.unit_by_id(action.actor_id)
        target = state.unit_by_id(action.target_id) if action.target_id else None
        action_phase_id = str(action.payload.get("phase") or state.phase)
        action_phase = next(
            (definition for definition in self.system.phases if definition.id == action_phase_id),
            None,
        )
        action_type = action.action_type
        command = str(action.payload.get("command", "")) if action_type == "command" else ""
        group = "command" if action_type == "command" else action_type
        distance: Optional[float] = None
        detail_parts: List[str] = []

        actor_name = unit.name if unit is not None else "Your army"
        target_name = target.name if target is not None else None
        actor_number = self._unit_number(state, unit) if unit is not None else None

        if unit is not None and action.destination is not None:
            if action_type in ("move", "run", "retreat"):
                distance = unit.position.distance_to(action.destination)
                objective_name = _is_inside_objective(state, action.destination)
                if objective_name:
                    detail_parts.append(f"to {objective_name}")
                elif _is_in_cover(state, action.destination):
                    detail_parts.append("into cover")
                else:
                    enemy = _nearest_enemy(state, unit)
                    if enemy is not None:
                        detail_parts.append(f"toward {enemy.name}")
                    else:
                        detail_parts.append(
                            f"to ({action.destination.x:.1f}, {action.destination.y:.1f})"
                        )
            elif action_type == "deploy":
                objective_name = _is_inside_objective(state, action.destination)
                if objective_name:
                    detail_parts.append(f"near {objective_name}")
                elif _is_in_cover(state, action.destination):
                    detail_parts.append("into cover")
                else:
                    detail_parts.append("inside your territory")

        if target is not None:
            if action_type == "shoot":
                distance = unit_edge_distance(unit, target) if unit is not None else None
                detail_parts.append(f'{distance:.1f}" away' if distance is not None else "")
            elif action_type == "charge" and action.destination is not None and unit is not None:
                distance = unit.position.distance_to(action.destination)
                detail_parts.append(f'{distance:.1f}" charge')
            elif action_type == "fight":
                distance = unit_edge_distance(unit, target) if unit is not None else None
                detail_parts.append(f'{distance:.1f}" away' if distance is not None else "")

        if action_type == "command":
            label = COMMAND_LABELS.get(command, command.replace("_", " ").title())
            detail_parts.append("1 command point")
        elif action_type == "end_phase":
            label = (
                f"End {action_phase.name}"
                if action_phase is not None
                else f"End {action_phase_id.replace('_', ' ').title()}"
            )
        elif action_type == "end_deployment":
            label = "Finish deployment"
        elif action_type == "deploy":
            label = "Deploy"
        elif action_type in ("move", "run", "retreat"):
            assert distance is not None
            label = f'{action_type.title()} {distance:.1f}"'
        elif action_type in ("shoot", "charge", "fight"):
            label = f'{action_type.title()} {target_name or "target"}'
        else:
            label = action_type.replace("_", " ").title()

        detail = " · ".join(part for part in detail_parts if part)
        return {
            "id": action.key(),
            "action": action.to_dict(),
            "action_type": action_type,
            "group": group,
            "group_label": ACTION_GROUP_LABELS.get(group, group.title()),
            "label": label,
            "detail": detail,
            "actor_id": action.actor_id,
            "actor_name": actor_name,
            "actor_number": actor_number,
            "target_id": action.target_id,
            "target_name": target_name,
            "command": command or None,
            "cp_cost": 1 if action_type == "command" else 0,
            "distance": _round(distance) if distance is not None else None,
            "tags": list(action.tags),
        }

    def apply_player_action(self, payload: Mapping[str, Any]) -> Tuple[List[Event], List[Decision]]:
        """Validate and apply one human action, then play the AI response."""

        state = self.session.state
        if state.is_complete:
            raise MatchError("the game is already complete")
        try:
            action = GameAction.from_dict(payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise MatchError(f"invalid action: {exc}") from exc

        actor_side = self.system.action_side(state, action)
        if actor_side is not Side.PLAYER:
            raise MatchError("that unit belongs to the AI opponent")
        if self.system.acting_side(state) is not Side.PLAYER:
            raise MatchError("it is not your decision yet")

        validation = self.session.validate(action)
        if not validation.ok:
            first = validation.errors[0].message if validation.errors else "illegal action"
            raise IllegalActionError(first, validation)

        before_seq = self._last_seq(state)
        self.session.apply(action)
        self._decision_descriptions.clear()
        decisions = run_ai_until_human(
            self.session, self.profile, on_decision=self._remember_decision
        )
        events = [event for event in self.session.state.events if event.seq > before_seq]
        return events, decisions

    def resume(self) -> Tuple[List[Event], List[Decision]]:
        """Run any outstanding AI decisions, returning the events they created."""

        before_seq = self._last_seq(self.session.state)
        self._decision_descriptions.clear()
        decisions = run_ai_until_human(
            self.session, self.profile, on_decision=self._remember_decision
        )
        events = [event for event in self.session.state.events if event.seq > before_seq]
        return events, decisions

    # ------------------------------------------------------------------
    # Snapshot and presentation

    def snapshot(
        self,
        *,
        events: Optional[Sequence[Event]] = None,
        decisions: Optional[Sequence[Decision]] = None,
    ) -> Dict[str, Any]:
        state = self.session.state
        return {
            "game_id": state.game_id,
            "state": state.to_dict(),
            "view": self.view(),
            "events": [event.to_dict() for event in (events or [])],
            "ai_decisions": [self._decision_view(decision) for decision in (decisions or [])],
        }

    def view(self) -> Dict[str, Any]:
        state = self.session.state
        acting_side = self.system.acting_side(state)
        terminal = state.is_complete
        if terminal:
            interaction = "game_over"
            turn_label = "Battle complete"
        elif acting_side is Side.PLAYER and state.active_side is Side.PLAYER:
            interaction = "player_turn"
            turn_label = "Your turn"
        elif acting_side is Side.PLAYER:
            interaction = "player_combat_response"
            turn_label = "Your combat pick"
        else:
            interaction = "ai"
            turn_label = "AI turn"

        phase = self.system.phase(state)
        phase_name = phase.name if phase is not None else state.phase.replace("_", " ").title()
        winner = state.metadata.get("winner")
        result = None
        if terminal:
            if winner == Side.PLAYER.value:
                result = "Victory"
            elif winner == Side.AI.value:
                result = "Defeat"
            else:
                result = "Draw"

        player_actions = [] if terminal else self.player_actions()
        instruction = self._instruction(interaction, phase_name, player_actions)

        return {
            "system": self.system.name,
            "edition": self.system.edition,
            "mission": {
                "id": state.metadata.get("mission"),
                "name": state.metadata.get("mission_name"),
                "source": state.metadata.get("mission_source"),
                "scoring": dict(state.metadata.get("scoring", {})),
            },
            "board": state.board.to_dict(),
            "round": state.round,
            "max_rounds": state.max_rounds,
            "phase": state.phase,
            "phase_name": phase_name,
            "phases": [
                {
                    "id": definition.id,
                    "name": definition.name,
                    "description": definition.description,
                    "current": definition.id == state.phase,
                }
                for definition in self.system.phases
            ],
            "active_side": state.active_side.value,
            "acting_side": acting_side.value,
            "interaction": interaction,
            "turn_label": turn_label,
            "instruction": instruction,
            "status": state.status,
            "result": result,
            "winner": winner,
            "scores": {side.value: state.score_for(side) for side in (Side.PLAYER, Side.AI)},
            "command_points": {
                side.value: int(state.command_points.get(side.value, 0))
                for side in (Side.PLAYER, Side.AI)
            },
            "factions": {
                Side.PLAYER.value: state.army_for(Side.PLAYER).name,
                Side.AI.value: state.army_for(Side.AI).name,
            },
            "ai_profile": self.profile.to_dict(),
            "units": self._units_view(state),
            "objectives": [
                {
                    "id": objective.id,
                    "name": objective.name,
                    "position": objective.position.to_dict(),
                    "radius": objective.radius,
                    "value": objective.value,
                    "controller": objective.controller.value if objective.controller else None,
                }
                for objective in state.objectives
            ],
            "terrain": [
                {
                    "id": feature.id,
                    "name": feature.name,
                    "points": [point.to_dict() for point in feature.footprint.points],
                    "height": feature.height,
                    "cover": feature.cover,
                    "blocks_line_of_sight": feature.blocks_line_of_sight,
                    "difficult": feature.difficult,
                    "tags": list(feature.tags),
                }
                for feature in state.terrain
            ],
            "deployment_zones": {
                side.value: [
                    [point.to_dict() for point in polygon.points]
                    for polygon in state.deployment_zones.get(side.value, [])
                ]
                for side in (Side.PLAYER, Side.AI)
            },
            "legal_actions": player_actions,
            "event_count": len(state.events),
            "last_event_seq": self._last_seq(state),
            "setup": {
                "mission": state.metadata.get("mission"),
                "player_pack": state.metadata.get("pack_ids", {}).get(Side.PLAYER.value),
                "ai_pack": state.metadata.get("pack_ids", {}).get(Side.AI.value),
                "ai_profile": self.profile.name,
                "seed": state.metadata.get("seed"),
                "skip_deployment": bool(
                    state.metadata.get(
                        "skip_deployment",
                        state.metadata.get("deployment_complete", False),
                    )
                ),
            },
        }

    def _instruction(
        self,
        interaction: str,
        phase_name: str,
        player_actions: Sequence[Mapping[str, Any]],
    ) -> str:
        if interaction == "game_over":
            return "The battle is over. Review the board or start a new game."
        if interaction == "player_combat_response":
            return "Your opponent is mid-turn. Pick a unit to fight in the alternating combat."
        if not player_actions:
            return "No player actions are available. Resume the game to continue the AI turn."
        if any(entry["action_type"] == "end_deployment" for entry in player_actions):
            return "Place your remaining units, then finish deployment."
        if any(entry["action_type"] == "end_phase" for entry in player_actions):
            return f"Choose an order for a unit, or end the {phase_name} phase."
        return "Choose an order for one of your units."

    def _units_view(self, state: GameState) -> List[Dict[str, Any]]:
        units: List[Dict[str, Any]] = []
        for side in (Side.PLAYER, Side.AI):
            for index, unit in enumerate(state.units_for(side), start=1):
                units.append(
                    {
                        "id": unit.id,
                        "name": unit.name,
                        "number": index,
                        "side": unit.side.value,
                        "position": unit.position.to_dict(),
                        "models": unit.models,
                        "max_models": unit.max_models,
                        "wounds": unit.wounds,
                        "max_wounds": unit.max_wounds,
                        "health_ratio": self._health_ratio(unit),
                        "save": unit.save,
                        "move": unit.move,
                        "points": unit.points,
                        "base_radius": unit.base_radius,
                        "keywords": list(unit.keywords),
                        "control": int(unit.stats.get("control", 1)),
                        "ward": unit.stats.get("ward"),
                        "alive": unit.alive,
                        "destroyed": unit.destroyed,
                        "flags": dict(unit.flags),
                        "status": self._status_tags(unit),
                        "weapons": [
                            {
                                "name": weapon.name,
                                "range_inches": weapon.range_inches,
                                "attacks": weapon.attacks,
                                "hit_on": weapon.hit_on,
                                "wound_on": weapon.wound_on,
                                "damage": weapon.damage,
                                "armor_penetration": weapon.armor_penetration,
                            }
                            for weapon in unit.weapons
                        ],
                        "nearest_enemy": self._nearest_enemy_distance(state, unit),
                    }
                )
        return units

    def _remember_decision(self, decision: Decision, state: GameState) -> None:
        self._decision_descriptions[id(decision)] = self.describe_action(decision.action, state)

    def _decision_view(self, decision: Decision) -> Dict[str, Any]:
        payload = decision.to_dict()
        described = self._decision_descriptions.get(id(decision))
        if described is None:
            described = self.describe_action(decision.action)
        payload["label"] = described["label"]
        payload["detail"] = described["detail"]
        payload["actor_name"] = described["actor_name"]
        payload["actor_number"] = described["actor_number"]
        payload["target_name"] = described["target_name"]
        return payload

    def _unit_number(self, state: GameState, unit: Unit) -> Optional[int]:
        index = 1
        for candidate in state.units_for(unit.side):
            if candidate.id == unit.id:
                return index
            index += 1
        return None

    def _status_tags(self, unit: Unit) -> List[str]:
        tags: List[str] = []
        if unit.flags.get("deployed"):
            tags.append("Deployed")
        if unit.flags.get("moved"):
            tags.append("Moved")
        if unit.flags.get("advanced"):
            tags.append("Ran/retreated")
        if unit.flags.get("shot"):
            tags.append("Shot")
        if unit.flags.get("charged"):
            tags.append("Charged")
        if unit.flags.get("fought"):
            tags.append("Fought")
        return tags

    def _nearest_enemy_distance(self, state: GameState, unit: Unit) -> Optional[float]:
        enemies = state.alive_units_for(unit.side.other)
        if not enemies:
            return None
        return _round(
            min(
                max(
                    0.0,
                    unit.position.distance_to(enemy.position)
                    - unit.base_radius
                    - enemy.base_radius,
                )
                for enemy in enemies
            )
        )

    def _health_ratio(self, unit: Unit) -> float:
        maximum = max(1, unit.max_wounds)
        return max(0.0, min(1.0, int(unit.wounds or 0) / maximum))

    def _last_seq(self, state: GameState) -> int:
        return max((event.seq for event in state.events), default=0)


def build_options(
    packs: Sequence[FactionPack],
    missions: Sequence[Mission],
) -> Dict[str, Any]:
    """Build the setup payload used by the web client.

    AI behaviour is owned by the server, so aggression profiles are not
    exposed as a player choice.
    """

    return {
        "system": {
            "id": Aos4System.system_id,
            "name": Aos4System.name,
            "edition": Aos4System.edition,
        },
        "packs": [
            {
                "id": pack.pack_id,
                "name": pack.faction,
                "points": sum(unit.points for unit in pack.units),
                "units": len(pack.units),
                "description": pack.source,
            }
            for pack in packs
        ],
        "missions": [
            {
                "id": mission.mission_id,
                "name": mission.name,
                "rounds": mission.rounds,
                "board": mission.board.to_dict(),
                "objectives": len(mission.objectives),
                "description": mission.source,
            }
            for mission in missions
        ],
        "defaults": {
            "player_pack": "stormcast-starter",
            "ai_pack": "skaven-starter",
            "mission": "contested-ground",
            "skip_deployment": True,
        },
    }


__all__ = ["Aos4Match", "MatchError", "build_options"]
