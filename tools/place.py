"""Hold an inventory item and place it on absolute map cells, in order, through the game's
own right-click "Place" (TaskBuild). For each cell: if Place isn't offered, wait a turn (a
pet standing there) and then walk next to it; after placing, check the cell changed.
Doors go onto existing wall cells.

usage: python -I tools/place.py ITEM X,Z [X,Z ...] [--height N]
  e.g. python -I tools/place.py "grass wall" 59,51 59,52 59,53
       python -I tools/place.py "wall torch" 62,50 --height 7   (mounted up the wall, run 04)
--height sets the placement height the way the place helper's height button does (bridge 0.15.0
`altitude`): the Place preview gives build mode its recipe, then the height applies to it.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import grab, matches, pc, ready, run, stop, wait_until, walk_beside  # noqa: E402


HEIGHT = int(sys.argv[sys.argv.index("--height") + 1]) if "--height" in sys.argv else None


def take(name):
    """The item in hand through common.grab: a whole-word match ("wall" no longer takes a wall
    torch; two different names are refused), cursed stacks skipped. Run 18: with the pack at its
    stack limit, a crafted or swapped-out item lands in a carried bag, whose slots are listed only
    while it is open (two doors were "nothing left to hold"): the bags are opened one by one."""
    # run 31: the last of "12 plank floors" is "a plank floor", which the plural no longer matches
    alt = name[:-1] if name.endswith("s") else name + "s"
    if matches(name, [pc().get("held") or ""]) or matches(alt, [pc().get("held") or ""]):
        return True
    if grab(name) or grab(alt):
        return True
    for bag in ("loot bag", "spoils bag", "backpack", "haul bag"):
        run("bag.py", bag)
        if grab(name):
            return True
    return False


def cell_sig(x, z):
    p = pc()
    c = call("cell", dx=x - p["x"], dz=z - p["z"])["data"]
    # run 31: a floor (G30's plank floors) changes only the floor, which this used to miss ("did not change")
    return (c.get("block"), c.get("floor"), c.get("floorMat"), c.get("obj"), tuple(c.get("things") or []))


def noun(name):
    """"2 wall torches" / "a wall torch" -> "wall torch": what the placed thing's name holds."""
    n = re.sub(r"^(an?|the|\d+)\s+", "", name.lower()).split(" (")[0].split(" [")[0]
    return re.sub(r"(es|s)$", "", n)


def landed(name, before, after):
    """The cell took the item: its block, floor or obj changed, or a thing of that name is new there. Run 32:
    a resident's garbage dropped on 58,52 changed the things and a torch that never left the pack was "placed"."""
    if after[:4] != before[:4]:
        return True
    new = [t for t in set(after[4]) if after[4].count(t) > before[4].count(t)]
    return any(noun(name) in t.lower() for t in new)


def place_at(name, x, z):
    before = cell_sig(x, z)
    for attempt in range(6):
        if not take(name):
            return "nothing left to hold"
        p = pc()
        acts = call("acts", dx=x - p["x"], dz=z - p["z"], mode="right")["data"]["acts"]
        pl = [a for a in acts if a["text"] == "Place"]
        if pl:
            if HEIGHT is not None:
                cur = call("altitude", d=0)["data"]["altitude"]
                if HEIGHT != cur:
                    call("altitude", d=HEIGHT - cur)
            call("do", i=pl[0]["i"])
            for _ in range(10):
                wait_until("frames", n=10, timeout=1500)  # the build task takes a few turns
                if landed(name, before, cell_sig(x, z)):
                    return "placed"
            return "Place ran but the cell did not change"
        if attempt < 2:
            call("act", action="Wait")  # a pet or NPC may be standing there
            wait_until("frames", n=15, timeout=2000)
        else:
            # Out of sight or too far: walk to a free neighbour of the target (run 18: the old
            # fallback tried only the cell south of it, a wall when the target is inside a new
            # house, so cells behind fresh walls were never placed; walk_beside paths in by the door).
            walk_beside(x, z, r=0, hp=0, timeout=15000)
    return "no Place offered: " + ", ".join(a["text"] for a in acts)


def main():
    name = sys.argv[1]
    cells = [tuple(int(v) for v in a.split(",")) for a in sys.argv[2:] if "," in a]
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for x, z in cells:
        # a window, a context menu, busy, a bad condition, a hostile in view: a decision (exit 3)
        why = ready(hp=None, hunger=None, burden=None)
        if why:
            print("held now:", pc()["held"])
            stop(why)
        print(f"{name} -> {x},{z}: {place_at(name, x, z)}")
    print("held now:", pc()["held"])


if __name__ == "__main__":
    main()
