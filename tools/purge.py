"""Drop the junk out of the pack and its carried bags, by rule, on a dungeon or field map (run 28: the pack and all
three bags were full after two nefias, and a boss chest's treasure map and tomes stayed in the chest; lessons
run 26: "the ladder's loot fills the 35-card pack and every bag within one or two nefias").

Dropped: corpses, bones, offal, hearts, skins; debuff and joke potions; hostile-summon, curse and levitate
scrolls; anything cursed or doomed; cheap-material gear (paper, grass, straw, wooden, stone, bone, sand, mica,
hide, copper, silk, jelly) that is identified and not ☆; figures (8.5 weight each, ~35 orens); ancient books and
plain books; trinkets (wigs, toys, tableware, wine, torches); copper ore, sesame, tobacco, dirty water.
Never dropped: anything unidentified ("(Miracle)", "(Godly)", "strange", "murky"...: elin-home, never sell or ship
unidentified), ☆ artifacts, ★ items, the kit (teleport, return, evacuation, cure, troll blood, blankets), spellbooks,
recipes, rods (stock.py decides those at home), gold, platinum, medals, maps, tomes.

usage: python -I tools/purge.py [--dry]
Exit 0 done, 1 refused (at home: ship instead; a window), 3 stopped (a hostile in view).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import base_ready, call, data, ready, refuse, run, setup, stop  # noqa: E402

BAGS = ("a backpack", "a loot bag", "a spoils bag")
MATERIALS = r"(paper|grass|straw|wooden|stone|bone|sand|mica|hide|copper|silk|jelly|oak|cotton|plastic|iron|coral|scale|raw food)"
GEAR = r"(shirt|amulet|necklace|ring|girdle|cloak|boots|shoes|hat|helm|gloves|staff|bardish|sickle|club|sword|axe|crossbow|bow|" \
       r"shield|mail|robe|breastplate|neck guard|gauntlets|spear|dagger|mace|mallet|scythe|claw|scimitar)"
DROP = [
    r"\bcorpse of\b", r"^an? bones?$", r"\bgrotesque offals?\b", r"\bhearts?$", r"^an? skin$|\bskins$",
    r"\bpotions? of (paralysis|confusion|blindness|mutation|silence|weaken resistance|infravision|ultravision|"
    r"putitification|weakness|strip blessing|sleep|salt solution|catification|berserk)\b",
    r"\bpoisons?$", r"\bpot of dirty water\b",
    r"\bscrolls? of (summon \w+|curse|levitate)\b",
    r"\b(cursed|doomed)\b",
    r"\bfigure of\b", r"\bancient book titled\b", r"^an? book titled\b",
    r"\b(wig|small stuffed toy|tableware|bottle of wine|wall torch|tobacc leaf|tobacc leaves|sesame)\b",
    r"\b(copper|iron) ores?\b",
    # run 28: Burden phase 2 from loot furniture (2 wooden doors, a weathercock pedestal) and 7 iron ores
    r"\b(wooden doors?|weathercock pedestal|granite pebbles?|ketchup|bottle of yeast|can of milk)\b",
    # run 28: a lattice door and a robot's remnant took the loot bag to 57.6 (Burden phase 2 on B5)
    r"\b(lattice doors?|doors?|windows?|remnant of|animal bones?|cans? of soft drink)\b",
    # run 34: room_check stopped a solo Dark Ruin with these in the pack and nothing "cheap" to drop
    r"\b(sleeping pills?|ripped scrolls?|bottles? of ale|(bone|iron|steel|wooden|stone|sand|glass) hand guns?)\b",
    # run 34: boss-chest furniture tipped Burden into phase 2 five times (a dog house 4.5s, a side table 2.5s,
    # a snow globe 1.2s, a Bowl 1.1s, a moon chakram 1.4s)
    r"^(an? |\d+ )?(side tables?|pedestals?|snow globes?|bowls?|dog houses?|moon chakrams?|coral moon chakrams?)\b",
    # run 40 (three bags at 35/35 in the rich north, far from home): herbs, cooking goods and spare torches had ridden along
    # for runs while 7 gold bars, Miracle pieces and ancient books fought them for slots; a blue herb cures poison and stays
    r"\b(purple|red|green) herbs?\b",
    r"\b(packs? of soybeans?|handfuls? of bonito flakes?|gelatins?|bags? of (sugar|salt)|bottles? of (sauce|pepper|chili|soy sauce)|"
    r"glass(es)? of wine|cans? of protein|straw bales?|tufts? of (grass|straw)|empty cans?|mini snowman|hormone drugs?|"
    r"(iron|steel) bolts?|granite stones?|microchips?)\b",
    r"^an? (blessed )?torch\b",
    rf"^(an? |\d+ )?(blessed |stale )?(pair of )?{MATERIALS} .*{GEAR}",
]
KEEP = [r"\(miracle\)|\(godly\)|\(superior\)", r"^☆|^★|☆|★", r"\b(strange|murky|gluey|pale|bubbly|majestic|runic|old tome)\b",
        r"\b(teleport|return|evacuation|cure|troll blood|blanket|spellbook|recipe|rod of|gold bar|platinum|medal|map|tome)\b",
        r"\bmonster ball\b", r"\blockpick\b",
        # run 40: adding "iron" to MATERIALS made the kit's iron pickaxe read as iron gear ("pickaxe" holds "axe"): tools stay
        r"\b(pickaxe|shovel|hammer|butcher's tool|hoe|sickle|fishing rod|watering can)\b",
        # run 34: --free dropped "an ancient book titled "Ponape Scripture"" on an ambush map: decoded ancient books
        # are the Mages Guild's contribution (G36); skill books and genes never go either
        r"\b(ancient book|specialized book|skill book|genes?)\b"]


def junk(name):
    n = name.lower()
    # run 39: learned recipes ("(Learned x2)": known already) and scrolls of magic map (63 rode along; no tool reads
    # them), potions of slow and salt water helped fill all three bags 35/35 four nefias from home: 20 stacks were
    # dropped by hand on a conquered floor
    if re.search(r"\brecipe of .*\(learned x\d+\)|\bscrolls? of magic map\b|\bpotions? of (slow|salt water)\b", n) \
            and not re.search(r"☆|★|\bblessed\b", n):
        return True
    if any(re.search(k, n) for k in KEEP):
        # a cursed or doomed copy of a kit item is still junk (stock.py's rule)
        return bool(re.search(r"\b(cursed|doomed)\b", n)) and not re.search(r"\(miracle\)|\(godly\)|☆|★", n)
    return any(re.search(d, n) for d in DROP)


def stacks():
    """{bag name or 'pack': [stack names]} from bridge `stock` (read-only)."""
    d = data("stock")
    out = {"pack": []}
    for i in d.get("pack") or []:
        if i.get("equipped"):
            continue
        if i["name"] in BAGS:
            out[i["name"]] = [j["name"] for j in i.get("items") or []]
        else:
            out["pack"].append(i["name"])
    return d, out


def drop_in_open(name):
    """Drop one stack by its exact card name from the open window(s)."""
    bs = call("buttons", all=True)["data"]["buttons"]
    hit = [b for b in bs if "ButtonGrid inventory" in b["name"] and (b.get("card") or "") == name]
    if not hit:
        return False
    r = call("invacts", i=hit[0]["i"])
    acts = r["data"]["acts"] if r.get("ok") else []
    drop = [a for a in acts if a.get("text") == "Drop"]
    if not drop:
        return False
    return bool(call("invdo", i=drop[0]["i"]).get("ok"))


def main():
    setup()
    # Start Runs 1 and 3: the list is a late character's: in a new game it threw away the only axe, twice, through wgo and through ladder
    if not base_ready():
        print("no purge in a new game: its materials and tools are what it's short of")
        return 0
    dry = "--dry" in sys.argv
    d, by = stacks()
    if d.get("zone") == "startSite":
        refuse("at home: ship the junk (stock.py, the shipping chest) instead of dropping it on the farm")
    why = ready(hp=None, hunger=None, burden=None, allow=("LayerInventory",), hostiles=False)
    if not why:
        # run 38: Lv2-4 wanderers 6 cells off stopped five purges on Savage Grassland B4 (the pack at 37 of 35 cards,
        # the ladder refusing): a foe 12+ levels under mine (the swarm rule's half-count line) 4+ cells off doesn't
        s = data("state")
        me = (s.get("pc") or {}).get("lv") or 0
        foes = [c for c in s.get("nearby") or [] if c.get("hostile")
                and not ((c.get("lv") or 0) <= me - 12 and c.get("dist", 0) >= 4)]
        if foes:
            f = min(foes, key=lambda c: c.get("dist", 99))
            why = f"hostile in view: {f['name']} Lv{f.get('lv')} at {f.get('dist')}"
    if why and not dry:
        stop(why)
    total = 0
    for where, names in by.items():
        bad = [n for n in names if junk(n)]
        if not bad:
            continue
        print(f"{where}: {len(bad)} to drop of {len(names)}")
        for n in bad:
            print(f"   {n}")
        if dry:
            total += len(bad)
            continue
        run("close.py")
        # the pack's own grid shows beside any open carried bag
        run("item.py", where if where != "pack" else "a backpack", "Open")
        for n in bad:
            if drop_in_open(n):
                total += 1
            else:
                print(f"   !! not dropped: {n}")
        run("close.py")
    print(f"{'would drop' if dry else 'dropped'} {total} stacks")
    if not dry:
        unclutter()
        if "--free" in sys.argv:
            free_cards(int(sys.argv[sys.argv.index("--free") + 1]))


# run 33: the pack grid sat full on most floors (meals "would fall to the floor", two skill books nearly left in
# chests) and unclutter had no bag room left. --free N drops the cheap, heavy or replaceable pack stacks, cheapest
# class first, until N cards are free; never the kit (PACK_KEEP), nothing KEEP names (artifacts, unidentified,
# books, rods, scrolls of the kit), never food or genes. What it can't free, it says.
CHEAP = [
    r"\b(stones?|ores?|logs?|chunks? of soil|pebbles?|planks?|branch(es)?|sticks?|bricks?|clay|sand)\b",
    r"\b(corpses?|bones?|offals?|fangs?|hearts?|skins?)\b",
    r"\bpotions? of (blindness|confusion|slow|silence|paralysis|sleep|poison|mutation|salt water)\b",
    r"\b(doors?|windows?|cones?|bottles?|cans?|torch(es)?|garbage|shit|vomit|rubble)\b",
    rf"^(an? |\d+ )?(blessed |stale )?(pair of )?{MATERIALS} .*{GEAR}",   # plain gear named by its material (no Miracle/Godly tag)
]


def drop_bag_excess(limit):
    """Drop up to `limit` stacks that stock.py's caps call excess (over-cap spellbooks, empty rods, over-cap scrolls
    and potions, plain armory gear) from the carried bags; never the kit's own stacks in the pack. Returns the count."""
    import stock
    _d, items = stock.inventory()
    spells = {x["spell"]: x["stock"] for x in data("power")["party"][0].get("spells") or []}
    # run 36 (run 35's open item: Bewitching Grassland stopped with known-spell books in the pack's own grid): the
    # pack's top-level excess counts too, never a kit stack (PACK_KEEP)
    # run 40: the rod caps (teleport and cure minor wound, 99 -> 4) are for shipping them home: excess rods with charges pay at the
    # chest, so they aren't dropped here; the same for spellbooks with charges (the user asked why so much loot was dumped)
    rows = [it for it, v, _why in stock.decide(items, spells) if v == "excess" and it["where"] == "pack"
            and (it.get("bag") or not re.search(PACK_KEEP, it["name"].lower()))
            and not re.search(r"\b(rod|spellbook) of .*\((?!0 )\d+ charges?\)", it["name"].lower())]
    done = 0
    for it in rows[:max(0, limit)]:
        if it.get("bag") and "moved" not in run("bag.py", it["bag"], "--take", it["name"]):
            continue
        if run("item.py", it["name"], "Drop").rc != 0:
            continue
        print(f"free: dropped {it['name']} from {it.get('bag') or 'the pack'} (stock excess)")
        done += 1
    return done


