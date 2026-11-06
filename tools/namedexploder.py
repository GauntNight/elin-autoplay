"""Kill a NAMED exploder from range (runs 33 and 37: a named hot guy's death blast took 214 -> -342 and 216 -> -478; run 41: Misty
Grassland B2's 『Hot guy』 halted the ladder three times at 3 cells, and each hand-run answer took a teleport). The loop the rule asks for:
over 5 cells away, an arrow spell; closer, steps straight away from it; adjacent with no room, a teleport scroll. Run at speed x1.

usage: python -I tools/namedexploder.py [NAME="Hot guy"] [SPELL=arrow_Cold] [--rounds N=40] [--mp-floor N=12]
Exit 0 it's dead or out of view, 1 refused (no such foe in view), 3 stopped (MP at the floor, HP under 60%, a window).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import cells, last, matches, refuse, run, setup, state, stop, wait_until  # noqa: E402

SAFE = 5


def find(name):
    s = state()
    hits = matches(name, [c for c in s.get("nearby") or [] if c.get("hostile")], key="name")
    return (s, min(hits, key=lambda c: c.get("dist", 99))) if hits else (s, None)


def step_away(t, p):
    sx = -1 if t["dx"] > 0 else 1 if t["dx"] < 0 else 0
    sz = -1 if t["dz"] > 0 else 1 if t["dz"] < 0 else 0
    opts = [(sx, sz), (sx, 0), (0, sz)] if sx and sz else [(sx, sz), (sx, 1), (sx, -1)] if sx else [(sx, sz), (1, sz), (-1, sz)]
    info = cells([(p["x"] + dx, p["z"] + dz) for dx, dz in opts])
    for dx, dz in opts:
        c = info.get((p["x"] + dx, p["z"] + dz)) or {}
        if c.get("blocked") or c.get("water") or not c.get("floor"):
            continue
        call("step", dx=dx, dz=dz)
        wait_until("frames", n=5)
        return True
    return False


def main():
    setup()
    args = sys.argv[1:]
    pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or not args[i - 1].startswith("--"))]
    name = pos[0] if pos else "Hot guy"
    spell = pos[1] if len(pos) > 1 else "arrow_Cold"
    rounds = int(args[args.index("--rounds") + 1]) if "--rounds" in args else 40
    floor = int(args[args.index("--mp-floor") + 1]) if "--mp-floor" in args else 12
    s, t = find(name)
    if not t:
        refuse(f"no hostile {name!r} in view")
    call("speed", i=1)
    for _ in range(rounds):
        s, t = find(name)
        if not t:
            print(f"{name}: gone from view")
            return
        p = s["pc"]
        if (s.get("layers") or {}).get("top"):
            stop(f"a window is open: {s['layers']['top']}")
        if p["hp"] < 0.6 * p["maxHp"]:
            stop(f"HP {p['hp']}/{p['maxHp']}: heal or leave")
        if p["mp"] < floor:
            stop(f"MP {p['mp']}: at the floor with {name} at {t['dist']}")
        if t["dist"] <= 3:  # the rule: a teleport if it closes within 4 (it was only at 1: a kamikaze covers 2 cells a turn)
            print("  " + last(run("item.py", "scrolls of teleport", "Read")))
            run("close.py")
            continue
        if t["dist"] < SAFE and step_away(t, p):
            continue
        out = run("cast.py", spell, name, "1", "--mp-floor", str(floor))
        print(f"  {name} at {t['dist']} hp {t.get('hpPct', t.get('hp'))}: {last(out)[:90]}")
        if out.rc == 1:
            refuse(last(out))
    stop(f"{rounds} rounds and {name} still in view")


if __name__ == "__main__":
    main()
