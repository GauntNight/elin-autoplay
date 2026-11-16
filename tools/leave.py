"""Leave a local outdoor map (ambush site, wilds, home) back to the world map through the
nearest border cell that offers "Enter". If no explored border cell is known (ambush maps
start mid-map, run 03), walk straight toward the nearest side of the map's bounds (bridge
0.11.0 `zone.bounds`) and look again. Refuses (exit 1) while a hostile is in view unless --force,
and at home while the pack holds items off the trip kit, holds no shovel, carries under 3 fireproof blankets
or 5 lockpick charges while storage holds more, or the Dishes box is shared; anywhere, while the party is over the ally cap. Stops
(exit 3) when a dialog opens on the way out (an escort client out of reach: answered No), when a
hostile comes into view or stands adjacent on the way to the edge, and when no exit is found.

usage: python -I tools/leave.py [--force] [--pack-ok] [--dishes-ok] [--gear-ok] [--shovel-ok] [--food-ok]
                                [--blanket-ok 'why'] [--pick-ok 'why'] [--party-ok] [--rations-ok]
At home it first checks the pack (packcheck.py) and makes the Dishes box private (dishes.py). --blanket-ok and --pick-ok
need a reason, and leaving short of either writes a row to runs/waivers.csv, which the close-out reports (the user, 2026-11-06).
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import log_waiver, overweight_stop, cells, refuse, run, stop, wait_until, waiver_reason, walk  # noqa: E402

MIN_MEALS = 6  # the Upkeep block: 3+ days of my own food at departure, ~2 meals a day (run 32: a nefia at hunger 68)
MIN_RATIONS = 2  # run 38: the Upkeep block's 'the next fare + 1' (the near fares are 1-2)
MIN_BLANKETS = 3  # the Upkeep block (the user, 2026-10-26): G23's fireproof blankets, 3 always in the pack
MIN_PICK_CHARGES = 5  # the Upkeep block (the user, 2026-11-06): about two locked chests; run 42 spent 14 charges on five


def count(items, match):
    """Pieces of things in `items`, and in any bag among them, whose name passes `match`."""
    return sum((it.get("num") or 1) * bool(match(it["name"])) + count(it.get("items") or [], match) for it in items)


def carried(match):
    """Pieces of carried things whose name passes `match`, in the pack and every carried bag (the Cooler Box
    included): bridge `stock`'s pack tree. Run 32: the shovel sat in the spoils bag while the old check, which
    read only the pack's own grid, called it missing all night."""
    from common import data
    return count(data("stock")["pack"], match)


def trip_meals():
    """Meals for the trip, counted by the same reader the eating does (items.meals, by kind at any depth). Run 49: the
    old count went by farmday's name list and passed six "meals" while eat_one had nothing it would eat (5 travel
    rations, all of them the Fast Travel reserve), and the first nefia stopped Hungry on B1. Rations count only above
    the reserve; run 36: stale food doesn't count (it rots on the road); run 44: three mini salads are one meal."""
    from items import RATION_RESERVE, meals
    whole = minis = 0
    for it in meals(0):
        name = (it.get("name") or "").lower()
        n = it.get("num") or 1
        if "stale" in name:
            continue
        if it.get("kind") == "ration":
            n = max(0, n - RATION_RESERVE)
        if re.search(r"\bmini\b", name):
            minis += n
        else:
            whole += n
    return whole + minis // 3


def blanket(name):
    """A fireproof blanket with a charge left ("a fireproof blanket (4 Charges)"): each charge saves the pack's
    items from one fire (fact #862)."""
    m = re.search(r"\((\d+) charges?\)", name.lower())
    return "fireproof blanket" in name.lower() and (m is None or int(m.group(1)) > 0)


def pick_charges(items):
    """Charges on the usable lockpicks in `items` and any bag among them ("a lockpick (16 Charges)"). A name showing no
    count reads as enough, as blanket() does; common.grab won't hold a cursed or doomed pick, so those count for nothing."""
    n = 0
    for it in items or []:
        low = it["name"].lower()
        if "lockpick" in low and "cursed" not in low and "doomed" not in low:
            m = re.search(r"\((\d+) charges?\)", low)
            n += (int(m.group(1)) if m else MIN_PICK_CHARGES) * (it.get("num") or 1)
        n += pick_charges(it.get("items"))
    return n


