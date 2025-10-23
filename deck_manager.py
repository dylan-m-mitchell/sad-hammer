"""Deck Manager for Solo Wargaming Battle Tactics and Action Decks

This module implements the card deck mechanics from Peter Holland's Solo Wargaming
system as described in the Woehammer blog posts:

1. Battle Tactics Deck (8 cards):
   - Shuffled at game start (only cards with enters_deck_on_turn=0)
   - One card drawn at the start of each AI turn
   - When drawn, card is discarded
   - Cards can be added to discard pile on specific turns (e.g., "Broken Ranks" after turn 1)
   - When deck is empty, reshuffle all discarded cards back into the deck

2. Action Deck (12 cards per turn):
   - Consists of 8 cards specific to the chosen Battle Tactic
   - Plus 4 Objective Action cards
   - Shuffled together each turn
   - One card drawn for each unit that passes its aggression check
   - Units act in initiative order (highest initiative first, shown in shield icon)

This replaces the ad-hoc deck handling in full_simulator.py and provides a
clean, testable interface for the card game mechanics.
"""

import random
from copy import deepcopy
from typing import List, Dict, Any, Optional, Tuple
from reference_card_decks import (
    battle_tactic_deck,
    tactic_to_actions,
    objective_action_deck
)


class TacticsDeckManager:
    """Manages the Battle Tactics deck for a game session.
    
    The Tactics Deck starts with 8 cards (those with enters_deck_on_turn=0),
    shuffled at initialization. Each turn, one card is drawn and discarded.
    Additional cards can be added to the discard pile based on their
    enters_deck_on_turn value. When the deck is empty, all discarded cards
    are reshuffled back into the deck.
    """
    
    def __init__(self, rng: Optional[random.Random] = None, current_turn: int = 1):
        """Initialize the tactics deck manager.
        
        Args:
            rng: Random number generator (for reproducible testing). If None, uses default.
            current_turn: The current game turn (default 1). Used to determine which
                         cards should already be in play.
        """
        self.rng = rng or random.Random()
        self.current_turn = current_turn
        
        # Build initial deck and discard pile based on current turn
        self.deck: List[Dict[str, Any]] = []
        self.discard_pile: List[Dict[str, Any]] = []
        
        # Add all cards to appropriate pile based on enters_deck_on_turn
        for tactic in battle_tactic_deck:
            enters_on = tactic.get('enters_deck_on_turn', 0)
            if enters_on < current_turn:
                # Card should already be in play (in deck or discard)
                # For simplicity, add to discard pile
                self.discard_pile.append(deepcopy(tactic))
            elif enters_on == current_turn:
                # Card enters this turn, add to discard pile (will be shuffled in if needed)
                self.discard_pile.append(deepcopy(tactic))
            # Cards with enters_on > current_turn are not yet in play
        
        # If this is turn 1, put all starting cards (enters_deck_on_turn=0) in deck
        if current_turn == 1:
            self.deck = [deepcopy(t) for t in battle_tactic_deck if t.get('enters_deck_on_turn', 0) == 0]
            self.discard_pile = []
            self.rng.shuffle(self.deck)
        else:
            # For later turns, reshuffle discard pile into deck
            self._reshuffle_if_needed()
    
    def _reshuffle_if_needed(self):
        """If deck is empty, reshuffle discard pile back into deck."""
        if not self.deck and self.discard_pile:
            self.deck = self.discard_pile[:]
            self.discard_pile = []
            self.rng.shuffle(self.deck)
    
    def advance_turn(self, new_turn: int):
        """Advance to a new turn, adding any cards that enter on this turn.
        
        Args:
            new_turn: The new turn number.
        """
        self.current_turn = new_turn
        
        # Check if any tactics should be added to the discard pile this turn
        for tactic in battle_tactic_deck:
            enters_on = tactic.get('enters_deck_on_turn', 0)
            if enters_on == new_turn:
                # Add this tactic to discard pile
                # Check if it's not already there
                already_in_play = any(
                    t['title'] == tactic['title'] 
                    for t in (self.deck + self.discard_pile)
                )
                if not already_in_play:
                    self.discard_pile.append(deepcopy(tactic))
    
    def draw_tactic(self) -> Optional[Dict[str, Any]]:
        """Draw one battle tactic card from the deck.
        
        Returns:
            The drawn tactic card dict, or None if no cards available.
        """
        self._reshuffle_if_needed()
        
        if not self.deck:
            return None
        
        card = self.deck.pop(0)
        self.discard_pile.append(card)
        return card
    
    def peek_deck_size(self) -> int:
        """Return the current size of the tactics deck (for debugging/testing)."""
        return len(self.deck)
    
    def peek_discard_size(self) -> int:
        """Return the current size of the discard pile (for debugging/testing)."""
        return len(self.discard_pile)


