"""Pick up a named thing lying on my cell (or a cell beside me) and check it reached the pack (run 45: the act on a cell with
two big wagons is "Pick all", with one "Pick (a big wagon)"; act.py "Pick all" found nothing, and the walk home that followed in
the same shell line left the wagon behind: a wasted 25-game-hour leg). Whatever the game calls the act ("Pick all", "Pick (NAME)",
"Grab (NAME)"), this takes the thing and counts it in the pack and the bags before and after.

usage: python -I tools/pickup.py NAME [DX DZ]       NAME: part of the thing's name ("big wagon"); DX DZ: a cell beside me
Exit 0 picked up (the pack holds one more), 1 refused (nothing by that name on the cell), 3 stopped (the act ran, the count didn't
change). Gate the next step on it: `pickup.py "big wagon" && leave.py`.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import refuse, setup, stop, wait_until  # noqa: E402


def carried(name):
    def count(items):
        return sum((it.get("num") or 1) * (name.lower() in it["name"].lower()) + count(it.get("items")) for it in items or [])
    return count(call("stock")["data"]["pack"])


def main():
    setup()
    args = sys.argv[1:]
    if not args:
        refuse(__doc__)
    name = args[0]
    dx, dz = (int(args[1]), int(args[2])) if len(args) >= 3 else (0, 0)
    acts = call("acts", dx=dx, dz=dz, mode="all")["data"]["acts"]
    texts = [a["text"] for a in acts]
    named = [a for a in acts if a["text"].startswith(("Pick (", "Grab (")) and name.lower() in a["text"].lower()]
    if not named:
        cell = call("cell", dx=dx, dz=dz)["data"]
        here = [str(t.get("name") if isinstance(t, dict) else t) for t in cell.get("things") or []]
        if not any(name.lower() in h.lower() for h in here):
            refuse(f"no {name!r} on the cell ({dx},{dz}): {here or 'nothing'}; acts {texts}")
        # more than one thing lies there: the game offers only "Pick all"
        named = [a for a in acts if a["text"].startswith("Pick all")]
        if not named:
            refuse(f"{name!r} lies there but no pick-up act is offered: {texts}")
    before = carried(name)
    call("do", i=named[0]["i"])
    wait_until("frames", n=20, timeout=3000)
    after = carried(name)
    if after <= before:
        stop(f"{named[0]['text']}: still {after} {name!r} carried")
    print(f"{named[0]['text']}: {name!r} carried {before} -> {after}")


if __name__ == "__main__":
    main()
