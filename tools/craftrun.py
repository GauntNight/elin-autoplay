"""A list of crafts at home's stations (run 42, G48: 30 first crafts): walks beside each station, checks the stamina, crafts one, and carries what it made to the shipping chest,
or to the yard's wagon when the chest is full, before the next, since crafted furniture Squashes (a locker 56 weight, run 42). Every step goes through farmday.home_guard (run 41).

usage: python -I tools/craftrun.py [--min-sp N] [--keep] [--ship] STATION:RECIPE[:USE] ...
       python -I tools/craftrun.py --min-sp 15 "blacksmith's table:Pipe" "mason's table:Sink:granite"
  --min-sp N  stop before a craft that would leave SP under N (default 12)
  --keep      leave what's made in the pack (materials, parts)
Prints each craft's SP, new items and the skill exp it paid. Exit 0 all done, 1 refused (no such station), 3 stopped (SP, a refused craft, a hostile through home_guard).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data, pc, refuse, run, setup, stop, walk_beside  # noqa: E402
from farmday import home_guard  # noqa: E402
from home import ARMORY5, BOX_STR, SHIPPING, STATIONS  # noqa: E402

CELLS = dict(STATIONS)
CELLS.update({"machine table": (49, 58), "tinker's table": (54, 58)})
OVERFLOW = BOX_STR(ARMORY5)  # the yard's wagon holds what the chest can't take today
NOT_MADE = re.compile(r"old ticket|orens|gold bar|platinum|medal", re.I)


def skills():
    return {k: (v.get("lv"), v.get("exp")) for k, v in (data("skills").get("skills") or {}).items()}


def names():
    """By id and uid-free count: a stack's name changes with its count (20 -> 15 iron ingots read as a new item once)."""
    out = {}
    for i in data("inv")["items"]:
        row = out.setdefault(i["id"], [0, i["name"]])
        row[0] += i.get("num") or 1
        row[1] = i["name"]
    return out


def ship(made):
    for name in made:
        full = len(data("stock").get("shipping") or []) >= 40
        out = run("box.py", OVERFLOW if full else "shipping chest", name)
        if out.rc or "did not move" in str(out):
            out = run("box.py", OVERFLOW, name)
            if out.rc or "did not move" in str(out):
                stop(f"{name}: no box took it")
        print(f"    {name} -> {'the wagon' if full else 'the shipping chest'}")


def main():
    setup()
    args = sys.argv[1:]
    floor = 12
    if "--min-sp" in args:
        i = args.index("--min-sp")
        floor = int(args[i + 1])
        del args[i:i + 2]
    keep = "--keep" in args
    args = [a for a in args if not a.startswith("--")]
    if not args:
        refuse(__doc__.splitlines()[3])
    done = 0
    for job in args:
        parts = job.split(":")
        station, recipe = parts[0], parts[1]
        use = parts[2] if len(parts) > 2 else None
        if station not in CELLS:
            refuse(f"no station '{station}' in home.STATIONS")
        home_guard("the crafts")
        x, z = CELLS[station]
        w = walk_beside(x, z, weak_ok=True)
        if not w.get("done"):
            stop(f"the walk to {station} ended: {w.get('why')}")
        p = pc()
        base = ["craft.py", str(x - p["x"]), str(z - p["z"]), recipe, "1"] + (["--use", use] if use else [])
        dry = run(*base, "--dry", timeout=60)
        m = re.search(r"stamina (\d+)", str(dry))
        if dry.rc or not m:
            print(f"  {recipe}: not offered or short: {str(dry).strip().splitlines()[-1][:120] if str(dry).strip() else ''}")
            run("close.py", timeout=30)
            continue
        cost = int(m.group(1))
        if p.get("sp", 0) - cost < floor:
            stop(f"{recipe}: {cost} SP from {p.get('sp')} would pass the floor {floor}")
        before, was = names(), skills()
        out = run(*base, timeout=120)
        run("hotbar.py", "--deselect", timeout=30)
        run("close.py", timeout=30)
        if out.rc:
            stop(f"{recipe}: craft.py rc {out.rc}: {str(out)[-200:]}")
        after, now = names(), skills()
        made = [row[1] for k, row in after.items() if row[0] > before.get(k, [0])[0] and not NOT_MADE.search(row[1])]
        gain = {k: f"{was.get(k, (0, 0))[1]}->{v[1]}" + (f" (Lv{v[0]})" if v[0] != was.get(k, (0, 0))[0] else "") for k, v in now.items() if v != was.get(k)}
        tickets = sum(row[0] - before.get(k, [0])[0] for k, row in after.items() if "old ticket" in row[1])
        print(f"  {recipe}: {cost} SP, {made}, tickets +{tickets}, {gain}")
        done += 1
        if made and not keep:
            ship(made)
    print(f"done: {done} of {len(args)} crafted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
