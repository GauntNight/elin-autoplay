"""Take a stairway by stepping into it from the cell beside it (run 33, the user's tip at the Vernis mine
entrance: "you just had to click on the entrance ... basically walk in to it"). A walkto onto the cell and
an act Wait there did nothing, and a TraitMineEntrance lists no Enter act; a bridge `step` into the cell
takes any stairway (nefia stairs both ways, the mine entrance). The first step is sometimes swallowed:
three tries. Never from the stairway cell itself (step off first: a Wait there is a turn, not the stairs).

usage: python -I tools/stairs.py down|up
Exit 0 (the zone changed, printed before -> after), 1 refused (no such stairway known), 3 stopped (a
hostile within 4, HP under 70%, a window, or the zone didn't change).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, data, pc, ready, refuse, state, stop, wait_until, walk, walk_beside  # noqa: E402

TRAITS = {"down": ("TraitStairsDown", "TraitMineEntrance"), "up": ("TraitStairsUp",)}


def zone_full():
    return (state().get("zone") or {}).get("full")


def known(kind):
    """The installed stairways of that kind on the explored map, nearest first."""
    hits = data("find", name="stair", r=999, n=20).get("hits") or []
    hits += data("find", name="mine entrance", r=999, n=5).get("hits") or [] if kind == "down" else []
    p = pc()
    out = [h for h in hits if h.get("installed") and h.get("trait") in TRAITS[kind]]
    return sorted(out, key=lambda h: max(abs(h["x"] - p["x"]), abs(h["z"] - p["z"])))


def step_into(x, z, tries=3):
    """Stand beside (x, z) and step into it until the zone changes. True on a zone change."""
    p = pc()
    if (p["x"], p["z"]) == (x, z):  # on the stairway: off to any free plain cell first
        for dx, dz in ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            c = call("cell", dx=dx, dz=dz).get("data") or {}
            if not c.get("blocked") and not c.get("water") and not c.get("things"):
                call("step", dx=dx, dz=dz)
                wait_until("frames", n=10, timeout=2000)
                break
        p = pc()
    if max(abs(p["x"] - x), abs(p["z"] - z)) > 1:
        walk_beside(x, z, weak_ok=True)
        p = pc()
    if max(abs(p["x"] - x), abs(p["z"] - z)) > 1:
        return False
    before = zone_full()
    for _ in range(tries):
        call("step", dx=x - p["x"], dz=z - p["z"])
        wait_until("zone", timeout=4000)
        if zone_full() != before:
            return True
        p = pc()
    return False


def take(kind):
    """Take the nearest known stairway of that kind; True when the zone changed."""
    hs = known(kind)
    if not hs:
        return False
    return step_into(hs[0]["x"], hs[0]["z"])


def main():
    kind = next((a for a in sys.argv[1:] if a in TRAITS), None)
    if not kind:
        refuse("usage: stairs.py down|up")
    why = ready(hp=70, hunger=None, hostile_r=4)
    if why:
        stop(why)
    if not known(kind):
        refuse(f"no known stairway {kind} on this map (explore first)")
    before = zone_full()
    if not take(kind):
        stop(f"the step into the stairway {kind} changed nothing: look.py")
    print(f"{before} -> {zone_full()}")


if __name__ == "__main__":
    main()
