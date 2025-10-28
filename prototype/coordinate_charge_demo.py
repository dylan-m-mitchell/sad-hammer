"""Prototype: minimal 2D coordinate system + charge roll demo

This standalone prototype demonstrates:
- attaching simple (x,y) coordinates to units
- computing Euclidean distances between units and objectives
- a simple charge roll mechanic: unit must be within (charge_distance + d6) to succeed

This file intentionally does not change any existing project logic; it merely
reads few things nominally and runs a self-contained demo.
"""

import math
import random
from dataclasses import dataclass
from typing import List, Tuple

random.seed(42)

@dataclass
class Position:
    x: float
    y: float

    def distance_to(self, other: 'Position') -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


@dataclass
class Unit:
    name: str
    pos: Position
    charge_range: float = 2.0  # base charge distance in inches


@dataclass
class Objective:
    name: str
    pos: Position


def roll_d6(rng: random.Random) -> int:
    return rng.randint(1, 6)


def can_charge(attacker: Unit, defender_pos: Position, rng: random.Random) -> Tuple[bool, int, float, float]:
    """Return (success, roll, distance, required)

    Charge success if distance <= (attacker.charge_range + roll)
    """
    dist = attacker.pos.distance_to(defender_pos)
    roll = roll_d6(rng)
    required = attacker.charge_range + roll
    success = dist <= required
    return success, roll, dist, required


def demo_turn():
    rng = random.Random(12345)

    # Create sample units with coordinates (in inches)
    ai_units = [
        Unit('Mournfang Pack A', Position(2.0, 5.0), charge_range=6.0),
        Unit('Huskard on Stonehorn', Position(10.0, 2.0), charge_range=8.0),
        Unit('Icebrow Hunter', Position(7.5, 9.0), charge_range=5.0),
    ]

    player_units = [
        Unit('Player Guard A', Position(8.0, 6.0), charge_range=4.0),
        Unit('Player Hero', Position(3.0, 7.0), charge_range=5.0),
    ]

    objectives = [
        Objective('Center Objective', Position(6.0, 6.0)),
        Objective('Left Objective', Position(1.0, 9.0)),
    ]

    print('--- Starting demo turn (positions in inches) ---')
    print('\nAI units:')
    for u in ai_units:
        print(f"  {u.name} @ ({u.pos.x:.1f}, {u.pos.y:.1f}) charge_range={u.charge_range}")

    print('\nPlayer units:')
    for p in player_units:
        print(f"  {p.name} @ ({p.pos.x:.1f}, {p.pos.y:.1f}) charge_range={p.charge_range}")

    print('\nObjectives:')
    for o in objectives:
        print(f"  {o.name} @ ({o.pos.x:.1f}, {o.pos.y:.1f})")

    # Pick an AI unit that will attempt a charge based on being nearest to a player unit
    attacker = ai_units[0]
    # Find nearest player unit
    nearest_player = min(player_units, key=lambda p: attacker.pos.distance_to(p.pos))

    print('\n--- Charge attempt ---')
    print(f"Attacker: {attacker.name} @ {attacker.pos.x:.1f},{attacker.pos.y:.1f}")
    print(f"Nearest defender: {nearest_player.name} @ {nearest_player.pos.x:.1f},{nearest_player.pos.y:.1f}")

    success, roll, dist, required = can_charge(attacker, nearest_player.pos, rng)
    print(f"Distance to target: {dist:.2f}in")
    print(f"Charge roll (d6): {roll}")
    print(f"Required distance (charge_range + roll): {required:.2f}in")
    print('Charge success!' if success else 'Charge failed.')

    # Now demo an attempt to move-to-objective (simple straight-line move) and then charge
    mover = ai_units[1]
    target_obj = objectives[0]
    print('\n--- Move toward objective then attempt charge on nearest player ---')
    print(f"Mover: {mover.name} @ ({mover.pos.x:.1f},{mover.pos.y:.1f}), target objective: {target_obj.name} @ ({target_obj.pos.x:.1f},{target_obj.pos.y:.1f})")

    # simple move: move up to 6" straight towards objective
    move_dist = 6.0
    vector_x = target_obj.pos.x - mover.pos.x
    vector_y = target_obj.pos.y - mover.pos.y
    vector_len = math.hypot(vector_x, vector_y)
    if vector_len > 0:
        ux = vector_x / vector_len
        uy = vector_y / vector_len
        # new position
        new_x = mover.pos.x + ux * min(move_dist, vector_len)
        new_y = mover.pos.y + uy * min(move_dist, vector_len)
    else:
        new_x, new_y = mover.pos.x, mover.pos.y

    print(f"Moved from ({mover.pos.x:.1f},{mover.pos.y:.1f}) to ({new_x:.1f},{new_y:.1f})")
    mover.pos = Position(new_x, new_y)

    # attempt charge on nearest player after move
    nearest_player_after = min(player_units, key=lambda p: mover.pos.distance_to(p.pos))
    success2, roll2, dist2, required2 = can_charge(mover, nearest_player_after.pos, rng)
    print(f"Distance to target after move: {dist2:.2f}in")
    print(f"Charge roll (d6): {roll2}")
    print(f"Required distance (charge_range + roll): {required2:.2f}in")
    print('Charge success!' if success2 else 'Charge failed.')


if __name__ == '__main__':
    demo_turn()
