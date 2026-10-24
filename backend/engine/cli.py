"""Command-line harness for the engine walking skeleton.

Examples:

    python -m backend.engine.cli demo --seed 7 --rounds 2
    python -m backend.engine.cli demo --seed 7 --json --save /tmp/demo.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from backend.engine.ai.policy import PROFILES, get_profile, run_ai_turn
from backend.engine.core.models import Side
from backend.engine.core.session import GameSession
from backend.engine.systems.demo import DemoSystem
from backend.engine.systems.registry import create_system, list_systems


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sad-hammer-engine",
        description="Run the shared rules engine walking skeleton.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="run an AI-vs-AI demo verification game")
    demo.add_argument("--seed", type=int, default=7)
    demo.add_argument("--rounds", type=int, default=2)
    demo.add_argument("--player-profile", choices=sorted(PROFILES), default="balanced")
    demo.add_argument("--ai-profile", choices=sorted(PROFILES), default="aggressive")
    demo.add_argument("--max-actions", type=int, default=100)
    demo.add_argument("--json", action="store_true", help="print final state as JSON")
    demo.add_argument("--save", type=Path, help="write the final state to a JSON file")
    demo.add_argument("--quiet", action="store_true", help="only print the result")

    aos4 = subparsers.add_parser("aos4", help="run an AI-vs-AI Age of Sigmar 4th verification game")
    aos4.add_argument("--seed", type=int, default=7)
    aos4.add_argument("--rounds", type=int, default=5)
    aos4.add_argument("--mission", default="contested-ground")
    aos4.add_argument("--player-pack", default="stormcast-starter")
    aos4.add_argument("--ai-pack", default="skaven-starter")
    aos4.add_argument("--player-profile", choices=sorted(PROFILES), default="balanced")
    aos4.add_argument("--ai-profile", choices=sorted(PROFILES), default="aggressive")
    aos4.add_argument("--max-actions", type=int, default=300)
    aos4.add_argument(
        "--auto-deploy",
        action="store_true",
        help="skip the deployment step and start at the first battle round",
    )
    aos4.add_argument("--json", action="store_true", help="print final state as JSON")
    aos4.add_argument("--save", type=Path, help="write the final state to a JSON file")
    aos4.add_argument("--quiet", action="store_true", help="only print the result")

    inspect = subparsers.add_parser("inspect", help="load and summarize a saved state")
    inspect.add_argument("path", type=Path)

    subparsers.add_parser("systems", help="list registered rules systems")
    return parser


def _print_events(session: GameSession, events: Sequence[object]) -> None:
    for event in events:
        message = getattr(event, "message", "")
        kind = getattr(event, "kind", "event")
        print(f"  [{kind}] {message}")


def _run_demo(args: argparse.Namespace) -> int:
    system = DemoSystem()
    session = GameSession.new(system, seed=args.seed, max_rounds=args.rounds)
    profiles = {
        Side.PLAYER: get_profile(args.player_profile),
        Side.AI: get_profile(args.ai_profile),
    }

    if not args.quiet:
        print(f"Sad Hammer engine: {system.name} ({system.edition})")
        print(
            f'Seed {args.seed}, {args.rounds} round(s), board {session.state.board.width}x{session.state.board.height}"'
        )
        print(
            f"Player AI profile: {profiles[Side.PLAYER].name}; AI profile: {profiles[Side.AI].name}"
        )
        print()

    safety = 0
    while not session.is_terminal():
        safety += 1
        if safety > args.rounds * 4 + 10:
            raise RuntimeError("demo did not terminate; possible action loop")
        side = session.state.active_side
        profile = profiles[side]
        if not args.quiet:
            print(
                f"Round {session.state.round}/{session.state.max_rounds}, "
                f"{side.value} turn, phase {session.state.phase}"
            )
        decisions = run_ai_turn(
            session,
            profile,
            max_actions=args.max_actions,
            top_alternatives=0 if args.quiet else 2,
        )
        for decision in decisions:
            if not args.quiet:
                print(
                    f"  {side.value} chooses {decision.action.action_type} "
                    f"({decision.action.actor_id}) score={decision.score:.2f}"
                )
                print(f"    why: {decision.reason}")
        if not args.quiet:
            print()

    winner = session.state.metadata.get("winner")
    print(
        f"Final: {session.state.score_for(Side.PLAYER)}-{session.state.score_for(Side.AI)} "
        f"after {session.state.round - 1} round(s); winner={winner or 'draw'}"
    )
    if args.save:
        path = session.save(args.save)
        print(f"Saved state to {path}")
    if args.json:
        print(session.to_json())
    return 0


def _run_aos4(args: argparse.Namespace) -> int:
    system = create_system("aos4")
    session = GameSession.new(
        system,
        seed=args.seed,
        max_rounds=args.rounds,
        mission=args.mission,
        player_pack=args.player_pack,
        ai_pack=args.ai_pack,
        skip_deployment=args.auto_deploy,
    )
    profiles = {
        Side.PLAYER: get_profile(args.player_profile),
        Side.AI: get_profile(args.ai_profile),
    }

    if not args.quiet:
        print(f"Sad Hammer engine: {system.name} ({system.edition})")
        print(
            f"Seed {args.seed}, {args.rounds} round(s), board "
            f'{session.state.board.width}x{session.state.board.height}"'
        )
        print(
            f"Player AI profile: {profiles[Side.PLAYER].name}; "
            f"AI profile: {profiles[Side.AI].name}"
        )
        print()

    safety = 0
    while not session.is_terminal():
        safety += 1
        if safety > args.rounds * 120 + 120:
            raise RuntimeError("AoS game did not terminate; possible action loop")
        side = session.state.active_side
        profile = profiles[side]
        if not args.quiet:
            print(
                f"Round {session.state.round}/{session.state.max_rounds}, "
                f"{side.value} turn, phase {session.state.phase}"
            )
        decisions = run_ai_turn(
            session,
            profile,
            max_actions=args.max_actions,
            top_alternatives=0 if args.quiet else 2,
        )
        for decision in decisions:
            if not args.quiet:
                print(
                    f"  {decision.side.value} chooses {decision.action.action_type} "
                    f"({decision.action.actor_id}) score={decision.score:.2f}"
                )
                print(f"    why: {decision.reason}")
        if not args.quiet:
            print()

    winner = session.state.metadata.get("winner")
    print(
        f"Final: {session.state.score_for(Side.PLAYER)}-{session.state.score_for(Side.AI)} "
        f"after {session.state.round - 1} round(s); winner={winner or 'draw'}"
    )
    if args.save:
        path = session.save(args.save)
        print(f"Saved state to {path}")
    if args.json:
        print(session.to_json())
    return 0


def _run_inspect(args: argparse.Namespace) -> int:
    from backend.engine.core.serialization import load_state

    state = load_state(args.path)
    system = create_system(state.system_id)
    session = GameSession(system, state)
    session.ensure_valid()
    print(json.dumps(session.summary(), indent=2, sort_keys=True))
    return 0


def _run_systems() -> int:
    print(json.dumps(list_systems(), indent=2, sort_keys=True))
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "demo":
        return _run_demo(args)
    if args.command == "aos4":
        return _run_aos4(args)
    if args.command == "inspect":
        return _run_inspect(args)
    if args.command == "systems":
        return _run_systems()
    parser.error(f"unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
