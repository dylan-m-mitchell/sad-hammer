import os
import sys

# Ensure the repository root is on sys.path so local modules can be imported when
# pytest is run from the project directory.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.battlescribe_parser import parse_battlescribe_html

# Uses the provided 'Current Stormcasts.html' in repo root as fixture if present

def test_parse_returns_units():
    path = os.path.join(os.path.dirname(__file__), '..', 'Current Stormcasts.html')
    if not os.path.exists(path):
        # If the fixture is missing, the test is skipped
        import pytest
        pytest.skip('BattleScribe fixture not present')

    units = parse_battlescribe_html(path)
    assert isinstance(units, list)
    assert len(units) > 0

    # Check that each unit dict contains mandatory keys
    for u in units:
        assert 'name' in u
        assert 'models' in u
        assert 'wounds_per_model' in u
        assert 'attacks' in u
        assert 'save' in u
        # weapons is present and normalized
        assert 'weapons' in u
        for w in u['weapons']:
            assert 'attacks' in w
            assert 'to_hit' in w
            assert 'to_wound' in w
            assert 'damage' in w
            # damage is either int or dict type D
            dmg = w['damage']
            assert isinstance(dmg, (int, dict))
            if isinstance(dmg, dict):
                assert dmg.get('type') == 'D'
                assert isinstance(dmg.get('sides'), int)
