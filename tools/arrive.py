"""Arrive home (run 19, the user's rule after run 18): the scripted part of elin-home section 1, in
order, with the Dishes box shared first. leave.py made it private on the way out (dishes.py).

  1. a hostile in view, or HP under 60%, stops it (deal with that first: shoot.py, fight.py)
  2. dishes.py share: at home the residents eat only from shared boxes, with no free meal (#685);
     then a drained attribute or a harmful mutation gets its potion (cure(): run 35)
  3. packcheck.py --move: the pack, the backpack and the Cooler Box against the trip kit
  4. unpack.py --take --pickup: the mail (each package emptied into the pack and grabbed, run 45; the storage bins are left
     out), the packages shipped after the trash step; a tax bill there is paid (run 35);
     yardchests.py: treasure chests lying loose (Poppy's Treasure Hunt, run 43)
  5. trash.py (garbage piles and the pack's junk into the trash can), then town.py: G12's five checks
Then a line on food: my hunger and what the Dishes box holds (the residents eat ~8 dishes a home
day: cookdishes.py). Keep the stay short and sleep on the world map (elin-home 6).

usage: python -I tools/arrive.py
Exit: 0 done, 1 refused (not at home), 3 stopped (a threat, or the Dishes box couldn't be shared).
"""
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import base_ready, last, refuse, run, setup, state, stop, threat  # noqa: E402


BODY, MIND = ("STR", "DEX", "END", "CHA"), ("PER", "LER", "WIL", "MAG")  # Element.List_Body / List_Mind


def cure():
    """Run 35 (facts #1098-#1099): a CHA drain (the ally cap 3 -> 2, -20% speed for the party) and a twisted-legs
    mutation (-5 speed) rode along unseen for a run. Drink restore body / restore mind for a drain and cure mutation
    for a harmful mutation (bridge 0.36.0 `skills`: drains, mutations), from the pack or a carried bag; packcheck
    --move puts the stack back afterwards."""
    from common import data
    sk = data("skills")
    drains = sk.get("drains") or {}
    # run 57: "restore mind" matched a spellbook of restore mind riding in the pack as well as 6 potions: name the potion
    need = [n for n, attrs in (("potion of restore body", BODY), ("potion of restore mind", MIND))
            if any(a in drains for a in attrs)]
    if any(m.get("neg") for m in (sk.get("mutations") or {}).values()):
        need.append("potion of cure mutation")
    if not need:
        return "drains and mutations: none"
    done = []
    for what in need:
        r = run("item.py", what, "Drink")
        for bag in ("spoils bag", "backpack", "loot bag", "haul bag"):
            if r.rc == 0:
                break
            if run("bag.py", bag, "--take", what).rc == 0:
                r = run("item.py", what, "Drink")
        # run 54: "NOT FOUND" printed for 53 restore body and 6 restore mind carried (a scorpion stood in view on arrival):
        # the line names item.py's own refusal now, and only says to buy when none is carried
        done.append(f"{what} drunk" if r.rc == 0 else f"{what} NOT DRUNK (rc {r.rc}: {last(r)[:80]}; none carried? buy at Minron, Mysilia)")
    after = data("skills")
    return (f"drains {drains} -> {after.get('drains') or 'none'}; " + "; ".join(done)
            + f"; mutations left: {[m['name'] for m in (after.get('mutations') or {}).values() if m.get('neg')] or 'none'}")


def sell_step():
    """G70 M3 (run 57; the user, 2026-11-21: "a Shopkeeper in town that we can use"): what keep.py calls "sell" leaves the
    pack for Samata at home before packcheck files it into a box (the keep rule: sell unless used). Never the carried
    ammo (the bow's: packcheck's kit word "arrow"), never gear (gearcheck.py and shipstar.py first), never what
    items.protected() holds (worn, the kit, unidentified, the carry list)."""
    import items as inv
    from keep import verdict
    carried = inv.inventory()
    uids = [f"uid:{it['uid']}" for it in carried
            if verdict(it)[0] == "sell" and (it.get("kind") or "") != "ammo" and not inv.protected(it, carried)]
    if not uids:
        return "sell: nothing keep.py sells in the pack"
    out = run("sell.py", "Samata", *uids, "--find", timeout=900)
    return f"sell ({len(uids)} stacks to Samata): {last(out) or out.rc}"


