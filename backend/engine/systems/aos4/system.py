"""Age of Sigmar 4th rules module for the Sad Hammer engine.

This is a deliberately scoped vertical slice of the core rules.  It implements
the seven-phase turn, core movement and attack abilities, a command-point
subset, objective control and a five-round mission.  It does not implement
spells, manifestations, battle tactics or faction-specific abilities; those are
tracked in the roadmap and the rules matrix.

The module owns no UI and no networking.  A human reports tabletop changes as
actions, while the same actions can be selected by the shared utility AI for
the computer opponent.
"""

from __future__ import annotations

import copy
import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from backend.engine.core.dice import Dice
from backend.engine.core.events import Event, make_event
from backend.engine.core.geometry import Vec2, clamp_point_within_board, point_at_range
from backend.engine.core.models import (
    Army,
    Board,
    GameState,
    Objective,
    Side,
    Unit,
    Weapon,
)
from backend.engine.core.validation import ValidationResult
from backend.engine.systems.aos4.combat import (
    charge_probability,
    expected_weapon_damage,
    resolve_weapon_attacks,
    unit_edge_distance,
    unit_in_combat,
)
from backend.engine.systems.aos4.datapack import (
    FactionPack,
    Mission,
    load_faction_pack,
    load_mission,
)
from backend.engine.systems.base import (
    ActionResult,
    GameAction,
    GameSystem,
    IllegalActionError,
    PhaseDefinition,
)

COMBAT_RANGE = 3.0
ENGAGEMENT_RANGE = 0.5
MAX_CHARGE = 12.0
CORE_PHASE_IDS: Tuple[str, ...] = (
    "start_of_turn",
    "hero",
    "movement",
    "shooting",
    "charge",
    "combat",
    "end_of_turn",
)
COMMANDS = ("rally", "all_out_attack", "all_out_defence")


