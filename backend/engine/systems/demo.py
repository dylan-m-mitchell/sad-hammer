"""A deliberately small rules system used to prove the engine interfaces.

This is not Age of Sigmar or Warhammer 40,000.  It is a two-phase skirmish
(movement, shooting) with one central objective.  Its purpose is to make every
shared engine contract executable and testable before the real rules modules
are built.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from backend.engine.core.dice import Dice
from backend.engine.core.events import Event, make_event
from backend.engine.core.geometry import (
    Polygon,
    Vec2,
    clamp_point_within_board,
    point_at_range,
)
from backend.engine.core.models import (
    Army,
    Board,
    GameState,
    Objective,
    Side,
    TerrainFeature,
    Unit,
    Weapon,
)
from backend.engine.core.validation import ValidationResult
from backend.engine.systems.base import (
    ActionResult,
    GameAction,
    GameSystem,
    IllegalActionError,
    PhaseDefinition,
)


class DemoSystem(GameSystem):
    """Two-player walking skeleton used by the CLI and engine tests."""

    system_id = "demo"
    name = "Demo Skirmish"
    edition = "engine-0.1"

    @property
    def phases(self) -> Sequence[PhaseDefinition]:
        return (
            PhaseDefinition("movement", "Movement", "Move toward objectives or threats."),
            PhaseDefinition("shooting", "Shooting", "Resolve ranged attacks."),
        )

    def create_game(self, seed: int = 0, **options: Any) -> GameState:
        max_rounds = int(options.get("max_rounds", 5))
        game_id = str(options.get("game_id", f"demo-{seed}"))

        player_army = Army(
            id="player-force",
            name="Player Force",
            side=Side.PLAYER,
            units=[
                Unit(
                    id="player-vanguard",
                    name="Vanguard Squad",
                    side=Side.PLAYER,
                    position=Vec2(9, 15),
                    move=6,
                    save=4,
                    models=5,
                    wounds_per_model=2,
                    base_radius=1.0,
                    points=100,
                    keywords=("infantry",),
                    weapons=[
                        Weapon(
                            id="pulse-carbine",
                            name="Pulse Carbine",
                            range_inches=24,
                            attacks=3,
                            hit_on=4,
                            wound_on=4,
                            damage=2,
                        )
                    ],
                ),
                Unit(
                    id="player-captain",
                    name="Vanguard Captain",
                    side=Side.PLAYER,
                    position=Vec2(9, 23),
                    move=6,
                    save=3,
                    models=1,
                    wounds_per_model=5,
                    base_radius=0.6,
                    points=90,
                    keywords=("infantry", "character"),
                    weapons=[
                        Weapon(
                            id="sidearm",
                            name="Sidearm",
                            range_inches=18,
                            attacks=2,
                            hit_on=3,
                            wound_on=3,
                            damage=2,
                        )
                    ],
                ),
            ],
        )
        ai_army = Army(
            id="ai-force",
            name="AI Force",
            side=Side.AI,
            units=[
                Unit(
                    id="ai-raiders",
                    name="Raider Mob",
                    side=Side.AI,
                    position=Vec2(35, 15),
                    move=6,
                    save=5,
                    models=5,
                    wounds_per_model=1,
                    base_radius=1.0,
                    points=90,
                    keywords=("infantry",),
                    weapons=[
                        Weapon(
                            id="scrap-rifle",
                            name="Scrap Rifle",
                            range_inches=18,
                            attacks=2,
                            hit_on=4,
                            wound_on=4,
                            damage=1,
                        )
                    ],
                ),
                Unit(
                    id="ai-brute",
                    name="Brute",
                    side=Side.AI,
                    position=Vec2(35, 7),
                    move=5,
                    save=4,
                    models=1,
                    wounds_per_model=8,
                    base_radius=0.8,
                    points=110,
                    keywords=("monster",),
                    weapons=[
                        Weapon(
                            id="heavy-blaster",
                            name="Heavy Blaster",
                            range_inches=12,
                            attacks=2,
                            hit_on=4,
                            wound_on=3,
                            damage=3,
                        )
                    ],
                ),
            ],
        )

        objective = Objective(
            id="central-relay",
            name="Central Relay",
            position=Vec2(22, 15),
            radius=4,
            value=2,
        )
        terrain = [
            TerrainFeature(
                id="west-ruin",
                name="West Ruin",
                footprint=Polygon.rectangle(14, 2, 6, 4),
                height=3,
                cover=True,
                tags=("ruin",),
            ),
            TerrainFeature(
                id="east-ruin",
                name="East Ruin",
                footprint=Polygon.rectangle(26, 24, 5, 4),
                height=3,
                cover=True,
                tags=("ruin",),
            ),
            TerrainFeature(
                id="barricade",
                name="Barricade",
                footprint=Polygon.rectangle(24, 4, 2, 3),
                height=2,
                cover=True,
                difficult=True,
                tags=("barricade",),
            ),
            TerrainFeature(
                id="obelisk",
                name="Obelisk",
                footprint=Polygon.rectangle(21, 8, 2, 2),
                height=6,
                blocks_line_of_sight=True,
                tags=("obstacle",),
            ),
        ]

        return GameState(
            schema_version=1,
            game_id=game_id,
            system_id=self.system_id,
            board=Board(width=44, height=30, name="Demo Table"),
            armies=[player_army, ai_army],
            objectives=[objective],
            terrain=terrain,
            deployment_zones={
                Side.PLAYER.value: [Polygon.rectangle(0, 0, 12, 30)],
                Side.AI.value: [Polygon.rectangle(32, 0, 12, 30)],
            },
            round=1,
            max_rounds=max_rounds,
            active_side=Side.PLAYER,
            phase="movement",
            scores={Side.PLAYER.value: 0, Side.AI.value: 0},
            command_points={Side.PLAYER.value: 0, Side.AI.value: 0},
            dice=Dice(seed).state,
            metadata={
                "mission": "central-relay",
                "notes": "Walking skeleton; not a full AoS or 40k ruleset.",
            },
        )

    # ------------------------------------------------------------------
    # Action enumeration

    def legal_actions(self, state: GameState) -> List[GameAction]:
        if state.is_complete:
            return []
        side = state.active_side
        actions: List[GameAction] = []
        if state.phase == "movement":
            for unit in state.alive_units_for(side):
                if unit.flags.get("moved"):
                    continue
                for destination, tags in self._move_candidates(state, unit):
                    actions.append(
                        GameAction(
                            action_type="move",
                            actor_id=unit.id,
                            destination=destination,
                            tags=("move",) + tags,
                        )
                    )
        elif state.phase == "shooting":
            for unit in state.alive_units_for(side):
                if unit.flags.get("shot"):
                    continue
                for enemy in state.alive_units_for(side.other):
                    weapon = self._ranged_weapon(unit)
                    if weapon is None:
                        continue
                    if self._can_shoot(state, unit, enemy, weapon):
                        shoot_tags = ["attack", "ranged"]
                        if any(obj.contains(enemy.position) for obj in state.objectives):
                            shoot_tags.append("objective")
                        actions.append(
                            GameAction(
                                action_type="shoot",
                                actor_id=unit.id,
                                target_id=enemy.id,
                                payload={"weapon_id": weapon.id},
                                tags=tuple(shoot_tags),
                            )
                        )

        actions.append(
            GameAction(
                action_type="end_phase",
                actor_id=side.value,
                tags=("phase",),
            )
        )
        return actions

    def _move_candidates(self, state: GameState, unit: Unit) -> List[Tuple[Vec2, Tuple[str, ...]]]:
        candidates: List[Tuple[Vec2, Tuple[str, ...]]] = []
        for objective in state.objectives:
            destination = self._destination(state, unit, objective.position)
            candidates.append((destination, ("objective",)))
        enemies = state.alive_units_for(unit.side.other)
        if enemies:
            nearest = min(enemies, key=lambda enemy: unit.position.distance_to(enemy.position))
            candidates.append((self._destination(state, unit, nearest.position), ("approach",)))
        for feature in state.terrain:
            if feature.cover:
                candidates.append(
                    (self._destination(state, unit, feature.footprint.center), ("defensive",))
                )

        unique: List[Tuple[Vec2, Tuple[str, ...]]] = []
        seen: Set[Tuple[float, float]] = set()
        for destination, tags in candidates:
            key = (round(destination.x, 4), round(destination.y, 4))
            if key in seen:
                continue
            if destination.distance_to(unit.position) < 0.01:
                continue
            seen.add(key)
            unique.append((destination, tags))
        return unique

    def _destination(self, state: GameState, unit: Unit, target: Vec2) -> Vec2:
        point = clamp_point_within_board(
            point_at_range(unit.position, target, unit.move),
            state.board.width,
            state.board.height,
            margin=unit.base_radius,
        )
        # Clamping to the board can move the point farther away than the unit's
        # Move characteristic if the unit started in a corner.  Re-apply the
        # range limit and the board inset until both hold.
        point = clamp_point_within_board(
            point_at_range(unit.position, point, unit.move),
            state.board.width,
            state.board.height,
            margin=unit.base_radius,
        )
        return point.rounded(4)

    def _ranged_weapon(self, unit: Unit) -> Optional[Weapon]:
        for weapon in unit.weapons:
            if not weapon.is_melee:
                return weapon
        return None

    def _can_shoot(self, state: GameState, attacker: Unit, target: Unit, weapon: Weapon) -> bool:
        if attacker.position.distance_to(target.position) > weapon.range_inches + 1e-9:
            return False
        return self._has_line_of_sight(state, attacker.position, target.position)

    def _has_line_of_sight(self, state: GameState, start: Vec2, end: Vec2) -> bool:
        for feature in state.terrain:
            if feature.blocks_line_of_sight and feature.footprint.intersects_segment(start, end):
                return False
        return True

    def _target_in_cover(self, state: GameState, target: Unit) -> bool:
        return any(feature.cover and feature.contains(target.position) for feature in state.terrain)

    # ------------------------------------------------------------------
    # Validation and application

    def validate_action(self, state: GameState, action: GameAction) -> ValidationResult:
        result = ValidationResult()
        if state.is_complete:
            result.add("game_complete", "the game is complete")
            return result
        if not isinstance(action, GameAction):
            result.add("action_type", "action must be a GameAction")
            return result
        if action.action_type not in ("move", "shoot", "end_phase"):
            result.add("unknown_action", f"unknown action type {action.action_type!r}")
            return result

        side = state.active_side
        if action.action_type == "end_phase":
            if action.actor_id != side.value:
                result.add(
                    "active_side",
                    f"it is {side.value}'s turn, not {action.actor_id!r}'s",
                )
            return result

        unit = state.unit_by_id(action.actor_id)
        if unit is None:
            result.add("unknown_unit", f"no unit with id {action.actor_id!r}")
            return result
        if unit.side is not side:
            result.add("wrong_side", f"unit {unit.id!r} does not belong to the active side")
        if not unit.alive:
            result.add("destroyed_unit", f"unit {unit.id!r} is destroyed")

        if action.action_type == "move":
            self._validate_move(state, action, unit, result)
        elif action.action_type == "shoot":
            self._validate_shoot(state, action, unit, result)
        return result

    def _validate_move(
        self,
        state: GameState,
        action: GameAction,
        unit: Unit,
        result: ValidationResult,
    ) -> None:
        if state.phase != "movement":
            result.add("wrong_phase", "movement is only legal in the movement phase")
        if unit.flags.get("moved"):
            result.add("already_moved", f"unit {unit.id!r} has already moved this turn")
        if action.destination is None:
            result.add("destination", "a move action needs a destination")
            return
        destination = action.destination
        if not state.board.contains(destination, margin=unit.base_radius):
            result.add("off_board", "the destination is outside the board")
        distance = unit.position.distance_to(destination)
        if distance > unit.move + 1e-4:
            result.add(
                "move_range",
                f'{unit.id!r} can move {unit.move}", not {distance:.2f}"',
            )
        for feature in state.terrain:
            if feature.blocks_line_of_sight and feature.contains(destination):
                result.add("terrain_blocked", f"the destination is inside {feature.name}")

    def _validate_shoot(
        self,
        state: GameState,
        action: GameAction,
        unit: Unit,
        result: ValidationResult,
    ) -> None:
        if state.phase != "shooting":
            result.add("wrong_phase", "shooting is only legal in the shooting phase")
        if unit.flags.get("shot"):
            result.add("already_shot", f"unit {unit.id!r} has already shot this turn")
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
        weapon = unit.weapon(str(action.payload.get("weapon_id", ""))) or self._ranged_weapon(unit)
        if weapon is None or weapon.is_melee:
            result.add("no_ranged_weapon", f"unit {unit.id!r} has no ranged weapon")
            return
        if unit.position.distance_to(target.position) > weapon.range_inches + 1e-9:
            result.add("out_of_range", f"target {target.id!r} is out of range")
        if not self._has_line_of_sight(state, unit.position, target.position):
            result.add("no_line_of_sight", f"target {target.id!r} is not visible")

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
        if action.action_type == "move":
            unit = next_state.unit_by_id(action.actor_id)
            if unit is None or action.destination is None:
                raise IllegalActionError("validated move is missing its unit or destination")
            origin = unit.position
            unit.position = action.destination
            unit.flags["moved"] = True
            events.append(
                make_event(
                    "unit_moved",
                    f'{unit.name} moved {origin.distance_to(unit.position):.1f}".',
                    unit=unit.id,
                    from_position=origin.to_dict(),
                    to_position=unit.position.to_dict(),
                )
            )
        elif action.action_type == "shoot":
            attacker = next_state.unit_by_id(action.actor_id)
            target = next_state.unit_by_id(action.target_id or "")
            if attacker is None or target is None:
                raise IllegalActionError("validated shoot is missing its attacker or target")
            weapon = attacker.weapon(
                str(action.payload.get("weapon_id", ""))
            ) or self._ranged_weapon(attacker)
            if weapon is None:
                raise IllegalActionError("validated shoot is missing a ranged weapon")
            events.extend(self._resolve_shooting(next_state, attacker, target, weapon, dice))
            attacker.flags["shot"] = True
        elif action.action_type == "end_phase":
            events.extend(self._end_phase(next_state, dice))

        next_state.dice = dice.state
        return ActionResult(state=next_state, events=events)

    def _resolve_shooting(
        self,
        state: GameState,
        attacker: Unit,
        target: Unit,
        weapon: Weapon,
        dice: Dice,
    ) -> List[Event]:
        hits = 0
        wounds = 0
        saves = 0
        damage = 0
        cover = self._target_in_cover(state, target)
        save_target = target.save - weapon.armor_penetration - (1 if cover else 0)
        save_target = max(2, min(6, save_target))
        attack_log: List[Dict[str, Any]] = []

        for _ in range(weapon.attacks):
            hit_roll = dice.d6()
            hit = hit_roll >= weapon.hit_on
            record: Dict[str, Any] = {"hit_roll": hit_roll, "hit": hit}
            if hit:
                hits += 1
                wound_roll = dice.d6()
                wound = wound_roll >= weapon.wound_on
                record["wound_roll"] = wound_roll
                record["wound"] = wound
                if wound:
                    wounds += 1
                    save_roll = dice.d6()
                    saved = save_roll >= save_target
                    record["save_roll"] = save_roll
                    record["saved"] = saved
                    if not saved:
                        saves += 0
                        damage += target.take_damage(weapon.damage)
                    else:
                        saves += 1
            attack_log.append(record)

        events = [
            make_event(
                "attack_resolved",
                (
                    f"{attacker.name} shot {target.name}: {hits} hit(s), "
                    f"{wounds} wound(s), {damage} damage."
                ),
                attacker=attacker.id,
                target=target.id,
                weapon=weapon.id,
                distance=round(attacker.position.distance_to(target.position), 2),
                cover=cover,
                save_target=save_target,
                attacks=attack_log,
                hits=hits,
                wounds=wounds,
                saves=saves,
                damage=damage,
                target_wounds=target.wounds,
                target_destroyed=not target.alive,
            )
        ]
        if not target.alive:
            events.append(
                make_event(
                    "unit_destroyed",
                    f"{target.name} was destroyed.",
                    unit=target.id,
                    side=target.side.value,
                )
            )
        return events

    def _end_phase(self, state: GameState, dice: Dice) -> List[Event]:
        phases = [phase.id for phase in self.phases]
        current_index = phases.index(state.phase)
        events: List[Event] = [
            make_event(
                "phase_ended",
                f"{state.active_side.value} ended the {state.phase} phase.",
                phase=state.phase,
                side=state.active_side.value,
            )
        ]
        if current_index + 1 < len(phases):
            state.phase = phases[current_index + 1]
            events.append(
                make_event(
                    "phase_started",
                    f"{state.active_side.value} started the {state.phase} phase.",
                    phase=state.phase,
                    side=state.active_side.value,
                )
            )
            return events

        ended_side = state.active_side
        events.append(
            make_event(
                "turn_ended",
                f"{ended_side.value} ended their turn.",
                side=ended_side.value,
            )
        )
        if ended_side is Side.PLAYER:
            state.active_side = Side.AI
            state.phase = phases[0]
            self._reset_flags(state, Side.AI)
            events.append(
                make_event(
                    "turn_started",
                    f"{state.active_side.value} started their turn.",
                    side=state.active_side.value,
                )
            )
            return events

        events.extend(self._score_objectives(state))
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
                        f"Game complete: {state.score_for(Side.PLAYER)} "
                        f"- {state.score_for(Side.AI)} "
                        f"({winner.value if winner else 'draw'})."
                    ),
                    player_score=state.score_for(Side.PLAYER),
                    ai_score=state.score_for(Side.AI),
                    winner=winner.value if winner else None,
                )
            )
            return events

        state.active_side = Side.PLAYER
        state.phase = phases[0]
        self._reset_flags(state, Side.PLAYER)
        events.append(
            make_event(
                "round_started",
                f"Round {state.round} started.",
                round=state.round,
            )
        )
        events.append(
            make_event(
                "turn_started",
                f"{state.active_side.value} started their turn.",
                side=state.active_side.value,
            )
        )
        return events

    def _reset_flags(self, state: GameState, side: Side) -> None:
        for unit in state.units_for(side):
            unit.reset_turn_flags()

    def _score_objectives(self, state: GameState) -> List[Event]:
        events: List[Event] = []
        for objective in state.objectives:
            player_present = any(
                objective.contains(unit.position) for unit in state.alive_units_for(Side.PLAYER)
            )
            ai_present = any(
                objective.contains(unit.position) for unit in state.alive_units_for(Side.AI)
            )
            if player_present and not ai_present:
                controller = Side.PLAYER
            elif ai_present and not player_present:
                controller = Side.AI
            else:
                controller = None
            objective.controller = controller
            if controller is not None:
                state.add_score(controller, objective.value)
                events.append(
                    make_event(
                        "objective_scored",
                        (
                            f"{controller.value} controls {objective.name} "
                            f"for {objective.value} VP."
                        ),
                        objective=objective.id,
                        side=controller.value,
                        value=objective.value,
                    )
                )
            else:
                events.append(
                    make_event(
                        "objective_contested",
                        f"{objective.name} is contested or empty.",
                        objective=objective.id,
                    )
                )
        return events

    def _winner(self, state: GameState) -> Optional[Side]:
        player = state.score_for(Side.PLAYER)
        ai = state.score_for(Side.AI)
        if player == ai:
            return None
        return Side.PLAYER if player > ai else Side.AI

    # ------------------------------------------------------------------
    # AI scoring

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
        cover_focus = float(weights.get("cover_focus", 1.0))
        mobility = float(weights.get("mobility", 1.0))

        if action.action_type == "end_phase":
            return 0.05

        unit = state.unit_by_id(action.actor_id)
        if unit is None:
            return -1000.0

        if action.action_type == "shoot":
            target = state.unit_by_id(action.target_id or "")
            if target is None:
                return -1000.0
            weapon = unit.weapon(str(action.payload.get("weapon_id", "")))
            if weapon is None:
                return 0.0
            hit_chance = max(0.0, min(1.0, (7 - weapon.hit_on) / 6.0))
            wound_chance = max(0.0, min(1.0, (7 - weapon.wound_on) / 6.0))
            cover = self._target_in_cover(state, target)
            save_target = max(
                2, min(6, target.save - weapon.armor_penetration - (1 if cover else 0))
            )
            save_chance = max(0.0, min(1.0, (7 - save_target) / 6.0))
            expected = (
                weapon.attacks * hit_chance * wound_chance * (1.0 - save_chance) * weapon.damage
            )
            score = expected * 5.0 * damage_focus
            if int(target.wounds or 0) <= weapon.damage * weapon.attacks:
                score += 1.5 * damage_focus
            if any(obj.contains(target.position) for obj in state.objectives):
                score += 1.5 * objective_focus
            if "character" in target.keywords:
                score += 1.0 * damage_focus
            return score

        if action.action_type == "move" and action.destination is not None:
            current_objective_distance = min(
                (unit.position.distance_to(obj.position) for obj in state.objectives),
                default=0.0,
            )
            destination_objective_distance = min(
                (action.destination.distance_to(obj.position) for obj in state.objectives),
                default=0.0,
            )
            objective_gain = max(0.0, current_objective_distance - destination_objective_distance)
            enemies = state.alive_units_for(side.other)
            current_enemy_distance = min(
                (unit.position.distance_to(enemy.position) for enemy in enemies),
                default=0.0,
            )
            destination_enemy_distance = min(
                (action.destination.distance_to(enemy.position) for enemy in enemies),
                default=0.0,
            )
            approach_gain = max(0.0, current_enemy_distance - destination_enemy_distance)
            score = objective_gain * 2.0 * objective_focus * mobility
            score += approach_gain * 1.25 * damage_focus * mobility
            if any(obj.contains(action.destination) for obj in state.objectives):
                score += 2.0 * objective_focus
            if any(
                feature.cover and feature.contains(action.destination) for feature in state.terrain
            ):
                score += 1.5 * cover_focus
            return score

        return 0.0

    def explain_action(self, state: GameState, action: GameAction, side: Side) -> str:
        unit = state.unit_by_id(action.actor_id)
        if action.action_type == "shoot":
            target = state.unit_by_id(action.target_id or "")
            if target is not None:
                return (
                    f"Shoot {target.name} with {unit.name if unit else action.actor_id}: "
                    "it offers the best mix of damage and objective pressure."
                )
        if action.action_type == "move" and action.destination is not None:
            if "defensive" in action.tags:
                return "Move into cover so the unit survives to contest the objective."
            if "approach" in action.tags:
                return "Close the distance to bring the enemy under fire."
            return "Advance toward the central objective."
        if action.action_type == "end_phase":
            return "No legal action improves the position enough to justify delaying the phase."
        return f"Choose {action.action_type} for {action.actor_id}."
