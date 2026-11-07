"""Bring in the treasure chests lying loose on the home map (run 43: seven from Poppy's Treasure Hunt lay in the yard, about 2,000 orens, 3 bars and 2 medals each; elin-home said arrive.py picked them up, and no tool did). One at a time, on its own cell: item.py takes the first of a name, and a locked twin in the pack stops chests.py (run 42). A locked one goes through unlock.py in the pack (a loose chest has no Pick Lock act) and back on its cell if it won't open.

usage: python -I tools/yardchests.py [--dry]     --dry lists them with their locks and moves nothing
Exit 0 done (or none), 1 refused (not at home), 3 stopped (home_guard's stops, chests.py's stop).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, data, last, pc, refuse, run, setup, state, stop, walk  # noqa: E402


def loose():
    hits = call("find", name="treasure chest", r=999, n=60)["data"]["hits"]
    return [h for h in hits if not h.get("installed", True)]


def here(name):
    """This cell's loose chest, as the cell's own listing has it (lockLv, uid)."""
    for t in data("cell", dx=0, dz=0).get("thingInfo") or []:
        if t.get("name") == name and t.get("placeState") != "installed":
            return t
    return None


def have_pick():
    return any("lockpick" in i["name"].lower() for i in data("inv")["items"])


def bare_power():
    return ((data("skills").get("skills") or {}).get("lockpicking") or {}).get("lv", 0) // 2 + 2


def carried_lock():
    """The lock of the chest just picked up, 0 when it opens."""
    locked = [i for i in data("inv")["items"] if "treasure chest" in i["name"].lower() and i.get("lockLv")]
    return locked[0]["lockLv"] if locked else 0


def main():
    setup()
    if not state()["zone"]["full"].startswith("Zone_startSite"):
        refuse("at home only")
    chests = loose()
    if not chests:
        print("yard chests: none")
        return 0
    from farmday import home_guard
    done = left = 0
    for h in chests:
        if "--dry" in sys.argv:
            cell = data("cell", dx=h["x"] - pc()["x"], dz=h["z"] - pc()["z"]).get("thingInfo") or []
            print(f"  {h['name']} at {h['x']},{h['z']}: lock {[t.get('lockLv') for t in cell if t.get('name') == h['name']]}")
            continue
        home_guard("the yard chests")
        walk(h["x"], h["z"], r=0, hp=60, timeout=30000)
        p = pc()
        if (p["x"], p["z"]) != (h["x"], h["z"]):
            print(f"  {h['name']} at {h['x']},{h['z']} not reached (at {p['x']},{p['z']})")
            left += 1
            continue
        info = here(h["name"])
        if not info:
            print(f"  {h['name']} at {h['x']},{h['z']}: gone")
            continue
        # run 43: a loose chest offers only Pick: no Pick Lock act (that's for installed ones). The pack route, as unlock.py does it
        if info.get("lockLv") and not have_pick() and bare_power() <= info["lockLv"]:
            print(f"  {h['name']} at {h['x']},{h['z']}: locked at {info['lockLv']}, no lockpick, bare power {bare_power()}: left here")
            left += 1
            continue
        out = run("act.py", "0", "0", f"Pick ({h['name']}")
        if out.rc:
            print(f"  {h['name']} at {h['x']},{h['z']}: no Pick act: {last(out)[:80]}")
            left += 1
            continue
        if info.get("lockLv"):
            out = run("unlock.py", "treasure chest", "6", timeout=300)
            print(f"  unlock: {last(out)[:90]}")
            if carried_lock():
                out = run("item.py", h["name"], "Drop")  # alone in the pack, so the first of the name is this one
                print(f"  {h['name']} at {h['x']},{h['z']}: still locked at {carried_lock() or info['lockLv']}: back on its cell ({last(out)[:40]})")
                left += 1
                continue
        out = run("chests.py", "--no-sort", timeout=300)
        print(out.strip())
        done += 1
        if out.rc:
            stop(f"chests.py stopped: {last(out)[:120]}")
    print(f"yard chests: {done} brought in, {left} left")
    return 0


if __name__ == "__main__":
    sys.exit(main())
