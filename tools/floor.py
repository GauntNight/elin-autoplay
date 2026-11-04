"""Lay a floor item on every cell of a room that doesn't have a wooden floor yet (G30 M1-M2, run 31), through
place.py's right-click Place. Rooms come from the bridge's `rooms` op (the game's own room detection), so
walls are skipped and so are cells that already carry the wanted floor material.

usage: python -I tools/floor.py ROOM [FLOOR_ITEM="plank floors"] [--mat oak] [--max N] [--dry]
  ROOM   a room name as town.py prints it (Workshop, Kitchen, Forge, Farmhouse, Storehouse, Depot, Residence)
  --mat  the floor material that counts as done (default: oak; a plank or wooden floor of another wood counts too)
Exit 0 when the room is done or N cells were laid; 1 refused (no such room, nothing to hold); 3 stopped (place.py).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import cells, refuse, run, stop  # noqa: E402


def todo(room, mat):
    r = [x for x in call("rooms")["data"]["rooms"] if (x.get("name") or "").lower() == room.lower()]
    if not r:
        refuse(f"no room named {room!r} (town.py lists them)")
    r = r[0]
    info = cells([(x, z) for x in range(r["x"], r["mx"] + 1) for z in range(r["z"], r["mz"] + 1)])
    done = lambda c: c.get("floorMat") == mat or "plank" in (c.get("floor") or "") or "wooden" in (c.get("floor") or "")
    return sorted(((x, z) for (x, z), c in info.items() if not c.get("wall") and not done(c)), key=lambda p: (p[1], p[0]))


def main():
    argv, args = sys.argv[1:], []
    for i, a in enumerate(argv):  # run 31: a flag's value ("--mat cedar") was taken for the item name
        if not a.startswith("--") and not (i and argv[i - 1] in ("--mat", "--max")):
            args.append(a)
    if not args:
        sys.exit(__doc__)
    room = args[0]
    item = args[1] if len(args) > 1 else "plank floors"
    mat = sys.argv[sys.argv.index("--mat") + 1] if "--mat" in sys.argv else "oak"
    cap = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else None
    pts = todo(room, mat)
    if cap is not None:
        pts = pts[:cap]
    print(f"{room}: {len(pts)} cells to floor")
    if "--dry" in sys.argv or not pts:
        print(" ".join(f"{x},{z}" for x, z in pts))
        return
    r = run("place.py", item, *[f"{x},{z}" for x, z in pts], timeout=1800)
    lines = [ln for ln in str(r).splitlines() if "placed" not in ln]
    print("\n".join(lines[-6:]))
    left = todo(room, mat)
    print(f"{room}: {len(left)} cells left without a wooden floor")
    if r.rc not in (0,):
        stop(f"place.py stopped (rc {r.rc})")


if __name__ == "__main__":
    main()
