"""Read the specialized books in the home's boxes (run 40). A specialized book gives 1,000 skill exp (blessed 1,500, cursed
500), or teaches the skill when it is unknown (fact #554), and character exp comes only from skill level-ups (fact #481),
so a book is exp sitting in a box: run 40 found ~30, filed in the library since run 27 because only an unlearned
skill's book was ever read. This takes them box by box, reads each until it crumbles, and prints what each paid.

usage: python -I tools/readskills.py [--dry] [--here] [--max N] [--skip SKILL ...]
  --dry     list the books and where they are
  --here    read only the books I carry, on any map
  --max N   stop after N reads, to measure a few first
  --skip    leave a skill's books boxed (repeatable)
Stops on a hostile, Hungry or a low HP (common.ready). A cursed book is read too: the 500 is still exp.
Exit 0 done, 1 refused, 3 stopped.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data, ready, refuse, run, setup, stop, wait_idle  # noqa: E402
from stock import free_cards, inventory  # noqa: E402

BOOK = re.compile(r"specialized books? of 「(.+)」")


def boxed(skip):
    """{where: [name]} the specialized books lying directly in the home's boxes."""
    out = {}
    for it in inventory()[1]:
        m = BOOK.search(it["name"])
        if m and it["where"] != "pack" and not it["bag"] and m.group(1).lower() not in skip:
            out.setdefault(it["where"], []).append(it["name"])
    return out


def carried():
    """The specialized books in the pack, bags included (item.py finds them there)."""
    return [i["name"] for i in data("inv")["items"] if BOOK.search(i["name"])]


def snapshot():
    p = data("state")["pc"]
    return p["lv"], p["exp"]


def main():
    setup()
    args = sys.argv[1:]
    limit = int(args[args.index("--max") + 1]) if "--max" in args else 999
    skip = {args[i + 1].lower() for i, a in enumerate(args) if a == "--skip"}
    here_only = "--here" in args  # only what I carry, on any map (bought in a town, run 40)
    if not here_only and not (data("state").get("zone") or {}).get("full", "").startswith("Zone_startSite"):
        refuse("not on the home map (--here reads only what I carry)")
    rows = {} if here_only else boxed(skip)
    for where, names in rows.items():
        print(f"  {where}: {'; '.join(names)}")
    if "--dry" in args:
        print(f"{sum(len(v) for v in rows.values())} stacks in {len(rows)} boxes; carried: {carried()}")
        return 0
    reads = gained = 0
    while reads < limit:
        here = [n for n in carried() if BOOK.search(n).group(1).lower() not in skip]
        if not here:
            rows = {} if here_only else boxed(skip)
            if not rows:
                break
            room = free_cards(data("stock")) - 1
            if room <= 0:
                stop(f"no free card to carry a book ({reads} read, +{gained} exp): bag a stack")
            where = max(rows, key=lambda w: len(rows[w]))
            batch = rows[where][:room]
            r = run("box.py", where, "--take", *batch)
            print(r, flush=True)
            if r.rc != 0:
                stop(f"box.py {where} --take refused (rc {r.rc})")
            continue
        why = ready(hp=60, hunger=70)
        if why:
            stop(f"{why} ({reads} read, +{gained} exp)")
        name = here[0]
        lv0, exp0 = snapshot()
        r = run("item.py", name, "Read", *(["--cursed-ok"] if "cursed" in name.lower() else []))
        if r.rc != 0:
            stop(f"item.py Read refused on {name}: {r}")
        wait_idle(timeout=120000)
        lv1, exp1 = snapshot()
        paid = exp1 - exp0 if lv1 == lv0 else None
        gained += paid or 0
        reads += 1
        log = " / ".join((data("state").get("log") or [])[-2:])
        print(f"read {name}: exp {'level up!' if paid is None else f'+{paid}'}  | {log[:110]}", flush=True)
    print(f"done: {reads} books read, +{gained} character exp")
    return 0


if __name__ == "__main__":
    sys.exit(main())
