"""Check the carried containers (the pack, the backpack, the loot bag, the Cooler Box) against the trip kit
and name the home box every other item belongs in (G12 zones, elin-home section 2a).

The user, run 11: "before we left the base you are carrying sticks, gold bars, furniture tickets, a
figure of a snail, coins, books, ecopos, tickets... it needs to be put someplace it triggers whenever
you leave base... it is a loss of treasure by not having those slots free."
leave.py runs this on the home map and refuses to leave while anything is out of place.

usage: python -I tools/packcheck.py           list what's out of place and where it goes (exit 1 if any)
       python -I tools/packcheck.py --move    carry it there now with box.py (at home only)
Unidentified items are listed but don't block: Appraising identifies them on the road (elin-pack).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call, close  # noqa: E402
from common import last  # noqa: E402
import home  # noqa: E402
from home import BOX_STR  # noqa: E402

TOOLS = Path(__file__).resolve().parent

# The trip kit (elin-play rule zero and elin-pack): everything else stays home.
# items carried until the user decides what to do with them (run 22: the ★Land Deed, G13 M2)
AWAITING_USER = ("land deed",)
# run 15: "orens" (picked-up coins are an item stack): "ore" sent 685 orens to the stone box, and
# the tax is paid from carried gold
KIT = ("orens", "bandage", "throwing dagger", "cooler box", "backpack", "cure minor wound", "cure major wound",
       "cure critical wound", "troll blood", "restore body", "restore mind", "potion of hero", "scroll of hero",
       "scroll of teleport", "scrolls of teleport", "short teleport", "evacuation", "scroll of return",
       "scrolls of return", "magic map", "incognito", "lockpick", "putit in amber", "rod of teleport",
       "rod of cure", "rod of slow", "rod of silence", "rod of holy shield", "woodcutter's axe",
       "pickaxe", "shears", "sleeping bag", "short bow", "long bow", "arrow", "torch", "tax bill",
       "adventure log", "potion of paralysis", "potions of paralysis", "blue herb", "iron sickle", "bronze war sickle", "hand gun", "bullets",  # run 32: Gun training (skill 1) at the dummy  # run 21: "sickle" took a ☆war sickle as kit
       "forest necklace", "edible necklace", "potion of silence", "rod of holy light", "makeshift bed", "futon", "hammer",  # run 48: the stupid futon is the carried bed
       "butcher's tool", "loot bag", "spoils bag", "haul bag", "pouch",
       "shovel",  # the user, 2026-10-29: a few of the wiki's hidden Small Medals need digging (medals.py)
       "fireproof blanket",  # the user, 2026-10-30: 3 ride along (leave.py); --move had no reason to keep them
       "potion of confusion", "potions of confusion", "rod of web", "bait", "monster ball",
       "water breathing", "forest gloves")  # run 55, G66: the Sunken Temple of Lurie is underwater: the Forest Gloves go on at its door, the blessed potions are the spare if acid strips the enchantment  # run 17: baits ride on the toolbelt (the Farm box is full; fishing anywhere)  # run 16: soak kamikazes Wet (delve.py throws them); web a foe and walk off  # run 13: butcher every corpse where it falls (G6 skins)  # run 12: Edible on roads, Forest (no blindness) in dungeons
# run 36: the pack's 35 cards filled with minor kit pulled out of the bags (rods of silence, web, holy shield, magic
# map; buff potions; spare scrolls), and the ladder's room check and leave.py's 3 free cards failed four times. Only
# the core kit must sit in the pack itself (the tools read it by name from there: escape, heals, food, the bed, the
# blanket, the bow); the rest of KIT may ride in any carried bag
CORE_KIT = ("orens", "cooler box", "cure minor wound", "cure major wound", "cure critical wound", "troll blood",
            "scroll of teleport", "scrolls of teleport", "evacuation", "scroll of return", "scrolls of return",
            "putit in amber", "rod of teleport", "rod of cure", "pickaxe", "short bow", "long bow", "arrow",
            "makeshift bed", "sleeping bag", "fireproof blanket", "travel ration", "loot bag", "spoils bag", "haul bag", "backpack", "pouch",
            "lockpick")
# run 38 (run 37's circuit stopped 'bags full (35, 35, 35)' five times, one or two nefias each): the bags carried
# minor kit no tool uses on a trip: the buffs are cast (Hero 116, Holy Shield 100 in stock), the attack rods and the
# rare scrolls rode for runs unread, and herbs and milk in the backpack can't be eaten (eat_one reads the pack and the
# Cooler Box). These kinds stay home (the spares chests) from every carried container; spare torches too, past the
# backpack (one worn, two blessed spares there)
HOME_ONLY = ("holy veil", "potion of speed", "potion of resistance", "potion of hero", "scroll of hero",
             "exterminate", "intonation", "telepathy", "earthquake", "divine wisdom", "meteor", "flying scroll",
             "salt water", "scroll of faith", "incognito", "rod of speed", "rod of death bolt",
             "rod of mind bolt", "rod of poison missile", "rod of fire missile", "rod of lightning bolt", "rod of bane")
FOOD_OK = ("mushroom", "tomato", "imo", "on the bone", "meat", "egg", "milk", "bread", "stew", "skewer",
           "corpse",  # run 12: cookable food; special mobs' corpses stay in the Cooler Box (elin-play)
           "roast", "ration", "fish", "herb", "fruit", "berry", "apple", "melon", "marshmallow", "cookie",  # run 21: melon, marshmallows, fortune cookies had no route
           "truffle", "soybean", "noodle", "mammoth",  # run 31: Semnof's whole roasted mammoths
           "banana", "stir-fry", "stir-fries", "manju", "croquette", "pizza",  # run 24: Tiguen's foods had no route
           "rice", "cheese", "jerky", "jerkies", "pie",  # run 19: "4 jerkies" had no route
           "sashimi", "sandwich", "onigiri",
           "sherbet", "sherbets", "anpan", "anpans", "breadstick", "breadsticks",  # run 55: a pumpkin sherbet had no route (Tiguen sells sherbets, anpans, breadsticks)
           "stir fried", "gourd", "curry", "curries",  # run 50: Erobird's stir fried gourds (kind meal) had no route
           "lunch box", "mousse", "shortcake", "mochi", "avocado", "watermelon", "sack", "dumpling",  # run 41: Semnof's stock had no route
             # run 39: palulu shortcakes had no route
            # run 36: an ally's lunch box (CHA, MAG, STR) and a mousse had no route
           "soup", "cake", "noel",  # run 30: seaweed soups, snow putit cakes, bush de noels had no route  # the review of 2026-10-23: these three sat inside the comment above
           # run 13: every fish in things.json (a carp had no route)
           "arowana", "bass", "bitterling", "blowfish", "bonito", "carp", "coelacanth", "eel", "flatfish",
           "goby", "goldfish", "mackerel", "moonfish", "muddler", "pintuna", "bream", "salmon",
           "sand borer", "sardine", "scad", "sea urchin", "shark", "striped jack", "sunfish",
           "sweetfish", "tadpole", "tilefish", "tuna", "turtle", "whale")
JUNK = ("rotten", "garbage", "empty bottle", "shit", "salt water", "remnant of what once was", "remnants of what once was",
        "pair of sandal", "exotic teapot", "cluttered book", "a stain", "ragged cloth")  # run 49: the game files these as junk (box.py refuses them for the chest); run 39: remnants (dattamono: a meat worth 50, CHA -20) had no route; run 13: cans are scrap; run 17: no vomit
# (a "Return request" quest item is a vomit: packcheck dumped Casaneck's, so it is never auto-junk)

# Where each kind of item lives at home (elin-home section 2 and 2a). First match wins.
ROUTES = [
    (JUNK, "trash", "the trash can (trash.py dump)"),
    # run 12: the Border Watch plan fell through to the shipping chest; a plan is read at home
    (("plan of", "plans of"), "read", "read it now at home (a plan teaches a policy: item.py NAME Read)"),
    (("seed",), BOX_STR(home.FARM_BOX) + "|" + BOX_STR(home.FARM_BOX2), "Farm box (the Depot; Farm box 2 in the Farmhouse when full)"),
    (("watering can", "hoe", "fishing rod", "bait"), BOX_STR(home.FARM_BOX), "Farm box (the Depot)"),  # run 13: bait beside the rod
    # run 18 (G12): spare room boards and plates, and walls for rotating facings, wait by the wall workshop
    (("room board", "room plate", "house plate", "house board", "plank wall", "stone wall", "log wall", "a roof", "signboard"),  # run 48: a roof, a signboard
     BOX_STR(home.WOOD_BOX), "Wood box (building parts)"),
    (("log", "plank", "branch", "stick", "bark", "resin"), BOX_STR(home.WOOD_BOX), "Wood box (the Workshop)"),
    # G56 M2 (run 48): the stonecutter and the mason's table stand in the Workshop, so stone and cut stone wait there in
    # 'Stone 2' (52,58); ores, ingots, glass and the rest stay in the Forge by the smelter and kiln (pebbles too: cookdishes)
    (("ore", "sand", "fragment", "clay", "ingot", "soil", "glass", "pebble"),
     BOX_STR(home.STONE_BOX) + "|" + BOX_STR(home.STONE_BOX_2), "Stone and ore box (the Forge)"),
    (("stone", "brick", "cut stone"),
     BOX_STR(home.STONE_BOX_2) + "|" + BOX_STR(home.STONE_BOX), "Stone 2 (the Workshop, by the stonecutter)"),
    # run 19 (the user): treasure maps in the shared Maps box, where Poppy's Treasure Hunt finds them
    (("treasure map",), BOX_STR(home.MAPS_BOX), "the shared Maps box (the Workshop)"),
    (("thread", "fiber", "string", "rope", "skin", "big leaf", "big leaves", "needle", "texture", "bolt"),
     "|".join(BOX_STR(b) for b in home.BAG_PARTS) + "|" + BOX_STR(home.ARMORY5) + "|" + BOX_STR(home.SPARES), "Bag parts box (the Workshop; the yard's wagon when full, run 42; the yard's chest last, run 44)"),
    (("bone", "nail", "battery", "batteries", "microchip", "memory chip", "scrap", "fang", "horn", "queen bee"), BOX_STR(home.PARTS_BOX) + "|" + BOX_STR(home.ARMORY5) + "|" + "|".join(BOX_STR(w) for w in home.BIG_WAGONS) + "|" + BOX_STR(home.SPARES), "Parts box (the Workshop; the yard's wagon, then the big wagons and the yard chest when full: run 45, a bone charm refused by the two full boxes)"),  # run 30: queen bees (a beehive part)
    (("leaf", "leaves", "tuft of", "tufts of", "grass wall"), BOX_STR(home.FODDER_BOX), "the fodder box (the Farmhouse)"),
    (("corpse",), "ship", "the shipping chest (a fresh corpse; cook it first if food is short)"),
    (("potion", "liquid", "scroll", "rod of", "poison"), BOX_STR(home.SPARES) + "|" + BOX_STR(home.SPARES2) + "|" + BOX_STR(home.SPARE_BOX) + "|" + BOX_STR(home.SPARES3) + "|" + BOX_STR(home.SPARES4) + "|" + BOX_STR(home.STORAGE_CHEST) + "|" + BOX_STR(home.OVERFLOW2), "the spares chests (the Storehouse; the Storage Chest and the mystic chest when full)"),
    (("paint", "dye"), "|".join(BOX_STR(b) for b in home.VALUABLES) + "|" + BOX_STR(home.SPARES), "valuables (paint and dyes: materials; run 31: dyes for G30's flower beds; the yard's chest last, run 44)"),
    (("platinum", "gold bar", "medal", "ecopo", "coin", "ticket", "figure", "figurine", "card of", "gene of",
      "flicker of decency", "gem", "jewel", "cards of", "figures of", "mandrake", "a card"), "|".join(BOX_STR(b) for b in home.VALUABLES) + "|" + BOX_STR(home.STORAGE_CHEST) + "|" + BOX_STR(home.OVERFLOW2) + "|" + "|".join(BOX_STR(b) for b in home.VALUABLES_OVERFLOW) + "|" + BOX_STR(home.SPARES),
     "valuables (the Storehouse; the Storage Chest when full, run 21; the yard's 276-slot chest last, run 44)"),
    # run 30 (G28): the Juremas decorations and dolls (things mount/deco) wait in Valuables 7, then the collectibles shelf
    # run 31 (G30 M5): loose lights (an old lantern from a nefia) wait with the decorations until they're installed
    (("holy wreath", "holy garland", "holy socks", "holy boots", "gift box", "candy cane", "doll", "lantern", "candle", "lamp",
      "wall decoration"),  # run 48
     BOX_STR(home.VALUABLES[-1]) + "|" + BOX_STR(home.COLLECTIBLES) + "|" + BOX_STR(home.SPARES), "decorations (Valuables 7 in the Depot; the collectibles shelf; the yard's chest, run 42)"),
    (("book", "spellbook", "recipe", "journal", "letter", "parchment"), "|".join(BOX_STR(b) for b in home.LIBRARY), "the library (the Storehouse)"),
    (("oil", "ale", "butter", "chili", "ketchup", "salt", "sugar", "mayo", "mayonnaise", "spice", "beer", "wine",
      "sake", "sauce", "sesame", "flour", "vinegar", "tea", "cappuccino",
      "herb", "coffee", "preservative", "seasoning", "pepper", "protein", "miso", "soft drink", "jam", "gelatin", "catechin",
      "glutamine", "honeycomb", "honey", "yeast", "juice", "crim powder", "wasabi"), BOX_STR(home.PANTRY) + "|" + BOX_STR(home.PANTRY_2) + "|" + BOX_STR(home.PANTRY_3) + "|" + "|".join(BOX_STR(w) for w in home.WAGONS), "Pantry (the Kitchen; the yard's wagons when full, run 43)"),  # run 14: a purple herb and coffee had no route; run 15: a preservative, pepper
    (("grave of",), "ship", "the shipping chest (a boss's grave: junk, value 0-ish)"),
    (("Scrubber", "charm ("), "ship", "the shipping chest (☆The Scrubber, a boss-chest regular, and plain charms: run 30)"),
    (("small plant", "guitar stand"), "ship", "the shipping chest (floor decorations the loot picks up: run 51)"),
    # run 34: four "decide" stacks held up leave.py twice (loot from Rustic Forest and run 33's chests)
    (("table clock", "boomerang", "beaker", "a saw", "old sketch", "tapestry", "tapestries", "stale head", "rubble", "ledger", "carved wooden", "a paper", "chess board", "a sink", "a dice", "wooden door", "an orb", "charm", "fishbowl", "alarm clock", "a head", "junk rope", "old lantern", "trident", "hanging shelf", "pipe bed", "a poster", "fortune telling", "lectern",
      # run 46: boss-chest and floor odds with no rule (a plate, hanging pots, sea pants, the rest)
      "tableware", "trash bin", "pot of water", "gamble chest", "a plate", "hanging pots", "sea pants", "cobweb", "moon chakram",
      "sleeping pill", "vomit", "music box", "pedestal", "snow globe", "rubber snail", "a rack", "churyu",
      # run 48: a boss chest's skull, the loot bag's odds (the dried mandrake is a currency: valuables, above)
      "skull", "iron scale", "a junk", "towel", "anchor", "assorted vegetable", "broken barrel", "a cup", "small window", "dirty dish",
      "a cabinet",
      # run 50: a saddle and a cushion had no rule ("a dish" left this list: the chest refused it twice, and the game's
      # category, junk, sends it to the trash can below)
      "saddle", "cushion"), "ship", "the shipping chest (odd loot nothing uses: run 34)"),
    # organs: board supply and gift jobs ask for them (a heart, grotesque offal; run 08, run 12)
    # run 15 (G14): ration grain waits by the millstone's stock: the harvest box keeps it (never shipped)
    (("bundle of wheat", "bundles of wheat", "rice plant", "bag of rice", "bags of rice", "flour", "api nut", "coffee bean"), BOX_STR(home.HARVEST_BOX), "the harvest box (ration grain and nuts, G14)"),
    (("offal", "heart", "liver", "kidney", "eyeball"), "ship", "the shipping chest (organs: the pantry is full, run 41)"),
    # run 56: stale meat (corpses have their own route above) crowded the meals out of the Cooler Box
    (("stale marbled meat", "stale marbled meats"), "ship", "the shipping chest (stale meat: run 56)"),
]


# the quality tags an unidentified piece shows; run 46: "A Cocky Wakizashi (Special)" had no rule and blocked leave.py
UNID_TAGS = ("(godly)", "(miracle)", "(good)", "(great)", "(excellent)", "(special)")

def _with_big_tail(routes):
    """Run 45 (G47's done-when broken a third run): a bone charm met its route's two boxes full while the yard chest had 100
    free; the stone, leaf, wood, wheat, seed and tool routes had no big box behind them either (61,57 and 60,41 were full).
    Every box chain now ends at the second big wagon and the yard chest; the Maps box stays alone (Poppy reads only it)."""
    tail = [home.BIG_WAGONS[1], home.SPARES]
    out = []
    for keys, where, label in routes:
        cells = where.split("|")
        if all(re.fullmatch(r"\d+,\d+", c) for c in cells) and where != BOX_STR(home.MAPS_BOX):
            cells += [BOX_STR(t) for t in tail if BOX_STR(t) not in cells]
            where = "|".join(cells)
        out.append((keys, where, label))
    return out


ROUTES = _with_big_tail(ROUTES)


from common import run as _run  # noqa: E402


def tool(*args, timeout=300):
    return _run(args[0], *args[1:], timeout=timeout)


def split_listing(text):
    """The item names in a box.py / bag.py listing line ("56,52: a hoe, 3 planks" or the whole
    output: the last non-empty line is used). Splits on "," outside brackets, so "(2d4, 2) [2, 0]"
    stays whole; "empty" and a line with no ":" give []. springday, trainday, farmday, cookdishes
    and ration read listings through it too (the review of 2026-10-23: their naive split broke on
    gear names)."""
    line = last(text)
    m = re.search(r":\s(.*)$", line)
    if not m or m.group(1).strip() in ("", "empty"):
        return []
    items, cur, depth = [], "", 0
    text = m.group(1)
    for n, ch in enumerate(text):
        depth += ch in "([" and 1 or (ch in ")]" and -1 or 0)
        # run 41: "1,753 orens" is one item: the separator is a comma and a space
        if ch == "," and depth == 0 and text[n + 1:n + 2] == " ":
            items.append(cur.strip())
            cur = ""
        else:
            cur += ch
    return [x for x in items + [cur.strip()] if x]


def bag_items(bag):
    out = tool("bag.py", bag)
    tool("close.py")
    return split_listing(out)


def norm_name(name):
    """Lower case, singular "scrolls of"/"potions of"/"rods of", so the kit names match."""
    low = name.lower()
    for a, b in (("scrolls of", "scroll of"), ("potions of", "potion of"), ("rods of", "rod of")):
        low = low.replace(a, b)
    return low


def _word_re(k):
    # a plural at the end of the key: +s, +es, y -> ies ("berry": berries; "jerky": jerkies)
    k = k.lower()
    if k.endswith("y"):
        return r"(?<![a-z0-9])" + re.escape(k[:-1]) + r"(?:y|ies)(?![a-z0-9])"
    return r"(?<![a-z0-9])" + re.escape(k) + r"(?:e?s)?(?![a-z0-9])"


def has_word(low, keys):
    """Whole-word match with an optional plural (run 11: "nail" matched "a figure of snail"; the
    review of 2026-10-23: the old word-START match let "sand" take a sandwich, "tea" a teapot and
    "fish" a fishing rod). A multi-word key is matched as a phrase."""
    low = (low or "").lower()
    return any(re.search(_word_re(k), low) for k in keys)


def is_kit(low):
    """A KIT word, but never a spellbook or a spent rod (run 44: "arrow" took the spellbooks of arrow of the moonlit night
    and ice arrow, "cure minor wound" its spellbooks, "rod of cure" two rods at 0 charges: 13 of them sat in the pack
    as kit and left it 2 cards over full, so shipstar couldn't carry a piece)."""
    low = (low or "").lower()
    if "spellbook" in low or re.search(r"\(0 charges?\)", low):
        return False
    return has_word(low, KIT)


GEAR = re.compile(r"\[-?\d+, ?-?\d+\]|\(\d+d\d+")  # "[6, 0]" armour, "(3d5+3, 2)" weapons


ARMORY = (BOX_STR(home.ARMORY) + "|" + BOX_STR(home.ARMORY2) + "|" + BOX_STR(home.ARMORY3) + "|" + BOX_STR(home.ARMORY4) + "|" + BOX_STR(home.ARMORY5), "the armory (the Residence: residents take what beats their gear; 'Armory 2' in the Workshop, 'Armory 3' and 'Armory 4' in the Depot when full)")


def is_food(low):
    """Food for the Cooler Box: a food word, not junk, not a seed (run 13: 'seed of tomato' passed)."""
    # run 33: 'a gene of mushroom' went to the Cooler Box as food; genes are valuables (P18, the Gene Machine)
    # run 34: "a card of turtle" came out of the spoils bag as food ("turtle" is a fish word): cards and figures are valuables
    if "seed" in low or "gene of" in low or "card of" in low or "figure of" in low or has_word(low, JUNK):
        return False
    # run 45: "a spellbook of summon fish" was sent to the pack as food on every sort ("fish"); books are never food
    if has_word(low, ("book", "spellbook", "recipe", "scroll", "rod", "potion")):
        return False
    if has_word(low, FOOD_OK):
        return True
    # run 32: a pepper potage packed for the trip went back to the Pantry while leave.py counted it as a meal:
    # anything eat_one would eat is Cooler Box food (imported here: farmday imports this module at its top)
    from farmday import is_meal
    return is_meal(low)


_KINDS = None


def _junk_kind(name):
    """True when the carried thing of this name is in the game's junk category (box.py's rule for the shipping chest),
    never a ☆ piece (run 49: ☆The Scrubber ships). One inventory read per run."""
    global _KINDS
    if _KINDS is None:
        try:
            import items as _items
            _KINDS = {(i.get("name") or "").lower(): i.get("kind") or "" for i in _items.inventory()}
        except Exception:  # noqa: BLE001 - the word rules still route it
            _KINDS = {}
    return _KINDS.get(name.lower(), "").startswith("junk") and not name.startswith("☆")


def route(name):
    low = norm_name(name)
    from common import hammer_scrap
    if hammer_scrap(name):  # run 13: the hammer breaks it into scrap (tools/scrap.py)
        # run 43: the Parts box and the one wagon both full on the last arrival: a light stand stayed unmoved (G47's done-when): every wagon after them
        return BOX_STR(home.PARTS_BOX) + "|" + "|".join(BOX_STR(w) for w in [home.ARMORY5] + [w for w in home.WAGONS if w != home.ARMORY5]), "Parts box (scrap junk: break it with tools/scrap.py; the yard's wagons when full, runs 42-43)"
    # run 34 (the user: "Careful Raw Food Weapons/Armor are not things to eat", "Don't throw it away if it rots"):
    # gear made of the "raw food" material rots like food ("A Rotten Raw Food Claw") and matched JUNK's "rotten";
    # unidentified things (a capitalized name, a quality tag) and gear never go to the trash
    unidentified = bool(re.match(r"^(an? |\d+ )?[A-Z]", re.sub(r"^(A |An )", lambda m: m.group(1).lower(), name.strip())))
    if has_word(low, JUNK) and not unidentified and not GEAR.search(name)             and not re.search(r"\(miracle\)|\(godly\)|\(superior\)|\[-?\d+, -?\d+\]|\(\d+d\d+", low):
        return "trash", "the trash can (trash.py dump)"
    # run 53: an iron scale and a paper pile were routed to the shipping chest by name and box.py refused both there
    # (the game's category is junk: the user's run-08 rule), so they rode in the pack: the category decides here too
    if _junk_kind(name):
        return "trash", "the trash can (trash.py dump; the game files it as junk)"
    # run 33 (the user: "sell those 0 rods as well for sure"): an empty rod ships (it still sells); dropping one in a
    # nefia wasted it, and the spares boxes filled with them
    if re.search(r"\brod\b.*\(0 charges?\)", low):
        return "ship", "the shipping chest (an empty rod: the user, run 33)"
    # gear before the material rules (run 12: a glass staff went to the stone box, bone boots to
    # the parts box); identified spare gear and jewelry arm the residents (G12 M8)
    # run 46: "charm" wasn't here, so ☆The Glittering Charm (kept for run 45's open trial) fell through to ROUTES' odd-loot
    # "charm" and shipped; a ☆/★ charm is neck gear and goes to "decide" like the rest
    is_gear = (GEAR.search(name) or has_word(low, ("amulet", "necklace", "ring", "girdle", "cloak"))
               or (has_word(low, ("charm",)) and ("☆" in name or "★" in name)))  # plain charms still ship (run 30)
    if is_gear and ("☆" in name or "★" in name):
        # run 13: an identified ☆ shirt went to the armory and a resident wore it within the hour,
        # before it could be shipped (☆ gear ships for hundreds plus hearth exp); decide by hand
        return "decide", "decide: ☆ gear: wear it or ship it (the armory hands it to a resident at once)"
    if is_gear:
        return ARMORY
    # run 38: a rod of lightning, mind or death bolt went to the bag parts box through ROUTES' "bolt"; rods are spares
    if re.search(r"\brod of\b", low):
        return next((w, lab) for keys, w, lab in ROUTES if "rod of" in keys)
    if has_word(low, ("torch",)):  # run 38: spare torches (seven rode along); the residents can carry them
        return ARMORY
    if has_word(low, ("book", "spellbook", "recipe")):  # run 12: "lightning bolt" matched the bolts
        if spell_over_cap(low):
            # run 49: over-cap spellbooks were filed into the library and every box of the chain filled; stock.py shipped
            # the excess back out 33 a morning while each arrival filed more. Past the cap they ship first now; the
            # library only when the chest is full for the day
            return ("shipping chest|" + "|".join(BOX_STR(b) for b in home.LIBRARY),
                    "the shipping chest (a spellbook past its cast cap: stock.py), else the library")
        return "|".join(BOX_STR(b) for b in home.LIBRARY), "the library (the Storehouse)"
    for keys, where, label in ROUTES:
        if has_word(low, keys):
            if where == "trash" and unidentified:  # run 34: "A Rotten Raw Food Claw (Miracle)"
                return "decide", "decide: unidentified, not junk whatever it is made of (identify it first)"
            return where, label
    # run 49: every arrival stopped on odds with no named route (a vase, a canvas, a long chair, a bowl, a box of decorated
    # knives...). The game's own category is a rule too (the run-48 lesson: the category beats the name): junk goes to
    # the trash can, loot furniture and decor ship; never a ☆/★ piece, never an unidentified one, and a plan or a book
    # never reaches here (routed above)
    cat = game_category(name)
    if cat and not unidentified and not re.search(r"[☆★]", name):
        if cat == "junk":
            return "trash", "the trash can (the game's category: junk)"
        if cat in SHIP_CATS:
            return "ship", f"the shipping chest (loot {cat} by the game's category: run 49)"
    # run 53: "a map" (thing map, TraitScrollMap) sat in a bag as "no rule" for runs; read, it marks nefias on the world map
    # (Silent Ruin 13 and Dark Machinarium 7 from two): it is used where it is found, never boxed
    if re.fullmatch(r"(an? |\d+ )?(blessed |cursed )?maps?", low.strip()):
        return "decide", "decide: read it now (item.py NAME Read): a nefia map marks ruins and caves for the circuit"
    # run 12: the old default was the shipping chest, and a flower crown and the Border Watch plan
    # went in at 02:30, three hours before the 05:00 sale; nothing is shipped without a rule now
    return "decide", "decide: not moved (no rule for it: ship, install, or add a route)"


# run 49: loot furniture and decor by the game's category (things.json); a light, a bed or a container the town wants is
# placed by hand before an arrival sorts it
SHIP_CATS = {"deco", "mount", "chair", "crafter", "container", "table", "furniture", "bed", "light", "ext", "util", "tool_deco"}
_CATS = {}


def game_category(name):
    """The game's category of a carried thing by its exact name (items.py's reader), or None."""
    if not _CATS:
        try:
            import items
            for it in items.inventory():
                _CATS[norm_name(it.get("name") or "")] = it.get("cat")
        except Exception:  # noqa: BLE001 (no bridge: no category rule)
            _CATS[""] = None
    return _CATS.get(norm_name(name))


# run 24: 24 Small Medals taken for Miral's ether antibodies went back into the valuables box with
# the next `--move`, and the trip reached Miral and Garokk's Workshop without them (10 game days).
# An errand's items are named in runs/carry.txt (one per line, # comments): they stay in the pack
# until the line is removed.
CARRY = Path(__file__).resolve().parent.parent / "runs" / "carry.txt"


def errand(low):
    try:
        keys = [k.strip().lower() for k in CARRY.read_text(encoding="utf-8").splitlines()
                if k.strip() and not k.lstrip().startswith("#")]
    except OSError:
        return False
    return any(k in low for k in keys)


def check():
    """Return (out_of_place [(container, item, where, label)], unidentified [names])."""
    bad, unid = [], []
    for i in call("inv")["data"]["items"]:
        if i.get("equipped"):
            continue
        n = i["name"]
        low = norm_name(n)
        if i.get("id") == "unidentified":
            unid.append(n)
        elif is_food(low):
            continue  # run 11: --move shipped 19 mushrooms (box.py reached into the open Cooler Box)
        elif errand(low):
            continue
        elif has_word(low, HOME_ONLY) or not is_kit(low):
            bad.append(("pack", n, *route(n)))
    for n in bag_items("backpack"):
        low = norm_name(n)
        if has_word(low, HOME_ONLY):
            bad.append(("backpack", n, *route(n)))
            continue
        if is_kit(low) or is_food(low) or errand(low):
            continue
        # the user, run 12: scrolls, potions and rods ride in the backpack, where fire can't burn
        # them (a hot guy's blast destroyed a rod, the sleeping bag and two scrolls in the open pack)
        if has_word(low, ("potion", "scroll", "rod of", "jar of")):
            continue
        if any(q in low for q in UNID_TAGS) or "godly" in low:
            unid.append(n)
            continue
        bad.append(("backpack", n, *route(n)))
    # run 14: bag 2 is "a loot bag" (renamed with boxcfg name=): the haul rides there, so on the
    # home map all of it is out of place; quality-marked gear waits for identification
    # run 55: the pouch was never read: 43 red herbs, 43 iron bolts, 28 tobacco leaves, two claymores, a crossbow and an
    # ancient book rode in it for runs while the other bags filled (the circuit stopped "bags full")
    for haul in ("loot bag", "spoils bag", "haul bag", "pouch"):  # run 14: bag 3 is the second haul bag; run 41: bag 4 (G45)
        for n in bag_items(haul):
            low = norm_name(n)
            # run 22: Loytel's ★Land Deed waits on the user (reading it claims Vernis, G13 M2): it
            # rides in the bag until they decide, and blocked every departure as "no rule"
            if has_word(low, AWAITING_USER):
                continue
            if errand(low):  # run 44: carry.txt's Small Medals went back to the valuables twice from the loot bag
                continue
            if any(q in low for q in UNID_TAGS):
                unid.append(n)
                continue
            if has_word(low, HOME_ONLY) or has_word(low, ("torch",)):
                bad.append((haul, n, *route(n)))
                continue
            # run 18: the spoils bag is the kit's overflow (the pack sits at its stack limit, so
            # crafted, bought and swapped-out items kept landing in bags where tools can't see them)
            if haul == "spoils bag" and (is_kit(low) or has_word(low, ("potion", "scroll", "rod of"))):
                continue
            # run 14: 10 bone arrows looted into the bag went to the armory; kit goes back to the pack
            # run 36: only the core kit (CORE_KIT); minor kit rides in the bag it's in
            if is_kit(low) and not has_word(low, CORE_KIT):
                continue
            if is_kit(low):
                bad.append((haul, n, "pack", "the pack (trip kit)"))
            elif is_food(low):
                # the review of 2026-10-23: a looted sandwich went to the stone box through "sand": food is never
                # routed to a box. Run 49: it no longer comes out into the pack either: items.meals eats from any
                # depth since the review of 2026-11-11, and the pulled stacks filled the grid (35 -> 41 cards) while
                # the bags held room; food rots in a bag as in the pack (only the Cooler Box keeps it)
                continue
            else:
                bad.append((haul, n, *route(n)))
    # run 53: 7 coffee beans tiramisus taken for the trip were counted by leave.py (items.meals: kind "meal" in the game's
    # table) and sent back to the Pantry here (no MEALS word), so leave refused both ways. What items.meals would eat is
    # Cooler Box food: the one table decides.
    try:
        import items as _items
        eatable = {(it.get("name") or "").lower() for it in _items.meals(hunger=100)}
    except Exception:  # noqa: BLE001 - the name rule below still runs
        eatable = set()
    for n in bag_items("Cooler Box"):
        low = norm_name(n)
        # run 11: the godly Raw Food Necklace (made of food, kept cool to slow its rot) was routed
        # to the shipping chest; quality-marked gear is never shipped from any bag
        if any(q in low for q in UNID_TAGS):
            unid.append(n)
            continue
        # run 56: FOOD_OK keeps corpses as cookable food (run 12), but trips eat bought meals now and the game files every
        # corpse the PC steps onto into this box: eight stacks of corpses and stale meat left no slot for meals, so
        # leave.py counted none. In the Cooler Box a corpse or stale meat leaves by its route (the shipping chest)
        if re.search(r"\bcorpses? of\b|\bstale\b", low):
            bad.append(("Cooler Box", n, *route(n)))
            continue
        if not is_food(low) and n.lower() not in eatable:
            bad.append(("Cooler Box", n, *route(n)))
    return bad, unid


_CASTS = {}


def spell_over_cap(low):
    """True for a spellbook stock.py would call excess: a cursed one, a hostile summon, or a spell at its cast cap
    (run 49). The casts are read once a run of packcheck (bridge `power`); any failure reads as not over the cap."""
    try:
        from stock import SPELL_CAP, base, spell_names
        b = base(low)
        if not b or b[0] != "spellbook":
            return False
        if b[2] == "cursed" or b[1] in ("summon monster",):
            return True
        alias = spell_names().get(b[1])
        if alias is None:
            return False
        if not _CASTS:
            from common import data
            _CASTS.update({s["spell"]: s["stock"] for s in data("power")["party"][0].get("spells") or []})
        return (_CASTS.get(alias) or 0) >= SPELL_CAP
    except Exception:  # noqa: BLE001 (the library then, as before)
        return False


GRID_CARDS = 35   # the pack grid's card count (bag.py's refusal line, run 22)
FREE_SLOTS = 3    # run 25: free grid slots required to leave home


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    bad, unid = check()
    for c, n, where, label in bad:
        print(f"  {c:10} {n}  ->  {label}")
    if unid:
        print("for identification (carried, not blocking): " + "; ".join(unid))
    if "--move" in sys.argv and bad:
        z = (call("state")["data"].get("zone") or {}).get("full", "")
        if not z.startswith("Zone_startSite"):
            sys.exit("not at home: --move only works on the home map")
        from farmday import home_guard
        # run 41 (G46): 58 stacks took 10.9 real minutes, one walk and one window a stack; now one box.py call a destination
        groups = {}

        def flush(key):
            names = groups.pop(key, [])
            where, label = key
            boxes = ["shipping chest"] if where == "ship" else where.split("|")
            # run 38: every armory box full, so plain gear (a hemp shirt, a bronze mace) came back into the pack at every
            # home visit and filled it (the ladder's room check refused twice, a meal couldn't come out of the Cooler
            # Box): plain gear (no star, no quality tag: checked in route) ships when no armory box takes it
            if (where, label) == ARMORY:
                boxes.append("shipping chest")
            for box in boxes:
                if not names:
                    break
                home_guard("packcheck --move")  # run 41: the box walk starved me to death at home, then walked on under attack
                lines = tool("box.py", box, *names).splitlines()
                tool("close.py")
                # run 20: the "|" chain never reached the Storage Chest. It stopped at the first box
                # whose answer was not "did not move" (a box that could not be opened or reached,
                # "no Transfer offered", a refusal) and reported that; only a move ends the chain now
                left = []
                for nm in names:
                    line = next((ln for ln in lines if ln.startswith(nm + ":")), "")
                    if line:
                        lines.remove(line)
                    if ": moved " in line:
                        print(f"   {line}  [{box}]")
                    else:
                        left.append(nm)
                names = left
            if names and where == "ship" and "organs" in label:
                # run 46: the shipping chest had taken its ~40 stacks for the morning and refused a heart (G47's count):
                # an organ that can't ship goes to the trash can (Ecopo) rather than ride out on the trip
                print("   " + (tool("trash.py", "dump", *names).strip().splitlines() or ["trash.py said nothing"])[-2:][0])
                tool("close.py")
                from common import _key, data
                flat = [it["name"] for top in data("stock")["pack"] for it in [top] + (top.get("items") or [])]
                names = [nm for nm in names if any(_key(nm) in _key(n) for n in flat)]
            for nm in names:
                # run 45: "a spotted potion" left the bag under another name (identified on the way) and every box "refused" it:
                # an item no longer in the pack by that name isn't a full box (G47 counts only those)
                from common import _key, data
                flat = [it["name"] for top in data("stock")["pack"] for it in [top] + (top.get("items") or [])]
                gone = not any(_key(nm) in _key(n) for n in flat)
                print(f"   {nm}: " + ("!! not in the pack by this name any more (identified or renamed on the way?): nothing to move"
                                       if gone else f"!! did not move: every box of its route refused ({where})"))

        for c, n, where, label in bad:
            home_guard("packcheck --move")
            name = re.sub(r"^(an?|\d+)\s+", "", n)
            if where in ("read", "decide"):
                print(f"   {n}: {label}")
                continue
            if c != "pack":
                # a take needs a free card in the pack's grid: empty what's waiting first
                if sum(1 for i in call("inv")["data"]["items"] if not i.get("equipped")) >= GRID_CARDS - 2:
                    for key in list(groups):
                        flush(key)
                print("   " + last(tool("bag.py", c, "--take", name)))
                tool("close.py")
            if where in ("trash", "pack"):
                continue
            groups.setdefault((where, label), []).append(name)
        for key in list(groups):
            flush(key)
        if any(w == "trash" for _, _, w, _ in bad):
            # run 20: a one-line answer ("no Use act on the trash can from 55,52") crashed [-2]
            lines = [ln for ln in tool("trash.py", "dump").splitlines() if ln.strip()]
            print("   " + (lines[-2] if len(lines) > 1 else (lines[0] if lines else "trash.py said nothing")))
        bad, unid = check()
    p = (call("state")["data"].get("pc") or {})
    stacks = p.get("stacks")  # bridge 0.30.0; an older mod: count the loose stacks
    if stacks is None:
        stacks = sum(1 for i in call("inv")["data"]["items"] if not i.get("equipped"))
    # run 25: the pack's grid holds 35 cards; at 35 every take from a bag, a chest or a box is refused or lands
    # in another window, and the day lost five stops to it (the meals, the identify rod, the gold bars, the
    # roasts at a nefia's door): leave home with 3 slots free (FREE_SLOTS), so a trip can take things out
    # the grid's own count: the inv entries not worn (bags and the orens card take a slot each); pc.stacks counts
    # the toolbelt's stacks too and read 37 at a full grid of 35 (run 25)
    try:
        grid = sum(1 for i in call("inv")["data"]["items"] if not i.get("equipped"))
    except Exception:  # noqa: BLE001 - an older mod: fall back to the state's count
        grid = stacks or 0
    free = GRID_CARDS - grid
    # run 40 (the user: "the chest in the bag? That's a double bag"): a boss's chest rode inside the backpack with 8 gold bars and 1,250
    # orens, and this check never looked inside it: name any container inside a bag, and what it holds
    for bag in call("stock")["data"].get("pack") or []:
        for inner in bag.get("items") or []:
            if inner.get("items") and "toolbelt" not in bag["name"].lower():
                print(f"!! nested: {bag['name']} holds {inner['name']} with {', '.join(i['name'] for i in inner['items'][:6])}")
    print(f"out of place: {len(bad)}; the pack holds {stacks} stacks ({free} grid slots free)" + ("" if bad or free < FREE_SLOTS else "  (pack ready)"))
    if not bad and free < FREE_SLOTS:
        print(f"!! the pack grid has {free} free slot(s) of {GRID_CARDS}: bag or store {FREE_SLOTS - free} more stack(s) before leaving")
        sys.exit(1)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
