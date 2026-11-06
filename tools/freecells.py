"""An ascii map of the home's cells, to pick where a big container fits (run 42, G47: a wagon is 2x2, a big wagon 4x4, and nothing
listed the free floor). '.' a free cell, '#' a wall or blocked, 'o' an object or a thing, '~' water, '+' tilled field.

usage: python -I tools/freecells.py [X0 X1 Z0 Z1]   default 40 72 35 66, north (high z) on top
Reads only. Exit 0.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import cells, setup  # noqa: E402


def mark(c):
    if not c:
        return "?"
    if c.get("blocked") or c.get("wall") or c.get("block"):
        return "#"
    if c.get("things") or c.get("obj"):
        return "o"
    f = str(c.get("floor") or "")
    if "water" in f or c.get("suffocate"):
        return "~"
    if "field" in f:
        return "+"
    return "."


def main():
    setup()
    a = [int(v) for v in sys.argv[1:5]] if len(sys.argv) >= 5 else [40, 72, 35, 66]
    x0, x1, z0, z1 = a
    pts = [(x, z) for z in range(z0, z1 + 1) for x in range(x0, x1 + 1)]
    got = cells(pts)
    print("      " + "".join(str((x // 10) % 10) for x in range(x0, x1 + 1)))
    print("      " + "".join(str(x % 10) for x in range(x0, x1 + 1)))
    for z in range(z1, z0 - 1, -1):
        print(f"z={z:<3} " + "".join(mark(got.get((x, z))) for x in range(x0, x1 + 1)))


if __name__ == "__main__":
    main()
