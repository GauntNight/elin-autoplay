"""Empty every mystic treasure chest in the pack at home and ship the empty chest (run 41: Poppy's Treasure Hunt leaves them on the
floor for arrive.py to pick up, digmap.py brings them home; packcheck had no rule for them, and each held up a home trip, G46).
Everything inside comes out to the pack, the medals and bars go through packcheck --move; a chest is worth ~112-200 shipped
(elin-pack). Close each chest before the next: an open one takes every later quick move (run 25).

usage: python -I tools/chests.py [--dry]
       python -I tools/chests.py --field   on a trip (run 41: five chests on a dig tour, 15 weight each, Burden phase 2): the money, medals,
                                           unidentified pieces and books go into the pack and bags, the chest stays on the tile with the rest
Exit 0 done (or none), 1 refused (not at home), 3 stopped (the pack full: a chest left as it is).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data, last, refuse, run, setup, state, stop  # noqa: E402
from packcheck import split_listing  # noqa: E402

BASE = "treasure chest"


def carried():
    """The chests that can be emptied now. Run 42: a locked one lists as empty, so it must not be dropped or shipped: it rides until unlock.py opens it
    (bare hands: power skill/2 + 2, so lock 21 needs a lockpick; fact #1109)."""
    every = [i for i in data("inv")["items"] if BASE in i["name"].lower()]
    for i in every:
        if i.get("lockLv"):
            print(f"  {i['name']}: locked (lock {i['lockLv']}): it stays closed in the pack; unlock.py with a lockpick")
    return [i for i in every if not i.get("lockLv")]


def free_cards():
    return 35 - sum(1 for i in data("inv")["items"] if not i.get("equipped"))


def from_bags():
    """Run 42: purge's unclutter tucks a chest from a dig into a bag, where "no chest left in the pack" missed three, with 5,000 orens and 11 medals between them."""
    for i in data("stock")["pack"]:
        for x in i.get("items") or []:
            if BASE in x["name"].lower() and free_cards() > 1:
                print("  " + last(run("bag.py", i["name"], "--take", x["name"])))
                run("close.py")
            elif BASE in x["name"].lower():  # run 44: four chests sat in the bags behind a full grid, and "no chest left" six times
                print(f"  {x['name']} in {i['name']}: no free card to take it out (free {free_cards()}): bag or drop a stack first")


KEEP = re.compile(r"orens|gold bar|medal|platinum|\((miracle|godly)\)|\b(strange|runic|majestic|old) tome|ancient book|spellbook|"
                  r"recipe|potion|scroll|rod of|ticket|\bcard\b|gene\b|☆|★", re.I)
RIDE = ("a spoils bag", "a backpack", "a loot bag", "a haul bag")


def twin_locked(name):
    """Run 42: Drop and box.py take the first chest of a name: with a locked chest of the same name in the pack, that was the locked one, contents and all."""
    return any(i["name"] == name and i.get("lockLv") for i in data("inv")["items"])


def to_bags(names):
    """Stacks just taken into the pack go on into whichever bag has room."""
    d = {i["name"]: len(i.get("items") or []) for i in data("stock")["pack"] if i["name"] in RIDE}
    for n in names:
        if re.search(r"orens|gold bar|medal", n, re.I):
            continue
        bag = min(d, key=d.get)
        out = run("bag.py", bag, n)
        run("close.py")
        print("   ", bag, "<-", n, "" if out.rc == 0 else "(" + last(out) + ")")
        d[bag] += 1


def bagged():
    return [x["name"] for i in data("stock")["pack"] for x in i.get("items") or [] if BASE in x["name"].lower()]


def field():
    for _ in range(12):
        # run 47: digmap's unload at burden phase 2 printed "no chest left in the pack" after every dig while 4-5 closed chests
        # rode in the loot bag (the unclutter put them there): home mode took them out of the bags, field mode never looked,
        # and the tour ended Overweight with the squash taking HP 352 -> 209 on the world map
        from_bags()
        if not carried():
            if bagged():
                stop(f"{len(bagged())} chests in the bags behind a full grid ({free_cards()} free): drop or bag a stack, then again")
            print("no chest left in the pack")
            return
        # run 41: a chest's name varies, and listing the first while dropping the second left 2,086 orens and 3 bars on a danger
        # 34 field. Run 58: four chests of one name: the bars of one went into another, and the drop of a chest that still held
        # its junk was refused (item.py, run 57). One chest at a time by its uid, its contents by theirs
        import items as inv
        its = inv.inventory()
        c = next((i for i in its if BASE in i["name"].lower() and not i.get("path") and not i.get("locked")), None)
        if c is None:
            print("no unlocked chest in the pack's own grid")
            return
        inside = [i for i in its if (i.get("path") or [None])[-1] == c["uid"]]
        keep = [i for i in inside if (KEEP.search(i["name"]) or re.match(r"An? [A-Z]", i["name"]) or i["name"].startswith(("\u2606", "\u2605")))
                and "learned x" not in i["name"].lower()]
        print(f"chest: keep {[i['name'] for i in keep]}; left behind {[i['name'] for i in inside if i not in keep]}")
        ups = [f"uid:{i['uid']}" for i in keep]
        while ups:
            room = max(1, free_cards() - 1)
            batch, ups = ups[:room], ups[room:]
            out = run("bag.py", f"uid:{c['uid']}", "--take", *batch)
            run("close.py")
            if out.rc:
                print(out.strip())
            to_bags([i["name"] for i in keep if f"uid:{i['uid']}" in batch])
        its = inv.inventory()
        left = [i["name"] for i in its if (i.get("path") or [None])[-1] == c["uid"]]
        bad = [n for n in left if n in {i["name"] for i in keep} and not any(x in n for x in ("orens",))]
        if bad:
            stop(f"{bad} wouldn't come out of the chest (uid:{c['uid']}): make room, then again")
        out = run("item.py", f"uid:{c['uid']}", "Drop", "--full-ok")
        print("  " + last(out))
        if out.rc or "has no" in last(out):
            stop("a chest can't be dropped here (the world map offers no Drop): run it on a local map")
    stop("12 rounds and chests left")


def main():
    setup()
    if "--field" in sys.argv:
        if (state().get("zone") or {}).get("region"):
            refuse("the world map offers no Drop: enter a local map first")
        field()
        return
    dry = "--dry" in sys.argv
    if not (state().get("zone") or {}).get("isHome") and "startSite" not in str((state().get("zone") or {}).get("full")):
        refuse("at home only")
    if not dry:
        from_bags()
    # run 50: a refused empty chest (the shipping chest full after a day's ☆) stopped the loop with three full chests behind it,
    # all of one name; each chest is now taken by its uid, and an empty one the chest refuses rides on while the rest are emptied
    skip = set()
    for _ in range(12):
        todo = [i for i in carried() if i.get("uid") not in skip]
        if not todo:
            print("no chest left in the pack" + (f" ({len(skip)} empty ones ride: the shipping chest refused them)" if skip else ""))
            return
        UID = todo[0].get("uid")
        NAME = f"uid:{UID}" if UID else todo[0]["name"]  # run 41: "a madam's favorite mystic treasure chest" too
        out = run("bag.py", NAME)
        items = split_listing(last(out))
        print(f"chest: {', '.join(items) or 'empty'}")
        if dry:
            run("item.py", NAME, "Close")
            return
        if free_cards() < min(3, len(items)):
            run("item.py", NAME, "Close")
            print("  " + last(run("packcheck.py", "--move", timeout=300)))
            if free_cards() < min(3, len(items)):
                # run 43: four stops in a row: unidentified pieces and rods sat in the grid with the bags half empty
                import purge
                purge.unclutter()
                run("close.py")
                # run 50: the unclutter bagged the chest itself, the take then found nothing and the full chest went to the
                # shipping chest's refusal as "empty": bring it back out before going on
                from_bags()
            if free_cards() < min(3, len(items)):
                stop(f"{free_cards()} free cards for {len(items)} stacks: a chest stays closed in the pack")
            out = run("bag.py", NAME)
            items = split_listing(last(out))
        if items:
            names = [i.lstrip("★") for i in items]
            out = run("bag.py", NAME, "--take", *names)
            print(out.strip())
        run("item.py", NAME, "Close")
        # run 41: a full grid left stacks inside: a chest ships only when it's empty, the next round takes the rest
        if split_listing(last(run("bag.py", NAME))):
            run("item.py", NAME, "Close")
            print("  stacks left inside: " + last(run("packcheck.py", "--move", timeout=300)))
            continue
        run("item.py", NAME, "Close")
        if not UID and twin_locked(NAME):
            stop(f"{NAME}: a locked chest has the same name: unlock.py first (a lockpick), or box.py would ship the locked one")
        out = run("box.py", "shipping chest", NAME)
        print("  " + last(out))
        # run 42: a full shipping chest (40 stacks after stock --ship) refused the empty chest and this loop walked packcheck 12 times, 7 game hours
        if out.rc or "did not move" in out:
            print("  the shipping chest refused the empty chest (full until morning?): it rides; on to the next")
            skip.add(UID)
            continue
        if "--no-sort" not in sys.argv:  # run 42: five chests in a row need one sort at the end, not five
            out = run("packcheck.py", "--move", timeout=300)
            print("  " + last(out))
    stop("12 rounds and chests left")


if __name__ == "__main__":
    main()
