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
    rng = rng or random.Random()
    action_deck = ActionDeckManager(tactic['title'], rng=rng)
    assignments = []
    # Determine designated units from tactic metadata (simple selectors)
    designated = []
    sel = (tactic or {}).get('designated_units') or ""
    sel_text = str(sel or "").strip()

    def unit_matches_keyword(u, kw):
        kws = [k.lower() for k in getattr(u, 'keywords', []) or []]
        return kw.lower() in kws

    def unit_wounds_value(u):
        # Prefer explicit current_wounds if present (from simulator state), then wounds_per_model * models, then wounds_per_model
        if hasattr(u, 'current_wounds'):
            try:
                return float(getattr(u, 'current_wounds') or 0)
            except Exception:
                pass
        wp = getattr(u, 'wounds_per_model', None)
        models = getattr(u, 'models', None)
        try:
            if wp is not None and models is not None:
                return float(wp) * float(models)
            if wp is not None:
                return float(wp)
        except Exception:
            pass
        return 0.0

    import re

    if not sel_text:
        designated = []
    else:
        st = sel_text.lower()
        # parse an explicit count like '2' or '2 monsters' or 'monster 2'
        m = re.match(r"^(?P<count>\d+)\s*(?P<rest>.*)$", st)
        if not m:
            m = re.match(r"^(?P<rest>.*)\s+(?P<count>\d+)$", st)

        count = None
        rest = st
        if m:
            count = int(m.group('count'))
            rest = (m.group('rest') or '').strip()

        # helper: candidates matching an attribute-only selector (no spatial info)
        def candidates_for(rest_text):
            rt = (rest_text or '').strip()
            if not rt:
                return [u for u in units]
            # common role keywords
            if 'monster' in rt:
                return [u for u in units if unit_matches_keyword(u, 'Monster')]
            if 'hero' in rt:
                return [u for u in units if unit_matches_keyword(u, 'Hero')]
            if 'battleline' in rt:
                return [u for u in units if unit_matches_keyword(u, 'Battleline')]
            # highest-wounds selector
            if 'highest' in rt and 'wound' in rt:
                # return all units sorted by wounds desc
                return sorted(list(units), key=lambda uu: unit_wounds_value(uu), reverse=True)
            # random selector, e.g. 'random' or 'random 1'
            if 'random' in rt:
                # random will be resolved later via rng.sample but return matching pool
                # strip 'random' and match the remainder
                sub = rt.replace('random', '').strip()
                if sub:
                    return candidates_for(sub)
                return [u for u in units]
            # named-unit matching: substring match against unit name
            return [u for u in units if (getattr(u, 'name', '').lower().find(rt) != -1)]

        pool = candidates_for(rest)

        # If highest-wounds requested, pool may be sorted already
        if 'highest' in rest and 'wound' in rest:
            # take first count or all
            if count:
                chosen = pool[:count]
            else:
                chosen = pool
            designated = [getattr(u, 'name', str(u)) for u in chosen]
        elif 'random' in rest:
            # random selection deterministic by rng, but apply Option A: prefer role (pool), then highest-wounds, then random tie-break
            if count is None:
                count = 1
            pool_units = list(pool)
            if not pool_units:
                designated = []
            else:
                k = min(count, len(pool_units))
                # sort by wounds desc
                sorted_units = sorted(pool_units, key=lambda uu: unit_wounds_value(uu), reverse=True)
                # if k equals len or no ties at cutoff, pick top k
                if k >= len(sorted_units):
                    chosen = sorted_units
                else:
                    cutoff_wounds = unit_wounds_value(sorted_units[k-1])
                    above = [u for u in sorted_units if unit_wounds_value(u) > cutoff_wounds]
                    tied = [u for u in sorted_units if unit_wounds_value(u) == cutoff_wounds]
                    need = k - len(above)
                    if need <= 0:
                        chosen = above[:k]
                    else:
                        # deterministically sample among tied
                        tied_names = [getattr(u, 'name', str(u)) for u in tied]
                        # shuffle deterministically via rng.sample on indices
                        sel_names = rng.sample(tied_names, min(len(tied_names), need))
                        chosen = above + [next(u for u in tied if getattr(u, 'name', str(u)) == n) for n in sel_names]
                designated = [getattr(u, 'name', str(u)) for u in chosen]
        else:
            # otherwise, non-random selection: take first N from pool in roster order
            if count:
                # If the selector was numeric-only (e.g. '2'), preserve roster order for backward compatibility.
                if not rest:
                    roster_names = [getattr(u, 'name', str(u)) for u in units]
                    designated = roster_names[:count]
                else:
                    # Apply Option A: prefer highest-wounds among the pool (role is already applied in pool), tie-break deterministically via rng
                    pool_units = [u for u in units if getattr(u, 'name', str(u)) in [getattr(x, 'name', str(x)) for x in pool]]
                    # sort by wounds desc
                    sorted_units = sorted(pool_units, key=lambda uu: unit_wounds_value(uu), reverse=True)
                    k = min(count, len(sorted_units))
                    if k >= len(sorted_units):
                        chosen = sorted_units
                    else:
                        cutoff_wounds = unit_wounds_value(sorted_units[k-1])
                        above = [u for u in sorted_units if unit_wounds_value(u) > cutoff_wounds]
                        tied = [u for u in sorted_units if unit_wounds_value(u) == cutoff_wounds]
                        need = k - len(above)
                        if need <= 0:
                            chosen = above[:k]
                        else:
                            tied_names = [getattr(u, 'name', str(u)) for u in tied]
                            sel_names = rng.sample(tied_names, min(len(tied_names), need))
                            chosen = above + [next(u for u in tied if getattr(u, 'name', str(u)) == n) for n in sel_names]
                    designated = [getattr(u, 'name', str(u)) for u in chosen]
            else:
                designated = [getattr(u, 'name', str(u)) for u in pool]

    # Build the ordered list of units that will receive cards: prefer designated ones first
    aggressive_units = [getattr(u, 'name', str(u)) for u in units if aggression_results.get(getattr(u, 'name', str(u)), False)]
    ordered_unit_names = []
    # add designated ones that are aggressive, in tactic order
    for dn in designated:
        if dn in aggressive_units and dn not in ordered_unit_names:
            ordered_unit_names.append(dn)
    # then fill with remaining aggressive units in original units order
    for u in [getattr(u, 'name', str(u)) for u in units]:
        if u in aggressive_units and u not in ordered_unit_names:
            ordered_unit_names.append(u)

    # Assign drawn cards to ordered units
    for unit_name in ordered_unit_names:
        card = action_deck.draw_card()
        if card:
            # find unit_obj by name
            unit_obj = next((uu for uu in units if getattr(uu, 'name', str(uu)) == unit_name), None)
            assignments.append({
                'unit': unit_name,
                'unit_obj': unit_obj,
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
