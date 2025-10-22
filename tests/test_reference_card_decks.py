import importlib.util
import pathlib


def _load_reference_module():
    """Load reference_card_decks.py by file path and return the module."""
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    module_path = repo_root / 'reference_card_decks.py'
    spec = importlib.util.spec_from_file_location('reference_card_decks', str(module_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reference_module_imports():
    module = _load_reference_module()
    assert module is not None


def test_deck_sizes_and_mappings():
    r = _load_reference_module()

    # Battleplan deck should have 12 cards
    assert hasattr(r, 'battleplan_deck')
    assert len(r.battleplan_deck) == 12

    # Tactic deck should have 8 tactics
    assert hasattr(r, 'battle_tactic_deck')
    assert len(r.battle_tactic_deck) == 8

    # Broken Ranks action deck must exist and be length 8
    # Every tactic listed should have an action deck of length 8
    for t in r.battle_tactic_deck:
        title = t['title']
        assert title in r.tactic_to_actions, f"Missing actions for tactic: {title}"
        assert len(r.tactic_to_actions[title]) == 8, f"Tactic {title} must have 8 actions"

    # objective_action_deck should be non-empty
    assert hasattr(r, 'objective_action_deck')
    assert len(r.objective_action_deck) >= 1