def free_cards(n):
    _, by = stacks()
    # run 34: the bags are pack cards too (stacks() keys them apart): without them purge saw 3+ free while ladder's
    # room_check counted 2 and refused, twice on Mossy Cave B1
    free = 35 - len(by["pack"]) - (len(by) - 1)
    if free >= n:
        return
    # run 39 (Unknown Ruin): "nothing cheap to drop" returned before unclutter ever ran, so spare rods and meals that
    # could move into the bags or the Cooler Box stayed in the grid: move first, drop only what is still needed
    unclutter()
    _, by = stacks()
    free = 35 - len(by["pack"]) - (len(by) - 1)
    if free >= n:
        return
    pool = [s for s in by["pack"] if not re.search(PACK_KEEP, s.lower()) and not junk(s)
            and not any(re.search(k, s.lower()) for k in KEEP) and not re.search(r"\bgene\b|salad|roast|onigiri|stew|bread", s.lower())]
    order = []
    for pat in CHEAP:
        order += [s for s in pool if re.search(pat, s.lower()) and s not in order]
    if not order:
        # run 34: four room-check refusals in one night with the bags full of over-cap spellbooks and empty rods
        # (stock.py's "excess"): drop those from the bags, then move pack stacks into the room they leave
        k = drop_bag_excess(n - free + 2)
        if k:
            unclutter()
            return
        print(f"free: {free} cards, {n} wanted, nothing cheap to drop (bag or box something by hand)")
        return
    run("close.py")
    run("item.py", "a backpack", "Open")
    dropped = 0
    for s in order:
        if free >= n:
            break
        if drop_in_open(s):
            dropped += 1
            free += 1
            print(f"free: dropped {s}")
    run("close.py")
    print(f"free: {free} cards after dropping {dropped}" + ("" if free >= n else f" (wanted {n}: nothing cheap left)"))