def try_enter(zone, r_max=12):
    """Use an explored border cell with Enter within r_max of me. Run 06: probing every cell in
    12 rings took hundreds of bridge calls and timed out; only cells on the map's bounds can be
    an edge, so check those, nearest first, and in one `cells` call (the review of 2026-10-23:
    ~100 `cell` calls per try before)."""
    s = call("state")["data"]
    b = s["zone"].get("bounds")
    p = s["pc"]
    if b:
        x0, z0, x1, z1 = (int(v) for v in b.split(","))
        cand = set()
        for x in range(p["x"] - r_max, p["x"] + r_max + 1):
            for z in range(p["z"] - r_max, p["z"] + r_max + 1):
                # the Enter cells lie one outside the bounds (run 06: bounds 36..64, edge at 65)
                if x in (x0 - 1, x0, x1, x1 + 1) or z in (z0 - 1, z0, z1, z1 + 1):
                    cand.add((x - p["x"], z - p["z"]))
        ring = sorted(cand, key=lambda d: max(abs(d[0]), abs(d[1])))
    else:
        ring = [(dx, dz) for r in range(1, r_max + 1) for dx in range(-r, r + 1)
                for dz in range(-r, r + 1) if max(abs(dx), abs(dz)) == r]
    pts = [(p["x"] + dx, p["z"] + dz) for dx, dz in ring]
    info = cells(pts)
    for (dx, dz), xz in zip(ring, pts):
        if not (info.get(xz) or {}).get("edge"):
            continue
        acts = call("acts", dx=dx, dz=dz, mode="all")["data"]["acts"]
        ent = [a for a in acts if a["text"] == "Enter"]
        if ent:
            call("do", i=ent[0]["i"])
            # the bridge's wait watches the zone (5 s at a time); the abandon dialog is checked
            # between waits, since one wait can't watch the zone and the top layer at once
            for _ in range(8):
                w = wait_until("zone", timeout=5000, zone=zone)
                if w.get("done") and w.get("zone") != zone:
                    return True
                st = call("state")["data"]
                if st["zone"]["full"] != zone:
                    return True
                # run 17: with the escort client out of reach the game asks "Really abandon the
                # quest and leave?" and this loop sat on it for minutes (the user caught it: "best
                # to not abandon the quest and find him"). Answer No and stop: find the client.
                if (st.get("layers") or {}).get("top") == "Dialog":
                    texts = " ".join(call("texts")["data"].get("texts") or [])
                    no = [b for b in call("buttons")["data"]["buttons"] if (b.get("text") or "").strip().endswith("No.")]
                    if "abandon" in texts.lower() and no:
                        call("click", i=no[0]["i"])
                        stop("leaving would abandon a quest (an escort client out of reach): answered No; find the client first")
                    stop(f"a dialog opened on the way out: {texts[:120]}")
            return False
    return False


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    blanket_why, pick_why = waiver_reason("--blanket-ok"), waiver_reason("--pick-ok")  # a bare flag stops here, before any step
    overweight_stop("leaving this map")
    # run 42: a wgo --ambush stopped with "could not find an exit": ConEntangle refuses every step (ConEntangle.TryMove) and wears off with turns
    for _ in range(30):
        p = call("state")["data"].get("pc") or {}
        if "ConEntangle" not in (p.get("conds") or p.get("conditions") or []):
            break
        call("act", action="Wait")
        time.sleep(0.25)
    s = call("state")["data"]
    # run 35: the 05:00 shipping report opened on an ambush map and wgo's leave.py stopped on it (the game ignores
    # a step under it); read the income and close it here, as springday and the circuit do
    if (s.get("layers") or {}).get("top") == "LayerShippingResult":
        from farmday import close_report
        s = close_report(s)
    foes = [c for c in s.get("nearby") or [] if c["hostile"]]
    if foes and "--force" not in sys.argv:
        refuse("hostiles in view: " + ", ".join(f"{c['name']} Lv{c['lv']} d{c['dist']}" for c in foes))
    zone = s["zone"]["full"]
    # a new game has no base yet (tools/newgame.py): the rules about leaving one wait until there is one
    from common import base_ready
    at_base = zone.startswith("Zone_startSite") and base_ready()
    # run 24: mounted on Kaberg my speed is 82, not 121 (Chara.RefreshSpeed): riding is home work
    if s["pc"].get("riding") and "--riding-ok" not in sys.argv:
        refuse(f"riding {s['pc']['riding']}: dismount first (bridge.py ride off; my speed is the mount's), "
               "or --riding-ok")
    # The user, run 11: the pack must be cleared of everything off the trip kit every time I leave
    # home ("it is a loss of treasure by not having those slots free"). packcheck.py lists it and
    # names the box; `packcheck.py --move` carries it there. --pack-ok skips (a deliberate haul).
    if at_base and "--pack-ok" not in sys.argv:
        r = run("packcheck.py")
        if r.rc != 0:
            print(r)
            refuse("leaving home refused: the pack holds items off the trip kit (packcheck.py --move, "
                   "then leave again; --pack-ok only for a deliberate haul)")
    # run 35: three allies over a cap of 2 (CHA 18) slowed the whole party 20% for half of run 34 (fact #1093)
    if "--party-ok" not in sys.argv:
        from common import party_cap
        allies, cap, cha = party_cap(s)
        if allies > cap:
            refuse(f"party over the cap: {allies} allies, cap {cap} (CHA {cha} / 10 + Party Animal): -20% speed for "
                   "everyone and Lonely Soul's loss; talk to one ally, 'Wait at your home' (--party-ok to go anyway)")
    # the user, run 29: "always a full set of gear" (the arm slot sat empty with ☆Forest Gloves in the pack):
    # no leaving home with an empty slot (common.empty_slots; --gear-ok when nothing fits it yet)
    if at_base and "--gear-ok" not in sys.argv:
        from common import empty_slots
        gaps = empty_slots()
        if gaps:
            refuse("leaving home refused: empty gear slot(s): " + ", ".join(gaps) + " (wear the best piece in "
                   "hand, buy one, or --gear-ok when nothing fits yet)")
    # the user, 2026-10-29: "you need to carry a shovel and dig for medals" (medals.py; packcheck's KIT keeps it)
    if at_base and "--shovel-ok" not in sys.argv:
        if not carried(lambda n: "shovel" in n.lower()):
            refuse("leaving home refused: no shovel in the pack (box.py \"Farm\" --take shovel; "
                   "--shovel-ok to leave without one)")
    # run 32: the Upkeep block's food rule was only a line in goals.md; the night's first nefia began at hunger 68
    # with nothing eat_one would take (the bread was in the loot bag, the Cooler Box held raw fish and corpses)
    if at_base and "--food-ok" not in sys.argv:
        meals = trip_meals()
        if meals < MIN_MEALS:
            refuse(f"leaving home refused: {meals} meals carried, under {MIN_MEALS} (3 days): restock the Cooler Box "
                   "(food in the bags doesn't count: eat_one never looks there) from the harvest box or a pantry, or --food-ok")
    # the user, 2026-10-30: "add Fire Blankets to the list of things to try to get before we leave home". G23 made
    # six in run 28, but packcheck's KIT never named them, so its --move could carry them back into storage
    # the user, 2026-11-06: run 42 never met the 3 and said so only at the end, so going short now leaves a row either way
    if at_base:
        have = carried(blanket)
        if have < MIN_BLANKETS and blanket_why:
            print(f"short of fireproof blankets: {have} carried, under {MIN_BLANKETS} (--blanket-ok: {blanket_why})")
            log_waiver("leave", f"{have} fireproof blankets carried, under {MIN_BLANKETS}", blanket_why)
        elif have < MIN_BLANKETS:
            from common import data
            stored = [f"{b['name']} {b['x']},{b['z']}" for b in data("stock")["boxes"]
                      if count(b.get("items") or [], blanket)]
            if stored:
                refuse(f"leaving home refused: {have} fireproof blankets carried, under {MIN_BLANKETS}, and storage "
                       f"holds more: {', '.join(stored)} (box.py \"BOX\" --take \"fireproof blanket\"; --blanket-ok 'why')")
            print(f"short of fireproof blankets: {have} carried, under {MIN_BLANKETS}, none in storage: make them at the "
                  "loom (5 textures + 4 carbon logs from the kiln), the sure source, or buy one (Sesa or Sayig in Aquli "
                  "Teola, Gizbird in Mysilia, ~360, stock at random)")
            log_waiver("leave", f"{have} fireproof blankets carried, under {MIN_BLANKETS}", "none in storage: warned, not refused")
    # the user, 2026-11-06: nothing checked for a lockpick, and the ladder leaves behind a chest bare hands can't open
    # (run 42: five locked map chests held 8,699 orens, 10 bars, 7 medals). No station makes one (fact on the lockpick):
    # shops only, so an empty storage warns, as the blankets and rations do
    if at_base:
        from common import data
        st = data("stock")
        have = pick_charges(st["pack"])
        if have < MIN_PICK_CHARGES and pick_why:
            print(f"short of lockpick charges: {have} carried, under {MIN_PICK_CHARGES} (--pick-ok: {pick_why})")
            log_waiver("leave", f"{have} lockpick charges carried, under {MIN_PICK_CHARGES}", pick_why)
        elif have < MIN_PICK_CHARGES:
            stored = [f"{b['name']} {b['x']},{b['z']}" for b in st["boxes"] if pick_charges(b.get("items"))]
            if stored:
                refuse(f"leaving home refused: {have} lockpick charges carried, under {MIN_PICK_CHARGES}, and storage "
                       f"holds more: {', '.join(stored)} (box.py \"BOX\" --take lockpick; --pick-ok 'why')")
            print(f"short of lockpick charges: {have} carried, under {MIN_PICK_CHARGES}, none in storage: no station makes "
                  "one, so buy on the next town trip (stock at random, 330-780: Sayig or Sesa in Aquli Teola, Gizbird in "
                  "Mysilia, Tarraf in Palmia, Alecgan in Noyel, Kerona in Derphy)")
            log_waiver("leave", f"{have} lockpick charges carried, under {MIN_PICK_CHARGES}", "none in storage: warned, not refused")
    # run 44: the sleeping bag left the pack at a home sort, and the next long walk stopped Very Sleepy ("There's no bed
    # in your backpack"); sleep.py on the road needs a bed carried. Refuse while storage holds one; else warn (the Rest
    # ability sleeps without a bed: fact on Rest)
    if at_base and "--bed-ok" not in sys.argv:
        from common import data
        st = data("stock")

        def bed(name):
            n = name.lower()
            # run 46: "a stupid futon" (Kazretta, Palmia, 2,741) slept the music loop, and this said no bed was carried
            return ("sleeping bag" in n or "makeshift bed" in n or n.endswith(" bed") or " bed " in n
                    or "futon" in n or "hammock" in n)

        if not carried(bed):
            stored = [f"{b['name']} {b['x']},{b['z']}" for b in st["boxes"] if count(b.get("items") or [], bed)]
            if stored:
                refuse(f"leaving home refused: no bed carried, and storage holds one: {', '.join(stored[:3])} "
                       "(box.py \"BOX\" --take \"sleeping bag\"; --bed-ok to go anyway)")
            print("no bed carried and none in storage: sleep on the road with the Rest ability (fact on Rest)")
    # run 38: goals.md's Upkeep says leave.py checks "travel rations on hand (the next fare + 1)", but nothing did: I
    # left with none, and a Fast Travel back from Capricious Forest (2) was impossible. The blanket's shape: refuse
    # while storage holds rations, else say where to buy them (inns: Upan, Tiguen, Robean, 47 each)
    if at_base and "--rations-ok" not in sys.argv:
        def ration(name):
            return "travel ration" in name.lower()
        have = carried(ration)
        if have < MIN_RATIONS:
            from common import data
            stored = [f"{b['name']} {b['x']},{b['z']}" for b in data("stock")["boxes"]
                      if count(b.get("items") or [], ration)]
            if stored:
                refuse(f"leaving home refused: {have} travel rations carried, under {MIN_RATIONS}, and storage holds "
                       f"more: {', '.join(stored)} (box.py \"BOX\" --take \"travel ration\"; --rations-ok)")
            print(f"short of travel rations: {have} carried, under {MIN_RATIONS} (a Fast Travel costs 1 + days): buy them "
                  "at an inn (Upan in Olvina, Tiguen in Mysilia, Robean in Lumiest, 47) on the way")
    # run 19 (the user, after run 18): away from home the residents eat free only when no shared box
    # holds prepared food, so the Dishes box goes private on the way out (arrive.py shares it again).
    if at_base and "--dishes-ok" not in sys.argv:
        r = run("dishes.py", "unshare")
        print(r.strip())
        if r.rc != 0:
            refuse("leaving home refused: the Dishes box is still shared (--dishes-ok to leave anyway)")
    for attempt in range(8):
        if try_enter(zone):
            print(f"left {zone} -> {call('state')['data']['zone']['full']}")
            return
        b = s["zone"].get("bounds")
        if not b:
            break
        x0, z0, x1, z1 = (int(v) for v in b.split(","))
        p = call("state")["data"]["pc"]
        # Head for the nearest side, 10 steps at a time, then look for an exit again.
        sides = sorted([(p["x"] - x0, (-1, 0)), (x1 - p["x"], (1, 0)), (p["z"] - z0, (0, -1)), (z1 - p["z"], (0, 1))])
        # Run 06: a ledge blocked the nearest side and every attempt pushed into it; when a side
        # doesn't move me, try the next nearest one.
        dist, (sx, sz) = sides[attempt % 4] if attempt < 4 else sides[0]
        print(f"no exit seen; walking toward the edge {dist} cells away ({sx:+d},{sz:+d})")
        # run 17: from mid-home every side's straight steps ran into walls and furniture eight
        # times over; the game's own pathing (walkto) to a cell beside that edge goes around them
        # (explored cells only: where it refuses, the steps below still run)
        tx = x0 + 1 if sx < 0 else x1 - 1 if sx > 0 else p["x"]
        tz = z0 + 1 if sz < 0 else z1 - 1 if sz > 0 else p["z"]
        # Start Run 1: --force means fleeing, and r=2, hp=60 cancelled the walk at once beside any foe or under 60% HP, exactly when it is needed:
        # "could not find an exit" stood in two of three deaths at the map's middle. A fleeing walk goes on until the edge.
        force = "--force" in sys.argv
        w = walk(tx, tz, r=0 if force else 2, hp=1 if force else 60, timeout=60000)
        if w.get("why") == "hostile":
            stop(f"a hostile came into view on the way to the edge: {w.get('hostile')} Lv{w.get('hostileLv')} at {w.get('hostileDist')}")
        if w.get("done") and try_enter(zone):
            print(f"left {zone} -> {call('state')['data']['zone']['full']}")
            return
        pc0 = call("state")["data"]["pc"]
        hp0, wet0 = pc0["hp"], "ConWet" in (pc0.get("conditions") or [])
        # run 42: a sea-bed ambush map (the cloak floats me over water on the world map) walled a water breather in behind these checks
        breathes = pc0.get("breathesWater")
        for _ in range(min(10, dist + 1)):
            # Run 07 death: these blind steps walked into the Derphy den's sea in the dark and I
            # drowned. Never step onto water or an unexplored cell; stop when wet or losing HP.
            nxt = call("cell", dx=sx, dz=sz)
            # run 19: a river of "shallow water" walled an ambush map in; shallow water only wets
            nd = nxt.get("data") or {}
            if not breathes and (not nxt.get("ok") or nd.get("suffocate") is True or (nd.get("water") and "shallow" not in str(nd.get("floor") or ""))):
                print(f"  stopped: the next cell is {'water' if nxt.get('ok') else nxt.get('error')}")
                break
            call("step", dx=sx, dz=sz)
            time.sleep(0.45)
            pc = call("state")["data"]["pc"]
            # run 26: already wet, the wet check never fired and the steps went on into deep water
            # (ConSuffocation at full HP: a teleport scroll got me out): in water at all is a stop
            if not breathes and (pc.get("inWater") or "ConSuffocation" in (pc.get("conditions") or [])):
                print(f"  stopped: in water (HP {pc['hp']}): stepping back")
                call("step", dx=-sx, dz=-sz)
                break
            if ("ConWet" in (pc.get("conditions") or []) and not wet0 and not breathes) or (pc["hp"] < hp0 and not force):
                print(f"  stopped: wet or hurt (HP {pc['hp']})")
                call("step", dx=-sx, dz=-sz)
                break
        s = call("state")["data"]
        if any(c["hostile"] and c["dist"] <= 1 for c in s.get("nearby") or []) and "--force" not in sys.argv:
            stop("a hostile is adjacent: deal with it first")
        # Start Run 3, two deaths: 56 -> -4 and 43 -> -4 HP on a flee that moved one cell in 30-40 turns (steps into a foe's cell are attacks, walks that go nowhere
        # still pass turns). A flee that isn't moving hands back at once: fight, or use an item.
        q = s["pc"]
        moved = abs(q["x"] - p["x"]) + abs(q["z"] - p["z"])
        if force and moved < 2:
            stop(f"the flee isn't moving ({moved} cells this attempt, HP {q['hp']}/{q['maxHp']}): fight or use an item")
    stop("could not find an exit")


if __name__ == "__main__":
    main()
