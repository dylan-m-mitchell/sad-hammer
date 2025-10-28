"""Tests for deck_manager.py

Tests the Battle Tactics Deck and Action Deck management systems to ensure
they follow the Peter Holland Solo Wargaming rules correctly.
"""

import pytest
import random
from backend.deck_manager import (
    TacticsDeckManager,
    ActionDeckManager,
    create_turn_action_assignments
)
from backend.reference_card_decks import battle_tactic_deck, objective_action_deck


class TestTacticsDeckManager:
    """Test the Battle Tactics Deck management."""
    
    def test_initial_deck_size_turn_1(self):
        """Turn 1 should have 7 cards (all except Broken Ranks which enters turn 2)."""
        tdm = TacticsDeckManager(rng=random.Random(42), current_turn=1)
        assert tdm.peek_deck_size() == 7
        assert tdm.peek_discard_size() == 0
    
    def test_broken_ranks_enters_turn_2(self):
        """Broken Ranks should be added to discard pile on turn 2."""
        tdm = TacticsDeckManager(rng=random.Random(42), current_turn=1)
        
        # Turn 1: Draw a card
        tactic1 = tdm.draw_tactic()
        assert tactic1 is not None
        assert tdm.peek_deck_size() == 6
        assert tdm.peek_discard_size() == 1
        
        # Advance to turn 2
        tdm.advance_turn(2)
        # Broken Ranks should now be in discard pile
        assert tdm.peek_discard_size() == 2  # The drawn card + Broken Ranks
    
    def test_deck_reshuffles_when_empty(self):
        """When deck is empty, discard pile should be reshuffled into deck."""
        tdm = TacticsDeckManager(rng=random.Random(42), current_turn=1)
        
        # Draw all 7 cards
        for _ in range(7):
            tactic = tdm.draw_tactic()
            assert tactic is not None
        
        assert tdm.peek_deck_size() == 0
        assert tdm.peek_discard_size() == 7
        
        # Next draw should trigger reshuffle
        tactic = tdm.draw_tactic()
        assert tactic is not None
        assert tdm.peek_deck_size() == 6  # Reshuffled 7, drew 1, leaving 6
        assert tdm.peek_discard_size() == 1  # The one just drawn
    
    def test_all_tactics_eventually_available(self):
        """All 8 tactics should be drawable by turn 2."""
        tdm = TacticsDeckManager(rng=random.Random(42), current_turn=1)
        tdm.advance_turn(2)  # Add Broken Ranks
        
        drawn_titles = set()
        # Draw until we've seen all 8
        for _ in range(20):  # More than enough iterations
            tactic = tdm.draw_tactic()
            if tactic:
                drawn_titles.add(tactic['title'])
            if len(drawn_titles) == 8:
                break
        
        assert len(drawn_titles) == 8
        # Verify Broken Ranks is included
        assert "Broken Ranks" in drawn_titles
    
    def test_draw_returns_none_when_no_cards(self):
        """If no cards are in deck or discard, draw should return None."""
        # Start at turn 10 with empty lists
        tdm = TacticsDeckManager(rng=random.Random(42), current_turn=10)
        tdm.deck = []
        tdm.discard_pile = []
        
        result = tdm.draw_tactic()
        assert result is None
    
    def test_reproducible_with_seed(self):
        """Same seed should produce same draw order."""
        tdm1 = TacticsDeckManager(rng=random.Random(123), current_turn=1)
        tdm2 = TacticsDeckManager(rng=random.Random(123), current_turn=1)
        
        for _ in range(5):
            card1 = tdm1.draw_tactic()
            card2 = tdm2.draw_tactic()
            assert card1['title'] == card2['title']


