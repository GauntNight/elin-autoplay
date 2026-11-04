"""Leave an ambush map through shallow water: step toward an edge one cell at a time and take its Enter.

Run 29: two sea ambushes in a row put me mid-lake (floor "water", Cell.CanSuffocate false: it only wets), and
leave.py stops at any water floor not named "shallow" (its run 07 / run 26 drowning rules), so it found no exit
twice; I stepped out by hand both times. This is that hand procedure: before every step the bridge's `cell`
must say suffocate false for the next cell (deep water drowns: run 19's death); it stops on a hostile in view,
on any HP lost in a step, on ConSuffocation (a step back first), and when a step doesn't move me.

usage: python -I tools/wade.py [DIR=nearest|w|e|n|s] [MAX_STEPS=20]
Exit 0 when it left the map, 3 stopped for a decision (hostile, deep water ahead, HP lost, blocked).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import setup, stop  # noqa: E402

DIRS = {"w": (-1, 0), "e": (1, 0), "s": (0, -1), "n": (0, 1)}


def enter_here(dx=0, dz=0):
    acts = call("acts", dx=dx, dz=dz, mode="all")["data"]["acts"]
    return next((a for a in acts if a["text"] == "Enter"), None)


def main():
    setup()
    a = sys.argv[1:]
    s = call("state")["data"]
    zone = s["zone"]["full"]
    x0, z0, x1, z1 = (int(v) for v in s["zone"]["bounds"].split(","))
    p = s["pc"]
    if a and a[0] in DIRS:
        d = DIRS[a[0]]
    else:
        d = min(((p["x"] - x0, DIRS["w"]), (x1 - p["x"], DIRS["e"]), (p["z"] - z0, DIRS["s"]), (z1 - p["z"], DIRS["n"])))[1]
    steps = int(a[1]) if len(a) > 1 else 20
    for i in range(steps):
        s = call("state")["data"]
        p = s["pc"]
        foes = [c for c in s.get("nearby") or [] if c.get("hostile")]
        if foes:
            stop(f"a hostile in view: {foes[0]['name']} Lv{foes[0]['lv']} at {foes[0]['dist']}")
        e = enter_here(*d)
        if e:
            call("do", i=e["i"])
            time.sleep(2)
            print(f"left {zone} -> {call('state')['data']['zone']['full']} after {i} steps")
            return
        c = call("cell", dx=d[0], dz=d[1])
        cd = c.get("data") or {}
        if not c.get("ok") or cd.get("suffocate") is not False:
            stop(f"the next cell ({p['x'] + d[0]},{p['z'] + d[1]}) is {'deep water' if cd.get('suffocate') else c.get('error') or 'unknown'}")
        call("step", dx=d[0], dz=d[1])
        time.sleep(0.6)
        p2 = call("state")["data"]["pc"]
        print(f"  {p['x']},{p['z']} -> {p2['x']},{p2['z']} ({cd.get('floor')})  HP {p2['hp']}")
        if "ConSuffocation" in (p2.get("conditions") or []):
            call("step", dx=-d[0], dz=-d[1])
            stop("suffocating after a step: stepped back")
        if p2["hp"] < p["hp"]:
            stop(f"HP {p['hp']} -> {p2['hp']} in a step")
        if (p2["x"], p2["z"]) == (p["x"], p["z"]):
            stop("the step didn't move me (blocked): try another direction")
    stop(f"no exit within {steps} steps")


if __name__ == "__main__":
    main()
