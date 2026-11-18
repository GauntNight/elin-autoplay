"""Stock caps across the pack, its bags and every home container (the user, run 27: "174 Casts of Short
Teleport ... set a threshold of not needing more than ~100 of a spell. After that we can sell the books
... a lot of rods (2x Holy light, etc) ... things in containers as well as things we have and create
some reasonable maximum thresholds"). Bridge 0.33.0's read-only `stock` op lists every box at once.

Each spellbook, rod, potion and scroll is sorted into keep, read (a book of a spell under its cap of
casts: reading it turns charges into casts and trains Literacy) or excess (over its cap, cursed, empty,
or a kind I never use), by the CAPS below. The copies kept are the best ones (blessed, then most
charges, then already in the pack). Excess goes to the shipping chest (shipping pays the shop formula
x1.1, fact #446), box by box, as many as the pack's free cards carry.

usage: python -I tools/stock.py                 the caps table and what is over it (nothing moves)
       python -I tools/stock.py --ship [N]      carry up to N excess stacks to the shipping chest
       python -I tools/stock.py --read [N]      read up to N books of spells under the cap, to the last charge
       python -I tools/stock.py --list KIND     every copy of one kind ("rod of speed") with its place
       python -I tools/stock.py --find TEXT ...  every stack of anything, capped or not, with its place and count
Exit 0 done, 1 refused, 2 bridge, 3 stopped (the pack full, the shipping chest full).
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data, last, refuse, run, setup, stop  # noqa: E402
from home import SHIPPING, SPARES, BOX_STR  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SPELL_CAP = 100  # casts a spell (the user's ~100)
NEVER_SELLS = re.compile(r"recipe of .*\(Learned|statue of Creator|casino chip", re.I)  # run 42: unsold through two mornings' payouts (fact: shipping chest)

# Rods by kind: how many to keep (the most charges). Heals and escapes keep every charged one.
# run 40: teleport and cure minor wound 99 -> 4: twelve and eleven rods rode in the bags, a quarter of their slots, with the bags full
# every three conquests and 15 teleport scrolls and 50 cure potions in the pack anyway (the user's stock caps, run 27: rods ship)
ROD_KEEP = {"teleport": 4, "cure minor wound": 4, "cure critical wound": 99, "cure major wound": 99,
            "healing": 99, "speed": 2, "identify": 1, "death bolt": 1, "holy light": 1, "holy shield": 1,
            "slow": 1, "web": 1, "mind funnel": 1, "nerve missile": 1, "fire missile": 1, "light bolt": 1,
            "lightning bolt": 1, "bane": 1, "mist of darkness": 1, "uncurse": 1, "magic map": 1}
ROD_NEVER = ("summon animal", "summon shadow", "strip blessing", "summon monster")  # hostile summons, my own buffs off
# Potions: heals keep all; debuffs and the useless go; the rest 5 of a kind.
POTION_ALL = ("cure", "healing", "troll blood", "restore body", "restore mind")
POTION_NEVER = ("weakness", "weaken resistance", "strip blessing", "mutation", "blindness", "confusion",
                "paralysis", "sleep", "poison", "salt solution", "dirty water", "infravision", "ultravision")
POTION_CAP = 5
# Scrolls: escapes keep (to a cap); levitate is the Ether Wing's job (run 27).
SCROLL_KEEP = {"teleport": 99, "return": 8, "evacuation": 6, "identify": 10, "enchant weapon": 99,
               "enchant armor": 99, "magic map": 10, "uncurse": 3, "exterminate": 3}  # run 34: magic map: the ladder reads one when no stairs down are seen
SCROLL_NEVER = ("levitate", "summon shadow", "summon monster", "curse")
SCROLL_CAP = 3

KINDS = {"bolt": "bolt_", "arrow": "arrow_", "touch": "hand_", "ball": "ball_", "funnel": "funnel_",
         "mist": "miasma_", "storm": "storm_", "breath": "breathe_"}


def spell_names():
    """Spellbook title -> spell alias, from the game's element table (kb.py's export): named spells by
    name ("nature's embrace" -> SpHOT), elemental ones by element word + kind ("ice bolt" -> bolt_Cold)."""
    rows = json.loads((ROOT / "knowledge" / "game" / "elements.json").read_text(encoding="utf-8"))
    names = {}
    for r in rows:
        a = str(r.get("alias") or "")
        # run 48: Telekinesis is type ActTelekinesis (group SPELL): its books read "spell unknown to the table" and kept
        # piling into the library chain until every box refused
        if (r.get("type") == "Spell" or r.get("group") == "SPELL") and r.get("name"):
            names[str(r["name"]).lower()] = a
    for r in rows:
        a = str(r.get("alias") or "")
        if a.startswith("ele") and r.get("altname"):
            word = str(r["altname"]).split(",")[0].lower()
            for kind, prefix in KINDS.items():
                names[f"{word} {kind}"] = prefix + a[3:]
    return names


def base(name):
    """'a blessed rod of speed (5 Charges)' -> ('rod', 'speed', 'blessed', 5)."""
    n = name.lower()
    bless = "cursed" if re.search(r"\b(cursed|doomed)\b", n) else "blessed" if "blessed" in n else ""
    m = re.search(r"\((\d+) charges?\)", n)
    charges = int(m.group(1)) if m else None
    n = re.sub(r"\s*\(\d+ charges?\)", "", n)
    n = re.sub(r"\s*\(learned[^)]*\)", "", n)
    m = re.match(r"^(?:an? |\d+ )?(?:(?:blessed|cursed|doomed) )?(spellbooks?|rods?|potions?|scrolls?) of (.+)$", n)
    if not m:
        return None
    return m.group(1).rstrip("s"), m.group(2).strip(), bless, charges


def walk_items(items, where, out, bag=None):
    for i in items or []:
        if i.get("equipped"):
            continue
        out.append({"name": i["name"], "num": i.get("num") or 1, "where": where, "bag": bag})
        if i.get("items"):
            walk_items(i["items"], where, out, bag=i["name"])


def inventory():
    d = data("stock")
    out = []
    walk_items(d.get("pack"), "pack", out)
    for b in d.get("boxes") or []:
        if b.get("items"):
            walk_items(b["items"], f"{b['x']},{b['z']}", out)
    return d, out


def decide(items, stock):
    """Sort each copy: keep / read / excess, with a reason."""
    names = spell_names()
    groups = defaultdict(list)
    for it in items:
        b = base(it["name"])
        if b:
            it["kind"], it["what"], it["bless"], it["charges"] = b
            groups[(b[0], b[1])].append(it)
    plan = []

    def rank(it):  # best first: blessed, most charges, already in the pack (no walk)
        return ({"blessed": 0, "": 1, "cursed": 2}[it["bless"]], -(it["charges"] or 0), it["where"] != "pack")

    for (kind, what), copies in sorted(groups.items()):
        copies.sort(key=rank)
        if kind == "spellbook":
            alias = names.get(what)
            have = stock.get(alias) if alias else None
            for it in copies:
                if it["bless"] == "cursed":
                    plan.append((it, "excess", "cursed: a read can go wrong"))
                elif what in ("summon monster",):  # run 28: the spell calls hostiles; never learn it
                    plan.append((it, "excess", "a hostile summon"))
                elif alias is None:
                    plan.append((it, "keep", "spell unknown to the table"))
                elif (have or 0) >= SPELL_CAP:
                    plan.append((it, "excess", f"{alias} at {have} casts (cap {SPELL_CAP})"))
                else:
                    plan.append((it, "read", f"{alias} at {have or 0} casts"))
            continue
        if kind == "rod":
            keep = 0 if any(w in what for w in ROD_NEVER) else ROD_KEEP.get(what, 1)
        elif kind == "potion":
            keep = (99 if any(w in what for w in POTION_ALL) else
                    0 if any(w in what for w in POTION_NEVER) else POTION_CAP)
        else:
            keep = (0 if what in SCROLL_NEVER else  # whole names: "curse" is in "uncurse"
                    next((v for k, v in SCROLL_KEEP.items() if what == k), SCROLL_CAP))
        kept = 0
        for it in copies:
            if it["bless"] == "cursed":
                plan.append((it, "excess", "cursed"))
            elif kind == "rod" and it["charges"] == 0:
                plan.append((it, "excess", "empty"))
            elif kept < keep:
                kept += it["num"] if kind != "rod" else 1
                plan.append((it, "keep", f"{kept} of {keep if keep < 99 else 'all'}"))
            else:
                plan.append((it, "excess", f"over the cap of {keep}"))
    # run 34: the three armories were full (packcheck's gear refused at 66,51, 48,59 and 42,50) and the bags never
    # emptied, so the ladder's room check stopped four times in one run. Residents take what beats their gear at once;
    # plain material gear still lying in an armory is shipped (never ☆/★ artifacts, unidentified or superior pieces)
    import home
    import purge
    armories = {f"{x},{z}" for (x, z) in (home.ARMORY, home.ARMORY2, home.ARMORY3, home.ARMORY4)}
    plain = re.compile(rf"^(an? |\d+ )?(blessed )?(pair of )?{purge.MATERIALS} .*{purge.GEAR}")
    for it in items:
        if it["where"] not in armories or it.get("bag"):
            continue
        n = it["name"]
        if re.search(r"[☆★]|\((miracle|godly|superior|legendary|mythical)\)", n, re.I):
            continue
        if plain is not None and plain.search(n.lower()):
            plan.append((it, "excess", "plain gear left in an armory (the residents took what beats theirs)"))
    # run 49: 246 gene stacks filled the valuables chain and the Storage Chests (55 in one), and every arrival's sort was
    # refused there. G38 (the gene-built crew) is done and the circuits run solo since run 38: a plain or inferior gene is
    # excess (an inferior one gives nothing: fact #1112); a superior gene stays, the Gene Machine's best for a crew later
    for it in items:
        n = it["name"].lower()
        if re.search(r"\bgenes? of\b", n) and "superior" not in n and "★" not in it["name"]:
            plan.append((it, "excess", "a plain or inferior gene: the crew is done (G38), solo since run 38"))
    return plan


def show(plan):
    for verdict in ("excess", "read", "keep"):
        rows = [p for p in plan if p[1] == verdict]
        print(f"\n{verdict.upper()} ({len(rows)} stacks)")
        for it, _, why in sorted(rows, key=lambda p: (p[0]["where"], p[0]["name"])):
            bag = f" > {it['bag']}" if it["bag"] else ""
            print(f"  {it['where']:>6}{bag}: {it['name']}  ({why})")


def free_cards(d):
    """The pack's free grid cards (35, packcheck.GRID_CARDS): stacks in the pack itself, not its bags."""
    return 35 - sum(1 for i in d.get("pack") or [] if not i.get("equipped"))