class TestActionDeckManager:
    """Test the Action Deck management for a single turn."""
    
    def test_action_deck_has_12_cards(self):
        """Action deck should have exactly 12 cards (8 tactic + 4 objective)."""
        adm = ActionDeckManager("Broken Ranks", rng=random.Random(42))
        assert adm.peek_deck_size() == 12
    
    def test_action_deck_includes_objective_cards(self):
        """Action deck should include the 4 objective cards."""
        adm = ActionDeckManager("Broken Ranks", rng=random.Random(42))
        
        # Draw all 12 cards
        drawn = []
        for _ in range(12):
            card = adm.draw_card()
            if card:
                drawn.append(card['title'])
        
        # Check that at least one objective card is present
        objective_titles = {card['title'] for card in objective_action_deck}
        drawn_set = set(drawn)
        assert len(objective_titles & drawn_set) == 4  # All 4 objective cards
    
    def test_cards_sorted_by_initiative(self):
        """get_drawn_cards_by_initiative should return cards in descending initiative order."""
        adm = ActionDeckManager("Broken Ranks", rng=random.Random(42))
        
        # Draw 5 cards
        for _ in range(5):
            adm.draw_card()
        
        sorted_cards = adm.get_drawn_cards_by_initiative()
        initiatives = [card.get('initiative', 0) for card in sorted_cards]
        
        # Check that initiatives are in descending order
        assert initiatives == sorted(initiatives, reverse=True)
    
    def test_unknown_tactic_raises_error(self):
        """Creating ActionDeckManager with unknown tactic should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown tactic"):
            ActionDeckManager("NonexistentTactic", rng=random.Random(42))
    
    def test_draw_returns_none_when_empty(self):
        """Drawing from empty deck should return None."""
        adm = ActionDeckManager("Broken Ranks", rng=random.Random(42))
        
        # Draw all 12 cards
        for _ in range(12):
            adm.draw_card()
        
        # 13th draw should return None
        assert adm.draw_card() is None
    
    def test_different_tactics_have_different_cards(self):
        """Different battle tactics should have different action cards."""
        adm1 = ActionDeckManager("Broken Ranks", rng=random.Random(42))
        adm2 = ActionDeckManager("Conquer", rng=random.Random(42))
        
        # Draw first card from each
        card1 = adm1.draw_card()
        card2 = adm2.draw_card()
        
        # They might be the same (objective cards), but the deck compositions differ
        # Check by drawing all cards and comparing sets
        all1 = [card1] + [adm1.draw_card() for _ in range(11)]
        all2 = [card2] + [adm2.draw_card() for _ in range(11)]
        
        titles1 = {c['title'] for c in all1 if c}
        titles2 = {c['title'] for c in all2 if c}
        
        # The tactic-specific cards should be different (though objective cards overlap)
        assert titles1 != titles2


class TestCreateTurnActionAssignments:
    """Test the helper function for creating action assignments."""
    
    def test_assigns_card_to_each_active_unit(self):
        """Each unit that passed aggression should get an action card."""
        # Mock units
        class MockUnit:
            def __init__(self, name):
                self.name = name
        
        units = [MockUnit(f"Unit{i}") for i in range(3)]
        aggression_results = {
            "Unit0": True,
            "Unit1": True,
            "Unit2": False,  # This one failed aggression
        }
        
        tactic = {"title": "Broken Ranks"}
        assignments = create_turn_action_assignments(
            tactic, units, aggression_results, rng=random.Random(42)
        )
        
        # Should have 2 assignments (Unit0 and Unit1)
        assert len(assignments) == 2
        assert assignments[0]['unit'] in ["Unit0", "Unit1"]
        assert assignments[1]['unit'] in ["Unit0", "Unit1"]
    
    def test_assignments_sorted_by_initiative(self):
        """Assignments should be sorted by initiative (highest first)."""
        class MockUnit:
            def __init__(self, name):
                self.name = name
        
        units = [MockUnit(f"Unit{i}") for i in range(5)]
        aggression_results = {f"Unit{i}": True for i in range(5)}
        
        tactic = {"title": "Broken Ranks"}
        assignments = create_turn_action_assignments(
            tactic, units, aggression_results, rng=random.Random(42)
        )
        
        # Check that initiatives are in descending order
        initiatives = [a['initiative'] for a in assignments]
        assert initiatives == sorted(initiatives, reverse=True)
    
    def test_returns_empty_list_if_no_units_act(self):
        """If no units passed aggression, should return empty list."""
        class MockUnit:
            def __init__(self, name):
                self.name = name
        
        units = [MockUnit(f"Unit{i}") for i in range(3)]
        aggression_results = {f"Unit{i}": False for i in range(3)}
        
        tactic = {"title": "Broken Ranks"}
        assignments = create_turn_action_assignments(
            tactic, units, aggression_results, rng=random.Random(42)
        )
        
        assert len(assignments) == 0
    
    def test_includes_all_assignment_fields(self):
        """Each assignment should have all required fields."""
        class MockUnit:
            def __init__(self, name):
                self.name = name
        
        units = [MockUnit("TestUnit")]
        aggression_results = {"TestUnit": True}
        
        tactic = {"title": "Broken Ranks"}
        assignments = create_turn_action_assignments(
            tactic, units, aggression_results, rng=random.Random(42)
        )
        
        assert len(assignments) == 1
        assignment = assignments[0]
        
        # Check all required fields
        assert 'unit' in assignment
        assert 'unit_obj' in assignment
        assert 'card' in assignment
        assert 'initiative' in assignment
        assert 'behavior' in assignment
        assert 'card_title' in assignment


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
