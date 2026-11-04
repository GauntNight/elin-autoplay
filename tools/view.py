"""Look at a spot of the map from a fixed vantage cell: walk there, capture the Elin
window (PrintWindow, window-only), crop around the target cell and save it zoomed.
Captures stay in runs/captures/ (gitignored).

usage: python -I tools/view.py VX,VZ TX,TZ [name] [--back]
  VX,VZ  vantage cell to stand on (walls near the player render cut away)
  TX,TZ  map cell to center the crop on
  --back walk back to where you started afterwards
"""
import sys
import time
from pathlib import Path

from PIL import Image, ImageEnhance

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import run, walk as common_walk  # noqa: E402
from bridge import call, close  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CAP = ROOT / "runs" / "captures"
# Screen offset per map step at default zoom, measured on run 03's captures:
# +x moves the image down-right, +z up-right (isometric).
STEP_X = (64, 32)
STEP_Z = (64, -32)


def walk(x, z):
    """Walk with the bridge's walkto (run 12 review); returns the player's state afterwards."""
    common_walk(x, z, r=0, hp=0, timeout=30000)
    return call("state")["data"]["pc"]


def main():
    vx, vz = (int(v) for v in sys.argv[1].split(","))
    tx, tz = (int(v) for v in sys.argv[2].split(","))
    name = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else "view"
    start = call("state")["data"]["pc"]
    p = walk(vx, vz)
    time.sleep(1.5)  # let the camera settle
    close()
    full = CAP / "full.png"
    out = run("elin_eye.py", str(full), "--width", "0")
    if out.rc != 0:
        sys.exit("capture failed: " + out)
    im = Image.open(full)
    w, h = im.size
    dx, dz = tx - p["x"], tz - p["z"]
    cx = w // 2 + dx * STEP_X[0] + dz * STEP_Z[0]
    cy = h // 2 + dx * STEP_X[1] + dz * STEP_Z[1] - 60
    box = (max(0, cx - 320), max(0, cy - 240), min(w, cx + 320), min(h, cy + 240))
    out = CAP / f"{name}.png"
    ImageEnhance.Brightness(im.crop(box).resize(((box[2] - box[0]) * 3 // 2, (box[3] - box[1]) * 3 // 2),
                                                Image.NEAREST)).enhance(1.4).save(out)
    print(out, "from", (p["x"], p["z"]), "target", (tx, tz))
    if "--back" in sys.argv:
        walk(start["x"], start["z"])


if __name__ == "__main__":
    main()
