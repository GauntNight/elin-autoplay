"""Explore a dungeon floor: walk to the nearest frontier (an explored floor cell beside an
unexplored one), look again, repeat. Stops at once (exit 3, "stop: ...") when a hostile is in
view, HP is under the floor, or a window opens; reports stairs as they come into view. Exit 0
with "stopped: move limit" or "stopped: no frontier left: floor explored" (the callers read
those lines; the stairs line "stairs (not the way in): ..." comes before them). Never rests or
waits (the user's rule: no idling in a dungeon).

usage: python -I tools/explore.py [MOVES=12] [MIN_HP_PCT=70]
Prints each move, then a summary: stairs seen, frontier left, why it stopped.
The start cell's stairs (the way back up) are remembered and not reported as new.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import stop, walk  # noqa: E402

WALK = set('.\"*>@pn')


def grid(r=40):
    d = call("map", r=r)["data"]
    m = re.search(r"x=(-?\d+), z=(-?\d+)", d["origin"])
    x0, z0 = int(m.group(1)), int(m.group(2))
    cells = {}
    for i, row in enumerate(d["rows"]):
        for j, ch in enumerate(row):
            cells[(x0 + j, z0 - i)] = ch
    return cells


def danger(s, min_hp):
    p = s["pc"]
    foes = [c for c in s.get("nearby") or [] if c.get("hostile")]
    if foes:
        return "hostile in view: " + ", ".join(f"{c['name']} Lv{c['lv']} d{c['dist']}" for c in foes)
    if p["hp"] * 100 < min_hp * p["maxHp"]:
        return f"HP {p['hp']}/{p['maxHp']} under {min_hp}%"
    top = (s.get("layers") or {}).get("top")
    if top:
        return f"window open: {top}"
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    nums = [int(a) for a in sys.argv[1:] if a.isdigit()]
    moves = nums[0] if nums else 12
    min_hp = nums[1] if len(nums) > 1 else 70
    s = call("state")["data"]
    why = danger(s, min_hp)
    if why:
        stop("not exploring: " + why)
    start = (s["pc"]["x"], s["pc"]["z"])
    tried, seen_stairs = set(), set()
    why, decide = "move limit", False
    for k in range(1, moves + 1):
        cells = grid()
        for xy, ch in cells.items():
            if ch == ">" and xy not in seen_stairs:
                seen_stairs.add(xy)
                note = " (where I came in)" if abs(xy[0] - start[0]) + abs(xy[1] - start[1]) <= 1 else ""
                print(f"   stairs at {xy[0]},{xy[1]}{note}")
        p = call("state")["data"]["pc"]
        here = (p["x"], p["z"])
        front = []
        for (x, z), ch in cells.items():
            if ch not in WALK or (x, z) in tried:
                continue
            if any(cells.get((x + ox, z + oz), " ") == " " for ox, oz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                front.append((abs(x - here[0]) + abs(z - here[1]), x, z))
        front = [f for f in front if f[0] > 0]
        if not front:
            why = "no frontier left: floor explored"
            break
        _, tx, tz = min(front)
        tried.add((tx, tz))
        # walkto (bridge 0.23.0) replies on arrival, a stop, a hostile in view (r=12), HP under the
        # floor or a window; a stairway or an unexplored target is refused and skipped (run 12 review)
        w = walk(tx, tz, r=12, hp=min_hp, timeout=40000)
        if w.get("why") == "refused":
            continue
        s = call("state")["data"]
        halt = danger(s, min_hp) if w.get("why") in ("hostile", "hp", "window", "zone") else None
        p = s["pc"]
        print(f"{k:2} -> {tx},{tz}  now {p['x']},{p['z']}  HP {p['hp']}/{p['maxHp']}  {p['date']}")
        if halt:
            why, decide = halt, True
            break
    others = sorted(xy for xy in seen_stairs if abs(xy[0] - start[0]) + abs(xy[1] - start[1]) > 1)
    if others:
        print("stairs (not the way in): " + "; ".join(f"{x},{z}" for x, z in others))
    if decide:
        stop(why)  # a hostile, HP or a window: the caller decides (exit 3)
    print("stopped: " + why)


if __name__ == "__main__":
    main()
