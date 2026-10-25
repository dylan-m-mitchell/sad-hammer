"""The stateless table planner.

The planner receives both rosters, the round, a seed and the AI units that have
been destroyed.  It returns a round of instructions written in relative table
language ("closest enemy", "within 12 inches", "if you can end in cover").  It
never sees or invents positions, distances, terrain or wounds; the player
measures, moves and rolls on the physical table.

Maneuvers are type-based and seeded.  Each unit's option is chosen by a stable
hash of the seed and unit ID, then advanced by one step per round, so the same
round and seed always replay the same plan while each round rotates.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from backend.table.rosters import Roster, TableUnit, TableWeapon

PRESS = "press"
SUPPORT = "support"
HOLD = "hold"

DOCTRINE_LABELS = {
    PRESS: "Press",
    SUPPORT: "Support",
    HOLD: "Hold",
}

PHASES: Tuple[Tuple[str, str], ...] = (
    ("hero", "Hero phase"),
    ("movement", "Movement phase"),
    ("shooting", "Shooting phase"),
    ("charge", "Charge phase"),
    ("combat", "Combat phase"),
    ("end", "End phase"),
)

_HOLD_KEYWORDS = {"hero", "hold", "defensive"}


@dataclass(frozen=True)
class Maneuver:
    id: str
    name: str
    instruction: str
    reason: str


@dataclass(frozen=True)
class Instruction:
    phase: str
    maneuver: str
    maneuver_name: str
    instruction: str
    reason: str
    unit_id: Optional[str] = None
    unit_name: Optional[str] = None
    doctrine: Optional[str] = None
    weapons: Tuple[TableWeapon, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "unit_id": self.unit_id,
            "unit_name": self.unit_name,
            "doctrine": self.doctrine,
            "maneuver": self.maneuver,
            "maneuver_name": self.maneuver_name,
            "instruction": self.instruction,
            "reason": self.reason,
            "weapons": [weapon.to_dict() for weapon in self.weapons],
        }


# --- doctrine ---------------------------------------------------------------
def classify_doctrine(unit: TableUnit) -> str:
    """Classify a unit as press, support or hold from its profile.

    Heroes and explicit defensive units are Hold so they stay near the line.
    A non-hero with any ranged weapon is Support.  Everything else presses.
    """

    keywords = {keyword.strip().lower() for keyword in unit.keywords}
    if keywords & _HOLD_KEYWORDS:
        return HOLD
    if unit.has_ranged_weapon:
        return SUPPORT
    return PRESS


def doctrine_reason(unit: TableUnit, doctrine: str) -> str:
    if doctrine == HOLD:
        if unit.is_hero:
            return "Hero — supports the line and holds ground."
        return "Defensive keyword — holds ground instead of charging out."
    if doctrine == SUPPORT:
        return "Ranged weapons — fights from range, not from a charge."
    return "Melee weapons only — closes the distance and fights."


# --- maneuver tables --------------------------------------------------------
PRESS_MOVEMENT = (
    Maneuver(
        "advance",
        "Full advance",
        "Advance directly toward the closest enemy unit, using the full move if you need it.",
        "Melee unit — close the distance quickly.",
    ),
    Maneuver(
        "cover",
        "Advance into cover",
        "Advance toward the closest enemy unit and end the move in cover if any is available.",
        "Melee unit — arrive protected.",
    ),
    Maneuver(
        "objective",
        "Push an objective",
        "Move onto the closest objective and pressure it.",
        "Melee unit — threaten the mission while advancing.",
    ),
)

SUPPORT_HOLD = Maneuver(
    "hold_in_cover",
    "Hold in cover",
    "Stay in cover where you are and prepare to shoot.",
    "Ranged unit — cover keeps the firing line alive.",
)
SUPPORT_REPOSITION = Maneuver(
    "reposition",
    "Reposition",
    "Move to a firing position with line of sight to the closest enemy unit.",
    "Ranged unit — shooting needs line of sight.",
)
SUPPORT_FALL_BACK = Maneuver(
    "fall_back",
    "Fall back",
    "Fall back away from the nearest enemy, staying in range to shoot.",
    "Ranged unit — make space and keep firing.",
)
SUPPORT_FOCUS = Maneuver(
    "focus_hero",
    "Line up the Hero",
    "Reposition to draw a line of sight to the closest enemy Hero.",
    "Ranged unit — enemy Heroes are the priority target.",
)

HOLD_MOVEMENT = (
    Maneuver(
        "support_friendly",
        "Support the line",
        "Stay within 12 inches of the nearest friendly unit and move with it.",
        "Hero — the army is stronger near its support piece.",
    ),
    Maneuver(
        "hold_objective",
        "Hold an objective",
        "Move onto the closest objective and stay there.",
        "Hero — a held objective wins rounds.",
    ),
    Maneuver(
        "cover_objective",
        "Cover the objective",
        "Move into cover within 3 inches of an objective.",
        "Defensive unit — survive while scoring.",
    ),
)

HERO_SUPPORT = Maneuver(
    "support_ability",
    "Lead from the line",
    "Use this unit's warscroll or command ability to support the nearest friendly unit within 12 inches.",
    "Hero phase — buffs and commands come before movement.",
)

PRESS_CHARGE = Maneuver(
    "charge",
    "Charge if in range",
    "If the closest enemy unit is within 12 inches, declare a charge against it. Otherwise make no charge.",
    "Melee unit — a charge is free extra movement.",
)
SUPPORT_CHARGE = Maneuver(
    "no_charge",
    "Hold fire",
    "Do not charge unless you have no shooting target and an enemy unit is already within 6 inches; only then charge that unit.",
    "Ranged unit — charging gives up the shooting phase.",
)
HOLD_CHARGE = Maneuver(
    "hold_charge",
    "Hold position",
    "Do not charge. Stay on your objective or next to the unit you are supporting.",
    "Hero — the job is support, not a charge.",
)

PRESS_COMBAT = Maneuver(
    "fight",
    "Fight",
    "Fight the closest enemy unit you are in combat with, using all of your melee weapons.",
    "Melee unit — combat is where it wins.",
)
SUPPORT_COMBAT = Maneuver(
    "fight_if_engaged",
    "Fight only if engaged",
    "If an enemy unit is in combat with you, fight it with your melee weapons; otherwise do nothing in this phase.",
    "Ranged unit — keep shooting instead of seeking combat.",
)
SUPPORT_COMBAT_UNARMED = Maneuver(
    "stay_alive",
    "Stay alive",
    "If an enemy unit is in combat with you, stay alive; this unit has no melee weapons to fight with.",
    "Ranged unit — it should never have been charged.",
)
HOLD_COMBAT = Maneuver(
    "fight_if_engaged",
    "Fight only if engaged",
    "If an enemy unit is in combat with you, fight it with your melee weapons; otherwise keep holding your position.",
    "Hero — hold the line rather than chase.",
)
HOLD_COMBAT_UNARMED = Maneuver(
    "stay_alive",
    "Stay alive",
    "If an enemy unit is in combat with you, stay alive; this unit has no melee weapons to fight with.",
    "Defensive unit — it should never have been charged.",
)

END_INSTRUCTIONS = (
    Instruction(
        phase="end",
        maneuver="score",
        maneuver_name="Score objectives",
        instruction=(
            "Score the objectives you control. A unit controls an objective if it has "
            "more models within 3 inches of it than any enemy unit."
        ),
        reason="End phase — objectives decide the battle.",
    ),
    Instruction(
        phase="end",
        maneuver="cleanup",
        maneuver_name="Clear the table",
        instruction=(
            "Remove destroyed units, mark any AI units you destroyed this round, "
            "then advance the round counter."
        ),
        reason="End phase — the physical table stays in your hands.",
    ),
)


def _stable_offset(seed: int, unit_id: str, phase: str) -> int:
    digest = hashlib.sha256(f"{seed}:{unit_id}:{phase}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def choose_maneuver(
    options: Sequence[Maneuver],
    *,
    seed: int,
    unit_id: str,
    phase: str,
    round_number: int,
) -> Maneuver:
    """Pick a maneuver deterministically and rotate it each round."""

    if not options:
        raise ValueError("a maneuver list cannot be empty")
    offset = _stable_offset(seed, unit_id, phase) % len(options)
    index = (offset + round_number - 1) % len(options)
    return options[index]


def _shooting_for(movement: Maneuver) -> Maneuver:
    if movement.id == "hold_in_cover":
        return Maneuver(
            "shoot_from_cover",
            "Shoot from cover",
            "Shoot the closest enemy unit you can see from cover, using all of your ranged weapons.",
            "Ranged unit — cover and shooting together.",
        )
    if movement.id == "fall_back":
        return Maneuver(
            "shoot_after_falling_back",
            "Shoot after falling back",
            "Shoot the closest enemy unit you can see after falling back, using all of your ranged weapons.",
            "Ranged unit — falling back does not end the shooting.",
        )
    if movement.id == "focus_hero":
        return Maneuver(
            "focus_hero",
            "Focus the Hero",
            "Focus your shooting on the closest enemy Hero, using all of your ranged weapons.",
            "Ranged unit — remove the enemy's support piece.",
        )
    return Maneuver(
        "shoot",
        "Shoot",
        "Shoot the closest enemy unit you can see, using all of your ranged weapons.",
        "Ranged unit — keep the pressure at range.",
    )


def _ranged_weapons(unit: TableUnit) -> Tuple[TableWeapon, ...]:
    return tuple(weapon for weapon in unit.weapons if weapon.is_ranged)


def _melee_weapons(unit: TableUnit) -> Tuple[TableWeapon, ...]:
    return tuple(weapon for weapon in unit.weapons if not weapon.is_ranged)


def _hero_names(roster: Roster) -> Tuple[str, ...]:
    return tuple(unit.name for unit in roster.units if unit.is_hero)


def _with_hero_reason(maneuver: Maneuver, hero_names: Sequence[str]) -> Maneuver:
    if not hero_names:
        return maneuver
    names = ", ".join(hero_names[:3])
    if len(hero_names) > 3:
        names = f"{names} and others"
    return Maneuver(
        id=maneuver.id,
        name=maneuver.name,
        instruction=maneuver.instruction,
        reason=f"{maneuver.reason} Enemy Heroes: {names}.",
    )


def support_movement_options(hero_names: Sequence[str]) -> Tuple[Maneuver, ...]:
    options = [SUPPORT_HOLD, SUPPORT_REPOSITION, SUPPORT_FALL_BACK]
    if hero_names:
        options.append(SUPPORT_FOCUS)
    return tuple(options)


def _unit_instruction(
    unit: TableUnit,
    doctrine: str,
    phase: str,
    maneuver: Maneuver,
    *,
    weapons: Tuple[TableWeapon, ...] = (),
) -> Instruction:
    return Instruction(
        phase=phase,
        unit_id=unit.id,
        unit_name=unit.name,
        doctrine=doctrine,
        maneuver=maneuver.id,
        maneuver_name=maneuver.name,
        instruction=maneuver.instruction,
        reason=maneuver.reason,
        weapons=weapons,
    )


def _destroyed_keys(destroyed: Iterable[str]) -> set:
    return {str(value).strip().lower() for value in destroyed if str(value).strip()}


def _is_destroyed(unit: TableUnit, destroyed: set) -> bool:
    return unit.id.lower() in destroyed or unit.name.lower() in destroyed


def build_plan(
    player_roster: Roster,
    ai_roster: Roster,
    *,
    round_number: int,
    seed: int,
    destroyed: Iterable[str] = (),
) -> Dict[str, Any]:
    """Build one deterministic round plan for the AI roster."""

    destroyed_set = _destroyed_keys(destroyed)
    active_units = [unit for unit in ai_roster.units if not _is_destroyed(unit, destroyed_set)]
    hero_names = _hero_names(player_roster)

    hero_phase: List[Instruction] = []
    movement_phase: List[Instruction] = []
    shooting_phase: List[Instruction] = []
    charge_phase: List[Instruction] = []
    combat_phase: List[Instruction] = []
    units_payload: List[Dict[str, Any]] = []

    for unit in active_units:
        doctrine = classify_doctrine(unit)
        units_payload.append(
            {
                "id": unit.id,
                "name": unit.name,
                "doctrine": doctrine,
                "doctrine_label": DOCTRINE_LABELS[doctrine],
                "doctrine_reason": doctrine_reason(unit, doctrine),
            }
        )

        if doctrine == HOLD:
            if unit.is_hero:
                hero_phase.append(_unit_instruction(unit, doctrine, "hero", HERO_SUPPORT))
            movement = choose_maneuver(
                HOLD_MOVEMENT,
                seed=seed,
                unit_id=unit.id,
                phase="movement",
                round_number=round_number,
            )
            charge = HOLD_CHARGE
            melee = _melee_weapons(unit)
            combat = HOLD_COMBAT if melee else HOLD_COMBAT_UNARMED
            shooting: Optional[Maneuver] = None
        elif doctrine == SUPPORT:
            options = support_movement_options(hero_names)
            movement = choose_maneuver(
                options,
                seed=seed,
                unit_id=unit.id,
                phase="movement",
                round_number=round_number,
            )
            charge = SUPPORT_CHARGE
            melee = _melee_weapons(unit)
            combat = SUPPORT_COMBAT if melee else SUPPORT_COMBAT_UNARMED
            shooting = _shooting_for(movement)
            if shooting.id == "focus_hero":
                shooting = _with_hero_reason(shooting, hero_names)
        else:
            movement = choose_maneuver(
                PRESS_MOVEMENT,
                seed=seed,
                unit_id=unit.id,
                phase="movement",
                round_number=round_number,
            )
            charge = PRESS_CHARGE
            melee = _melee_weapons(unit)
            combat = PRESS_COMBAT
            shooting = None

        movement_phase.append(_unit_instruction(unit, doctrine, "movement", movement))
        if shooting is not None:
            shooting_phase.append(
                _unit_instruction(
                    unit,
                    doctrine,
                    "shooting",
                    shooting,
                    weapons=_ranged_weapons(unit),
                )
            )
        charge_phase.append(_unit_instruction(unit, doctrine, "charge", charge))
        combat_phase.append(_unit_instruction(unit, doctrine, "combat", combat, weapons=melee))

    phase_instructions = {
        "hero": hero_phase,
        "movement": movement_phase,
        "shooting": shooting_phase,
        "charge": charge_phase,
        "combat": combat_phase,
        "end": list(END_INSTRUCTIONS),
    }
    phases = [
        {
            "id": phase_id,
            "name": phase_name,
            "instructions": [instruction.to_dict() for instruction in phase_instructions[phase_id]],
        }
        for phase_id, phase_name in PHASES
    ]

    return {
        "round": round_number,
        "seed": seed,
        "player_roster": {
            "name": player_roster.name,
            "faction": player_roster.faction,
            "unit_count": len(player_roster.units),
        },
        "ai_roster": {
            "name": ai_roster.name,
            "faction": ai_roster.faction,
            "unit_count": len(ai_roster.units),
            "active_count": len(active_units),
            "destroyed": [
                unit.id for unit in ai_roster.units if _is_destroyed(unit, destroyed_set)
            ],
        },
        "units": units_payload,
        "phases": phases,
    }


__all__ = [
    "DOCTRINE_LABELS",
    "HOLD",
    "PHASES",
    "PRESS",
    "SUPPORT",
    "Instruction",
    "Maneuver",
    "build_plan",
    "choose_maneuver",
    "classify_doctrine",
    "doctrine_reason",
    "support_movement_options",
]
