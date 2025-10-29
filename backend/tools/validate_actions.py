import re
from backend import reference_card_decks as ref


FORBIDDEN_BY_TACTIC = {
    "Broken Ranks": [r"next\s+turn", r"Retreat"],
    "Bring It Down": [r"next\s+turn"],
    "Slay the Warlord": [r"next\s+turn"],
    "Conquer": [r"next\s+turn", r"hold\b", r"defend\b"],
    "Aggressive Expansion": [r"next\s+turn"],
    "Savage Spearhead": [r"next\s+turn", r"hold\b"],
    "Monstrous Takeover": [r"next\s+turn"],
}

# Phrases that make otherwise forbidden words acceptable under tactics (conditional, post-completion contexts)
ALLOW_IF_CONTAINS = {
    "Conquer": ["objective was captured this turn"],
    "Savage Spearhead": ["wholly within enemy territory"],
}


def scan():
    errors = []
    for tactic, actions in ref.tactic_to_actions.items():
        patterns = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_BY_TACTIC.get(tactic, [])]
        if not patterns:
            continue
        for a in actions:
            behavior = a.get("behavior", "") or ""
            allow_markers = ALLOW_IF_CONTAINS.get(tactic, [])
            is_allowed = any(m.lower() in behavior.lower() for m in allow_markers)
            for pat in patterns:
                if pat.search(behavior) and not is_allowed:
                    errors.append((tactic, a.get("title"), behavior))
    return errors


if __name__ == "__main__":
    errs = scan()
    if errs:
        print("Found forbidden phrases in action behaviors:")
        for t, title, beh in errs:
            print(f"- {t} / {title}: {beh}")
        raise SystemExit(1)
    print("All action behaviors passed validation.")


