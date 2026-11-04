"""Move installed furniture: the game's right-click "Grab" on the source cell (home furniture),
then place.py on the target cell (G12, run 18: stations and boxes into their houses).
A container keeps its contents when grabbed, so a full box can make me Burdened for the walk.

usage: python -I tools/move.py FX,FZ TX,TZ [NAME] [FX,FZ TX,TZ [NAME] ...]
  NAME  part of the thing's name when the source cell holds more than one installed thing
  e.g.  python -I tools/move.py 58,40 47,60 loom 58,41 49,60 spinner
Each pair walks beside the source, grabs, walks to the target (inside a walled house: through
its door) and places. Stops at the first failure (exit 3) and says what is in hand.
After moving a station or a box, update tools/home.py (and the skills' tables) in the same session.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, cells, pc, run, setup, stop, wait_idle, walk_beside  # noqa: E402


def grab(x, z, name=None):
    """Grab the installed thing at (x, z) into the pack; returns its name (no article)."""
    r = walk_beside(x, z, weak_ok=True)
    if not r.get("done") and r.get("why") not in ("arrived",):
        stop(f"can't reach {x},{z}: {r.get('why')}")
    p = pc()
    acts = call("acts", dx=x - p["x"], dz=z - p["z"], mode="right")["data"]["acts"]
    grabs = [a for a in acts if a["text"].startswith("Grab (")]
    if name:
        grabs = [a for a in grabs if name.lower() in a["text"].lower()]
    if len(grabs) != 1:
        stop(f"{x},{z}: {len(grabs)} Grab acts match {name!r}: {[a['text'] for a in acts]}")
    text = grabs[0]["text"]
    call("do", i=grabs[0]["i"])
    wait_idle(10000)
    thing = re.sub(r"^Grab \((an? |the )?", "", text).rstrip(")")
    after = cells([(x, z)])[(x, z)]
    if any(thing in t for t in after.get("things") or []):
        stop(f"{x},{z}: {thing} is still there after Grab")
    return thing


def main(argv):
    setup()
    args = list(argv)
    moves = []
    while args:
        if len(args) < 2 or "," not in args[0] or "," not in args[1]:
            stop(f"expected FX,FZ TX,TZ [NAME]: {args}")
        src = tuple(int(v) for v in args.pop(0).split(","))
        dst = tuple(int(v) for v in args.pop(0).split(","))
        name = args.pop(0) if args and "," not in args[0] else None
        moves.append((src, dst, name))
    for (fx, fz), (tx, tz), name in moves:
        thing = grab(fx, fz, name)
        out = run("place.py", thing, f"{tx},{tz}", timeout=300)
        line = [ln for ln in out.splitlines() if "->" in ln]
        print(f"{thing}: {fx},{fz} -> {tx},{tz}: {line[-1].split(': ', 1)[-1] if line else out.strip()}")
        if "placed" not in out:
            stop(f"{thing} not placed at {tx},{tz}; held: {pc()['held']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
