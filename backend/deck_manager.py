"""Deck Manager for Solo Wargaming Battle Tactics and Action Decks

Copied into backend package for server ownership.
"""

import random
from copy import deepcopy
from typing import List, Dict, Any, Optional, Tuple
from backend.reference_card_decks import (
    battle_tactic_deck,
    tactic_to_actions,
    objective_action_deck
)


class TacticsDeckManager:
    """Manages the Battle Tactics deck for a game session."""
    
    def __init__(self, rng: Optional[random.Random] = None, current_turn: int = 1):
        self.rng = rng or random.Random()
        self.current_turn = current_turn
        
        self.deck: List[Dict[str, Any]] = []
        self.discard_pile: List[Dict[str, Any]] = []
        
        for tactic in battle_tactic_deck:
            enters_on = tactic.get('enters_deck_on_turn', 0)
            if enters_on < current_turn:
                self.discard_pile.append(deepcopy(tactic))
            elif enters_on == current_turn:
                self.discard_pile.append(deepcopy(tactic))
        
        if current_turn == 1:
            self.deck = [deepcopy(t) for t in battle_tactic_deck if t.get('enters_deck_on_turn', 0) == 0]
            self.discard_pile = []
            self.rng.shuffle(self.deck)
        else:
            self._reshuffle_if_needed()
    
    def _reshuffle_if_needed(self):
        if not self.deck and self.discard_pile:
            self.deck = self.discard_pile[:]
            self.discard_pile = []
            self.rng.shuffle(self.deck)
    
    def advance_turn(self, new_turn: int):
        self.current_turn = new_turn
        
        for tactic in battle_tactic_deck:
            enters_on = tactic.get('enters_deck_on_turn', 0)
            if enters_on == new_turn:
                already_in_play = any(
                    t['title'] == tactic['title'] 
                    for t in (self.deck + self.discard_pile)
                )
                if not already_in_play:
                    self.discard_pile.append(deepcopy(tactic))
    
    def draw_tactic(self) -> Optional[Dict[str, Any]]:
        self._reshuffle_if_needed()
        
        if not self.deck:
            return None
        
        card = self.deck.pop(0)
        self.discard_pile.append(card)
        return card
    
    def peek_deck_size(self) -> int:
        return len(self.deck)
    
    def peek_discard_size(self) -> int:
        return len(self.discard_pile)


class ActionDeckManager:
    def __init__(self, tactic_title: str, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()
        self.tactic_title = tactic_title
        
        tactic_actions = tactic_to_actions.get(tactic_title)
        if tactic_actions is None:
            raise ValueError(f"Unknown tactic: {tactic_title}")
        
        self.deck: List[Dict[str, Any]] = []
        self.deck.extend(deepcopy(tactic_actions))
        self.deck.extend(deepcopy(objective_action_deck))
        
        self.rng.shuffle(self.deck)
        
        self.drawn_cards: List[Dict[str, Any]] = []
    
    def draw_card(self) -> Optional[Dict[str, Any]]:
        if not self.deck:
            return None
        
        card = self.deck.pop(0)
        self.drawn_cards.append(card)
        return card
    
    def peek_deck_size(self) -> int:
        return len(self.deck)
    
    def get_drawn_cards_by_initiative(self) -> List[Dict[str, Any]]:
        return sorted(self.drawn_cards, key=lambda c: c.get('initiative', 0), reverse=True)


def create_turn_action_assignments(
    tactic: Dict[str, Any],
    units: List[Any],
    aggression_results: Dict[str, bool],
    rng: Optional[random.Random] = None
) -> List[Dict[str, Any]]:
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
    
    assignments.sort(key=lambda a: a['initiative'], reverse=True)
    
    return assignments


if __name__ == '__main__':
    import random as _r
    print("=== Tactics Deck Manager Demo ===\n")
    tdm = TacticsDeckManager(rng=_r.Random(42), current_turn=1)
    print(f"Turn 1: Deck has {tdm.peek_deck_size()} cards, Discard has {tdm.peek_discard_size()} cards")
