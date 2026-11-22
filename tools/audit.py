"""Tally every home container by kind (G70 Smart Storage M1, run 57; the user, 2026-11-21: "go carefully through our current
storage rules, what we currently have available, and make some decisions about what we need to keep and what we need to
sell"). Reads the bridge's `stock` op once (every installed container on the home map, without walking), sorts each stack
by the game's own category (things.json, never a word in its name: elin-play's rule since runs 47-50), and counts how many
of the game's recipes take each thing, by its id or its category (graph.json's `needs` edges, kb.py's source).

What a tool, the kit or a goal uses is my reading, not the table's: the audit prints the numbers, and
knowledge/storage-audit.md puts a keep / sell / trash call beside each category for the user (M2).

usage: python -I tools/audit.py [--csv PATH] [--top N]
  prints one block per category, largest first: stacks, items, the containers holding it, the recipes that use it, and its
  N biggest kinds (default 6); --csv writes one row per kind (category, id, name, stacks, items, recipe uses, containers).
Exit 0, 2 the bridge.
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data, setup  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "knowledge" / "game"
COUNT = re.compile(r"^(?:an?|\d+)\s+")
CHARGES = re.compile(r"\s*\(\d+ Charges?\)|\s*\+\d+$|\s*\[[^\]]*\]$")


def load(name):
    return json.loads((GAME / f"{name}.json").read_text(encoding="utf-8"))


def base_name(name):
    """'12 seeds of rosewood tree' -> 'seeds of rosewood tree'; charges and pluses dropped so copies group."""
    n = COUNT.sub("", re.sub(r"[☆★]", "", name)).strip()
    return CHARGES.sub("", n).strip()


def main():
    setup()
    argv = sys.argv[1:]
    top = int(argv[argv.index("--top") + 1]) if "--top" in argv else 6
    out_csv = argv[argv.index("--csv") + 1] if "--csv" in argv else None
    things = {t["id"]: t for t in load("things")}
    cats = {c["id"]: c for c in load("categories")}

    def root(cat):
        seen = []
        while cat in cats and cats[cat].get("_parent") and cat not in seen:
            seen.append(cat)
            cat = cats[cat]["_parent"]
        return cat

    uses = defaultdict(int)  # thing:ID or category:ID -> recipes that take it
    for a, rel, b, _meta in load("graph")["edges"]:
        if rel == "needs":
            uses[b] += 1

    def recipe_uses(tid):
        n = uses.get(f"thing:{tid}", 0)
        cat = (things.get(tid) or {}).get("category")
        while cat:
            n += uses.get(f"category:{cat}", 0)
            cat = (cats.get(cat) or {}).get("_parent")
        return n

    s = data("stock")
    by_cat = defaultdict(lambda: {"stacks": 0, "items": 0, "boxes": defaultdict(int), "kinds": defaultdict(lambda: [0, 0, set()])})
    total = 0
    for box in s["boxes"]:
        if not box.get("installed"):
            continue
        where = f"{box['name']} {box['x']},{box['z']}"
        for it in box.get("items") or []:
            tid = it.get("id") or "?"
            cat = (things.get(tid) or {}).get("category") or "?"
            key = f"{root(cat)}/{cat}"
            c = by_cat[key]
            c["stacks"] += 1
            c["items"] += it.get("num") or 1
            c["boxes"][where] += 1
            k = c["kinds"][(tid, base_name(it["name"]))]
            k[0] += 1
            k[1] += it.get("num") or 1
            k[2].add(where)
            total += 1
    rows = []
    for key, c in sorted(by_cat.items(), key=lambda kv: -kv[1]["stacks"]):
        kinds = sorted(c["kinds"].items(), key=lambda kv: -kv[1][0])
        print(f"== {key}: {c['stacks']} stacks, {c['items']} items, {len(kinds)} kinds")
        print("   in: " + "; ".join(f"{w} ({n})" for w, n in sorted(c["boxes"].items(), key=lambda kv: -kv[1])[:6])
              + (" ..." if len(c["boxes"]) > 6 else ""))
        for (tid, name), (st, n, wh) in kinds[:top]:
            print(f"   {st:>3} x {name} [{tid}] items {n}, recipes {recipe_uses(tid)}")
        for (tid, name), (st, n, wh) in kinds:
            rows.append([key, tid, name, st, n, recipe_uses(tid), "; ".join(sorted(wh))])
    print(f"{total} stacks in {sum(1 for b in s['boxes'] if b.get('installed'))} containers, {len(by_cat)} categories")
    if out_csv:
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["category", "id", "name", "stacks", "items", "recipe_uses", "containers"])
            w.writerows(rows)
        print(f"wrote {out_csv}")


if __name__ == "__main__":
    main()
