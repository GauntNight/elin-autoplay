"""Cut wood on a field map for a craft push (run 42, G48: Carpentry needs about 70 logs at potential 145; a forest tile beside home gives a log and two branches a tree, 0.5 SP, about 9 real
seconds; the map is fog until walked, so it alternates gather.py and explore.py). Logs go into the haul bag, where purge can't drop them; branches past the cap are dropped.

usage: python -I tools/woodrun.py LOGS [--minutes M=8] [--min-sp 30]
Stops at LOGS held in all (pack and bags), the time, SP under the floor, Hungry (a meal first, a failed meal is a stop), or a hostile it can't fight (common.ready's reasons).
Exit 0 target or time reached, 1 refused (not on a field map, no axe), 3 stopped.
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data, last, pc, ready, refuse, run, setup, state, stop  # noqa: E402

LOG = re.compile(r"^(\d+|an?) (\w+ )*?logs?$")
BRANCH = re.compile(r"^(\d+|an?) (\w+ )*?branch(es)?$")


def held_logs():
    n = 0
    for i in data("stock")["pack"]:
        for x in [i] + list(i.get("items") or []):
            if LOG.match(x["name"]) and "carbon" not in x["name"]:
                n += x.get("num") or 1
    return n


def clear_pack():
    names = [i["name"] for i in data("inv")["items"] if LOG.match(i["name"]) and "carbon" not in i["name"]]
    if names:
        run("bag.py", "a haul bag", *names, timeout=120)
        run("close.py", timeout=30)
    for i in data("inv")["items"]:
        if BRANCH.match(i["name"]):
            run("item.py", i["name"], "Drop", timeout=60)


def main():
    setup()
    args = sys.argv[1:]
    nums = [a for i, a in enumerate(args) if a.isdigit() and (i == 0 or not args[i - 1].startswith("--"))]
    if not nums:
        refuse(__doc__.splitlines()[3])
    want = int(nums[0])
    minutes = float(args[args.index("--minutes") + 1]) if "--minutes" in args else 8
    floor = int(args[args.index("--min-sp") + 1]) if "--min-sp" in args else 30
    z = (state().get("zone") or {})
    if z.get("region") or "field" not in str(z.get("full")):
        refuse(f"a field map only: {z.get('full')}")
    end = time.time() + minutes * 60
    idle = 0
    while time.time() < end:
        have = held_logs()
        if have >= want:
            print(f"target: {have} logs")
            break
        p = pc()
        if p.get("sp", 0) < floor:
            stop(f"SP {p.get('sp')} under {floor}, {have} logs")
        if (p.get("hunger") or 0) >= 65:
            out = run("eat.py", timeout=120)
            if out.rc:
                stop(f"no meal at hunger {p.get('hunger')}: {last(out)[:80]}")
        foes = [c for c in state().get("nearby") or [] if c.get("hostile")]
        for f in foes[:3]:
            if (f.get("lv") or 99) > p.get("lv", 0) - 3:
                stop(f"{f.get('name')} Lv{f.get('lv')} in view, {have} logs")
            run("fight.py", f.get("id") or f["name"], timeout=180)
        in_pack = sum(i.get("num") or 1 for i in data("inv")["items"] if i.get("id") == "log")
        out = run("gather.py", "tree", "log", str(in_pack + min(want - have, 8)), str(floor), "40", "--weak-ok", timeout=240)
        run("hotbar.py", "--deselect", timeout=30)
        clear_pack()
        if held_logs() == have:
            idle += 1
            why = ready(hp=60, hunger=None, burden=None)
            if why and "hostile" in why:
                continue  # the top of the loop fights what's weak and stops on what isn't
            if why and "held" not in why:
                stop(f"not walking: {why}")
            ex = run("explore.py", "8", "60", timeout=240)
            if "no frontier left" in str(ex) or idle >= 6:
                print(f"this map is done: {have} logs ({last(ex)[:70]})")
                return 0
        else:
            idle = 0
        print(f"{held_logs()} logs; SP {pc().get('sp')}; {last(out)[:60]}", flush=True)
    print(f"done: {held_logs()} logs; SP {pc().get('sp')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