def main():
    t0 = time.time()
    setup()
    s = state()
    if not s["zone"]["full"].startswith("Zone_startSite"):
        refuse(f"not at home ({s['zone']['full']})")
    if not base_ready():
        refuse("this game has no base yet (runs/no-base.txt): nothing to unload into. Sort the pack by hand for now.")
    why = threat(60, s)
    if why:
        stop(f"arrive: {why}")
    from farmday import home_guard
    home_guard("the arrival", limit=50)  # run 41: arrived at 70 with no meal landed, walked the boxes to 93 and died
    d = run("dishes.py", "share")
    print(d.strip())
    if d.rc != 0:
        stop("arrive: the Dishes box isn't shared: the residents can't eat while I'm here")
    print(cure())
    print(sell_step())
    p = run("packcheck.py", "--move", timeout=1200)  # run 35: a full unload ran past the 300 s default twice
    print(p.strip())
    home_guard("the arrival, after the unload")
    # run 45: 26 spam packages (one junk item each) had piled up around the office: this step only listed them.
    # Now it empties them into the pack and grabs each; the trash step below takes the junk, the packages ship
    mail = [ln for ln in run("unpack.py", "--take", "--pickup", timeout=900).splitlines()
            if ln.strip() and not ln.rstrip().endswith("[bin]")]
    print("\n".join(mail))
    # run 35: April's bill (4,476) lay in the mail post through two arrivals ("opened nothing": unpack opens parcels,
    # not bills); springday's pay_tax was the only payer and no farm round ran. Pay it here (paytax.py refuses short)
    from farmday import pay_tax
    tax = pay_tax()
    print(tax or "tax: no bill in the mail post")
    # run 43: seven of Poppy's chests lay in the yard, and elin-home said this tool picked them up
    y = run("yardchests.py", timeout=900)
    print(y.strip())
    if y.rc:
        stop(f"arrive: yardchests.py: {last(y) or y.rc}")
    if "none" not in last(y):
        p = run("packcheck.py", "--move", timeout=1200)
        print(p.strip())
    home_guard("the arrival, before the trash")
    # run 19: both test arrivals failed town.py on garbage until trash.py ran: sweep it first
    print("trash: " + (run("trash.py", timeout=600).strip().splitlines() or ["?"])[-2:][0])
    from common import data
    pk = [it for it in data("stock")["pack"] if it.get("id") == "cardboard_box"]
    if pk:  # run 45: the emptied mail packages ship (~17 each); a package that still holds something stays put
        print("packages: " + (run("box.py", "shipping chest", *["package"] * len(pk)).strip().splitlines() or ["?"])[-1])
    t = run("town.py")
    print("town: " + (t.strip().splitlines() or ["?"])[-1])
    # G65 (the user, run 54: "keep Fireproof Blankets in stock ... it's clearly a frequent issue"): the loom chain from
    # the boxes' skins and fiber up to 6 charged blankets, SP above the trip's floor; a short SP is a line, not a stop
    b = run("blanket.py", timeout=1200)
    print("blankets: " + " / ".join(ln.strip() for ln in str(b).splitlines()
                                     if ln.startswith(("made:", "no blankets", "stop:", "plan:"))) + f" (rc {b.rc})")
    pc = state()["pc"]
    print(f"food: my hunger {pc['hunger']} ({pc.get('hungerText') or 'ok'}); feed the residents from the "
          f"Dishes box above (cookdishes.py), keep the stay short")
    if p.rc != 0:
        print("!! packcheck left items out of place (above): put them away before leaving")
    # G46 (the user, after run 40: a short home trip): the measure, per arrival: real minutes and what had no box to go to
    m = re.search(r"out of place: (\d+)", str(p))
    minutes = (time.time() - t0) / 60
    log = Path(__file__).resolve().parent.parent / "runs" / "arrivals.csv"
    new = not log.exists()
    with log.open("a", encoding="utf-8", newline="\n") as f:
        if new:
            f.write("logged_at,game_date,minutes,out_of_place\n")
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S},{pc.get('date')},{minutes:.1f},{m.group(1) if m else ''}\n")
    print(f"arrive: {minutes:.1f} real minutes, {m.group(1) if m else '?'} out of place (runs/arrivals.csv)")


if __name__ == "__main__":
    main()