class ActionDeckManager:
    """Manages the Action Deck for a single turn.
    
    Each turn, an Action Deck is created by:
    1. Taking the 8 action cards for the chosen Battle Tactic
    2. Adding the 4 Objective Action cards
    3. Shuffling all 12 cards together
    4. Drawing one card for each unit that passes aggression check
    5. Sorting units by initiative (highest first)
    """
    
    def __init__(self, tactic_title: str, rng: Optional[random.Random] = None):
        """Initialize the action deck for this turn.
        
        Args:
            tactic_title: The title of the battle tactic (used to look up action cards).
            rng: Random number generator (for reproducible testing). If None, uses default.
        
        Raises:
            ValueError: If tactic_title is not found in tactic_to_actions mapping.
        """
        self.rng = rng or random.Random()
        self.tactic_title = tactic_title
        
        # Get the 8 tactic-specific action cards
        tactic_actions = tactic_to_actions.get(tactic_title)
        if tactic_actions is None:
            raise ValueError(f"Unknown tactic: {tactic_title}")
        
        # Build the 12-card action deck (8 tactic + 4 objective)
        self.deck: List[Dict[str, Any]] = []
        self.deck.extend(deepcopy(tactic_actions))
        self.deck.extend(deepcopy(objective_action_deck))
        
        # Shuffle the deck
        self.rng.shuffle(self.deck)
        
        # Track which cards have been drawn
        self.drawn_cards: List[Dict[str, Any]] = []
    
    def draw_card(self) -> Optional[Dict[str, Any]]:
        """Draw one action card from the deck.
        
        Returns:
            The drawn card dict, or None if deck is empty.
        """
        if not self.deck:
            return None
        
        card = self.deck.pop(0)
        self.drawn_cards.append(card)
        return card
    
    def peek_deck_size(self) -> int:
        """Return the current size of the action deck (for debugging/testing)."""
        return len(self.deck)
    
    def get_drawn_cards_by_initiative(self) -> List[Dict[str, Any]]:
        """Return all drawn cards sorted by initiative (highest first).
        
        Returns:
            List of drawn cards sorted by initiative in descending order.
        """
        return sorted(self.drawn_cards, key=lambda c: c.get('initiative', 0), reverse=True)


def create_turn_action_assignments(
    tactic: Dict[str, Any],
    units: List[Any],
    aggression_results: Dict[str, bool],
    rng: Optional[random.Random] = None
) -> List[Dict[str, Any]]:
    """Create action card assignments for all units that passed aggression checks.
    
    This is a helper function that:
    1. Creates an Action Deck for the given tactic
    2. Draws one card for each unit that passed its aggression check
    3. Returns assignments sorted by initiative (highest first)
    
    Args:
        tactic: The battle tactic dict (with 'title' field)
        units: List of unit objects
        aggression_results: Dict mapping unit name to bool (True if passed check)
        rng: Random number generator (for reproducible testing)
    
    Returns:
        List of assignment dicts with structure:
        {
            'unit': unit_name,
            'unit_obj': unit_object,
            'card': action_card_dict,
            'initiative': initiative_value
        }
        Sorted by initiative in descending order (highest initiative acts first).
    """
    action_deck = ActionDeckManager(tactic['title'], rng=rng)
    assignments = []
    
    for unit in units:
        unit_name = getattr(unit, 'name', str(unit))
        if aggression_results.get(unit_name, False):
            card = action_deck.draw_card()
            if card:
                assignments.append({
                    'unit': unit_name,
                    'unit_obj': unit,
                    'card': card,
                    'initiative': card.get('initiative', 0),
                    'behavior': card.get('behavior', ''),
                    'card_title': card.get('title', 'Unknown')
                })
    
    # Sort by initiative (highest first)
    assignments.sort(key=lambda a: a['initiative'], reverse=True)
    
    return assignments


if __name__ == '__main__':
    # Simple test/demo
    print("=== Tactics Deck Manager Demo ===\n")
    
    # Create deck manager for turn 1
    tdm = TacticsDeckManager(rng=random.Random(42), current_turn=1)
    print(f"Turn 1: Deck has {tdm.peek_deck_size()} cards, Discard has {tdm.peek_discard_size()} cards")
    
    # Draw a few tactics
    for turn in range(1, 5):
        tdm.advance_turn(turn)
        tactic = tdm.draw_tactic()
        if tactic:
            print(f"Turn {turn}: Drew '{tactic['title']}'")
            print(f"  Deck: {tdm.peek_deck_size()} cards, Discard: {tdm.peek_discard_size()} cards")
    
    print("\n=== Action Deck Manager Demo ===\n")
    
    # Create action deck for "Broken Ranks"
    adm = ActionDeckManager("Broken Ranks", rng=random.Random(42))
    print(f"Created Action Deck for 'Broken Ranks': {adm.peek_deck_size()} cards")
    
    # Draw 5 cards
    print("\nDrawing 5 action cards:")
    for i in range(5):
        card = adm.draw_card()
        if card:
            print(f"  {i+1}. {card['title']} (Initiative: {card.get('initiative', 'N/A')})")
    
    print(f"\nCards sorted by initiative:")
    for card in adm.get_drawn_cards_by_initiative():
        print(f"  {card['title']} (Initiative: {card.get('initiative', 'N/A')})")
