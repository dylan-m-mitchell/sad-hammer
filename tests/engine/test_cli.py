import json

from backend.engine.cli import main


def test_aos4_cli_loads_explicit_content_files(tmp_path):
    saved = tmp_path / "state.json"
    assert (
        main(
            [
                "aos4",
                "--seed",
                "7",
                "--rounds",
                "1",
                "--auto-deploy",
                "--quiet",
                "--mission",
                "data/aos4/missions/contested-ground.json",
                "--player-pack",
                "data/aos4/factions/stormcast-starter.json",
                "--ai-pack",
                "data/aos4/factions/skaven-starter.json",
                "--save",
                str(saved),
            ]
        )
        == 0
    )
    state = json.loads(saved.read_text(encoding="utf-8"))
    assert state["status"] == "complete"
    assert state["metadata"]["mission"] == "contested-ground"
