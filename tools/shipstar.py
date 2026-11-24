"""Carry the identified ☆ gear in the bags to the shipping chest (run 40). Every run did this by hand (run 34's 29 pieces,
run 39's six): ☆ gear pays 3-4x a shop's offer by the chest (elin-pack 3), and each piece holds a bag slot until it goes.

Worn gear is never touched, nor a ★ artifact, an unidentified piece or anything else. Checking a piece against the
worn one is still mine: --keep NAME (repeatable) leaves a piece in its bag, and --dry lists what would move. As many as
the pack's free cards carry at a time, bag by bag, one card left free. Stops at the chest's 40 stacks.

usage: python -I tools/shipstar.py [--dry] [--keep NAME ...]
Exit 0 done, 1 refused (not at home), 3 stopped (the pack full, the chest full).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data, refuse, run, setup, stop  # noqa: E402
from home import SHIPPING  # noqa: E402
from job import JOBS  # noqa: E402

CHEST_MAX = 40  # fact #1001: the shipping chest's stacks
# Run 44: Queen's Victory went into the chest. It was off its finger only because the Fighting Bull (thief protection) is
# worn in Derphy, and gearcheck had recorded it there as a candidate. Pieces kept for a swap never ship.
# Run 50: the Godbane Breastplate (blindness negated) rides as the swap for the Brilliant Ring Mail (PV 35, confusion
# negated) on a floor whose foes blind
# Run 55: ☆The Rigid Ring 『Cheating Bleed』 (worn) negates blindness, so Bad West's swap shipped; 『The Evening』 (thieves'
# protection and Pickpocket, no PV loss) is the Derphy ring beside the Fighting Bull
# Run 58: Hoof Transformation took ☆The Queen boots off mid-floor and purge bagged them; shipstar, run by the arrival now, was one free
# card from shipping them. What I wore at the run's start or since (runs/worn.txt, written by leave.py) is mine and never ships from here
KEPT = ("Queen's Victory", "The Evening")


def pieces(keep):
    """{bag: [name]} the ☆ gear inside the pack's bags (never the Cooler Box), and in the pack's own grid under "pack"."""
    out = {}
    for it in data("stock").get("pack") or []:
        if it.get("items") is None and not it.get("equipped") and it["name"].startswith("☆") \
                and "putit" not in it["name"].lower() and not any(k.lower() in it["name"].lower() for k in keep):
            out.setdefault("pack", []).append(it["name"])
        if it.get("items") is None or "cooler" in it["name"].lower():
            continue
        names = [s["name"] for s in it["items"] if s["name"].startswith("☆")
                 and not any(k.lower() in s["name"].lower() for k in keep)]
        if names:
            out[it["name"]] = names
    return out


def free_cards():
    return 35 - sum(1 for i in data("stock").get("pack") or [] if not i.get("equipped"))


def main():
    setup()
    args = sys.argv[1:]
    keep = [args[i + 1] for i, a in enumerate(args) if a == "--keep"] + list(KEPT)
    # run 47: the Rigid Long Bow ('Newly Bleed', the kit's ranged weapon on runs/carry.txt since run 45) shipped, because a
    # `gearcheck.py weapon` read recorded it and this tool knew only KEPT. What I chose to carry never ships from here.
    import items
    keep += [ln for ln in items.carry_list() if ":" not in ln]
    worn = JOBS.parent / "worn.txt"
    keep += [ln for ln in worn.read_text(encoding="utf-8").splitlines() if ln.strip()] if worn.exists() else []
    if not (data("state").get("zone") or {}).get("full", "").startswith("Zone_startSite"):
        refuse("not on the home map")
    # run 40 (the user: "how often do you look at current equipment versus new?"): this tool made shipping unread pieces easy, and 14
    # went that way. Only what gearcheck.py has shown beside the worn piece ships
    record = JOBS / "gearcheck.txt"
    checked = set(record.read_text(encoding="utf-8").splitlines()) if record.exists() else set()
    todo = pieces(keep)
    unread = [n for names in todo.values() for n in names if n not in checked]
    if unread and "--dry" not in args:
        refuse(f"{len(unread)} pieces not compared with the worn gear yet: run gearcheck.py first ({unread[0]}, ...)")
    total = sum(len(v) for v in todo.values())
    for bag, names in todo.items():
        for n in names:
            print(f"  {bag}: {n}")
    if "--dry" in args or not total:
        print(f"{total} ☆ pieces in the bags")
        return 0
    moved = 0
    while True:
        todo = pieces(keep)
        if not todo:
            break
        room = free_cards() - 1
        if room <= 0 and "pack" not in todo:  # the grid's own pieces need no free card, and shipping them makes some
            stop(f"no free card to carry a piece (shipped {moved}): bag or ship a stack")
        if "pack" in todo:
            todo = {"pack": todo["pack"]}
        chest = data("stock").get("shipping") or []
        if len(chest) >= CHEST_MAX:
            stop(f"the shipping chest holds {len(chest)} stacks (shipped {moved}): the rest ride on until 05:00 empties it")
        bag, names = next(iter(todo.items()))
        batch = names[:min(room, CHEST_MAX - len(chest))] if bag != "pack" else names[:CHEST_MAX - len(chest)]
        if bag != "pack":
            r = run("bag.py", bag, "--take", *batch)
            print(r, flush=True)
            if r.rc != 0:
                stop(f"bag.py {bag} --take refused (rc {r.rc})")
        r = run("box.py", f"{SHIPPING[0]},{SHIPPING[1]}", *batch)
        print(r, flush=True)
        if r.rc != 0:
            stop(f"box.py shipping refused (rc {r.rc}): is the shipping chest full?")
        moved += len(batch)
    print(f"shipped {moved} ☆ pieces")
    return 0


if __name__ == "__main__":
    sys.exit(main())
