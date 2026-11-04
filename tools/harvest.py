"""Harvest one cell with the held tool, then pick up what dropped there.

Runs the game's own "Collect"/harvest act on the cell at map delta DX,DZ (the
task walks there itself), waits until the drops appear or the player stands
still, then uses the cell's own "Pick"/"Pick all" act. Stops on any dialog,
a hostile in view, or SP below the floor.

usage: python -I tools/harvest.py DX DZ [min_sp] [--force] [--weak-ok]
--weak-ok: go on with hostiles 3+ levels below me in view (the user, run 19, in a harvest job:
"Range attack or ignore"; a Lv1 rat stopped every harvest)
Refuses a growing plant that isn't ripe (--force to override). "Ripe" can still be past its
best: "It is too shriveled to be of any use!" (run 05, wild berries and crims at home).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import THRESHOLDS, pack_full, state, walk  # noqa: E402

# harvestjob.py sets this True in process (its --weak-ok): hostiles 3+ levels below me don't stop
# the walk or the harvest. The command line's --weak-ok does the same for a subprocess.
WEAK_OK = False

# Plants picked for a crop (GrowSystem.CanHarvest), where an unripe or second harvest destroys
# the plant. Weeds and trees also have growth stages but are cut, never "ripe": not guarded.
FRUITING = ("berry", "crim", "api", "bamboo", "mushroom", "imo", "potato", "cabbage", "carrot",
            "wheat", "rice", "tomato", "pumpkin", "eggplant", "onion", "corn", "melon", "radish",
            "strawberry", "grape", "cotton", "flax", "herb", "lettuce", "garlic", "pepper")

# harvest() outcomes
DONE, NO_ACT, LOW_SP, INTERRUPTED = "done", "no_act", "low_sp", "interrupted"


def weak_ok():
    return WEAK_OK or "--weak-ok" in sys.argv


def at_home(s):
    """The home map (Zone_startSite...): its walks need no hostile radius or HP floor."""
    return str((s.get("zone") or {}).get("full") or "").startswith("Zone_startSite")


def harvest(dx, dz, min_sp=3, say=print, force=False):
    """Harvest the cell at (dx, dz) from the player and pick up the drops. Returns an outcome.
    force=True takes an unripe fruit plant too (clear.py: destroying it is the point, run 10)."""
    s = state()
    pc = s["pc"]
    if pc["sp"] < min_sp:
        say(f"SP {pc['sp']} is below {min_sp}: rest first")
        return LOW_SP
    tx, tz = pc["x"] + dx, pc["z"] + dz
    acts = call("acts", dx=dx, dz=dz, mode="right")["data"]["acts"]
    pick = [a for a in acts if a["act"] in ("TaskHarvest", "TaskMine") or a["text"].startswith(("Collect", "Mine"))]  # vine bushes, wrecks: "Collect (Normal/Hard)"; run 18: walls "Mine (Easy)"
    if not pick and max(abs(dx), abs(dz)) > 1:
        # Out of sight (night) or no path from here: walk next to it and look again.
        ax, az = tx - (1 if dx > 0 else -1 if dx < 0 else 0), tz - (1 if dz > 0 else -1 if dz < 0 else 0)
        # off the home map the walk keeps walkto's stops (the review of 2026-10-23, errors row 21:
        # r=0, hp=0 let a foe arrive mid-walk unseen until the task poll started)
        rad, floor = (0, 0) if at_home(s) else (4, THRESHOLDS["walk_hp"])
        w = walk(ax, az, r=rad, hp=floor, timeout=30000, weak_ok=weak_ok())
        if w.get("why") in ("hostile", "hp", "window", "water", "zone"):
            say(f"stopped: the walk to {tx},{tz} ended: {w.get('why')} {w.get('hostile') or w.get('water') or ''}")
            return INTERRUPTED
        pc = state()["pc"]
        dx, dz = tx - pc["x"], tz - pc["z"]
        acts = call("acts", dx=dx, dz=dz, mode="right")["data"]["acts"]
        pick = [a for a in acts if a["act"] in ("TaskHarvest", "TaskMine") or a["text"].startswith(("Collect", "Mine"))]  # vine bushes, wrecks: "Collect (Normal/Hard)"; run 18: walls "Mine (Easy)"
    if not pick:
        say(f"no harvest act at {tx},{tz}: " + ", ".join(a["text"] for a in acts))
        return NO_ACT
    c0 = call("cell", dx=dx, dz=dz)["data"]
    obj = c0.get("obj")
    # A growing plant (crop, berry, crim, api) harvested when not ripe is destroyed for grass and
    # a branch, and so is one harvested twice (run 05: an api lost to a second run). Vine bushes
    # and wrecks have no growth stage and are left alone.
    fruiting = obj and "tree" not in obj and any(w in obj for w in FRUITING)
    if fruiting and c0.get("ripe") is not True and not force and "--force" not in sys.argv:
        say(f"{obj} at {tx},{tz} is not ripe (stage {c0.get('growStage')}): refusing (--force to override)")
        return NO_ACT
    call("do", i=pick[0]["i"])
    say(f"harvesting {obj} at {tx},{tz}")
    last, still = None, 0
    for _ in range(60):
        time.sleep(1.0)
        s = state()
        if s.get("drama") or (s.get("layers") or {}).get("top"):
            say(f"stopped: a dialog or window opened: {(s.get('layers') or {}).get('top')}")
            return INTERRUPTED
        lv = s["pc"].get("lv") or 0
        if any(c["hostile"] and not (weak_ok() and (c.get("lv") or 99) <= lv - 3)
               for c in s.get("nearby") or []):
            say("stopped: hostile in view")
            return INTERRUPTED
        pc = s["pc"]
        pos = (pc["x"], pc["z"], pc["turn"])
        still = still + 1 if pos == last else 0
        last = pos
        cell = call("cell", dx=tx - pc["x"], dz=tz - pc["z"])["data"]
        if cell.get("obj") != obj and still >= 2:
            break
        # A fruit plant stays the same object after its harvest (a berry stays a berry): stop when
        # I'm idle again (run 05: the loop waited out its 60 s and missed the drops)
        if still >= 2 and (pc["ai"] or "").startswith("NoGoal"):
            break
    pc = s["pc"]
    cell = call("cell", dx=tx - pc["x"], dz=tz - pc["z"])["data"]
    say(f"  cell now: obj {cell.get('obj')}, things {cell.get('things')}  SP {pc['sp']}/{pc['maxSp']}")
    if cell.get("things"):
        # run 12 (errors row 5): a pick-up into a full pack vanished; the drops stay on the cell
        if pack_full():
            say(f"  the pack is full ({THRESHOLDS['pack_max']}+ stacks): the drops stay at {tx},{tz}")
            return DONE
        acts = call("acts", dx=tx - pc["x"], dz=tz - pc["z"], mode="all")["data"]["acts"]
        picks = [a for a in acts if a["text"].startswith("Pick")]
        if picks:
            call("do", i=picks[-1]["i"])
            time.sleep(2.5)
    return DONE


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = [x for x in sys.argv[1:] if x not in ("--force", "--weak-ok")]
    r = harvest(int(a[0]), int(a[1]), int(a[2]) if len(a) > 2 else 3)
    sys.exit(0 if r == DONE else 1)


if __name__ == "__main__":
    main()
