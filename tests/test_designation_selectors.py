import pytest

from backend import deck_manager


class SimpleUnit:
    def __init__(self, name, keywords=None):
        self.name = name
        self.keywords = keywords or []


class FakeActionDeckManager:
    """A deterministic fake action deck used to keep draw order stable in tests.

    Each draw returns a card with the same initiative so the post-assignment
    sort by initiative does not change the draw order. This lets tests assert
    the order in which units were given cards.
    """

    def __init__(self, tactic_title, rng=None):
        self.tactic_title = tactic_title
        self.rng = rng
        self._next = 0

    def draw_card(self):
        if self._next >= 100:
            return None
        c = {"title": f"Card {self._next}", "initiative": 0, "behavior": f"Behavior {self._next}"}
        self._next += 1
        return c


@pytest.fixture(autouse=True)
def stub_action_deck(monkeypatch):
    """Replace the real ActionDeckManager with our fake for all tests in this module."""
    monkeypatch.setattr(deck_manager, "ActionDeckManager", FakeActionDeckManager)
    yield


def test_monster_selector_prioritizes_monsters():
    units = [SimpleUnit("A", ["Monster"]), SimpleUnit("B", ["Hero"]), SimpleUnit("C", [])]
    aggression = {u.name: True for u in units}
    tactic = {"title": "Any", "designated_units": "monster"}

    assignments = deck_manager.create_turn_action_assignments(tactic, units, aggression, rng=None)
    assigned_order = [a["unit"] for a in assignments]

    # Monster A should be given a card before non-monsters
    assert assigned_order[0] == "A"
    assert set(assigned_order) == {"A", "B", "C"}


def test_numeric_selector_takes_first_n_units():
    units = [SimpleUnit("U1"), SimpleUnit("U2"), SimpleUnit("U3"), SimpleUnit("U4")]
    aggression = {u.name: True for u in units}
    tactic = {"title": "Any", "designated_units": "2"}

    assignments = deck_manager.create_turn_action_assignments(tactic, units, aggression, rng=None)
    assigned_order = [a["unit"] for a in assignments]

    # First two roster units should be prioritized
    assert assigned_order[0] == "U1"
    assert assigned_order[1] == "U2"
    assert set(assigned_order) == {"U1", "U2", "U3", "U4"}


def test_all_selector_gives_all_units_cards():
    """All units should receive cards regardless of aggression_results."""
    units = [SimpleUnit("One"), SimpleUnit("Two"), SimpleUnit("Three")]
    # aggression_results is ignored in new system - all units act
    aggression = {"One": False, "Two": True, "Three": True}
    tactic = {"title": "Any", "designated_units": "all"}

    assignments = deck_manager.create_turn_action_assignments(tactic, units, aggression, rng=None)
    assigned_order = [a["unit"] for a in assignments]

    # All units should get cards in roster order
    assert assigned_order == ["One", "Two", "Three"]


def test_hero_selector_with_no_match_falls_back_to_aggressive_order():
    units = [SimpleUnit("Alpha"), SimpleUnit("Beta")]
    aggression = {"Alpha": True, "Beta": True}
    tactic = {"title": "Any", "designated_units": "hero"}

    assignments = deck_manager.create_turn_action_assignments(tactic, units, aggression, rng=None)
    assigned_order = [a["unit"] for a in assignments]

    # No heroes present: assignments should be in roster aggressive order
    assert assigned_order == ["Alpha", "Beta"]
