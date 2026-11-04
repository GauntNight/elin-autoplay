"""Clear wild plants off the home map to bring the soil back under its limit (G3, run 05).

The home board's Fertility is MaxSoil minus the soil cost of every object on the map (Zone.
GetSoilCost: costSoil / 10 for each cell). Above the limit every crop harvest loses
rnd(2 + overage / 20) items (GrowSystem.PopHarvest), so a farm needs the land cleared first.
Soil cost per object (objs table): weed 1, white or yellow flower 1, berry 1, bamboo 1, crim 2,
api 2, mushroom 2, green/blue/red grass 2, trees 0.5, imo 3. Weeds also give grass (weed stew).

usage: python -I tools/clear.py OBJECT [N=20] [min_sp=8] [radius=60] [--tool NAME] [--skip X0,Z0,X1,Z1]
  e.g. python -I tools/clear.py "white flower" 30 --tool "woodcutter's axe"
--tool holds that pack item first. --skip leaves a box alone (the field: mushrooms are planted
there too, run 10). Only objects inside the zone's bounds are taken (run 10: the map holds ten
times more plants outside them, and they cost no soil), unripe fruit plants included. Any held tool speeds plant work by its material's hardness
(BaseTaskHarvest: toolLv += hardness; run 05: iron axe 5 flowers in 13 game minutes, bare hands
9 minutes for one). Only the soil inside zone.bounds counts; plants outside it are "edge".
Harvests up to N objects named OBJECT, nearest first, skipping the map edge (only "Enter" there)
and anything that gives no harvest act. Stops at the SP floor, on a hostile or a window.
Drops are picked up; food goes to the Cooler Box afterwards by hand (bag.py).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call, close  # noqa: E402
from common import grab, matches, pc, ready, refuse, stop  # noqa: E402
from gather import nearest  # noqa: E402
from harvest import DONE, LOW_SP, INTERRUPTED, harvest  # noqa: E402

COST = {"weed": 1, "white flower": 1, "yellow flower": 1, "berry": 1, "bamboo": 1, "crim": 2,
        "api": 2, "mushroom": 2, "green grass": 2, "blue grass": 2, "red grass": 2}


def take_tool(name):
    """Hold a pack item: empty the hotbar selection (a selected slot, e.g. the Putit after a
    throw, outranks a Grab; run 05), then common.grab (a whole-word match, cursed stacks skipped;
    in process, no item.py subprocess)."""
    if matches(name, [pc().get("held") or ""]):
        return
    from hotbar import deselect
    deselect()
    grab(name, what="tool")


def main():
    a = sys.argv[1:]
    why = ready(hp=None, hunger=None)  # a window, busy, a bad condition, a hostile in view
    if why:
        stop(why)
    if "--tool" in a:
        k = a.index("--tool")
        take_tool(a[k + 1])
        held = pc().get("held") or ""
        if not matches(a[k + 1], [held]):
            refuse(f"couldn't hold {a[k + 1]!r} (holding {held!r})")
        a = a[:k] + a[k + 2:]
    box = None
    if "--skip" in a:
        k = a.index("--skip")
        box = tuple(int(v) for v in a[k + 1].split(","))
        a = a[:k] + a[k + 2:]
    bounds = tuple(int(v) for v in call("state")["data"]["zone"]["bounds"].split(","))
    obj = a[0]
    n = int(a[1]) if len(a) > 1 else 20
    min_sp = int(a[2]) if len(a) > 2 else 8
    r = int(a[3]) if len(a) > 3 else 60
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p0 = call("state")["data"]["pc"]
    skip, done, why = set(), 0, f"{n} cleared"
    quiet = lambda *_: None  # noqa: E731
    while done < n:
        t = nearest(obj, r, skip, ripe_only=False, inside=bounds, outside=box)
        if not t:
            why = f"no reachable {obj} left within {r}"
            break
        _, dx, dz, x, z = t
        out = harvest(dx, dz, min_sp, say=quiet, force=True)
        if out == DONE:
            c = call("cell", dx=x - call("state")["data"]["pc"]["x"], dz=z - call("state")["data"]["pc"]["z"])["data"]
            if c.get("obj") and obj in c["obj"]:
                skip.add((x, z))  # still standing (a fruit plant keeps its object): don't count it
            else:
                done += 1
        elif out in (LOW_SP, INTERRUPTED):
            why = "SP floor" if out == LOW_SP else "interrupted (hostile or window)"
            break
        else:
            skip.add((x, z))
    p = call("state")["data"]["pc"]
    soil = COST.get(obj, 0) * done
    print(f"cleared {done} {obj} (soil -{soil}); SP {p0['sp']} -> {p['sp']}; "
          f"{p0['date']} -> {p['date']}; stopped: {why}")
    if why.startswith("interrupted"):  # a hostile or a window: the caller decides (exit 3)
        sys.exit(3)


if __name__ == "__main__":
    main()
