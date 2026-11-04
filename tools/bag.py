"""Move items between the pack and a container carried in it (Cooler Box, purse, bag) with the
game's own Shift+click quick move (bridge 0.13.0 `shiftclick`, InvOwner.OnShiftClick). A
carried container holds many items in one pack slot (the user, run 04: carry bags so the pack
stops overflowing; keep food in the cooler box).

usage: python -I tools/bag.py BAG [--take] [ITEM ...]
  BAG     part of the container's name ("Cooler Box")
  ITEM    part of an item's name; each moves one stack
  --take  move from the bag to the pack (to eat or use it)
  no ITEM lists what the bag holds
Exit: 0 every item moved, 1 any item not moved (run 38: a full pack exited 0).
item.py finds items inside an open bag too (run 04: `item.py "piles of bread" Eat` ate from the Cooler Box); --take raised a NullReference in the game on the world map.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call, norm  # noqa: E402
from common import open_inventory, stack_hits, wait_idle, wait_until  # noqa: E402


def slots():
    return open_inventory()  # run 17: the injected key stopped working; the hotbar button opens it


def acts_of(i):
    """A slot's acts; run 21: right after a loot walk invacts answered "busy" and the bare
    ["data"] crashed the tool: wait for idle and ask once more, then refuse."""
    r = call("invacts", i=i)
    if not r.get("ok"):
        wait_idle(timeout=5000)
        r = call("invacts", i=i)
    if not r.get("ok"):
        sys.exit(f"invacts refused: {r.get('error')}")
    return r["data"]["acts"]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    take = "--take" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--take"]
    bag, items = args[0], args[1:]
    # run 11: Shift+click moves to the other open window; with the trash can's recycle grid open
    # four food stacks went into the recycler and were destroyed. Close any drag grid first.
    for _ in range(4):
        if (call("state")["data"].get("layers") or {}).get("top") != "LayerDragGrid":
            break
        call("closetop")
        wait_until("frames", n=8, timeout=1000)
    top = (call("state")["data"].get("layers") or {}).get("top")
    if top == "LayerDragGrid":
        sys.exit("a drag grid (recycler, converter) is open and won't close: not moving anything")
    if top and top != "LayerInventory":
        # run 21: under the morning shipping report this said "no 'Cooler Box' in the pack"
        sys.exit(f"a window is open ({top}): read.py, then close.py")
    bs = slots()
    # run 24: with Monashy's wares still open (shop.py --keep-open), three pieces taken out of the
    # backpack went by Shift+click into his Merchant Chest for nothing: no other window's grid may be open
    # (the held-tool widget's SubButton also shows mine false with no container: grids only)
    other = sorted({b.get("in") for b in call("buttons", all=True)["data"]["buttons"]
                    if b.get("card") and b.get("mine") is False and b.get("in")
                    and "ButtonGrid" in (b.get("name") or "")})
    if other:
        sys.exit(f"another container is open ({', '.join(other)}): a quick move would go into it; close.py first")
    mine = [b for b in bs if bag.lower() in (b.get("card") or "").lower() and b.get("in") == "pack"]
    if not mine:
        sys.exit(f"no {bag!r} in the pack")
    # Shift+click moves to the other open container, so close every other carried container first
    # (run 10: with the backpack open too, "Cooler Box" moves sent food into the backpack to rot).
    checked = set()
    while True:
        others = [b for b in bs if b.get("in") == "pack" and b.get("card") and b["card"] != mine[0]["card"]
                  and b["card"] not in checked
                  and any(k in b["card"].lower() for k in ("box", "backpack", "bag", "trunk", "pouch", "purse", "chest", "package"))]
        # run 25: "chest" was missing, so two carried mystic treasure chests opened from the pack stayed
        # registered windows all afternoon and every take landed inside them (the mushrooms, the identify
        # rod, the gold bars); a chest's menu shows "Close" while it is open, like a bag's
        if not others:
            break
        b = others[0]
        checked.add(b["card"])
        other = {a["text"]: a["i"] for a in acts_of(b["i"])}
        if "Close" in other:
            call("invdo", i=other["Close"])
            wait_until("frames", n=10, timeout=1500)
            bs = slots()
            mine = [m for m in bs if bag.lower() in (m.get("card") or "").lower() and m.get("in") == "pack"]
    acts = {a["text"]: a["i"] for a in acts_of(mine[0]["i"])}
    if "Open" in acts:  # "Close" means it's open already
        call("invdo", i=acts["Open"])
        wait_until("frames", n=15, timeout=2000)  # the bag's window is built beside the pack's
    bs = slots()
    # bridge 0.13.1 tells each slot's container ("in": "pack" or the bag's name)
    bagname = mine[0]["card"]

    def inside_of(bs):
        return [b for b in bs if b.get("card") and b.get("in") and b["in"] != "pack" and b["in"] in bagname]
    inside = inside_of(bs)
    if not items:
        print(f"{mine[0]['card']}: " + (", ".join(b["card"] for b in inside) or "empty"))
        return
    failed = []  # run 38: a full pack printed 'not moved' and exited 0, so a loop over takes went on blind
    for it in items:
        # run 38: a worn piece shows as an equipment-panel slot ('inventory drag float', in "pack") too, and "blessed torch"
        # bagged the worn torch (leave.py then refused: no light source): only the pack's grid cards move into a bag
        src = inside if take else [b for b in bs if b.get("in") == "pack" and b["card"] != bagname
                                   and "inventory grid" in (b.get("name") or "")]
        # whole-word matching, so "corpse" doesn't take "corpse of 『Goblin』" by accident; run 13: an
        # exact full name (count included) wins, and stacks differing only in count are one item
        hit, ambiguous = stack_hits(it, src)
        if ambiguous:
            print(f"{it}: matches several: " + " | ".join(sorted({b["card"] for b in hit})[:6]) + " (give the full name)")
            failed.append(it)
            continue
        if not hit:
            print(f"{it}: not {'in the bag' if take else 'in the pack'}")
            failed.append(it)
            continue
        r = call("shiftclick", i=hit[0]["i"])
        if "NullReference" in str(r.get("error") or "") and take:
            # run 16: after one move the grid rebuilds; the next slot's button was stale for 0.4 s
            # and every later item failed. Wait, list again, retry once.
            wait_until("frames", n=30, timeout=2000)
            bs = slots()
            hit, _ = stack_hits(it, inside_of(bs))
            r = call("shiftclick", i=hit[0]["i"]) if hit else r
        err = str(r.get("error") or r)
        if not take and "NullReference" in err:  # run 13: a full Cooler Box (9 slots) answers this way
            err = f"not moved: the bag is probably full ({len(inside)} stacks inside)"
        elif take and "NullReference" in err:  # run 16: the same answer from a full pack (42+ stacks)
            # run 21: the move usually lands anyway (a copper hammer, practice gloves, a geyser): the
            # UI grid lags, so ask the pack itself (inv lists the pack's own things)
            wait_until("frames", n=20, timeout=2500)
            card = hit[0]["card"]
            if any(i["name"] == card for i in call("inv")["data"]["items"]):
                r = {"ok": True, "data": {"moved": hit[0]["card"], "changed": True}}
            else:
                # run 21: the pack's grid held 35 cards while state counted 39 stacks (the toolbelt's
                # count too), so pack_full() at 42 never fired; a full grid refuses every take
                grid = len([b for b in bs if b.get("in") == "pack" and b.get("card")
                            and "inventory grid" in (b.get("name") or "")])
                err = f"not moved: the pack's grid is full ({grid} cards): put a pack stack in a bag or drop one"
        if take and r.get("ok") and r["data"].get("changed"):
            # run 22: a carried treasure chest opened with item.py stayed registered as a window, and
            # three takes from other bags "moved" into it (shift-click goes to the top other window)
            wait_until("frames", n=10, timeout=1500)
            names = [i["name"] for i in call("inv")["data"]["items"]]
            if hit[0]["card"] not in names and not re.search(r"\borens?$", hit[0]["card"]):
                err = (f"!! left the bag but isn't in the pack: another container window took it "
                       f"(a carried chest or bag opened earlier?): close.py, then look inside it")
                r = {"ok": False}
        moved = r.get("ok") and r["data"].get("changed")
        print(f"{it}: " + (f"moved {r['data']['moved']}" if moved else err))
        if not moved:
            failed.append(it)
        wait_until("frames", n=8, timeout=1000)  # the grids rebuild after a move
        bs = slots()
        inside = inside_of(bs)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
