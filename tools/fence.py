"""Sell the stolen goods at a black market (run 33: done by hand at Minwer and Siyun with a scratch loop).

What is sold is what the game itself marks stolen (bridge 0.40.0 `items`: the flag Sleight of Hand sets), wherever
it rides, minus anything tools/items.py protects (worn things, the kit, the carry list, unidentified things). The
review of 2026-11-11: runs/stolen.txt, a list of names written by steal.py, sold my own fireproof blanket for a
stolen "blanket" (run 44), went stale when identification renamed things (run 44), and missed goods in the bags
(run 43). The file is no longer read.

Each stack is moved into the pack's own grid (a shop lists only that), the fence's wares are opened (shop.py
--keep-open), each is sold with its "Sell N" act by its uid, and the shop is closed (the Thieves Guild books the
contribution when the window closes: elin-guilds). Only Derphy (Siyun), Port Kapul (Minwer) and my own land buy
stolen goods below rank 4.

usage: python -I tools/fence.py SHOPKEEPER [--dry]
  --dry  list what would be sold and what is held back, and sell nothing (no shopkeeper needed)
Exit 0, 1 refused (nothing stolen is carried, the shopkeeper not in view), 3 stopped (the gold didn't move).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, data, last, refuse, run, setup, stop, txlog  # noqa: E402
import items as inv  # noqa: E402


def goods(carried):
    """(to sell, [(item, why held back)]) among the carried things the game marks stolen."""
    sell, held = [], []
    for it in carried:
        if not it.get("stolen"):
            continue
        # run 47: 8 stolen wall lamps were held back as "kit (light)": a thing the game marks stolen was taken minutes ago and
        # is never my kit (the worn torch is the light); the other guards (worn, unidentified, the carry list) still hold
        why = inv.protected(it, carried, kit=False)
        # run 52: runs/carry.txt's "cargo" line (run 44: "unsold stolen goods for Siyun") is there so nothing drops or
        # ships the stolen cargo before the sale; it held seven cargo containers (20 kg each) back from the fence itself
        # for runs, and their weight sat in the bags. A stolen thing on the carry list for that reason is sold here
        if why == "on the carry list (cargo)":
            why = None
        # run 54: the bow's own 28 stone arrows carried the game's stolen flag (a stolen stack merged into them once) and
        # went on Leoban's sale list: ammo is the bow's kit and pays the guild next to nothing (sqrt of ~1 oren)
        if not why and (it.get("kind") or inv.kind(it) or "").startswith("ammo"):
            why = "ammo (the bow's kit, even when the game marks it stolen)"
        if why:
            held.append((it, why))
        else:
            sell.append(it)
    return sell, held


def main():
    setup()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    if not args and not dry:
        refuse("usage: fence.py SHOPKEEPER [--dry]")
    carried = inv.inventory()
    sell, held = goods(carried)
    for it, why in held:
        print(f"  kept: {it['name']} ({inv.where(it, carried)}): {why}")
    if dry:
        for it in sell:
            print(f"  would sell: {it['name']} ({inv.where(it, carried)})")
        print(f"{len(sell)} stolen stacks to sell, {len(held)} held back")
        return
    if not sell:
        refuse("nothing stolen is carried (the game's own flag; `items.py` shows what is)")
    # run 43: thefts in the bags weren't on the shop's list (it shows only the pack's grid): 15 of 27 "not sold"
    stuck = []
    for it in sell:
        if it.get("path"):
            ok, why = inv.to_pack(it, inv.inventory())
            if not ok:
                stuck.append(f"{it['name']} ({why})")
    out = run("shop.py", args[0], "--keep-open", timeout=300)
    if out.rc != 0:
        refuse(f"shop.py: {last(out) or out.rc}")
    sold, left = [], []
    gold0 = data("state")["pc"].get("gold")
    for it in sell:
        bs = call("buttons", all=True)["data"]["buttons"]
        hit = [b for b in bs if "inventory grid" in (b.get("name") or "") and b.get("mine") is not False
               and b.get("uid") == it["uid"]]
        if not hit:
            left.append(it["name"])
            continue
        acts = call("invacts", i=hit[0]["i"]).get("data", {}).get("acts", [])
        sells = [a for a in acts if a["text"].startswith("Sell")]
        if not sells:
            left.append(it["name"])
            continue
        a = sells[-1]  # "Sell N" for the whole stack
        call("invdo", i=a["i"])
        sold.append(f"{it['name']} ({a['text']})")
        txlog("sold", it["name"], "pack", "the fence", a["text"])  # run 49: the run's item ledger
    run("close.py")
    run("talk.py")
    # run 43: 14 "sold" with the gold, the guild total and the pack unchanged: a sale counts only when the purse moved
    if sold and data("state")["pc"].get("gold") == gold0:
        stop(f"{len(sold)} Sell acts and the gold didn't move: the shopkeeper asleep or out of money? Nothing sold")
    print(f"sold {len(sold)}: " + "; ".join(sold))
    if left or stuck:
        print(f"not sold: {', '.join(left + stuck)} (not in the pack's grid: a full pack?)")
    if sold:
        print([ln for ln in run("journal.py", "guilds").splitlines() if "Thieves" in ln][-1:] or "")


if __name__ == "__main__":
    main()
