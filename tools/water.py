"""Water the home field once (run 10): take the can from its box if needed, refill it at the lake
when it holds fewer charges than the field has cells (TaskWater spends one charge a cell), "Water
crops", and put the can back in the tool box. Water after 06:00: the next morning's growth tick is
doubled (+10 instead of +5) on watered cells, and the flag clears after each tick.

The iron can holds 17 charges and the field grew past that (run 10: the pasture row and the second
imo, last in the walk, lagged a stage behind the tomatoes). --extra refills the can and waters the
listed cells one by one with "Water" (a field watered today offers only the single-cell act).

Rain (the user's rule, run 15: "raining means you don't need to water plants... everything is
already wet"): while it rains the game marks every unroofed farm-field cell watered (Zone.RainWater),
so nothing is watered, and the can stays in its box, when no field cell is dry.

usage: python -I tools/water.py [--keep] [--extra X,Z [X,Z ...]]   (--keep leaves the can in the pack)
The field is farmday.FIELD.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import last, wait_idle  # noqa: E402
from farmday import LAKE_STAND, LAKE_WATER, can_charges, dry_cells, run, state, walk, water  # noqa: E402

TOOL_BOX = "%d,%d" % __import__("home").FARM_BOX  # the Farm box (G12, run 11)


def refill():
    walk(*LAKE_STAND)
    p = state()["pc"]
    run("act.py", str(LAKE_WATER[0] - p["x"]), str(LAKE_WATER[1] - p["z"]), "Draw Water", "right")
    wait_idle(timeout=10000)


def extra(cells):
    run("item.py", "watering can", "Grab")
    run("close.py")
    refill()
    done = 0
    # the dry field cells among the listed ones, read once (the review of 2026-10-23: a cell call per
    # listed cell after dry_cells() had read them all); a sign, a tree or grass inside the rectangle
    # is not a field cell, and "Water" on a watered cell spends a charge and SP again (run 12, the user)
    todo = set(dry_cells(cells))
    for x, z in cells:
        if (x, z) not in todo:
            continue
        # run 12 (the user saw 6 dry cells): the can ran dry after 11 of 25 cells and the rest
        # got nothing; go back to the lake whenever it's empty and carry on
        if not can_charges():
            refill()
        walk(x, z - 1)
        p = state()["pc"]
        out = run("act.py", str(x - p["x"]), str(z - p["z"]), "Water", "right")
        wait_idle(timeout=8000)  # the watering task ends on its own (was a 10 x 0.8 s poll)
        done += "no act" not in out
    run("item.py", "watering can", "Put away")
    run("close.py")
    return f"second pass: {done}/{len(cells)} cells; can {can_charges()} charges"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    cells = []
    if "--extra" in a:
        cells = [tuple(map(int, c.split(","))) for c in a[a.index("--extra") + 1:] if "," in c]
    dry = dry_cells(cells)
    if not dry:
        print("water: skipped, the field is already wet (rain waters every unroofed field cell)")
        return
    if can_charges() is None:
        print(last(run("box.py", TOOL_BOX, "--take", "watering can")))
    print(water())
    if cells:
        print(extra(cells))
    if "--keep" not in a:
        print(last(run("box.py", TOOL_BOX, "watering can")))


if __name__ == "__main__":
    main()
