"""Read the recipes in the home's boxes (run 41, the user: "Why don't you read the recipes you have available to you?"; "Seems we have a
lot of them in various chests"). elin-pack has said to read unlearned recipes on the spot since run 08, and no tool did: packcheck filed
them in the library and nothing read them from there, so 101 lay in 12 boxes, 37 never learned. A new recipe opens a craft, whose first
making pays an old ticket and skill exp (firstcraft.py); a known one read again improves that recipe ("You improve the recipe": fact to
come from this tool's rows) and either way the read frees a box slot.

usage: python -I tools/readrecipes.py [--dry] [--known] [--max N] [--here]
  --dry    list them and where they are
  --known  read the recipes already learned too (by default only the new ones)
  --max N  stop after N reads, to measure a few first
  --here   only what I carry, on any map
Stops on a hostile, Hungry or a low HP (common.ready). Exit 0 done, 1 refused, 3 stopped.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data, ready, refuse, run, setup, stop, wait_idle  # noqa: E402
from stock import free_cards, inventory  # noqa: E402


def wanted(name, known):
    low = name.lower()
    return "recipe of" in low and "cursed" not in low and "doomed" not in low and (known or "learned" not in low)


def boxed(known):
    out = {}
    for it in inventory()[1]:
        if wanted(it["name"], known) and it["where"] != "pack" and not it["bag"]:
            out.setdefault(it["where"], []).append(it["name"])
    return out


def carried(known):
    return [i["name"] for i in data("inv")["items"] if wanted(i["name"], known)]


def main():
    setup()
    args = sys.argv[1:]
    known = "--known" in args
    limit = int(args[args.index("--max") + 1]) if "--max" in args else 999
    here_only = "--here" in args
    if not here_only and not (data("state").get("zone") or {}).get("full", "").startswith("Zone_startSite"):
        refuse("not on the home map (--here reads only what I carry)")
    rows = {} if here_only else boxed(known)
    for where, names in rows.items():
        print(f"  {where}: {'; '.join(names)}")
    if "--dry" in args:
        print(f"{sum(len(v) for v in rows.values())} recipes in {len(rows)} boxes; carried: {carried(known)}")
        return 0
    reads = 0
    p0 = data("state")["pc"]
    while reads < limit:
        here = carried(known)
        if not here:
            rows = {} if here_only else boxed(known)
            if not rows:
                break
            room = free_cards(data("stock")) - 1
            if room <= 0:
                stop(f"no free card to carry a recipe ({reads} read): bag a stack")
            where = max(rows, key=lambda w: len(rows[w]))
            batch = rows[where][:room]
            r = run("box.py", where, "--take", *batch)
            if r.rc != 0:
                stop(f"box.py {where} --take refused (rc {r.rc}): {r}")
            continue
        why = ready(hp=60, hunger=70)
        if why:
            stop(f"{why} ({reads} read)")
        name = here[0]
        r = run("item.py", name, "Read")
        if r.rc != 0:
            stop(f"item.py Read refused on {name}: {r}")
        wait_idle(timeout=60000)
        reads += 1
        log = " / ".join((data("state").get("log") or [])[-2:])
        print(f"read {name}  | {log[:110]}", flush=True)
    p1 = data("state")["pc"]
    print(f"done: {reads} recipes read; exp {p0['exp']} -> {p1['exp']} (Lv{p1['lv']}), SP {p0['sp']} -> {p1['sp']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
