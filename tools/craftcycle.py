"""Train Blacksmith and Carpentry to their targets at home (run 42, G48 M2): repeats a cheap recipe on plentiful materials, eats, sleeps, again. Measured at Blacksmith 4, potential 242:
Bolt (1 scrap, 2 SP) pays 12 exp a SP; at Carpentry 6, potential 300: the sawmill (a log, 1 SP) pays 18 exp a SP; then desks (4 planks, 3 SP, ~10 exp a SP at 8). Every step has home_guard's stops (run 41) and a failed meal is a stop.

usage: python -I tools/craftcycle.py [--blacksmith N] [--carpentry N] [--cycles N] [--floor SP]   defaults 8, 12, 12 cycles, floor 12
Exit 0 targets reached or the cycles run, 3 stopped (a hostile above my level, HP, hunger with no meal, materials out, a tool's stop).
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data, pc, run, setup, state, stop, walk_beside  # noqa: E402
from farmday import home_guard  # noqa: E402
from home import FODDER_BOX, STATIONS, WOOD_BOX, BOX_STR, PARTS_BOX  # noqa: E402

TABLE = STATIONS["blacksmith's table"]
SAW = STATIONS["sawmill"]
LOG = re.compile(r"^(\d+|an?) (\w+ )*?logs?$")
SKIP_LOG = re.compile(r"carbon|feywood", re.I)  # carbon logs make blankets; feywood is rare


def skill(name):
    row = (data("skills").get("skills") or {}).get(name) or {}
    return row.get("lv", 0), row.get("exp", 0), row.get("potential", 0)


def need_meal():
    h = (state().get("pc") or {}).get("hunger")
    return isinstance(h, (int, float)) and h >= 45


def beside(xy):
    w = walk_beside(xy[0], xy[1], weak_ok=True)
    if not w.get("done"):
        stop(f"the walk to {xy} ended: {w.get('why')}")
    p = pc()
    return xy[0] - p["x"], xy[1] - p["z"]


def bolts(sp, floor):
    n = (sp - floor) // 2
    if n < 1:
        return
    dx, dz = beside(TABLE)
    out = run("craft.py", str(dx), str(dz), "Bolt", str(min(n, 40)), "--use", "scraps", timeout=300)
    run("hotbar.py", "--deselect", timeout=30)
    run("close.py", timeout=30)
    if out.rc:
        stop(f"Bolt: rc {out.rc}: {str(out)[-160:]}")


def logs_in_box():
    box = next(b for b in data("stock")["boxes"] if (b["x"], b["z"]) == tuple(FODDER_BOX))
    return [i["name"] for i in box["items"] if LOG.match(i["name"]) and not SKIP_LOG.search(i["name"])]


def saw(sp, floor):
    room = sp - floor
    if room < 1:
        return
    have = [i["name"] for i in data("inv")["items"] if LOG.match(i["name"]) and not SKIP_LOG.search(i["name"])]
    if not have:
        boxed = logs_in_box()
        if not boxed:
            stop("no logs left in the fodder box")
        out = run("box.py", BOX_STR(FODDER_BOX), "--take", boxed[0], timeout=120)
        if out.rc:
            stop(f"box.py --take {boxed[0]}: rc {out.rc}")
        have = [i["name"] for i in data("inv")["items"] if LOG.match(i["name"]) and not SKIP_LOG.search(i["name"])]
        if not have:
            stop("took logs and found none in the pack")
    stack = have[0]
    m = re.match(r"(\d+)", stack)
    size = int(m.group(1)) if m else 1
    dx, dz = beside(SAW)
    args = ["convert.py", str(dx), str(dz), "Saw", "--sp-each", "1"]
    if size > room:
        args += ["--max", str(room)]
    out = run(*args, stack, timeout=300)
    if out.rc:
        stop(f"sawing {stack}: rc {out.rc}: {str(out)[-160:]}")
    planks = [i["name"] for i in data("inv")["items"] if "plank" in i["name"]]
    if planks:
        run("box.py", BOX_STR(WOOD_BOX), *planks, timeout=120)


def wood_scrap(sp, floor):
    """Logs in the wood box: the carpenter's Scrap, 1 log and 4 SP, pays the most Carpentry a log (run 42) and makes the Blacksmith's scrap. False when there are none."""
    room = (sp - floor) // 4
    if room < 1:
        return False
    box = next(b for b in data("stock")["boxes"] if (b["x"], b["z"]) == tuple(WOOD_BOX))
    stacks = []
    for i in box["items"]:
        m = re.match(r"(\d+|an?) (\w+) logs?$", i["name"])
        if m and m.group(2) not in ("carbon", "feywood"):
            stacks.append((int(m.group(1)) if m.group(1).isdigit() else 1, m.group(2)))
    if not stacks:
        return False
    size, wood = max(stacks)
    dx, dz = beside(STATIONS["carpenter's table"])
    out = run("craft.py", str(dx), str(dz), "Scrap", str(min(room, size)), "--use", wood, timeout=300)
    run("hotbar.py", "--deselect", timeout=30)
    run("close.py", timeout=30)
    if out.rc:
        stop(f"Scrap: rc {out.rc}: {str(out)[-160:]}")
    return True


def desks(sp, floor):
    """No logs left: the carpenter's table. A desk is 4 planks and 3 SP, about 10 exp a SP at Carpentry 8 and 1.6 weight (run 42)."""
    room = (sp - floor) // 3
    if room < 1:
        return False
    box = next(b for b in data("stock")["boxes"] if (b["x"], b["z"]) == tuple(WOOD_BOX))
    stacks = []
    for i in box["items"]:
        m = re.match(r"(\d+) (\w+) planks?$", i["name"])
        if m and int(m.group(1)) >= 4:
            stacks.append((int(m.group(1)), m.group(2)))
    if not stacks:
        stop("no planks left in the wood box")
    size, wood = max(stacks)
    n = min(room, size // 4)
    dx, dz = beside(STATIONS["carpenter's table"])
    out = run("craft.py", str(dx), str(dz), "Desk", str(n), "--use", wood, timeout=300)
    run("hotbar.py", "--deselect", timeout=30)
    run("close.py", timeout=30)
    if out.rc:
        stop(f"Desk: rc {out.rc}: {str(out)[-160:]}")
    return True


def main():
    setup()
    args = sys.argv[1:]

    def opt(name, default):
        return int(args[args.index(name) + 1]) if name in args else default
    want_b, want_c, cycles, floor = opt("--blacksmith", 8), opt("--carpentry", 12), opt("--cycles", 12), opt("--floor", 12)
    for cycle in range(1, cycles + 1):
        home_guard("the craft cycle")
        p = pc()
        b, c = skill("blacksmith"), skill("carpentry")
        print(f"cycle {cycle}: SP {p.get('sp')}, hunger {p.get('hunger')}, Blacksmith {b}, Carpentry {c}")
        if b[0] >= want_b and c[0] >= want_c:
            print("both targets reached")
            return 0
        sp = p.get("sp", 0)
        if sp > floor + 3:
            if b[0] < want_b:
                bolts(sp, floor)
            else:
                for _ in range(5):  # stacks of logs are small: go on until the SP is used
                    if wood_scrap(pc().get("sp", 0), floor):
                        pass
                    elif logs_in_box() or any(LOG.match(i["name"]) and not SKIP_LOG.search(i["name"]) for i in data("inv")["items"]):
                        saw(pc().get("sp", 0), floor)
                    elif not desks(pc().get("sp", 0), floor):
                        break
                    if pc().get("sp", 0) <= floor + 3 or skill("carpentry")[0] >= want_c:
                        break
            p = pc()
        if p.get("sp", 0) <= floor + 12:
            while need_meal():
                out = run("eat.py", timeout=120)
                if out.rc:
                    stop(f"no meal: {str(out)[-120:]}")
            out = run("sleep.py", "--home-ok", timeout=180)
            if out.rc:
                stop(f"sleep.py: rc {out.rc}: {str(out)[-160:]}")
            time.sleep(0.5)
    print(f"cycles done: Blacksmith {skill('blacksmith')}, Carpentry {skill('carpentry')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
