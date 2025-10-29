import unittest
from typing import List

from backend.full_simulator import SoloSimulator, Unit
from backend import reference_card_decks as ref


def collect_events_by_key(events: List[dict], key: str):
    return [e for e in events if key in e]


class TestTacticsBehavior(unittest.TestCase):
    def setUp(self):
        # Minimal units; keywords used for certain tactics
        self.units = [
            Unit("Unit A", aggression="Neutral", keywords=["Battleline"]),
            Unit("Unit B", aggression="Neutral", keywords=["Monster"]),
            Unit("Unit C", aggression="Neutral", keywords=["Hero"]),
            Unit("Unit D", aggression="Neutral"),
        ]

    def test_single_use_tactics_over_five_turns(self):
        sim = SoloSimulator(self.units, seed=123)
        drawn = []
        for _ in range(5):
            events = sim.simulate_turn()
            for ev in events:
                if ev.get("event") == "battle_tactic_drawn":
                    drawn.append(ev.get("tactic"))
                    break
        self.assertEqual(len(drawn), 5, "Should draw a tactic each turn")
        self.assertEqual(len(set(drawn)), 5, "Tactics should be unique (single-use)")

    def test_ferocious_advance_forced_run_together(self):
        sim = SoloSimulator(self.units, seed=42)
        # Force the deck to draw Ferocious Advance
        fa = next(t for t in ref.battle_tactic_deck if t["title"] == "Ferocious Advance")
        sim.tactics_deck.deck = [fa]
        sim.tactics_deck.discard_pile = []

        events = sim.simulate_turn()
        # Ensure exact text is emitted
        bte = next(e for e in events if e.get("event") == "battle_tactic_drawn")
        self.assertIn("exact_text", bte)
        self.assertTrue(bte.get("exact_text"), "Ferocious Advance should include verbatim exact_text")

        # Find action resolutions and confirm 3 Run Together for designated units
        actions = [e.get("action_resolved") for e in events if e.get("action_resolved")]
        run_together = [a for a in actions if a and a.get("card_title") == "Run Together"]
        self.assertGreaterEqual(len(run_together), 3, "Should assign 3 'Run Together' actions for Ferocious Advance")


if __name__ == "__main__":
    unittest.main()