# the pack's own grid (35 cards) keeps the kit; the rest rides in the bags (run 28: a full grid ate meals
# "a meal would fall to the floor" three times, and the ladder's chests found no room)
PACK_KEEP = (r"(cooler box|putit in amber|axe|backpack|loot bag|spoils bag|pickaxe|scrolls? of (return|teleport|"
             r"evacuation|identify)|potions? of (cure|troll)|orens|long bow|rods? of (teleport|cure)|arrows|skewers?|"
             r"blanket|platinum|makeshift bed|travel rations?|lockpick|hand gun|shotgun|rifle|bullets?|quarrels?|crossbow|fishing rod|baits?)")
FREE_CARDS = 4
COOLER_SLOTS = 9  # the ★Cooler Box (fact #225: a 9-slot container)


def unclutter():
    _, by = stacks()
    free = 35 - len(by["pack"]) - (len(by) - 1)  # run 34: the bags are pack cards too
    if free >= FREE_CARDS:
        return
    # run 39: "A Grass Battle Axe (Miracle)" matched PACK_KEEP's "axe" and sat in the grid; the ladder's room check
    # refused Capricious Grassland at 2 free cards: unidentified loot is never kit
    movable = [n for n in by["pack"] if not re.search(PACK_KEEP, n.lower()) or re.search(r"\((miracle|godly)\)", n.lower())]
    # run 39 (Rustic Grassland): the kit alone took 33 grid cards (five rods of teleport, four of cure minor wound),
    # the ladder refused at 2 free and purge found "nothing cheap": the rods past the two with most charges move
    for kind in ("rod of teleport", "rod of cure minor wound"):
        rods = [n for n in by["pack"] if kind in n.lower() and "blessed" not in n.lower() and n not in movable]
        rods.sort(key=lambda n: -int((re.search(r"\((\d+) charges?\)", n.lower()) or [0, 0])[1]))
        movable += rods[2:]
    room = {b: 35 - len(by.get(b) or []) for b in BAGS if b in by}
    plan = {}
    # run 39: the meals bought at Olvina (roasts, shortcakes, cheese, imos) went into the backpack and the spoils bag,
    # where eat_one never looks (the pack and the Cooler Box only), and the walk stopped Hungry with 28 meals carried:
    # meals go into the Cooler Box while it has room (COOLER_SLOTS), else they stay in the pack
    from farmday import is_meal  # lazy: farmday imports this module's helpers inside eat_one
    meals = [n for n in movable if is_meal(n)]
    movable = [n for n in movable if n not in meals]
    cooler = next((i for i in data("stock").get("pack") or [] if "Cooler Box" in (i.get("name") or "")), None)
    if meals and cooler is not None:
        slots = COOLER_SLOTS - len(cooler.get("items") or [])
        if slots > 0:
            out = run("bag.py", "Cooler Box", *meals[:slots])
            print(f"unclutter: Cooler Box <- {min(slots, len(meals))} meals ({out.rc})")
            free += min(slots, len(meals))
    for n in movable:
        if free >= FREE_CARDS + 2 or not room:
            break
        b = max(room, key=room.get)
        if room[b] <= 0:
            break
        plan.setdefault(b, []).append(n)
        room[b] -= 1
        free += 1
    for b, names in plan.items():
        out = run("bag.py", b, *names)
        print(f"unclutter: {b} <- {len(names)} ({out.rc})")
    run("close.py")


if __name__ == "__main__":
    main()
