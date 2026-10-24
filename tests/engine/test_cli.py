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


def test_aos4_bench_json_is_reproducible(capsys):
    args = ["aos4-bench", "--games", "2", "--rounds", "1", "--json"]
    assert main(args) == 0
    first = json.loads(capsys.readouterr().out)

    assert first["games"] == 2
    assert first["player_wins"] + first["ai_wins"] + first["draws"] == 2
    assert first["errors"] == 0
    assert [result["seed"] for result in first["results"]] == [1, 2]

    assert main(args) == 0
    second = json.loads(capsys.readouterr().out)
    assert first["results"] == second["results"]
