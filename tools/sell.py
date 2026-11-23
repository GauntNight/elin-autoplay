"""Sell chosen things to a shopkeeper, at home or in town (G70 Smart Storage M3, run 57; the user, 2026-11-21: "It may
also help to have a Store in our home so we can sell things locally when we run out of time/room", then "for a store I
just mean a Shopkeeper in town that we can use"). Run 57's M0 read: Samata the healer (home, shop level 2) bought a ☆
laser gun for 1,284 orens with no category gate; the shipping chest pays ~1.1x a shop's price but takes ~40 stacks a
morning (fact #1001), so this is the outlet for what the chest refuses or what can't wait for a morning.

Each thing is named by uid (items.py lists them), refused when items.protected() holds it (worn, unidentified, the kit,
a full container, the carry list), moved into the pack's own grid (a shop's sell list shows only that), and sold with its
own "Sell N" act. A sale counts only when the purse moved and the thing left the pack (fence.py's lesson, run 54: a fence
out of money "sold" stacks that were still carried). Run 57: a home shopkeeper has no purse in the code; a sale is refused
silently when her shop's container is full of what I sold, so a sale that moves no gold presses the window's "Restock
(-1 Influence)" once (it rebuilds her stock) and retries; a second failure stops the rest.

--find: at home, first walk to the resident board, open Residents, pick the shopkeeper's row and press Find (the user's
tip, run 57: "you can use the board, I think, to find residents as well. Similar to a guard in town"): the game walks
me to them wherever they wander.

usage: python -I tools/sell.py SHOPKEEPER uid:N [uid:N ...] [--find] [--dry]
Exit 0 sold (or --dry listed), 1 refused (a protected thing, nothing to sell, no shopkeeper), 2 the bridge,
3 stopped (the buyer's gold ran out, a window, the Find walk didn't arrive).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import data, last, refuse, run, setup, stop, txlog, walk_beside  # noqa: E402
import home  # noqa: E402
import items as inv  # noqa: E402


def gold():
    return data("state")["pc"].get("gold") or 0


def find_resident(name):
    """The resident board's Find: walk beside the board, open Residents, the row whose name holds NAME, its Find."""
    bx, bz = home.BOARDS["resident"]
    # run 57: a fixed walk to the cell east of the board stopped one short on a garbage pile, and acts at (-1,0) read
    # the garbage: stand on any free neighbour and ask the board's own cell
    w = walk_beside(bx, bz)
    me = data("state")["pc"]
    if max(abs(me["x"] - bx), abs(me["z"] - bz)) > 1:
        stop(f"the walk to the resident board ended at {me['x']},{me['z']}: {w}")
    acts = call("acts", dx=bx - me["x"], dz=bz - me["z"]).get("data", {}).get("acts", [])
    hit = [a for a in acts if (a.get("text") or "").startswith("Residents")]
    if not hit:
        me = data("state")["pc"]
        stop(f"no Residents act beside the board (at {me.get('x')},{me.get('z')}): {[a.get('text') for a in acts]}")
    call("do", i=hit[0]["i"])
    bs = call("buttons").get("data", {}).get("buttons", [])
    rows = [b for b in bs if "ButtonGeneral" in (b.get("name") or "") and name.lower() in (b.get("text") or "").lower()]
    if len(rows) != 1:
        run("close.py")
        refuse(f"{len(rows)} rows on the resident board hold '{name}': name the resident in full")
    call("click", i=rows[0]["i"], expect=name)
    menu = call("buttons", all=True).get("data", {}).get("buttons", [])
    fnd = [b for b in menu if "Context_ButtonInteraction" in (b.get("name") or "") and (b.get("text") or "").strip() == "Find"]
    if not fnd:
        run("close.py")
        stop(f"no Find in {name}'s menu on the resident board")
    call("click", i=fnd[0]["i"], expect="Find")
    call("wait", until="idle", timeout=60000)
    run("close.py")