def unclog(d):
    """Run 42: 13 learned recipes, a statue of Creator and a casino chip sat through two mornings' payouts: what the chest won't sell keeps its slot, and it holds 40, so the
    day's shipment was 25. They come out first, to the spares wagon (the trash can refuses a recipe, run 42)."""
    stuck = [x.get("name") for x in d.get("shipping") or [] if NEVER_SELLS.search(x.get("name") or "")]
    while stuck:
        room = free_cards(data("stock"))
        if room <= 1:
            print(f"  unclog: no free card for {len(stuck)} stacks that never sell")
            return
        batch, stuck = stuck[:room - 1], stuck[room - 1:]
        out = run("box.py", BOX_STR(SHIPPING), "--take", *batch)
        if out.rc:
            print(f"  unclog: {out.strip()[-120:]}")
            return
        print("  unclog: " + last(run("box.py", BOX_STR(SPARES), *batch, timeout=300))[:100])


def ship(plan, d, limit):
    unclog(d)
    # run 30: the carried bags held most of the excess and were skipped; a bag's rows come out through
    # bag.py --take (one level deep: the pack's own bags, never a box's)
    rows = [p[0] for p in plan if p[1] == "excess" and (not p[0]["bag"] or p[0]["where"] == "pack")]
    by_box = defaultdict(list)
    for it in rows:
        by_box[(it["where"], it["bag"] or "")].append(it["name"])
    moved = 0
    # the pack's own excess first (no take), then its bags, then box by box
    order = sorted(by_box, key=lambda k: (k[0] != "pack", k[1] != ""))
    from farmday import home_guard  # run 41: a walk at home has stops; this one had none (added run 42)
    for where, bag in order:
        names = by_box[(where, bag)]
        while names and moved < limit:
            home_guard("stock --ship")
            if where != "pack" or bag:
                d = data("stock")
                room = free_cards(d)
                if room <= 0:
                    stop("the pack is full: no card free to carry the excess (box or bag a stack)")
                batch = names[:min(room, limit - moved)]
                r = run("bag.py", bag, "--take", *batch) if bag else run("box.py", where, "--take", *batch)
                print(r)
                # run 51 (twice): two rods of one name in a batch, the second "not in the bag", and the stop here left the
                # taken ones stranded in the pack (34 stacks): ship what came out, stop only when nothing did
                if r.rc != 0 and ": moved" not in str(r):
                    stop(f"{'bag.py ' + bag if bag else 'box.py ' + where} --take refused (rc {r.rc})")
            else:
                batch = names[:limit - moved]
            r = run("box.py", BOX_STR(SHIPPING), *batch)
            print(r)
            if r.rc != 0 and ": moved" not in str(r):
                # run 53: the chest was full for the morning (40 stacks) after a batch came out of a box, and the rods and
                # scrolls stayed in the pack (the next decode found no free card): what was taken goes back where it was
                if where != "pack" or bag:
                    back = run("bag.py", bag, *batch) if bag else run("box.py", where, *batch)
                    print(f"  the chest refused: back to {bag or where}: {last(back)[:80]}")
                stop(f"box.py shipping refused (rc {r.rc}): is the shipping chest full?")
            moved += len(batch)
            names = names[len(batch):]
    print(f"shipped {moved} stacks")


