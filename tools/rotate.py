"""Set walls to a facing, using the game's own "Rotate block" (hold any wall item and
right-click an existing wall; each rotation steps blockDir 0 -> 1 -> 2 -> 0).

blockDir (from BaseTileMap): 0 = panel along the x axis, its decorated side facing z-1;
1 = panel along the z axis, decorated side facing x+1; 2 = both (a corner piece).

usage: python -I tools/rotate.py DIR X,Z [X,Z ...]
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import pc  # noqa: E402


def cell(x, z):
    p = pc()
    return call("cell", dx=x - p["x"], dz=z - p["z"])["data"]


def main():
    want = int(sys.argv[1])
    cells = [tuple(int(v) for v in a.split(",")) for a in sys.argv[2:]]
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    held = pc()["held"] or ""
    if "wall" not in held.lower():
        sys.exit(f"hold a wall item first (holding {held or 'nothing'})")
    for x, z in cells:
        c = cell(x, z)
        if not c.get("wall"):
            print(f"{x},{z}: not a wall ({c.get('block')})")
            continue
        for _ in range(4):
            if c["blockDir"] == want:
                break
            p = pc()
            acts = call("acts", dx=x - p["x"], dz=z - p["z"], mode="right")["data"]["acts"]
            rot = [a for a in acts if a["text"].startswith("Rotate")]
            if not rot:
                print(f"{x},{z}: no Rotate act ({[a['text'] for a in acts]})")
                break
            before = c["blockDir"]
            call("do", i=rot[0]["i"])
            for _ in range(10):
                time.sleep(0.6)
                c = cell(x, z)
                if c["blockDir"] != before:
                    break
        print(f"{x},{z}: blockDir {c['blockDir']}{' crossWall' if c.get('crossWall') else ''}")


if __name__ == "__main__":
    main()