class Aos4System(GameSystem):
    """A complete core-rules turn for a two-army Age of Sigmar 4th game."""

    system_id = "aos4"
    name = "Age of Sigmar 4th"
    edition = "4th"

    @property
    def phases(self) -> Sequence[PhaseDefinition]:
        return (
            PhaseDefinition("start_of_turn", "Start of Turn", "Resolve start-of-turn abilities."),
            PhaseDefinition("hero", "Hero", "Use hero-phase commands such as Rally."),
            PhaseDefinition("movement", "Movement", "Move, run or retreat."),
            PhaseDefinition("shooting", "Shooting", "Resolve ranged attacks."),
            PhaseDefinition("charge", "Charge", "Attempt charges with 2D6."),
            PhaseDefinition("combat", "Combat", "Pile in and fight, alternating between players."),
            PhaseDefinition("end_of_turn", "End of Turn", "Control objectives and score."),
        )

    def acting_side(self, state: GameState) -> Side:
        """Return the side picking the next combat unit, otherwise the active side."""

        if state.phase == "combat":
            next_side = self._next_combat_side(state)
            if next_side is not None:
                return next_side
        return state.active_side

    # ------------------------------------------------------------------
    # Setup

    def create_game(self, seed: int = 0, **options: Any) -> GameState:
        mission_option = options.get("mission", "contested-ground")
        mission = (
            mission_option
            if isinstance(mission_option, Mission)
            else load_mission(str(mission_option))
        )
        player_pack_option = options.get("player_pack", "stormcast-starter")
        ai_pack_option = options.get("ai_pack", "skaven-starter")
        player_pack = (
            player_pack_option
            if isinstance(player_pack_option, FactionPack)
            else load_faction_pack(str(player_pack_option))
        )
        ai_pack = (
            ai_pack_option
            if isinstance(ai_pack_option, FactionPack)
            else load_faction_pack(str(ai_pack_option))
        )
        if player_pack.pack_id == ai_pack.pack_id:
            raise ValueError("player_pack and ai_pack must be different packs")

        max_rounds = int(options.get("max_rounds", mission.rounds))
        if max_rounds < 1:
            raise ValueError("max_rounds must be at least 1")
        skip_deployment = bool(options.get("skip_deployment", False))
        game_id = str(options.get("game_id", f"aos4-{seed}"))

        player_units = self._build_units(player_pack, Side.PLAYER, "player", mission)
        ai_units = self._build_units(ai_pack, Side.AI, "ai", mission)

        state = GameState(
            schema_version=1,
            game_id=game_id,
            system_id=self.system_id,
            board=mission.board,
            armies=[
                Army(
                    id="player-force",
                    name=player_pack.faction,
                    side=Side.PLAYER,
                    units=player_units,
                ),
                Army(
                    id="ai-force",
                    name=ai_pack.faction,
                    side=Side.AI,
                    units=ai_units,
                ),
            ],
            objectives=mission.default_objectives(),
            terrain=list(mission.terrain),
            deployment_zones={
                side: list(polygons) for side, polygons in mission.deployment_zones.items()
            },
            round=1,
            max_rounds=max_rounds,
            active_side=Side.PLAYER,
            phase="deployment" if not skip_deployment else "start_of_turn",
            scores={Side.PLAYER.value: 0, Side.AI.value: 0},
            command_points={Side.PLAYER.value: 0, Side.AI.value: 0},
            dice=Dice(seed).state,
            metadata={
                "mission": mission.mission_id,
                "mission_name": mission.name,
                "mission_source": mission.source,
                "scoring": dict(mission.scoring),
                "turn_number": 0,
                "deployment_complete": skip_deployment,
                "skip_deployment": skip_deployment,
                "command_usage": {},
                "combat_last_side": None,
                "pack_ids": {
                    Side.PLAYER.value: player_pack.pack_id,
                    Side.AI.value: ai_pack.pack_id,
                },
                "sources": {
                    Side.PLAYER.value: player_pack.source,
                    Side.AI.value: ai_pack.source,
                },
            },
        )
        if skip_deployment:
            self._begin_battle(state)
        return state

    def _build_units(
        self,
        pack: FactionPack,
        side: Side,
        prefix: str,
        mission: Mission,
    ) -> List[Unit]:
        deployments = {
            entry.unit_id: entry.position for entry in mission.deployment_for(side, pack.pack_id)
        }
        zones = mission.deployment_zones[side.value]
        units: List[Unit] = []
        for index, profile in enumerate(pack.units):
            position = deployments.get(profile.id)
            if position is None:
                position = self._fallback_position(
                    zones[0],
                    index,
                    len(pack.units),
                    profile.base_radius,
                    mission.board,
                )
            unit = profile.to_unit(side, position, id_prefix=prefix)
            units.append(unit)
        return units

    def _fallback_position(
        self,
        zone: Any,
        index: int,
        count: int,
        base_radius: float,
        board: Board,
    ) -> Vec2:
        bounds = zone.bounds
        columns = 3
        rows = max(1, math.ceil(count / columns))
        column = index % columns
        row = index // columns
        x = bounds.x + bounds.width * (0.2 + 0.3 * column)
        y = bounds.y + bounds.height * ((row + 0.5) / rows)
        return clamp_point_within_board(Vec2(x, y), board.width, board.height, margin=base_radius)

    # ------------------------------------------------------------------
    # Action enumeration

    def legal_actions(self, state: GameState) -> List[GameAction]:
        if state.is_complete:
            return []
        phase = state.phase
        if phase == "deployment":
            return self._deployment_actions(state)
        if phase == "start_of_turn" or phase == "end_of_turn":
            return [self._end_phase_action(state)]
        if phase == "hero":
            return self._hero_actions(state)
        if phase == "movement":
            return self._movement_actions(state)
        if phase == "shooting":
            return self._shooting_actions(state)
        if phase == "charge":
            return self._charge_actions(state)
        if phase == "combat":
            return self._combat_actions(state)
        return []

    def _end_phase_action(self, state: GameState) -> GameAction:
        return GameAction(
            action_type="end_phase",
            actor_id=state.active_side.value,
            payload={"phase": state.phase},
            tags=("phase",),
        )

    def _deployment_actions(self, state: GameState) -> List[GameAction]:
        actions: List[GameAction] = []
        side = state.active_side
        for unit in state.alive_units_for(side):
            if unit.flags.get("deployed"):
                continue
            for destination in self._deployment_candidates(state, unit):
                actions.append(
                    GameAction(
                        action_type="deploy",
                        actor_id=unit.id,
                        destination=destination,
                        tags=("deployment",),
                    )
                )
        actions.append(
            GameAction(
                action_type="end_deployment",
                actor_id=side.value,
                tags=("deployment", "phase"),
            )
        )
        return actions

    def _deployment_candidates(self, state: GameState, unit: Unit) -> Sequence[Vec2]:
        zone = self._deployment_zone(state, unit.side)
        if zone is None:
            return []
        bounds = zone.bounds
        candidates: List[Vec2] = []
        for objective in state.objectives:
            x = min(
                max(objective.position.x, bounds.x + unit.base_radius),
                bounds.right - unit.base_radius,
            )
            y = min(
                max(objective.position.y, bounds.y + unit.base_radius),
                bounds.bottom - unit.base_radius,
            )
            point = Vec2(x, y)
            if zone.contains(point):
                candidates.append(point)
        for feature in state.terrain:
            if feature.cover and zone.contains(feature.footprint.center):
                candidates.append(feature.footprint.center)
        candidates.append(Vec2(bounds.center.x, bounds.center.y))
        return self._unique_destinations(state, unit, candidates, require_no_engagement=False)

    def _hero_actions(self, state: GameState) -> List[GameAction]:
        actions = self._command_actions(state, ("rally",))
        actions.append(self._end_phase_action(state))
        return actions

    def _movement_actions(self, state: GameState) -> List[GameAction]:
        actions: List[GameAction] = []
        for unit in state.alive_units_for(state.active_side):
            if unit.flags.get("moved"):
                continue
            if self._unit_in_combat(state, unit):
                for destination in self._retreat_candidates(state, unit):
                    actions.append(
                        GameAction(
                            action_type="retreat",
                            actor_id=unit.id,
                            destination=destination,
                            tags=("retreat", "movement"),
                        )
                    )
                continue
            for destination in self._movement_candidates(state, unit, unit.move):
                actions.append(
                    GameAction(
                        action_type="move",
                        actor_id=unit.id,
                        destination=destination,
                        tags=self._destination_tags(state, destination),
                    )
                )
            for destination in self._movement_candidates(state, unit, unit.move + 3.5):
                actions.append(
                    GameAction(
                        action_type="run",
                        actor_id=unit.id,
                        destination=destination,
                        tags=("run",) + self._destination_tags(state, destination),
                    )
                )
        actions.append(self._end_phase_action(state))
        return actions

    def _shooting_actions(self, state: GameState) -> List[GameAction]:
        actions: List[GameAction] = []
        side = state.active_side
        for unit in state.alive_units_for(side):
            if unit.flags.get("shot") or unit.flags.get("advanced"):
                continue
            if self._unit_in_combat(state, unit):
                continue
            for target in state.alive_units_for(side.other):
                if self._can_shoot(state, unit, target):
                    tags = ["attack", "ranged"]
                    if any(objective.contains(target.position) for objective in state.objectives):
                        tags.append("objective")
                    actions.append(
                        GameAction(
                            action_type="shoot",
                            actor_id=unit.id,
                            target_id=target.id,
                            tags=tuple(tags),
                        )
                    )
        actions.extend(self._command_actions(state, ("all_out_attack", "all_out_defence")))
        actions.append(self._end_phase_action(state))
        return actions

    def _charge_actions(self, state: GameState) -> List[GameAction]:
        actions: List[GameAction] = []
        side = state.active_side
        for unit in state.alive_units_for(side):
            if unit.flags.get("charged") or unit.flags.get("advanced"):
                continue
            if self._unit_in_combat(state, unit):
                continue
            for enemy in state.alive_units_for(side.other):
                destination = self._charge_destination(unit, enemy)
                if destination is None:
                    continue
                if not self._destination_clear(state, unit, destination):
                    continue
                actions.append(
                    GameAction(
                        action_type="charge",
                        actor_id=unit.id,
                        target_id=enemy.id,
                        destination=destination,
                        tags=("charge",),
                    )
                )
        actions.append(self._end_phase_action(state))
        return actions

    def _combat_actions(self, state: GameState) -> List[GameAction]:
        actions: List[GameAction] = []
        next_side = self._next_combat_side(state)
        if next_side is not None:
            for unit in self._combat_pool_for_side(state, next_side):
                for enemy in self._enemies_in_combat(state, unit):
                    actions.append(
                        GameAction(
                            action_type="fight",
                            actor_id=unit.id,
                            target_id=enemy.id,
                            tags=("fight", "combat"),
                        )
                    )
        actions.extend(self._command_actions(state, ("all_out_attack", "all_out_defence")))
        if not self._combat_pending(state):
            actions.append(self._end_phase_action(state))
        return actions

    def _command_actions(self, state: GameState, commands: Sequence[str]) -> List[GameAction]:
        side = state.active_side
        usage = self._command_usage_snapshot(state)
        if state.command_points.get(side.value, 0) < 1:
            return []
        actions: List[GameAction] = []
        for unit in state.alive_units_for(side):
            if unit.id in usage.get("units", []):
                continue
            for command in commands:
                if usage.get("commands", {}).get(command, 0) >= 1:
                    continue
                if self._command_makes_sense(state, unit, command):
                    actions.append(
                        GameAction(
                            action_type="command",
                            actor_id=unit.id,
                            payload={"command": command},
                            tags=("command", command),
                        )
                    )
        return actions

    # ------------------------------------------------------------------
    # Validation

    def validate_action(self, state: GameState, action: GameAction) -> ValidationResult:
        result = ValidationResult()
        if state.is_complete:
            result.add("game_complete", "the game is complete")
            return result
        if not isinstance(action, GameAction):
            result.add("action_type", "action must be a GameAction")
            return result
        allowed = {
            "deploy",
            "end_deployment",
            "end_phase",
            "move",
            "run",
            "retreat",
            "shoot",
            "charge",
            "fight",
            "command",
        }
        if action.action_type not in allowed:
            result.add("unknown_action", f"unknown action type {action.action_type!r}")
            return result

        if action.action_type == "end_deployment":
            self._validate_end_deployment(state, action, result)
            return result
        if action.action_type == "end_phase":
            self._validate_end_phase(state, action, result)
            return result
        if action.action_type == "deploy":
            self._validate_deploy(state, action, result)
            return result

        unit = state.unit_by_id(action.actor_id)
        if unit is None:
            result.add("unknown_unit", f"no unit with id {action.actor_id!r}")
            return result
        if not unit.alive:
            result.add("destroyed_unit", f"unit {unit.id!r} is destroyed")
        if action.action_type == "fight":
            self._validate_fight(state, action, unit, result)
        elif unit.side is not state.active_side:
            result.add("wrong_side", f"unit {unit.id!r} does not belong to the active side")
        elif action.action_type == "move":
            self._validate_move(state, action, unit, result, run=False)
        elif action.action_type == "run":
            self._validate_move(state, action, unit, result, run=True)
        elif action.action_type == "retreat":
            self._validate_retreat(state, action, unit, result)
        elif action.action_type == "shoot":
            self._validate_shoot(state, action, unit, result)
        elif action.action_type == "charge":
            self._validate_charge(state, action, unit, result)
        elif action.action_type == "command":
            self._validate_command(state, action, unit, result)
        return result

    def _validate_end_deployment(
        self, state: GameState, action: GameAction, result: ValidationResult
    ) -> None:
        if state.phase != "deployment":
            result.add("wrong_phase", "the army is not in its deployment step")
            return
        if action.actor_id != state.active_side.value:
            result.add("active_side", f"it is {state.active_side.value}'s deployment step")
            return
        for unit in state.alive_units_for(state.active_side):
            if not self._in_deployment_zone(state, unit.side, unit.position):
                result.add(
                    "outside_deployment_zone",
                    f"{unit.id!r} is outside its deployment zone",
                )

    def _validate_end_phase(
        self, state: GameState, action: GameAction, result: ValidationResult
    ) -> None:
        if action.actor_id != state.active_side.value:
            result.add("active_side", f"it is {state.active_side.value}'s turn")
            return
        if state.phase not in CORE_PHASE_IDS:
            result.add("wrong_phase", f"cannot end the {state.phase!r} phase")
            return
        if state.phase == "combat" and self._combat_pending(state):
            result.add("combat_pending", "all eligible units must fight before the phase ends")

    def _validate_deploy(
        self, state: GameState, action: GameAction, result: ValidationResult
    ) -> None:
        if state.phase != "deployment":
            result.add("wrong_phase", "deployment actions are only legal during deployment")
            return
        unit = state.unit_by_id(action.actor_id)
        if unit is None:
            result.add("unknown_unit", f"no unit with id {action.actor_id!r}")
            return
        if unit.side is not state.active_side:
            result.add("wrong_side", "only the active army can deploy")
        if unit.flags.get("deployed"):
            result.add("already_deployed", f"{unit.id!r} has already been placed")
        if action.destination is None:
            result.add("destination", "a deployment action needs a destination")
            return
        if not state.board.contains(action.destination, margin=unit.base_radius):
            result.add("off_board", "the destination is outside the board")
        if not self._in_deployment_zone(state, unit.side, action.destination):
            result.add("outside_deployment_zone", "the destination is outside your territory")
        if not self._destination_clear(state, unit, action.destination):
            result.add("overlap", "the destination overlaps another unit")

    def _validate_move(
        self,
        state: GameState,
        action: GameAction,
        unit: Unit,
        result: ValidationResult,
        *,
        run: bool,
    ) -> None:
        if state.phase != "movement":
            result.add("wrong_phase", "movement is only legal in the movement phase")
        if unit.flags.get("moved"):
            result.add("already_moved", f"unit {unit.id!r} has already moved this turn")
        if action.destination is None:
            result.add("destination", "a move action needs a destination")
            return
        destination = action.destination
        maximum = unit.move + (6.0 if run else 0.0)
        distance = unit.position.distance_to(destination)
        if distance > maximum + 1e-4:
            result.add(
                "move_range",
                f'{unit.id!r} can move at most {maximum:.1f}", not {distance:.2f}"',
            )
        if not state.board.contains(destination, margin=unit.base_radius):
            result.add("off_board", "the destination is outside the board")
        if not self._destination_clear(state, unit, destination):
            result.add("overlap", "the destination overlaps another unit")
        if self._unit_in_combat(state, unit):
            result.add("in_combat", "a unit in combat must retreat rather than move normally")
        for enemy in state.alive_units_for(unit.side.other):
            edge = max(
                0.0,
                destination.distance_to(enemy.position) - unit.base_radius - enemy.base_radius,
            )
            if edge <= COMBAT_RANGE + 1e-9:
                result.add(
                    "engagement",
                    'a normal move or run cannot end within 3" of an enemy',
                )
                break

    def _validate_retreat(
        self, state: GameState, action: GameAction, unit: Unit, result: ValidationResult
    ) -> None:
        if state.phase != "movement":
            result.add("wrong_phase", "retreat is only legal in the movement phase")
        if unit.flags.get("moved"):
            result.add("already_moved", f"unit {unit.id!r} has already moved this turn")
        if not self._unit_in_combat(state, unit):
            result.add("not_in_combat", "only a unit in combat can retreat")
        if action.destination is None:
            result.add("destination", "a retreat action needs a destination")
            return
        distance = unit.position.distance_to(action.destination)
        if distance > unit.move + 1e-4:
            result.add("move_range", f'{unit.id!r} can retreat at most {unit.move:.1f}"')
        if not state.board.contains(action.destination, margin=unit.base_radius):
            result.add("off_board", "the destination is outside the board")
        if not self._destination_clear(state, unit, action.destination):
            result.add("overlap", "the destination overlaps another unit")
        for enemy in state.alive_units_for(unit.side.other):
            edge = max(
                0.0,
                action.destination.distance_to(enemy.position)
                - unit.base_radius
                - enemy.base_radius,
            )
            if edge <= COMBAT_RANGE + 1e-9:
                result.add("engagement", 'a retreat must end outside 3" of every enemy')
                break

    def _validate_shoot(
        self, state: GameState, action: GameAction, unit: Unit, result: ValidationResult
    ) -> None:
        if state.phase != "shooting":
            result.add("wrong_phase", "shooting is only legal in the shooting phase")
        if unit.flags.get("shot"):
            result.add("already_shot", f"unit {unit.id!r} has already shot this turn")
        if unit.flags.get("advanced"):
            result.add("advanced", "a unit that ran or retreated cannot shoot")
        if self._unit_in_combat(state, unit):
            result.add("in_combat", "a unit in combat cannot shoot")
        if action.target_id is None:
            result.add("target", "a shoot action needs a target")
            return
        target = state.unit_by_id(action.target_id)
        if target is None:
            result.add("unknown_target", f"no unit with id {action.target_id!r}")
            return
        if target.side is unit.side:
            result.add("friendly_target", "cannot shoot a friendly unit")
        if not target.alive:
            result.add("destroyed_target", f"target {target.id!r} is destroyed")
        if not any(weapon.range_inches > 0 for weapon in unit.weapons):
            result.add("no_ranged_weapon", f"unit {unit.id!r} has no ranged weapon")
        if not self._can_shoot(state, unit, target):
            result.add("no_shot", "the target is not visible and in range with a ranged weapon")

    def _validate_charge(
        self, state: GameState, action: GameAction, unit: Unit, result: ValidationResult
    ) -> None:
        if state.phase != "charge":
            result.add("wrong_phase", "charges are only legal in the charge phase")
        if unit.flags.get("charged"):
            result.add("already_charged", f"unit {unit.id!r} has already charged")
        if unit.flags.get("advanced"):
            result.add("advanced", "a unit that ran or retreated cannot charge")
        if self._unit_in_combat(state, unit):
            result.add("in_combat", "a unit already in combat cannot charge")
        if action.target_id is None:
            result.add("target", "a charge action needs a target")
            return
        target = state.unit_by_id(action.target_id)
        if target is None:
            result.add("unknown_target", f"no unit with id {action.target_id!r}")
            return
        if target.side is unit.side:
            result.add("friendly_target", "cannot charge a friendly unit")
        if not target.alive:
            result.add("destroyed_target", f"target {target.id!r} is destroyed")
        if action.destination is None:
            result.add("destination", "a charge action needs a destination")
            return
        distance = unit.position.distance_to(action.destination)
        if distance > MAX_CHARGE + 1e-4:
            result.add("charge_range", 'a charge move cannot exceed 12"')
        if not state.board.contains(action.destination, margin=unit.base_radius):
            result.add("off_board", "the destination is outside the board")
        if not self._destination_clear(state, unit, action.destination):
            result.add("overlap", "the destination overlaps another unit")
        edge = max(
            0.0,
            action.destination.distance_to(target.position) - unit.base_radius - target.base_radius,
        )
        if edge > ENGAGEMENT_RANGE + 1e-9:
            result.add("charge_engagement", 'a charge must end within 1/2" of its target')

    def _validate_fight(
        self, state: GameState, action: GameAction, unit: Unit, result: ValidationResult
    ) -> None:
        if state.phase != "combat":
            result.add("wrong_phase", "fights are only legal in the combat phase")
        if unit.flags.get("fought"):
            result.add("already_fought", f"unit {unit.id!r} has already fought")
        next_side = self._next_combat_side(state)
        if next_side is None:
            result.add("no_combat", "there are no eligible units left to fight")
        elif unit.side is not next_side:
            result.add("combat_order", f"it is {next_side.value}'s turn to pick a unit")
        pool = self._combat_pool_for_side(state, unit.side) if next_side else []
        if unit not in pool:
            result.add("not_eligible", "this unit is not currently eligible to fight")
        if action.target_id is None:
            result.add("target", "a fight action needs a target")
            return
        target = state.unit_by_id(action.target_id)
        if target is None:
            result.add("unknown_target", f"no unit with id {action.target_id!r}")
            return
        if target.side is unit.side:
            result.add("friendly_target", "cannot fight a friendly unit")
        if not target.alive:
            result.add("destroyed_target", f"target {target.id!r} is destroyed")
        if not unit_in_combat(unit, target, COMBAT_RANGE):
            result.add("not_in_combat", f"target {target.id!r} is outside combat range")

    def _validate_command(
        self, state: GameState, action: GameAction, unit: Unit, result: ValidationResult
    ) -> None:
        if unit.side is not state.active_side:
            result.add("wrong_side", "only the active army can use commands")
        command = str(action.payload.get("command", ""))
        if command not in COMMANDS:
            result.add("unknown_command", f"unknown command {command!r}")
            return
        if state.command_points.get(unit.side.value, 0) < 1:
            result.add("no_command_points", "not enough command points")
        if command == "rally" and state.phase != "hero":
            result.add("wrong_phase", "Rally is a Hero-phase command")
        if command in ("all_out_attack", "all_out_defence") and state.phase not in (
            "shooting",
            "combat",
        ):
            result.add("wrong_phase", "this command is only available in Shooting or Combat")
        usage = self._command_usage_snapshot(state)
        if unit.id in usage.get("units", []):
            result.add("unit_commanded", f"{unit.id!r} has already used a command this phase")
        if usage.get("commands", {}).get(command, 0) >= 1:
            result.add("command_used", f"{command!r} has already been used this phase")
        if command == "rally" and int(unit.wounds or 0) >= unit.max_wounds:
            result.add("full_health", "Rally cannot heal a unit that is already at full health")

    # ------------------------------------------------------------------
    # Application

    def apply_action(self, state: GameState, action: GameAction) -> ActionResult:
        validation = self.validate_action(state, action)
        if not validation.ok:
            raise IllegalActionError(
                f"illegal action {action.action_type}: {validation.errors[0].message}",
                validation,
            )

        next_state = copy.deepcopy(state)
        dice = Dice(next_state.dice)
        events: List[Event] = []
        action_type = action.action_type

        if action_type == "deploy":
            self._apply_deploy(next_state, action, events)
        elif action_type == "end_deployment":
            self._apply_end_deployment(next_state, events)
        elif action_type == "end_phase":
            self._advance_phase(next_state, dice, events)
        elif action_type in ("move", "run", "retreat"):
            self._apply_move(next_state, action, dice, events)
        elif action_type == "shoot":
            self._apply_shoot(next_state, action, dice, events)
        elif action_type == "charge":
            self._apply_charge(next_state, action, dice, events)
        elif action_type == "fight":
            self._apply_fight(next_state, action, dice, events)
        elif action_type == "command":
            self._apply_command(next_state, action, dice, events)
        else:  # pragma: no cover - validation has already rejected this
            raise IllegalActionError(f"unsupported action {action_type!r}")

        next_state.dice = dice.state
        return ActionResult(state=next_state, events=events)

    def _apply_deploy(self, state: GameState, action: GameAction, events: List[Event]) -> None:
        unit = state.unit_by_id(action.actor_id)
        if unit is None or action.destination is None:
            raise IllegalActionError("validated deployment action is incomplete")
        unit.position = action.destination
        unit.flags["deployed"] = True
        events.append(
            make_event(
                "unit_deployed",
                f"{unit.name} deployed at ({unit.position.x:.1f}, {unit.position.y:.1f}).",
                unit=unit.id,
                side=unit.side.value,
                position=unit.position.to_dict(),
            )
        )

    def _apply_end_deployment(self, state: GameState, events: List[Event]) -> None:
        events.append(
            make_event(
                "deployment_ended",
                f"{state.active_side.value} finished deployment.",
                side=state.active_side.value,
            )
        )
        state.metadata["deployment_complete"] = True
        self._begin_battle(state, events)

    def _apply_move(
        self,
        state: GameState,
        action: GameAction,
        dice: Dice,
        events: List[Event],
    ) -> None:
        unit = state.unit_by_id(action.actor_id)
        if unit is None or action.destination is None:
            raise IllegalActionError("validated movement action is incomplete")
        origin = unit.position
        distance = origin.distance_to(action.destination)
        if action.action_type == "run":
            roll = dice.d6()
            allowed = unit.move + roll
            travel = min(distance, allowed)
            destination = origin.lerp(action.destination, travel / distance) if distance else origin
            unit.position = destination
            unit.flags["moved"] = True
            unit.flags["advanced"] = True
            events.append(
                make_event(
                    "unit_ran",
                    f'{unit.name} ran {origin.distance_to(destination):.1f}" (D6={roll}).',
                    unit=unit.id,
                    side=unit.side.value,
                    roll=roll,
                    move=unit.move,
                    distance=round(origin.distance_to(destination), 2),
                    from_position=origin.to_dict(),
                    to_position=destination.to_dict(),
                )
            )
            return

        unit.position = action.destination
        unit.flags["moved"] = True
        if action.action_type == "retreat":
            unit.flags["advanced"] = True
            mortal = dice.d3()
            applied = unit.take_damage(mortal)
            events.append(
                make_event(
                    "unit_retreated",
                    f"{unit.name} retreated and suffered {applied} mortal damage.",
                    unit=unit.id,
                    side=unit.side.value,
                    distance=round(distance, 2),
                    mortal_damage=applied,
                    from_position=origin.to_dict(),
                    to_position=unit.position.to_dict(),
                )
            )
            if not unit.alive:
                events.append(self._destroyed_event(unit))
            return

        events.append(
            make_event(
                "unit_moved",
                f'{unit.name} moved {distance:.1f}".',
                unit=unit.id,
                side=unit.side.value,
                distance=round(distance, 2),
                from_position=origin.to_dict(),
                to_position=unit.position.to_dict(),
            )
        )

    def _apply_shoot(
        self,
        state: GameState,
        action: GameAction,
        dice: Dice,
        events: List[Event],
    ) -> None:
        attacker = state.unit_by_id(action.actor_id)
        target = state.unit_by_id(action.target_id or "")
        if attacker is None or target is None:
            raise IllegalActionError("validated shoot action is incomplete")
        hit_modifier = 1 if self._has_buff(state, attacker, "all_out_attack") else 0
        save_modifier = 1 if self._has_buff(state, target, "all_out_defence") else 0
        for weapon in attacker.weapons:
            if weapon.is_melee or not self._weapon_in_range(attacker, target, weapon):
                continue
            if not target.alive:
                break
            self._resolve_attack(
                state,
                attacker,
                target,
                weapon,
                dice,
                events,
                hit_modifier=hit_modifier,
                save_modifier=save_modifier,
                ranged=True,
            )
        attacker.flags["shot"] = True

    def _apply_charge(
        self,
        state: GameState,
        action: GameAction,
        dice: Dice,
        events: List[Event],
    ) -> None:
        unit = state.unit_by_id(action.actor_id)
        target = state.unit_by_id(action.target_id or "")
        if unit is None or target is None or action.destination is None:
            raise IllegalActionError("validated charge action is incomplete")
        distance = unit.position.distance_to(action.destination)
        roll = dice.d6() + dice.d6()
        unit.flags["charged"] = True
        success = roll + 1e-9 >= distance
        if not success:
            events.append(
                make_event(
                    "charge_failed",
                    f'{unit.name} failed a {distance:.1f}" charge with a roll of {roll}.',
                    unit=unit.id,
                    target=target.id,
                    roll=roll,
                    distance=round(distance, 2),
                )
            )
            return
        origin = unit.position
        unit.position = action.destination
        unit.flags["moved"] = True
        unit.stats["charge_turn"] = int(state.metadata.get("turn_number", 1))
        events.append(
            make_event(
                "charge_succeeded",
                f'{unit.name} charged {target.name} with a roll of {roll} ({distance:.1f}").',
                unit=unit.id,
                target=target.id,
                side=unit.side.value,
                roll=roll,
                distance=round(distance, 2),
                from_position=origin.to_dict(),
                to_position=unit.position.to_dict(),
            )
        )

    def _apply_fight(
        self,
        state: GameState,
        action: GameAction,
        dice: Dice,
        events: List[Event],
    ) -> None:
        attacker = state.unit_by_id(action.actor_id)
        target = state.unit_by_id(action.target_id or "")
        if attacker is None or target is None:
            raise IllegalActionError("validated fight action is incomplete")
        self._pile_in(state, attacker, target, events)
        hit_modifier = 1 if self._has_buff(state, attacker, "all_out_attack") else 0
        save_modifier = 1 if self._has_buff(state, target, "all_out_defence") else 0
        for weapon in attacker.weapons:
            if not weapon.is_melee or not target.alive:
                continue
            self._resolve_attack(
                state,
                attacker,
                target,
                weapon,
                dice,
                events,
                hit_modifier=hit_modifier,
                save_modifier=save_modifier,
                ranged=False,
            )
        attacker.flags["fought"] = True
        state.metadata["combat_last_side"] = attacker.side.value
        events.append(
            make_event(
                "unit_fought",
                f"{attacker.name} fought {target.name}.",
                unit=attacker.id,
                target=target.id,
                side=attacker.side.value,
            )
        )

    def _apply_command(
        self,
        state: GameState,
        action: GameAction,
        dice: Dice,
        events: List[Event],
    ) -> None:
        unit = state.unit_by_id(action.actor_id)
        if unit is None:
            raise IllegalActionError("validated command is missing its unit")
        command = str(action.payload.get("command"))
        state.command_points[unit.side.value] = max(
            0, state.command_points.get(unit.side.value, 0) - 1
        )
        usage = self._command_usage(state)
        usage["commands"][command] = usage["commands"].get(command, 0) + 1
        usage["units"].append(unit.id)
        token = self._phase_token(state)

        if command == "rally":
            roll = dice.d3()
            before = int(unit.wounds or 0)
            unit.wounds = min(unit.max_wounds, before + roll)
            if unit.wounds > 0:
                unit.destroyed = False
                unit.models = min(
                    unit.max_models or 0,
                    max(1, math.ceil(unit.wounds / unit.wounds_per_model)),
                )
            events.append(
                make_event(
                    "rally_resolved",
                    f"{unit.name} rallied {unit.wounds - before} wound(s).",
                    unit=unit.id,
                    side=unit.side.value,
                    roll=roll,
                    healed=unit.wounds - before,
                    wounds=unit.wounds,
                    models=unit.models,
                )
            )
        elif command == "all_out_attack":
            unit.stats["all_out_attack"] = token
        elif command == "all_out_defence":
            unit.stats["all_out_defence"] = token

        events.append(
            make_event(
                "command_used",
                f"{unit.side.value} used {command} on {unit.name}.",
                unit=unit.id,
                side=unit.side.value,
                command=command,
                command_points=state.command_points.get(unit.side.value, 0),
            )
        )

    # ------------------------------------------------------------------
    # Combat resolution

    def _resolve_attack(
        self,
        state: GameState,
        attacker: Unit,
        target: Unit,
        weapon: Weapon,
        dice: Dice,
        events: List[Event],
        *,
        hit_modifier: int,
        save_modifier: int,
        ranged: bool,
    ) -> None:
        if ranged:
            cover = self._target_in_cover(state, target)
        else:
            cover = False
        if ranged and cover:
            hit_modifier -= 1
        ward = target.stats.get("ward")
        result = resolve_weapon_attacks(
            dice,
            weapon,
            target.save,
            int(ward) if ward is not None else None,
            hit_modifier=hit_modifier,
            save_modifier=save_modifier,
        )
        applied = target.take_damage(result.damage)
        events.append(
            make_event(
                "attack_resolved",
                (
                    f"{attacker.name} attacked {target.name} with {weapon.name}: "
                    f"{result.hits} hit(s), {result.wounds} wound(s), "
                    f"{applied} damage."
                ),
                attacker=attacker.id,
                target=target.id,
                side=attacker.side.value,
                weapon=weapon.id,
                ranged=ranged,
                distance=round(unit_edge_distance(attacker, target), 2),
                cover=cover,
                hit_modifier=hit_modifier,
                save_modifier=save_modifier,
                save_target=max(2, target.save + weapon.armor_penetration - save_modifier),
                **result.to_dict(),
                target_wounds=target.wounds,
                target_models=target.models,
                target_destroyed=not target.alive,
            )
        )
        if not target.alive:
            events.append(self._destroyed_event(target))

    def _pile_in(
        self,
        state: GameState,
        attacker: Unit,
        target: Unit,
        events: List[Event],
    ) -> None:
        edge = unit_edge_distance(attacker, target)
        if edge <= ENGAGEMENT_RANGE + 1e-9:
            return
        center_distance = attacker.position.distance_to(target.position)
        desired = attacker.base_radius + target.base_radius + 0.4
        travel = min(COMBAT_RANGE, max(0.0, center_distance - desired))
        if travel <= 1e-6 or center_distance <= 1e-9:
            return
        destination = attacker.position.lerp(target.position, travel / center_distance)
        destination = clamp_point_within_board(
            destination,
            state.board.width,
            state.board.height,
            margin=attacker.base_radius,
        )
        if not self._destination_clear(state, attacker, destination):
            return
        origin = attacker.position
        attacker.position = destination
        events.append(
            make_event(
                "unit_piled_in",
                f'{attacker.name} piled in {origin.distance_to(destination):.1f}".',
                unit=attacker.id,
                target=target.id,
                distance=round(origin.distance_to(destination), 2),
                from_position=origin.to_dict(),
                to_position=destination.to_dict(),
            )
        )

    def _destroyed_event(self, unit: Unit) -> Event:
        return make_event(
            "unit_destroyed",
            f"{unit.name} was destroyed.",
            unit=unit.id,
            side=unit.side.value,
        )

    # ------------------------------------------------------------------
    # Turn and phase flow

    def _advance_phase(
        self,
        state: GameState,
        dice: Dice,
        events: List[Event],
    ) -> None:
        current = state.phase
        events.append(
            make_event(
                "phase_ended",
                f"{state.active_side.value} ended the {current} phase.",
                phase=current,
                side=state.active_side.value,
            )
        )
        if current == "end_of_turn":
            self._end_turn(state, dice, events)
            return
        index = CORE_PHASE_IDS.index(current)
        next_phase = CORE_PHASE_IDS[index + 1]
        state.phase = next_phase
        state.metadata["combat_last_side"] = None
        started = make_event(
            "phase_started",
            f"{state.active_side.value} started the {next_phase} phase.",
            phase=next_phase,
            side=state.active_side.value,
        )
        started.phase = next_phase
        events.append(started)

    def _end_turn(
        self,
        state: GameState,
        dice: Dice,
        events: List[Event],
    ) -> None:
        ended_side = state.active_side
        events.append(
            make_event(
                "turn_ended",
                f"{ended_side.value} ended their turn.",
                side=ended_side.value,
            )
        )
        events.extend(self._update_objective_control(state))
        events.extend(self._score_objectives(state, ended_side))

        if ended_side is Side.PLAYER:
            self._start_turn(state, Side.AI, events)
            return

        reset_points = {side.value: 0 for side in (Side.PLAYER, Side.AI)}
        state.command_points = reset_points
        events.append(
            make_event(
                "command_points_reset",
                "Command points reset at the end of the battle round.",
                phase="end_of_turn",
            )
        )
        state.round += 1
        if state.round > state.max_rounds:
            state.status = "complete"
            state.phase = "complete"
            winner = self._winner(state)
            state.metadata["winner"] = winner.value if winner else "draw"
            events.append(
                make_event(
                    "game_complete",
                    (
                        f"Game complete: {state.score_for(Side.PLAYER)}"
                        f"-{state.score_for(Side.AI)} "
                        f"({winner.value if winner else 'draw'})."
                    ),
                    phase="complete",
                    round=state.round,
                    player_score=state.score_for(Side.PLAYER),
                    ai_score=state.score_for(Side.AI),
                    winner=winner.value if winner else None,
                )
            )
            return

        self._start_battle_round(state, events)
        self._start_turn(state, Side.PLAYER, events)

    def _begin_battle(self, state: GameState, events: Optional[List[Event]] = None) -> None:
        state.round = 1
        self._start_battle_round(state, events)
        self._start_turn(state, Side.PLAYER, events)

    def _start_battle_round(self, state: GameState, events: Optional[List[Event]] = None) -> None:
        player = state.score_for(Side.PLAYER)
        ai = state.score_for(Side.AI)
        underdog: Optional[Side] = None
        if player < ai:
            underdog = Side.PLAYER
        elif ai < player:
            underdog = Side.AI
        for side in (Side.PLAYER, Side.AI):
            points = 4 + (1 if underdog is side else 0)
            state.command_points[side.value] = points
        if events is not None:
            round_started = make_event(
                "round_started",
                f"Battle round {state.round} started.",
                phase="start_of_turn",
                round=state.round,
                player_command_points=state.command_points[Side.PLAYER.value],
                ai_command_points=state.command_points[Side.AI.value],
                underdog=underdog.value if underdog else None,
            )
            round_started.round = state.round
            round_started.phase = "start_of_turn"
            events.append(round_started)
            events.extend(self._update_objective_control(state))

    def _start_turn(
        self,
        state: GameState,
        side: Side,
        events: Optional[List[Event]] = None,
    ) -> None:
        state.active_side = side
        state.phase = "start_of_turn"
        state.metadata["turn_number"] = int(state.metadata.get("turn_number", 0)) + 1
        state.metadata["combat_last_side"] = None
        state.metadata["command_usage"] = {}
        for unit in state.units_for(side):
            unit.reset_turn_flags()
        if events is not None:
            turn_started = make_event(
                "turn_started",
                f"{side.value} started their turn (round {state.round}).",
                phase="start_of_turn",
                round=state.round,
                side=side.value,
            )
            turn_started.round = state.round
            turn_started.phase = "start_of_turn"
            turn_started.side = side.value
            events.append(turn_started)

    def _winner(self, state: GameState) -> Optional[Side]:
        player = state.score_for(Side.PLAYER)
        ai = state.score_for(Side.AI)
        if player == ai:
            return None
        return Side.PLAYER if player > ai else Side.AI

    # ------------------------------------------------------------------
    # Objectives and scoring

    def _update_objective_control(
        self, state: GameState, events: Optional[List[Event]] = None
    ) -> List[Event]:
        emitted: List[Event] = []
        assignments: Dict[str, List[Unit]] = {objective.id: [] for objective in state.objectives}
        for unit in state.all_units():
            if not unit.alive:
                continue
            candidates = [
                objective for objective in state.objectives if objective.contains(unit.position)
            ]
            if not candidates:
                continue
            closest = min(
                candidates,
                key=lambda objective: unit.position.distance_to(objective.position),
            )
            assignments[closest.id].append(unit)

        for objective in state.objectives:
            player_control = sum(
                unit.models * int(unit.stats.get("control", 1))
                for unit in assignments[objective.id]
                if unit.side is Side.PLAYER
            )
            ai_control = sum(
                unit.models * int(unit.stats.get("control", 1))
                for unit in assignments[objective.id]
                if unit.side is Side.AI
            )
            previous = objective.controller
            if player_control > ai_control:
                objective.controller = Side.PLAYER
            elif ai_control > player_control:
                objective.controller = Side.AI
            # Equal control leaves the previous controller in place: control
            # persists until an opponent actually takes it.
            if objective.controller is not previous:
                emitted.append(
                    make_event(
                        "objective_controlled",
                        f"{objective.controller.value if objective.controller else 'nobody'} "
                        f"controls {objective.name}.",
                        objective=objective.id,
                        side=objective.controller.value if objective.controller else None,
                        player_control=player_control,
                        ai_control=ai_control,
                    )
                )
            elif events is not None:
                emitted.append(
                    make_event(
                        "objective_checked",
                        (
                            f"{objective.name}: player control {player_control}, "
                            f"ai control {ai_control}, controller "
                            f"{objective.controller.value if objective.controller else 'none'}."
                        ),
                        objective=objective.id,
                        player_control=player_control,
                        ai_control=ai_control,
                        controller=objective.controller.value if objective.controller else None,
                    )
                )
        if events is not None:
            events.extend(emitted)
        return emitted

    def _score_objectives(self, state: GameState, side: Side) -> List[Event]:
        events: List[Event] = []
        for objective in state.objectives:
            if objective.controller is side:
                state.add_score(side, objective.value)
                events.append(
                    make_event(
                        "objective_scored",
                        f"{side.value} scored {objective.value} VP for {objective.name}.",
                        objective=objective.id,
                        side=side.value,
                        value=objective.value,
                        total=state.score_for(side),
                    )
                )
        return events

    # ------------------------------------------------------------------
    # Combat ordering helpers

    def _combat_pending(self, state: GameState) -> bool:
        return bool(self._combat_pending_units(state))

    def _combat_pending_units(self, state: GameState) -> List[Unit]:
        units: List[Unit] = []
        for unit in state.all_units():
            if not unit.alive or unit.flags.get("fought"):
                continue
            if self._enemies_in_combat(state, unit):
                units.append(unit)
        return units

    def _combat_pool_for_side(self, state: GameState, side: Side) -> List[Unit]:
        pending = self._combat_pending_units(state)
        strike_first = self._strike_first_units(state, pending)
        pool = strike_first if strike_first else pending
        return [unit for unit in pool if unit.side is side]

    def _strike_first_units(self, state: GameState, pending: Sequence[Unit]) -> List[Unit]:
        turn_number = int(state.metadata.get("turn_number", 0))
        return [unit for unit in pending if int(unit.stats.get("charge_turn", -1)) == turn_number]

    def _next_combat_side(self, state: GameState) -> Optional[Side]:
        pending = self._combat_pending_units(state)
        if not pending:
            return None
        strike_first = self._strike_first_units(state, pending)
        pool = strike_first if strike_first else pending
        last_raw = state.metadata.get("combat_last_side")
        last: Optional[Side] = None
        if last_raw is not None:
            try:
                last = Side.parse(last_raw)
            except ValueError:
                last = None
        order = [state.active_side, state.active_side.other]
        if last is not None:
            order = [last.other, last]
        for side in order:
            if any(unit.side is side for unit in pool):
                return side
        return pool[0].side

    # ------------------------------------------------------------------
    # Geometry and capability helpers

    def _unit_in_combat(self, state: GameState, unit: Unit) -> bool:
        return bool(self._enemies_in_combat(state, unit))

    def _enemies_in_combat(self, state: GameState, unit: Unit) -> List[Unit]:
        return [
            enemy
            for enemy in state.alive_units_for(unit.side.other)
            if unit_in_combat(unit, enemy, COMBAT_RANGE)
        ]

    def _deployment_zone(self, state: GameState, side: Side):
        zones = state.deployment_zones.get(side.value, [])
        return zones[0] if zones else None

    def _in_deployment_zone(self, state: GameState, side: Side, point: Vec2) -> bool:
        return any(
            polygon.contains(point) for polygon in state.deployment_zones.get(side.value, [])
        )

    def _destination_clear(self, state: GameState, unit: Unit, destination: Vec2) -> bool:
        if not state.board.contains(destination, margin=unit.base_radius):
            return False
        for other in state.all_units():
            if other.id == unit.id or not other.alive:
                continue
            minimum = unit.base_radius + other.base_radius + 0.1
            if destination.distance_to(other.position) < minimum:
                return False
        for feature in state.terrain:
            if "impassable" in feature.tags and feature.contains(destination):
                return False
        return True

    def _unique_destinations(
        self,
        state: GameState,
        unit: Unit,
        destinations: Sequence[Vec2],
        *,
        require_no_engagement: bool,
    ) -> Tuple[Vec2, ...]:
        result: List[Vec2] = []
        seen: Set[Tuple[float, float]] = set()
        for candidate in destinations:
            destination = candidate.rounded(4)
            key = (destination.x, destination.y)
            if key in seen:
                continue
            if destination.distance_to(unit.position) < 0.01:
                continue
            if not self._destination_clear(state, unit, destination):
                continue
            if require_no_engagement:
                blocked = False
                for enemy in state.alive_units_for(unit.side.other):
                    edge = max(
                        0.0,
                        destination.distance_to(enemy.position)
                        - unit.base_radius
                        - enemy.base_radius,
                    )
                    if edge <= COMBAT_RANGE + 1e-9:
                        blocked = True
                        break
                if blocked:
                    continue
            seen.add(key)
            result.append(destination)
        return tuple(result)

    def _movement_candidates(
        self, state: GameState, unit: Unit, maximum: float
    ) -> Tuple[Vec2, ...]:
        candidates: List[Vec2] = []
        for objective in state.objectives:
            candidates.append(
                clamp_point_within_board(
                    point_at_range(unit.position, objective.position, maximum),
                    state.board.width,
                    state.board.height,
                    margin=unit.base_radius,
                )
            )
        for enemy in state.alive_units_for(unit.side.other):
            candidate = self._approach_destination(state, unit, enemy, maximum)
            if candidate is not None:
                candidates.append(candidate)
        for feature in state.terrain:
            if feature.cover:
                candidates.append(
                    clamp_point_within_board(
                        point_at_range(unit.position, feature.footprint.center, maximum),
                        state.board.width,
                        state.board.height,
                        margin=unit.base_radius,
                    )
                )
        return self._unique_destinations(state, unit, candidates, require_no_engagement=True)

    def _approach_destination(
        self, state: GameState, unit: Unit, enemy: Unit, maximum: float
    ) -> Optional[Vec2]:
        distance = unit.position.distance_to(enemy.position)
        if distance <= 1e-9:
            return None
        desired = unit.base_radius + enemy.base_radius + COMBAT_RANGE + 0.05
        if distance <= desired + 0.01:
            return None
        travel = min(maximum, distance - desired)
        if travel <= 0.01:
            return None
        return clamp_point_within_board(
            unit.position.lerp(enemy.position, travel / distance),
            state.board.width,
            state.board.height,
            margin=unit.base_radius,
        )

    def _retreat_candidates(self, state: GameState, unit: Unit) -> Tuple[Vec2, ...]:
        candidates: List[Vec2] = []
        for enemy in state.alive_units_for(unit.side.other):
            vector = unit.position - enemy.position
            length = vector.length()
            if length <= 1e-9:
                continue
            direction = vector / length
            candidates.append(
                clamp_point_within_board(
                    unit.position + direction * unit.move,
                    state.board.width,
                    state.board.height,
                    margin=unit.base_radius,
                )
            )
        result: List[Vec2] = []
        for destination in self._unique_destinations(
            state, unit, candidates, require_no_engagement=False
        ):
            if all(
                max(
                    0.0,
                    destination.distance_to(enemy.position) - unit.base_radius - enemy.base_radius,
                )
                > COMBAT_RANGE + 1e-9
                for enemy in state.alive_units_for(unit.side.other)
            ):
                result.append(destination)
        return tuple(result)

    def _charge_destination(self, unit: Unit, enemy: Unit) -> Optional[Vec2]:
        distance = unit.position.distance_to(enemy.position)
        desired = unit.base_radius + enemy.base_radius + 0.4
        if distance <= desired + 1e-9:
            return None
        travel = distance - desired
        if travel > MAX_CHARGE + 1e-9:
            return None
        destination = unit.position.lerp(enemy.position, travel / distance)
        return destination.rounded(4)

    def _destination_tags(self, state: GameState, destination: Vec2) -> Tuple[str, ...]:
        tags: List[str] = []
        if any(objective.contains(destination) for objective in state.objectives):
            tags.append("objective")
        if any(feature.cover and feature.contains(destination) for feature in state.terrain):
            tags.append("cover")
        return tuple(tags)

    def _weapon_in_range(self, attacker: Unit, target: Unit, weapon: Weapon) -> bool:
        return unit_edge_distance(attacker, target) <= weapon.range_inches + 1e-9

    def _can_shoot(self, state: GameState, attacker: Unit, target: Unit) -> bool:
        for weapon in attacker.weapons:
            if weapon.is_melee or not self._weapon_in_range(attacker, target, weapon):
                continue
            if self._has_line_of_sight(state, attacker, target):
                return True
        return False

    def _has_line_of_sight(self, state: GameState, attacker: Unit, target: Unit) -> bool:
        for feature in state.terrain:
            if not feature.blocks_line_of_sight:
                continue
            if not feature.footprint.intersects_segment(attacker.position, target.position):
                continue
            if self._unit_has_fly(attacker):
                continue
            if unit_edge_distance(attacker, target) <= 3.0 + 1e-9:
                continue
            return False
        return True

    def _target_in_cover(self, state: GameState, target: Unit) -> bool:
        if self._unit_has_fly(target):
            return False
        turn_number = int(state.metadata.get("turn_number", 0))
        if int(target.stats.get("charge_turn", -1)) == turn_number:
            return False
        return any(feature.cover and feature.contains(target.position) for feature in state.terrain)

    def _unit_has_fly(self, unit: Unit) -> bool:
        return any(keyword.lower() == "fly" for keyword in unit.keywords)

    def _phase_token(self, state: GameState) -> str:
        return f"{state.round}:{state.phase}"

    def _has_buff(self, state: GameState, unit: Unit, kind: str) -> bool:
        return str(unit.stats.get(kind, "")) == self._phase_token(state)

    def _command_usage_snapshot(self, state: GameState) -> Dict[str, Any]:
        usage = state.metadata.get("command_usage")
        if not isinstance(usage, Mapping):
            return {}
        if usage.get("round") != state.round or usage.get("phase") != state.phase:
            return {}
        return dict(usage)

    def _command_usage(self, state: GameState) -> Dict[str, Any]:
        usage = state.metadata.get("command_usage")
        if (
            not isinstance(usage, dict)
            or usage.get("round") != state.round
            or usage.get("phase") != state.phase
        ):
            usage = {
                "round": state.round,
                "phase": state.phase,
                "commands": {},
                "units": [],
            }
            state.metadata["command_usage"] = usage
        usage.setdefault("commands", {})
        usage.setdefault("units", [])
        return usage

    def _command_makes_sense(self, state: GameState, unit: Unit, command: str) -> bool:
        if command == "rally":
            return int(unit.wounds or 0) < unit.max_wounds
        if command == "all_out_attack":
            if state.phase == "shooting":
                return (
                    not unit.flags.get("shot")
                    and not unit.flags.get("advanced")
                    and any(
                        weapon.range_inches > 0
                        for weapon in unit.weapons
                        if any(
                            self._can_shoot(state, unit, enemy)
                            for enemy in state.alive_units_for(unit.side.other)
                        )
                    )
                )
            if state.phase == "combat":
                return not unit.flags.get("fought") and self._unit_in_combat(state, unit)
            return False
        if command == "all_out_defence":
            if state.phase == "shooting":
                return any(weapon.range_inches > 0 for weapon in unit.weapons)
            if state.phase == "combat":
                return self._unit_in_combat(state, unit)
            return False
        return False

    # ------------------------------------------------------------------
    # AI evaluation

    def evaluate_action(
        self,
        state: GameState,
        action: GameAction,
        side: Side,
        weights: Optional[Mapping[str, float]] = None,
    ) -> float:
        weights = weights or {}
        objective_focus = float(weights.get("objective_focus", 1.0))
        damage_focus = float(weights.get("damage_focus", 1.0))
        risk_tolerance = float(weights.get("risk_tolerance", 0.5))
        cover_focus = float(weights.get("cover_focus", 1.0))
        mobility = float(weights.get("mobility", 1.0))

        if action.action_type in ("end_phase", "end_deployment"):
            return 0.05
        unit = state.unit_by_id(action.actor_id)
        if unit is None:
            return -1000.0
        side = unit.side

        if action.action_type == "deploy" and action.destination is not None:
            return self._position_value(
                state,
                unit,
                action.destination,
                objective_focus,
                damage_focus,
                cover_focus,
                mobility,
                deployment=True,
            )

        if action.action_type == "move" and action.destination is not None:
            return self._position_value(
                state,
                unit,
                action.destination,
                objective_focus,
                damage_focus,
                cover_focus,
                mobility,
                deployment=False,
            )

        if action.action_type == "run" and action.destination is not None:
            expected = self._position_value(
                state,
                unit,
                action.destination,
                objective_focus,
                damage_focus,
                cover_focus,
                mobility,
                deployment=False,
            )
            return expected * 0.85
        if action.action_type == "retreat" and action.destination is not None:
            health_ratio = self._health_ratio(unit)
            pressure = max(
                (
                    max(0.0, 18.0 - unit_edge_distance(unit, enemy))
                    for enemy in state.alive_units_for(side.other)
                ),
                default=0.0,
            )
            return (1.0 - health_ratio) * 3.0 * cover_focus + pressure * 0.05 - 0.2

        if action.action_type == "shoot":
            target = state.unit_by_id(action.target_id or "")
            if target is None:
                return -1000.0
            return self._attack_value(
                state,
                unit,
                target,
                objective_focus=objective_focus,
                damage_focus=damage_focus,
                risk_tolerance=risk_tolerance,
                ranged=True,
            )

        if action.action_type == "charge":
            target = state.unit_by_id(action.target_id or "")
            if target is None or action.destination is None:
                return -1000.0
            distance = unit.position.distance_to(action.destination)
            chance = charge_probability(distance)
            expected = expected_weapon_damage(
                [weapon for weapon in unit.weapons if weapon.is_melee],
                target.save,
                self._ward(target),
                melee=True,
            )
            value = expected * chance * 4.0 * damage_focus
            value += self._target_objective_bonus(state, target, objective_focus)
            if expected * chance >= int(target.wounds or 0):
                value += 2.0 * damage_focus
            retaliation = self._retaliation_damage(state, unit, target, melee=True)
            value -= retaliation * 2.4 * (1.0 - risk_tolerance) * chance
            risk = (1.0 - self._health_ratio(unit)) * (1.0 - risk_tolerance)
            value -= risk * 1.5
            return value

        if action.action_type == "fight":
            target = state.unit_by_id(action.target_id or "")
            if target is None:
                return -1000.0
            return self._attack_value(
                state,
                unit,
                target,
                objective_focus=objective_focus,
                damage_focus=damage_focus,
                risk_tolerance=risk_tolerance,
                ranged=False,
            )

        if action.action_type == "command":
            command = str(action.payload.get("command", ""))
            if command == "rally":
                missing = max(0, unit.max_wounds - int(unit.wounds or 0))
                return 1.0 + missing * 0.35 * objective_focus
            if command == "all_out_attack":
                return 1.4 * damage_focus + 0.3 * mobility
            if command == "all_out_defence":
                return 1.0 * cover_focus + (1.0 - risk_tolerance) * 0.5
        return 0.0

    def _position_value(
        self,
        state: GameState,
        unit: Unit,
        destination: Vec2,
        objective_focus: float,
        damage_focus: float,
        cover_focus: float,
        mobility: float,
        *,
        deployment: bool,
    ) -> float:
        side = unit.side
        approach_gain = self._objective_approach_gain(state, unit.position, destination, side)
        hold_delta = self._objective_hold_value(
            state, destination, side
        ) - self._objective_hold_value(state, unit.position, side)
        enemies = state.alive_units_for(side.other)
        current_enemy = min(
            (unit.position.distance_to(enemy.position) for enemy in enemies),
            default=0.0,
        )
        destination_enemy = min(
            (destination.distance_to(enemy.position) for enemy in enemies),
            default=0.0,
        )
        threat_gain = max(0.0, current_enemy - destination_enemy)
        score = approach_gain * 2.4 * objective_focus * mobility
        score += hold_delta * 3.2 * objective_focus * mobility
        score += threat_gain * 1.1 * damage_focus * mobility
        cover_delta = float(self._position_in_cover(state, destination)) - float(
            self._position_in_cover(state, unit.position)
        )
        score += cover_delta * (0.5 if deployment else 1.2) * cover_focus
        if deployment:
            score -= 0.05
        else:
            score -= 0.1 * unit.position.distance_to(destination)
        return score

    def _objective_priority(self, objective: Objective, side: Side) -> float:
        """How much a side wants an objective, weighted by its value and owner."""

        value = float(objective.value)
        if value <= 0:
            return 0.0
        if objective.controller is None:
            return value
        if objective.controller is side:
            return value * 1.25
        return value * 1.75

    def _objective_hold_value(self, state: GameState, position: Vec2, side: Side) -> float:
        """Value of actually standing on an objective, including abandoning it later."""

        return max(
            (
                self._objective_priority(objective, side)
                for objective in state.objectives
                if objective.contains(position)
            ),
            default=0.0,
        )

    def _objective_approach_gain(
        self,
        state: GameState,
        origin: Vec2,
        destination: Vec2,
        side: Side,
    ) -> float:
        """Distance closed on the most attractive objective, weighted by its value."""

        gain = 0.0
        for objective in state.objectives:
            priority = self._objective_priority(objective, side)
            if priority <= 0:
                continue
            before = max(0.0, origin.distance_to(objective.position) - objective.radius)
            after = max(0.0, destination.distance_to(objective.position) - objective.radius)
            gain = max(gain, priority * max(0.0, before - after))
        return gain

    def _position_in_cover(self, state: GameState, position: Vec2) -> bool:
        return any(feature.cover and feature.contains(position) for feature in state.terrain)

    def _attack_value(
        self,
        state: GameState,
        attacker: Unit,
        target: Unit,
        *,
        objective_focus: float,
        damage_focus: float,
        risk_tolerance: float,
        ranged: bool,
    ) -> float:
        weapons = [
            weapon
            for weapon in attacker.weapons
            if (weapon.range_inches > 0) == ranged
            and (not ranged or self._weapon_in_range(attacker, target, weapon))
        ]
        if not weapons:
            return 0.0
        hit_modifier = 0
        if ranged and self._target_in_cover(state, target):
            hit_modifier -= 1
        expected = expected_weapon_damage(
            weapons,
            target.save,
            self._ward(target),
            hit_modifier=hit_modifier,
            ranged=ranged,
            melee=not ranged,
        )
        value = expected * 4.0 * damage_focus
        if expected >= int(target.wounds or 0):
            value += 2.5 * damage_focus
        value += self._target_objective_bonus(state, target, objective_focus)
        if "Hero" in target.keywords or "hero" in target.keywords:
            value += 0.8 * damage_focus
        retaliation = self._retaliation_damage(state, attacker, target, melee=not ranged)
        value -= retaliation * 2.4 * (1.0 - risk_tolerance)
        return value

    def _retaliation_damage(
        self,
        state: GameState,
        attacker: Unit,
        target: Unit,
        *,
        melee: bool,
    ) -> float:
        """Expected damage the target can return, used as a risk penalty."""

        if melee:
            weapons = [weapon for weapon in target.weapons if weapon.is_melee]
            if not weapons:
                return 0.0
            return expected_weapon_damage(
                weapons,
                attacker.save,
                self._ward(attacker),
                melee=True,
            )
        weapons = [
            weapon
            for weapon in target.weapons
            if not weapon.is_melee and self._weapon_in_range(target, attacker, weapon)
        ]
        if not weapons:
            return 0.0
        hit_modifier = -1 if self._target_in_cover(state, attacker) else 0
        return expected_weapon_damage(
            weapons,
            attacker.save,
            self._ward(attacker),
            hit_modifier=hit_modifier,
            ranged=True,
        )

    def _target_objective_bonus(
        self, state: GameState, target: Unit, objective_focus: float
    ) -> float:
        bonus = 0.0
        for objective in state.objectives:
            if not objective.contains(target.position):
                continue
            if objective.controller is target.side:
                weight = 0.8
            elif objective.controller is None:
                weight = 1.2
            else:
                weight = 1.7
            bonus = max(bonus, float(objective.value) * weight)
        return bonus * objective_focus

    def _health_ratio(self, unit: Unit) -> float:
        maximum = max(1, unit.max_wounds)
        return max(0.0, min(1.0, int(unit.wounds or 0) / maximum))

    def _ward(self, unit: Unit) -> Optional[int]:
        value = unit.stats.get("ward")
        return int(value) if value is not None else None

    def explain_action(self, state: GameState, action: GameAction, side: Side) -> str:
        unit = state.unit_by_id(action.actor_id)
        target = state.unit_by_id(action.target_id or "") if action.target_id else None
        if action.action_type in ("end_phase", "end_deployment"):
            return "No legal action improves the position enough to justify delaying the phase."
        if action.action_type == "deploy":
            if "cover" in action.tags:
                return "Deploy into cover while staying inside the friendly territory."
            return "Deploy closer to the objective while staying inside the friendly territory."
        if action.action_type == "command":
            command = str(action.payload.get("command", ""))
            if command == "rally":
                return "Spend a command point to restore wounds and keep this unit in the fight."
            if command == "all_out_attack":
                return "Spend a command point for a better chance to hit with this unit's attacks."
            return "Spend a command point to improve this unit's save against the coming attacks."
        if action.action_type == "move":
            if "cover" in action.tags:
                return "Advance into cover to survive the next round of attacks."
            if "objective" in action.tags:
                return "Move onto the objective to build control pressure."
            return "Close the distance toward the next objective or threat."
        if action.action_type == "run":
            if "objective" in action.tags:
                return "Run to reach the objective early, accepting that the unit cannot shoot."
            return "Run to close distance quickly, accepting that the unit cannot shoot."
        if action.action_type == "retreat":
            return "Disengage from combat to preserve this unit and regroup."
        if action.action_type == "shoot" and target is not None:
            return (
                f"Shoot {target.name} with {unit.name if unit else action.actor_id}: "
                "it offers the best mix of damage and objective pressure."
            )
        if action.action_type == "charge" and target is not None:
            return f"Charge {target.name}: the expected melee damage justifies the charge risk."
        if action.action_type == "fight" and target is not None:
            return f"Fight {target.name}: this attack has the best expected value on the board."
        return f"Choose {action.action_type} for {action.actor_id}."

    # ------------------------------------------------------------------
    # Presentation helpers

    def describe_state(self, state: GameState) -> str:
        return (
            f"{self.name}: round {state.round}, {state.active_side.value} "
            f"({state.phase}), {state.score_for(Side.PLAYER)}"
            f"-{state.score_for(Side.AI)}"
        )


__all__ = ["Aos4System"]