def read_books(plan, limit):
    """Take each book to read out of its box (one at a time: two of a spell would make its name ambiguous)
    and read it until it falls apart. Stops on a hostile, a bad condition or a window (common.ready); a
    failed read costs a charge and one of four mishaps (TraitBaseSpellbook.ReadFailEffect: half the MP,
    confusion, weak monsters, a teleport on this map), so a confused reader waits it out first."""
    import time
    from common import ready, wait_idle
    books = [p[0] for p in plan if p[1] == "read"]
    books.sort(key=lambda it: it["where"] != "pack")
    read = 0
    for it in books[:limit]:
        title = re.sub(r"\s*\(\d+ charges?\)", "", it["name"], flags=re.I)
        title = re.sub(r"^an? ", "", title)
        if it["bag"]:
            r = run("bag.py", it["bag"], "--take", it["name"])
            print(r)
        elif it["where"] != "pack":
            if free_cards(data("stock")) <= 0:
                stop("the pack is full: no card free for a book")
            r = run("box.py", it["where"], "--take", it["name"])
            print(r)
            if r.rc != 0:
                stop(f"box.py {it['where']} --take refused (rc {r.rc})")
        for _ in range((it["charges"] or 1) + 2):
            for _wait in range(20):
                why = ready(hunger=None, hp=50)
                if not why or "Con" not in why:
                    break
                time.sleep(3)  # confused or dim: stay put until it clears (elin-play)
            if why:
                stop(f"not reading: {why}")
            left = [i["name"] for i in data("inv")["items"] if title.lower() in i["name"].lower()]
            if not left:
                break
            before = {s["spell"]: s["stock"] for s in data("power")["party"][0].get("spells") or []}
            r = run("item.py", left[0], "Read")
            if r.rc != 0:
                stop(f"item.py Read refused: {r}")
            wait_idle(timeout=90000)
            after = {s["spell"]: s["stock"] for s in data("power")["party"][0].get("spells") or []}
            gain = {k: after[k] - before.get(k, 0) for k in after if after[k] != before.get(k, 0)}
            print(f"  read {left[0]}: {gain or 'no gain (a failed read?)'}")
            read += 1
    print(f"{read} reads")


