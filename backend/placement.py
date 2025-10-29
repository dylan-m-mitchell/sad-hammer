import os
import json
from typing import List, Dict, Tuple, Any, Optional

_ZONE_BIAS = None


def _load_zone_bias() -> List[Dict[str, Any]]:
    global _ZONE_BIAS
    if _ZONE_BIAS is not None:
        return _ZONE_BIAS
    path = os.path.join(os.path.dirname(__file__), "..", "backend", "battleplan_zone_bias.json")
    # normalize path (api_server calls this from repo root); try alternate path
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(__file__), "battleplan_zone_bias.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            _ZONE_BIAS = json.load(f)
    except Exception:
        _ZONE_BIAS = []
    return _ZONE_BIAS


def get_zone_entry_for_bp(bp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not bp:
        return None
    entries = _load_zone_bias()
    try:
        bid = bp.get("id")
        if bid is not None:
            for e in entries:
                if e.get("id") == bid:
                    return e
    except Exception:
        pass
    try:
        title = str(bp.get("title", "")).lower()
        for e in entries:
            if str(e.get("title", "")).lower() == title:
                return e
    except Exception:
        pass
    return None


def build_proposed_placement(
    turn: int, rng, bp: Dict[str, Any], ai_profiles: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Construct a proposed placement dict for the given turn, using rng for tie-breaking.

    The returned dict follows the shape the API expects: event, turn, battleplan, allowed_zones, suggestions.
    """
    zone_entry = get_zone_entry_for_bp(bp)
    zones = zone_entry.get("zones", {}) if zone_entry else {}
    allowed_zones = [z for z, w in zones.items() if (w is not None and w >= 0)] if zones else []

    placement = {
        "event": "placement",
        "turn": turn,
        "battleplan": bp,
        "allowed_zones": allowed_zones,
        "suggestions": [],
    }

    # heuristic weights for unit attributes
    def unit_base_pref(unit_profile: Dict[str, Any]) -> Dict[str, int]:
        kws = [k.lower() for k in (unit_profile.get("keywords") or []) if isinstance(k, str)]
        models = 0
        try:
            models = int(unit_profile.get("models", 0) or 0)
        except Exception:
            models = 0
        wounds = 0
        try:
            wounds = int(unit_profile.get("wounds_per_model", 0) or 0)
        except Exception:
            wounds = 0

        # base preference vector: dict of multipliers to apply to zone bias
        pref = {
            "forward": 1,
            "center": 1,
            "left": 1,
            "right": 1,
            "defensive": 1,
            "reserve": 1,
            "scattered": 1,
        }

        # monsters / heroes prefer centre/forward and anchors
        if any("monster" in k for k in kws) or any("hero" in k for k in kws):
            pref["center"] += 1
            pref["forward"] += 1
            pref["defensive"] += 1

        # small & fast units (models >1 but low wounds) prefer forward/scattered for objective play
        if models > 1 and wounds <= 2:
            pref["forward"] += 1
            pref["scattered"] += 1

        # single-model high-wounds (skirmish heroes or monsters) prefer defensive/center
        if models <= 1 and wounds >= 3:
            pref["defensive"] += 1
            pref["center"] += 1

        # high model count suggests screening or board presence (scattered)
        if models >= 10:
            pref["scattered"] += 2

        return pref

    for u in ai_profiles:
        name = u.get("name")
        # compute per-zone score = battleplan weight * unit preference multiplier
        per_zone_scores = {}
        base_pref = unit_base_pref(u)
        if zones:
            for z, w in zones.items():
                # default weight safety
                try:
                    weight = int(w)
                except Exception:
                    try:
                        weight = float(w)
                        weight = int(weight)
                    except Exception:
                        weight = 0
                mul = base_pref.get(z, 1)
                per_zone_scores[z] = weight * mul
        else:
            # fallback: neutral equally scored zones
            for z in ["left", "center", "right", "forward", "defensive", "reserve", "scattered"]:
                per_zone_scores[z] = base_pref.get(z, 1)

        # pick best score(s)
        max_score = max(per_zone_scores.values()) if per_zone_scores else 0
        top_zones = [z for z, s in per_zone_scores.items() if s == max_score]
        suggested = rng.choice(top_zones) if top_zones else None

        reason = ""
        if any("monster" in k for k in (u.get("keywords") or [])) or any(
            "hero" in k for k in (u.get("keywords") or [])
        ):
            reason = "Prefer centre/anchor; monster/hero bias applied"
        else:
            reason = "Scored by battleplan weights and unit prefs"

        suggestion = {
            "unit": name,
            "suggested_zone": suggested,
            "reason": reason,
            "scores": per_zone_scores,
        }

        # Heuristic extra hints for frontend placement guidance
        try:
            # priority: High for monsters/heroes, Medium for large squads, Low otherwise
            pr = "Low"
            if any("monster" in k for k in (u.get("keywords") or [])) or any(
                "hero" in k for k in (u.get("keywords") or [])
            ):
                pr = "High"
            else:
                try:
                    mcount = int(u.get("models", 0) or 0)
                    if mcount >= 10:
                        pr = "Medium"
                except Exception:
                    pr = "Low"

            # short zone hint text for the suggested zone
            zh = f"Place in {suggested or 'scattered'}"
            if pr == "High":
                zh += " (anchor/high-value model)"
            elif pr == "Medium":
                zh += " (screen/holding objective)"

            # distance_range: approximate deployment distance guidance (small, medium, deep)
            # monsters/hero/defensive -> medium/deep; skirmishers/forward -> small/medium
            dr = "medium"
            if pr == "High":
                dr = "medium"
            try:
                mcount = int(u.get("models", 0) or 0)
                wounds = int(u.get("wounds_per_model", 0) or 0)
                if mcount > 8 and wounds <= 2:
                    dr = "small"
                if wounds >= 6:
                    dr = "deep"
            except Exception:
                pass

            # coordinate_hint: textual guidance to help player place on a battleplan image
            coord = ""
            if suggested in ("left", "right"):
                coord = f"Near the {suggested} table edge"
            elif suggested == "center":
                coord = "Centered along the midline"
            elif suggested == "forward":
                coord = "Close to the enemy deployment line (forward)"
            elif suggested == "defensive":
                coord = "Set back toward your deployment to hold objectives"
            elif suggested == "reserve":
                coord = "Off-table or rear reserve area"
            else:
                coord = "Spread or scatter across the chosen sector"

            suggestion["priority"] = pr
            suggestion["zone_hint"] = zh
            suggestion["distance_range"] = dr
            suggestion["coordinate_hint"] = coord
        except Exception:
            # non-fatal: leave suggestion without hints if heuristic fails
            pass

        placement["suggestions"].append(suggestion)

    return placement


def validate_placements(
    proposed: Dict[str, Any], placements: List[Dict[str, Any]]
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Validate that placements satisfy the proposed placement allowed_zones and include all units.

    Returns (True, None) on success. On failure, returns (False, error_details).
    """
    if not proposed:
        return False, {"error": "no_proposed_placement"}
    allowed = set(proposed.get("allowed_zones", []) or [])
    if not allowed:
        return False, {"error": "no_allowed_zones_defined"}

    if not isinstance(placements, list):
        return False, {"error": "placements_must_be_list"}

    # suggestions may include 'unit' or 'name' depending on source; support both
    unit_names = [
        (u.get("unit") if u.get("unit") is not None else u.get("name"))
        for u in proposed.get("suggestions", [])
    ]
    provided_units = [p.get("unit") for p in placements if isinstance(p, dict)]
    missing = [n for n in unit_names if n not in provided_units]
    if missing:
        return False, {"error": "missing_unit_placements", "missing": missing}

    invalid = []
    for p in placements:
        if not isinstance(p, dict):
            invalid.append({"provided": p, "reason": "not_object"})
            continue
        unit = p.get("unit")
        zone = p.get("zone")
        if zone not in allowed:
            invalid.append({"unit": unit, "zone": zone})

    if invalid:
        return False, {"error": "invalid_zones", "details": invalid}

    return True, None
