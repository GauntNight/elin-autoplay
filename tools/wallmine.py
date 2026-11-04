"""Mine the dungeon walls around me with the pickaxe (run 14): a Machinarium's metal frames give a
scrap each (the blacksmith's table's binding material since run 05) for about 1 SP, and every
wall trains Mining (G11 wants Mining 10: the basalt pickaxe then opens the home's iron big rock).

usage: python -I tools/wallmine.py [N=20] [min_sp=10] [radius=6] [--kind metal]
Scans the cells within RADIUS for walls/blocks whose right-click offers "Collect", nearest first,
and harvests up to N of them (harvest.py: walks there, collects, picks up the drop). Stops (exit 3)
on a hostile in view, SP under the floor, a window, or a full pack; exit 0 when no wall is left;
exit 1 without a pickaxe. --kind keeps only blocks whose name has KIND. (minewalls.py is the
home practice loop; this one mines dungeon walls.)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, grab, pack_full, refuse, setup, stop, threat, top  # noqa: E402
from harvest import DONE, harvest  # noqa: E402


def candidates(radius, kind):
    pts = [[dx, dz] for dx in range(-radius, radius + 1) for dz in range(-radius, radius + 1) if dx or dz]
    out = []
    for p, c in zip(pts, call("cells", cells=pts)["data"]["cells"]):
        if c and c.get("block") and (not kind or kind in c["block"]) and not c.get("edge"):
            out.append((abs(p[0]) + abs(p[1]), p[0], p[1], c["cell"], c["block"]))
    return sorted(out)


def main():
    setup()
    nums = [int(a) for a in sys.argv[1:] if a.isdigit()]
    n = nums[0] if nums else 20
    min_sp = nums[1] if len(nums) > 1 else 10
    radius = nums[2] if len(nums) > 2 else 6
    kind = sys.argv[sys.argv.index("--kind") + 1] if "--kind" in sys.argv else ""
    if not grab("pickaxe", what="tool"):  # a whole word, never a cursed one (the review of 2026-10-23)
        refuse("no pickaxe in the pack")
    done, tried = 0, set()

    def report():
        log = call("state")["data"].get("log") or []
        print(f"mined {done}; " + " / ".join(l for l in log[-6:] if "pick up" in l.lower() or "skill" in l.lower()))
    while done < n:
        why = threat()
        if why:
            report()
            stop(why)
        if top():
            report()
            stop(f"window open ({top()})")
        p = call("state")["data"]["pc"]
        if p["sp"] < min_sp:
            report()
            stop(f"SP {p['sp']} under {min_sp}")
        if pack_full():  # run 12 (errors row 5): a pick-up into a full pack vanished
            report()
            stop("the pack is full: store or drop something first")
        here = (p["x"], p["z"])
        todo = [c for c in candidates(radius, kind) if c[3] not in tried]
        hit = None
        for _, dx, dz, cell, block in todo:
            tried.add(cell)
            acts = call("acts", dx=dx, dz=dz, mode="right")["data"]["acts"]
            if any(a["text"].startswith(("Collect", "Mine")) for a in acts):  # run 18: cave soil and rock blocks offer "Mine (Easy)"
                hit = (dx, dz, cell, block)
                break
        if not hit:
            print("no mineable wall left in reach")
            break
        out = harvest(hit[0], hit[1], min_sp=min_sp, say=lambda *_: None)
        p2 = call("state")["data"]["pc"]
        print(f"  {hit[3]} {hit[2]}: {out}  SP {p2['sp']}")
        if out == DONE:
            done += 1
    report()


if __name__ == "__main__":
    main()
