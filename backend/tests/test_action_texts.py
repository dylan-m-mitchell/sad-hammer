import re
import unittest
from backend import reference_card_decks as ref


class TestActionTexts(unittest.TestCase):
    def test_no_next_turn_in_broken_ranks(self):
        actions = ref.tactic_to_actions.get("Broken Ranks", [])
        for a in actions:
            self.assertNotRegex(a.get("behavior", ""), re.compile(r"next\s+turn", re.IGNORECASE))

    def test_no_retreat_in_broken_ranks_default(self):
        actions = ref.tactic_to_actions.get("Broken Ranks", [])
        for a in actions:
            title = (a.get("title") or "").lower()
            # Allow titles that explicitly are about retreat in other tactics, but not for Broken Ranks
            self.assertNotIn("retreat", title)
            self.assertNotRegex(a.get("behavior", ""), re.compile(r"\bretreat\b", re.IGNORECASE))

    def test_validator_tool_reports_no_errors(self):
        # Import and run the validator
        from backend.tools.validate_actions import scan

        errs = scan()
        self.assertFalse(errs, f"Validator errors found: {errs}")


if __name__ == "__main__":
    unittest.main()


