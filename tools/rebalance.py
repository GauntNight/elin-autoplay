"""Bring every home box under 90% of its slots (G29's done-when, the user 2026-10-29) by moving its last stacks
into the second ★Storage Chest (home.STORAGE_CHEST_2), a few at a time through the pack with box.py.

usage: python -I tools/rebalance.py [--dry] [--batch N] [--limit PCT]
  --dry      list what would move and stop
  --batch N  stacks a trip (default 3: the pack grid must have that many free cards)
  --limit    the fill line in percent (default 90: a box ends at most at the line minus one stack)
Skips magic chests (their `slots` leaves out the wrench upgrades), fridges, the mail post, packages, the practice
chest, the shipping chest and anything that isn't a plain container or a treasure chest. Exit 0 done, 1 refused,
3 stopped (a box.py move that didn't go: the stacks stay where box.py left them, and it says so).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import refuse, run, stop  # noqa: E402
import home  # noqa: E402

SKIP_NAMES = ("mail post", "package", "practice chest", "sturdy treasure chest", "Dishes")
OK_TRAITS = ("TraitContainer", "TraitChest")


def over(limit):
    boxes = call("stock")["data"]["boxes"]
    todo = []
    for b in boxes:
        if (b["x"], b["z"]) == home.STORAGE_CHEST_2 or b.get("trait") not in OK_TRAITS:
            continue
        if any(s.lower() in b["name"].lower() for s in SKIP_NAMES) or not b.get("slots"):
            continue
        n, cap = b.get("count") or len(b.get("items") or []), b["slots"]
        keep = int(cap * limit / 100)
        if n * 100 >= cap * limit:
            keep = min(keep, n) - (1 if keep * 100 >= cap * limit else 0)
            names = [i["name"] for i in (b.get("items") or [])][keep:]
            todo.append((b, n, cap, names))
    return todo


def main():
    args = sys.argv[1:]
    batch = int(args[args.index("--batch") + 1]) if "--batch" in args else 3
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else 90
    todo = over(limit)
    if not todo:
        print(f"no box at {limit}%+")
        return
    for b, n, cap, names in todo:
        print(f"{b['name']} {b['x']},{b['z']}: {n}/{cap} -> move {len(names)}: " + "; ".join(names))
    if "--dry" in args:
        return
    to = "{},{}".format(*home.STORAGE_CHEST_2)
    moved = 0
    for b, n, cap, names in todo:
        src = f"{b['x']},{b['z']}"
        for i in range(0, len(names), batch):
            part = names[i:i + batch]
            r = run("box.py", src, "--take", *part)
            print(r)
            if r.rc != 0 or "did not move" in r or "not moved" in r:
                stop(f"the take from {src} didn't go cleanly (above): {moved} stacks moved so far")
            r = run("box.py", to, *part)
            print(r)
            if r.rc != 0 or "did not move" in r or "not moved" in r:
                stop(f"the put into {to} didn't go cleanly (above): those stacks are in the pack; {moved} moved so far")
            moved += len(part)
    print(f"moved {moved} stacks into the ★Storage Chest at {to}")
    left = over(limit)
    print("still at the line: " + ("; ".join(f"{b['name']} {b['x']},{b['z']} {n}/{cap}" for b, n, cap, _ in left) or "none"))


if __name__ == "__main__":
    main()
