"""Open the mail: every package (delivery box) on the map, one at a time, with its contents
listed. Deliveries, quest rewards and the tax bill arrive in packages by the hearth or the
mail post, and they pile up unopened (run 04 found four, holding a tool, a can, a bottle).

  --take    move the contents into the pack (Take All); refuses when the pack would pass
            30 stacks (a full pack drops or refuses items silently)
  --pickup  also grab each emptied package, so it can go into the shipping chest or be sold
            (worth about 15 orens). Decor standing on a package is lifted first and put back.

usage: python -I tools/unpack.py [--take] [--pickup] [radius]
Then triage what came out (elin-play: use now / bring / store / sell or ship).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from close import close_all  # noqa: E402
from common import act, contents, last, pc, top, wait_until  # noqa: E402
from common import walk_beside as common_walk_beside  # noqa: E402
from place import place_at  # noqa: E402

from home import FARM_BOX, LIBRARY, PANTRY_2, SPARES2  # noqa: E402

PACK_MAX = 38  # run 15: the trip kit alone is ~29 stacks, so 30 blocked every package; the pack refuses the 44th
# Packages kept as storage bins at home (elin-home): listed, never emptied or picked up. The farm
# box is a mail package too; run 13 found --take would have emptied it (only the library was here).
# The spare at 53,53 was shipped by mistake in run 04.
BINS = {tuple(FARM_BOX), tuple(SPARES2), tuple(PANTRY_2), *(tuple(c) for c in LIBRARY)}  # run 14: pantry 2


def pack_stacks():
    return sum(1 for i in call("inv")["data"]["items"] if not i.get("equipped"))


def stand_beside(x, z):
    """common.walk_beside at home (no radius, no HP floor) with a long timeout, answering whether
    I now stand next to (x, z); box.py and boxshift.py open containers through it.
    Run 20: from the home map's edge (arriving from the world map) the walk to the Kitchen's fridge
    took over 20 s and arrive.py stopped with "can't reach the container" twice."""
    common_walk_beside(x, z, r=0, hp=0, timeout=60000)
    p = pc()
    return abs(p["x"] - x) <= 1 and abs(p["z"] - z) <= 1


def put_away_held():
    """Empty the hands through the held stack's own "Put away" (while something is held,
    right-click offers Place, not Grab). Not common.put_away, which is the hotbar's Deselect;
    that is the fallback here for a hotbar item."""
    held = pc()["held"]
    if not held:
        return
    slots = [b for b in call("buttons", all=True)["data"]["buttons"]
             if b.get("card") == held and "ButtonGrid inventory" in b["name"]]
    for s in slots:
        rep = call("invacts", i=s["i"])
        acts = [a for a in (rep.get("data") or {}).get("acts", []) if a["text"] == "Put away"]
        if acts:
            call("invdo", i=acts[0]["i"])
            wait_until("frames", n=8, timeout=1000)
            return
    # A hotbar item is "held" by being the selected slot and has no Put away (run 04, the Putit
    # on slot 1). The widget's Deselect button didn't clear it in run 05; hotbar.deselect does
    # (pick the slot's item up, then Cancel drops it back unselected).
    from hotbar import deselect
    deselect()


def grab_package(x, z):
    """Grab the package at x,z; decor on top of it is grabbed first and placed back."""
    lifted, result = [], "package not reached"
    for _ in range(4):
        put_away_held()  # each grab leaves the item in hand
        did = act(x, z, "Grab", "right")
        if not did:
            result = "no Grab offered"
            break
        wait_until("frames", n=15, timeout=2000)
        if "package" in did:
            result = "grabbed"
            break
        lifted.append(did[len("Grab ("):-1])
    put_away_held()
    for name in lifted:  # decor goes back on the same cell either way
        name = name[2:] if name.startswith("a ") else name[3:] if name.startswith("an ") else name
        print(f"    put back {name}: {place_at(name, x, z)}")
    return result, lifted


def mail_parcels():
    """Run 17: salaries ("a parcel labelled Salary", 75-82 orens each: the Merchants Guild and
    others) and gifts arrive INSIDE the mail post, not as packages on the map: eight parcels had
    piled up unopened. Take each parcel or gift out and open it (the coins go to the purse)."""
    import re
    from common import run
    from home import MAIL_POST
    from packcheck import split_listing
    where = f"{MAIL_POST[0]},{MAIL_POST[1]}"
    items = split_listing(run("box.py", where))  # box.py closes its window itself
    mail = [x for x in items if re.search(r"parcel|gift", x, re.I) and "bill" not in x.lower()]
    opened = []
    for x in mail:
        if "moved" in run("box.py", where, "--take", x):
            for bag in ("", "loot bag", "backpack"):  # a full pack sends it into a bag
                if bag:
                    run("bag.py", bag)
                out = run("item.py", x, "Open")
                run("close.py")
                if last(out).startswith("Open"):
                    opened.append(x)
                    break
    print("mail post: opened " + (", ".join(opened) if opened else "nothing"))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    take, pickup = "--take" in sys.argv, "--pickup" in sys.argv
    if (call("state")["data"].get("zone") or {}).get("full", "").startswith("Zone_startSite"):
        mail_parcels()
    nums = [a for a in sys.argv[1:] if a.isdigit()]
    r = int(nums[0]) if nums else 999
    hits = [h for h in call("find", name="package", r=r, n=40)["data"]["hits"] if h["name"].endswith("package")]
    if not hits:
        print("no packages on the map")
        return
    for h in hits:
        x, z = h["x"], h["z"]
        close_all(lambda *_: None)
        if not stand_beside(x, z):
            print(f"{x},{z}: can't get beside it")
            continue
        if not act(x, z, "Open"):
            print(f"{x},{z}: no Open offered")
            continue
        if top() != "LayerInventory":
            wait_until("layer", timeout=4000)  # the container window opens
        if top() != "LayerInventory":
            print(f"{x},{z}: opened, but no container window (top {top()})")
            continue
        items = contents()
        print(f"{x},{z}: " + (", ".join(items) if items else "empty") + (" [bin]" if (x, z) in BINS else ""))
        if (x, z) in BINS:
            continue
        if take and items:
            if pack_stacks() + len(items) > PACK_MAX:
                print(f"  !! pack at {pack_stacks()} stacks: clear it first (tools/packcheck.py --move)")
                close_all(lambda *_: None)
                return
            btn = [b for b in call("buttons")["data"]["buttons"] if (b.get("text") or "").startswith("Take All")]
            if not btn:  # the review of 2026-10-23: an IndexError when the window has no Take All
                print(f"  !! no 'Take All' button in this window (top {top()}): left as is; take the items by name with box.py --take")
                close_all(lambda *_: None)
                continue
            call("click", i=btn[0]["i"])
            wait_until("frames", n=15, timeout=2000)
            # Take All also opens the pack beside the box, so reopen the box alone to check it
            close_all(lambda *_: None)
            act(x, z, "Open")
            if top() != "LayerInventory":
                wait_until("layer", timeout=4000)
            left = contents()
            print("  took all" if not left else f"  !! still inside: {', '.join(left)}")
            items = left
        close_all(lambda *_: None)
        if pickup and not items:
            print(f"  {grab_package(x, z)[0]}")
    close_all(lambda *_: None)


if __name__ == "__main__":
    main()
