"""Replace a building's walls with another wall item, keeping each wall's facing (G30 M1, run 31: the Residence's grass
walls to oak plank). The game won't place a wall onto a wall (the cell offers only "Rotate block"), so for each cell:
note its blockDir, mine the old wall with the pickaxe (my own land: no crime), place the new wall through place.py's
right-click Place, and turn it back to the old facing with Rotate (rotate.py's loop). The mined walls drop on the
ground: pick them up afterwards (loot.py, or ship them).

usage: python -I tools/rewall.py WALL X,Z [X,Z ...] [--pickaxe NAME] [--dry]
  WALL     the wall item to place (e.g. "plank walls"); doors are skipped (a door cell is left as it is)
Stops (exit 3) on a cell it couldn't mine or place, with the cells done so far; HP, a hostile or a window stop it too
(common.ready). Exit 0 when every cell holds the new wall at its old facing.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import THRESHOLDS, grab, pc, ready, refuse, stop, wait_idle, walk_beside  # noqa: E402


def cell(x, z):
    p = pc()
    return call("cell", dx=x - p["x"], dz=z - p["z"])["data"]


def act(x, z, prefix, mode="right"):
    p = pc()
    acts = call("acts", dx=x - p["x"], dz=z - p["z"], mode=mode)["data"]["acts"]
    hit = [a for a in acts if a["text"].startswith(prefix)]
    if not hit:
        return [a["text"] for a in acts]
    call("do", i=hit[0]["i"])
    wait_idle(20000)
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        sys.exit(__doc__)
    wall, pts = args[0], [tuple(int(v) for v in a.split(",")) for a in args[1:]]
    pick = sys.argv[sys.argv.index("--pickaxe") + 1] if "--pickaxe" in sys.argv else "steel pickaxe"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    done = []
    for x, z in pts:
        c = cell(x, z)
        if c.get("door"):
            print(f"{x},{z}: a door, skipped")
            continue
        if not c.get("wall"):
            print(f"{x},{z}: no wall here ({c.get('block')}): placing only")
        want, old = c.get("blockDir") or 0, c.get("block")
        if "--dry" in sys.argv:
            print(f"{x},{z}: {old} dir {want}")
            continue
        why = ready(hp=THRESHOLDS["walk_hp"])
        if why:
            stop(f"{why} (done: {done})")
        w = walk_beside(x, z)
        if not w.get("done"):
            stop(f"the walk to {x},{z} ended: {w.get('why')} (done: {done})")
        if c.get("wall"):
            if not grab(pick):
                refuse(f"no {pick!r} in the pack")
            miss = act(x, z, "Mine")
            if miss is not None:
                stop(f"{x},{z}: no Mine act ({miss}) (done: {done})")
            if cell(x, z).get("wall"):
                stop(f"{x},{z}: the wall still stands after Mine (done: {done})")
        # run 31: the last of "24 plank walls" is "a plank wall", which the plural no longer matches
        if not (grab(wall) or grab(wall[:-1] if wall.endswith("s") else wall + "s")):
            refuse(f"no {wall!r} in the pack (done: {done}; {x},{z} is open now)")
        miss = act(x, z, "Place")
        c = cell(x, z)
        if miss is not None or not c.get("wall"):
            stop(f"{x},{z}: the new wall didn't go in ({miss}); the cell is open now (done: {done})")
        for _ in range(4):  # rotate.py's loop: each Rotate steps 0 -> 1 -> 2 -> 0
            if c.get("blockDir") == want:
                break
            before = c.get("blockDir")
            if act(x, z, "Rotate") is not None:
                break
            for _ in range(10):
                time.sleep(0.4)
                c = cell(x, z)
                if c.get("blockDir") != before:
                    break
        done.append(f"{x},{z}")
        print(f"{x},{z}: {old} -> {c.get('block')} ({c.get('blockMat')}), dir {c.get('blockDir')} (was {want})")
    print(f"replaced {len(done)} walls")


if __name__ == "__main__":
    main()
