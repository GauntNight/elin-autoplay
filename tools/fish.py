"""Fish from a shore cell until the bait runs out, SP drops below a floor, or a hostile shows
up. Each catch lands on the player's own cell; it is picked up after every catch.

usage: python -I tools/fish.py SHORE_X,SHORE_Z [min_sp]
  e.g. python -I tools/fish.py 47,41      (the home lake in world_4)
Needs: a fishing rod and baits in the pack (Quick Craft "Bait" from a mushroom).
Exit 0 at the bait or SP floor, 1 refused (no rod, no Fishing act), 3 stopped (a hostile in view,
a window, HP under walk_hp).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import THRESHOLDS, cells, grab, pack_full, pc, put_away, ready, refuse, stop, wait_idle, wait_until  # noqa: E402
from common import walk as common_walk  # noqa: E402


def walk(x, z):
    """Walk with the bridge's walkto (run 12 review); returns the player's state afterwards."""
    common_walk(x, z, r=0, hp=0, timeout=30000)
    return call("state")["data"]["pc"]


def hold_rod():
    """The rod in hand through common.grab (whole-word name; run 13: the old inventory-window path
    crashed with the window closed)."""
    held = pc().get("held") or ""
    if "fishing rod" in held:
        return True  # run 15: Grab toggles, so grabbing a held rod would put it away
    if held:
        put_away()  # run 15: the baits just crafted were in hand and the rod's Grab didn't take
    return "rod" in (grab("fishing rod", what="rod") or "")


def baits():
    """Every bait slot the bridge lists (run 16: crafted baits stacked in the worn toolbelt, which
    `inv` doesn't list, and fish.py read 0 with 12 in the pack)."""
    import re
    n = sum(i["num"] for i in call("inv")["data"]["items"] if i["id"] == "bait")
    if n:
        return n
    for b in call("buttons", all=True)["data"]["buttons"]:
        m = re.match(r"(\d+ )?baits?$", (b.get("card") or "").strip())
        if m and "ButtonGrid inventory" in b["name"]:
            n += int(m.group(1) or 1)
    return n


def fishing_spot():
    """The water cell to fish, found once (the review of 2026-10-23: the old scan made ~100 bridge
    calls per cast): a cell with a fish silhouette (a visible fish spot, run 05) within 3 cells,
    else the nearest cell that offers Fishing. Returns (dx, dz) or None."""
    p = pc()
    ring = sorted(((dx, dz) for dx in range(-3, 4) for dz in range(-3, 4) if dx or dz),
                  key=lambda d: max(abs(d[0]), abs(d[1])))
    info = cells([(p["x"] + dx, p["z"] + dz) for dx, dz in ring])
    water = [(dx, dz) for dx, dz in ring if (info.get((p["x"] + dx, p["z"] + dz)) or {}).get("water")]
    spots = [(dx, dz) for dx, dz in water if "fish" in ((info.get((p["x"] + dx, p["z"] + dz)) or {}).get("obj") or "")]
    for dx, dz in spots + water:
        acts = call("acts", dx=dx, dz=dz, mode="right")["data"]["acts"]
        if any(a["text"] == "Fishing" for a in acts):
            return dx, dz
    return None


def main():
    sx, sz = (int(v) for v in sys.argv[1].split(","))
    min_sp = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    walk(sx, sz)
    why = ready(hp=THRESHOLDS["walk_hp"], hunger=None, sp=min_sp)
    if why:
        stop(why)
    if not hold_rod():
        refuse("no fishing rod to hold")
    spot = fishing_spot()
    if not spot:
        refuse("no Fishing act within 3 cells: pick a shore cell")
    caught = 0
    while baits() > 0:
        wait_idle(timeout=300000)  # run 32: a cast can outlast the 120 s wait below, and ready() then read "busy: AI_Fish"
        s = call("state")["data"]
        p = s["pc"]
        if p["sp"] < min_sp:
            print(f"stopping: SP {p['sp']}")
            break
        why = ready(s, hp=THRESHOLDS["walk_hp"], hunger=None)
        if why:
            print(f"caught {caught}; baits left {baits()}; SP {p['sp']}/{p['maxSp']}; {p['date']}")
            stop(why)
        acts = call("acts", dx=spot[0], dz=spot[1], mode="right")["data"]["acts"]
        fishing = [a for a in acts if a["text"] == "Fishing"]
        if not fishing:
            refuse(f"the Fishing act is gone from the cell at {spot} (moved? the rod put away?)")
        call("do", i=fishing[0]["i"])
        wait_until("frames", n=10, timeout=1500)  # the fishing task starts
        wait_idle(timeout=120000)  # AI_Fish ends on a catch or a lost bait (was a 60 x 2 s poll)
        here = call("acts", dx=0, dz=0, mode="all")["data"]["acts"]
        picks = [a for a in here if a["text"].startswith("Pick")]
        if picks and pack_full():  # errors.csv row 5: a pick-up into a full pack vanishes
            print("  the pack is full: the catch stays on the ground")
            picks = []
        if picks:
            call("do", i=picks[-1]["i"])
            wait_until("frames", n=15, timeout=2000)
            caught += 1
        log = call("state")["data"]["log"]
        print("  " + " / ".join(l for l in log[-4:] if "catch" in l or "bait" in l.lower() or "pick up" in l))
    p = call("state")["data"]["pc"]
    print(f"caught {caught}; baits left {baits()}; SP {p['sp']}/{p['maxSp']}; {p['date']}")


if __name__ == "__main__":
    main()