def main():
    setup()
    argv = sys.argv[1:]
    dry, find = "--dry" in argv, "--find" in argv
    args = [a for a in argv if not a.startswith("--")]
    if not args or len(args) < 2 and not dry:
        refuse("usage: sell.py SHOPKEEPER uid:N [uid:N ...] [--find] [--dry]")
    who, uids = args[0], []
    for a in args[1:]:
        if not a.startswith("uid:") or not a[4:].isdigit():
            refuse(f"name each thing by uid (items.py lists them): '{a}'")
        uids.append(int(a[4:]))
    carried = inv.inventory()
    by = {i["uid"]: i for i in carried}
    sell = []
    for u in uids:
        it = by.get(u)
        if not it:
            # run 57: a stack taken from a box merged into one already carried and took its uid: skip it, sell the rest
            print(f"  not carried: uid:{u} (merged into another stack?)")
            continue
        why = inv.protected(it, carried)
        if why:
            refuse(f"{it['name']} (uid:{u}): {why}")
        sell.append(it)
    if dry:
        for it in sell:
            print(f"  would sell: {it['name']} ({inv.where(it, carried)})")
        return
    ready, later = [], []
    for it in sell:
        if it.get("path"):
            if later:  # the grid filled already: the rest wait for the next round
                later.append(it["uid"])
                continue
            ok, why = inv.to_pack(it, inv.inventory())
            if not ok and "grid is full" in str(why):
                # run 58: 31 rods in the bags and 6 free cards: one call sold 6 and left 25. The rest go in the next round
                later.append(it["uid"])
                continue
            if not ok:
                # run 57: 11 holy boots in a lame purse inside the worn toolbelt refused the whole batch: skip that one
                print(f"  left: {it['name']} won't come out of {inv.where(it, carried)}: {why}")
                continue
        ready.append(it)
    sell = ready
    if not sell:
        refuse("nothing came out of the bags into the pack's grid")
    # run 57: the board walk was a third of each clear-out batch; when the shopkeeper is already in view, talk at once
    near = [c for c in data("state").get("nearby") or [] if who.lower() in (c.get("name") or "").lower()
            and max(abs(c.get("dx") or 0), abs(c.get("dz") or 0)) <= 12]
    if find and not near:
        find_resident(who)
    out = run("shop.py", who, "--keep-open", timeout=300)
    if out.rc != 0:
        refuse(f"shop.py {who}: {last(out) or out.rc}")
    sold, total, why_stop, restocks = [], 0, None, 0

    def try_sell(it):
        """The gold paid for the whole stack, 0 when the sale didn't go through, None when it isn't on the list."""
        bs = call("buttons", all=True)["data"]["buttons"]
        hit = [b for b in bs if "inventory grid" in (b.get("name") or "") and b.get("mine") is not False
               and b.get("uid") == it["uid"]]
        if not hit:
            print(f"  not on the sell list: {it['name']}")
            return None
        acts = call("invacts", i=hit[0]["i"]).get("data", {}).get("acts", [])
        sells = [a for a in acts if a["text"].startswith("Sell")]
        if not sells:
            print(f"  no Sell act (the shop won't take it): {it['name']}")
            return None
        g0 = gold()
        call("invdo", i=sells[-1]["i"])  # "Sell N" for the whole stack
        paid = gold() - g0
        if paid <= 0 and not any("orens" in a["text"] for a in sells):
            # run 57: wooden bullets and makeshift arrows list "Sell 11" with no price: worth 0, which the game refuses
            # (Transaction.IsValid: price 0), and the Restock pressed for them was spent for nothing
            print(f"  no price (worth 0 here): {it['name']}")
            unsold.append(it["name"])
            return None
        return paid

    fails = 0  # failures in a row right after a Restock
    unsold = []
    for it in sell:
        paid = try_sell(it)
        if paid is None:
            continue
        if paid <= 0:
            # run 57: Samata "stopped paying" after ~6,400 orens. Not a purse: the code has none (InvOwner.Transaction
            # credits the player only); a sale is refused, silently, when the shop's own container is full of what I sold.
            # Her window's "Restock (-1 Influence)" rebuilds the stock (Trait.OnBarter) and empties it: press it, retry.
            # A thing that still won't sell right after a Restock is the thing (run 57: royal gift boxes): skip it; two
            # four such in a row mean the Restock did nothing (no influence left?): stop
            rs = [b for b in call("buttons").get("data", {}).get("buttons", []) if (b.get("text") or "").startswith("Restock")]
            if rs and fails == 0:
                call("click", i=rs[0]["i"], expect="Restock")
                restocks += 1
                txlog("restock", who, "", "", "-1 influence: the shop was full")
                paid = try_sell(it) or 0
        if paid <= 0:
            fails += 1
            unsold.append(it["name"])
            # run 57: a house plate and a story book in a row stopped a batch at 2: unsellable things come in runs
            if fails >= 4:
                why_stop = (f"four sales in a row moved no gold after a Restock ({', '.join(unsold[-4:])}): "
                            f"{who}'s shop won't take more (no influence left?) (paid {total:,} before)")
                break
            continue
        fails = 0
        total += paid
        sold.append(f"{it['name']} {paid:,}")
        txlog("sold", it["name"], "pack", who, f"{paid} orens")
    run("close.py")
    run("talk.py")
    still = {i.get("uid") for i in inv.inventory()}
    kept = [it["name"] for it in sell if it["uid"] in still]
    print(f"sold {len(sold)} for {total:,} orens" + (f" ({restocks} restock{'s' * (restocks > 1)}, -1 influence each)" if restocks else "")
          + ": " + "; ".join(sold))
    if kept:
        print(f"still carried: {', '.join(kept)}")
    if unsold:
        print(f"wouldn't sell even after a Restock: {', '.join(unsold)}")
    if why_stop:
        stop(why_stop)
    if later and sold:
        print(f"next round: {len(later)} that waited for grid room", flush=True)
        sys.argv = [sys.argv[0], who, *(f"uid:{u}" for u in later)] + (["--find"] if find else [])
        main()
    elif later:
        print(f"left in the bags (the pack's grid is full and nothing sold): {len(later)}")


if __name__ == "__main__":
    main()