def main():
    setup()
    args = sys.argv[1:]
    d, items = inventory()
    if d.get("zone") != "startSite" and "--anywhere" not in args:
        refuse(f"at home only (zone {d.get('zone')}): the boxes are the Meadow's")
    if "--find" in args:  # run 41: any item at all, not only the kinds under a cap (materials for a craft, a tally)
        for want in args[args.index("--find") + 1:]:
            hits = [it for it in items if want.lower() in it["name"].lower()]
            print(f"{want}: {sum(it['num'] for it in hits)}")
            for it in hits:
                print(f"  {it['where']:>6}{' in ' + it['bag'] if it['bag'] else ''}: {it['name']}")
        return
    stock = {s["spell"]: s["stock"] for s in data("power")["party"][0].get("spells") or []}  # me, not Kaberg
    plan = decide(items, stock)
    if "--list" in args:
        want = args[args.index("--list") + 1].lower()
        for it, verdict, why in plan:
            if want in it["name"].lower():
                print(f"  {verdict:>6}  {it['where']:>6}: {it['name']}  ({why})")
        return
    if "--read" in args:
        i = args.index("--read")
        read_books(plan, int(args[i + 1]) if i + 1 < len(args) and args[i + 1].isdigit() else 999)
        return
    if "--ship" in args:
        i = args.index("--ship")
        limit = int(args[i + 1]) if i + 1 < len(args) and args[i + 1].isdigit() else 999
        ship(plan, d, limit)
        return
    show(plan)
    ex = [p for p in plan if p[1] == "excess"]
    print(f"\n{len(ex)} excess stacks ({sum(1 for p in ex if p[0]['bag'])} in carried bags: bag.py them out first); "
          f"{sum(1 for p in plan if p[1] == 'read')} books to read; the pack has {free_cards(d)} free cards")


if __name__ == "__main__":
    main()
