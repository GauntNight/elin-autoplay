"""Collect needles from cacti on a beach map (the user's idea, run 08: G6's loom needs 6 needles; a
cactus gives a bone needle when collected by hand, ripe or not: GrowSystemCactus.OnMineObj).
Harvests every cactus on the explored map (right-click "Collect", wait, pick up the needle), then
explores to reveal more. Fights hostiles 3+ levels below me; stops (exit 3) for anything stronger,
HP under 70%, SP under the floor, or a window.

Find beach tiles from the world map: `bridge.py terrain 40 beach` (the nearest: 6 tiles east of home).

usage: python -I tools/needles.py [WANT=12] [MIN_SP=10] [ROUNDS=30]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call, close as bridge_close  # noqa: E402
from common import THRESHOLDS, last, pack_full, ready, run, stop, wait_idle, wait_until, walk_beside  # noqa: E402

TOOLS = Path(__file__).resolve().parent


def needles():
    n = 0
    for i in call("inv")["data"]["items"]:
        if i["id"] == "needle":
            n += int(i["name"].split()[0]) if i["name"][0].isdigit() else 1
    return n


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    nums = [int(a) for a in sys.argv[1:] if a.isdigit()]
    want = nums[0] if nums else 12
    min_sp = nums[1] if len(nums) > 1 else 10
    rounds = nums[2] if len(nums) > 2 else 30
    tried = set()
    start = needles()
    for _ in range(rounds):
        s = call("state")["data"]
        pc = s["pc"]
        # one shared check (the review of 2026-10-23): a window, busy, a bad condition, HP under
        # dungeon_hp (70), SP, the world map, deep water; weak hostiles (3+ levels below) are
        # fought below instead of stopping the round
        why = ready(s, hp=THRESHOLDS["dungeon_hp"], hunger=None, sp=min_sp, weak_ok=True)
        if why:
            print(f"needles: {start} -> {needles()}")
            stop(why)
        if needles() >= want:
            print(f"have {needles()} needles")
            break
        weak = [c for c in s.get("nearby") or [] if c.get("hostile")]
        if weak:
            out = run("fight.py", weak[0]["name"].split(" ", 1)[-1], "70", "20")
            print("  fight:", last(out)[:100])
            if out.rc == 3:
                stop("the fight stopped: " + last(out)[:120])
            continue
        hits = [h for h in call("find", name="cactus", r=999, n=50)["data"]["hits"]
                if h["kind"] == "obj" and (h["x"], h["z"]) not in tried]
        if not hits:
            out = run("explore.py", "8", "70")
            tail = last(out)
            print("  explore:", tail[:120])
            if out.rc == 3:
                stop("explore stopped: " + tail[:120])
            if "explored" in tail or "no frontier" in tail:
                break
            continue
        h = hits[0]
        tried.add((h["x"], h["z"]))
        # walk_beside picks a free neighbour (the old loop tried eight goto targets with a poll each)
        w = walk_beside(h["x"], h["z"], hp=THRESHOLDS["dungeon_hp"], timeout=20000, weak_ok=True)
        p = call("state")["data"]["pc"]
        if max(abs(p["x"] - h["x"]), abs(p["z"] - h["z"])) > 1:
            print(f"  can't reach the cactus at {h['x']},{h['z']} ({w.get('why')})")
            if w.get("why") in ("hostile", "hp", "window", "zone"):
                stop(f"the walk stopped: {w.get('why')}")
            continue
        cx, cz = h["x"] - p["x"], h["z"] - p["z"]
        run("hotbar.py", "--deselect")
        acts = call("acts", dx=cx, dz=cz, mode="right")["data"]["acts"]
        col = [a for a in acts if a["text"].startswith("Collect") or a["text"].startswith("Harvest")]
        if not col:
            print(f"  no Collect on the cactus at {h['x']},{h['z']}: " + " | ".join(a["text"] for a in acts))
            continue
        call("do", i=col[0]["i"])
        wait_idle(timeout=60000)  # the collect task ends on its own (was a 40 x 1.5 s poll)
        for _ in range(4):  # the needle (and a ripe cactus's fruit and seed) land on its cell
            if pack_full():  # errors.csv row 5: a pick-up into a full pack vanishes
                print("  the pack is full: not picking up")
                break
            acts = call("acts", dx=cx, dz=cz, mode="all")["data"]["acts"]
            picks = [a for a in acts if a["text"].startswith("Pick")]
            if not picks:
                break
            call("do", i=picks[0]["i"])
            wait_until("frames", n=10, timeout=1500)
        print(f"  cactus at {h['x']},{h['z']}: needles now {needles()}")
    print(f"needles: {start} -> {needles()}")


if __name__ == "__main__":
    main()
