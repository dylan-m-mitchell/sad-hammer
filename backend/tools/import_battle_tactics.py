import argparse
import json
import os
from typing import Any, Dict


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def merge_tactics(base: Dict[str, Any], incoming: Dict[str, Any], force: bool) -> Dict[str, Any]:
    base_titles = {t.get("title"): t for t in base.get("tactics", [])}
    for t in incoming.get("tactics", []):
        title = t.get("title")
        if not title:
            continue
        if title in base_titles and not force:
            # keep existing entry
            continue
        base_titles[title] = t
    merged = {
        "season": incoming.get("season", base.get("season")),
        "source": incoming.get("source", base.get("source")),
        "tactics": list(base_titles.values()),
    }
    return merged


def scrape_stub() -> Dict[str, Any]:
    # Placeholder: implement site-specific scraping if permissible
    # Return an empty structure to avoid overwriting without --force
    return {"season": None, "source": None, "tactics": []}


def main():
    ap = argparse.ArgumentParser(description="Import or update battle tactics store")
    ap.add_argument("--store", default="backend/rules/battle_tactics.json")
    ap.add_argument("--load-json", dest="load_json_path")
    ap.add_argument("--scrape", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    existing = {"season": None, "source": None, "tactics": []}
    if os.path.exists(args.store):
        existing = load_json(args.store)

    incoming = {"season": None, "source": None, "tactics": []}
    if args.load_json_path:
        incoming = load_json(args.load_json_path)
    elif args.scrape:
        incoming = scrape_stub()

    merged = merge_tactics(existing, incoming, force=args.force)
    save_json(args.store, merged)
    print(f"Updated store at {args.store} with {len(merged.get('tactics', []))} tactics.")


if __name__ == "__main__":
    main()


