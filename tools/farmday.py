"""springday's library (run 05's own day loop is gone: springday.py superseded it in run 10, and
the review of 2026-10-23 dropped the dead main() with its stale sleep spot). What stays is what
springday, trainday, ladder and water import:

  eat_one()        one meal from the Cooler Box (its own stacks first, then the MEALS words);
                   None with a dialog or window open, or nothing edible
  MEALS            the words that make a stack a meal (whole words, plurals included)
  pay_tax()        a Tax Bill in the mail post is paid at the home tax chest (paytax.py)
  close_report()   the morning shipping report, if open, is read (the income) and closed
  loop_gate()      why to stop a home loop, or None: common.ready at the loop thresholds
  walk(x, z)       walkto at home (no hostile radius, no HP floor: home-only), returns pc
  water() / dry_cells() / can_charges()   the field's watering (water.py adds the second pass)
  cook_stews(k) / meals_in_cooler()       weed stews at the bonfire for the Cooler Box

The field is home.FIELD. Never uses Pass Time or waits.
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call, close  # noqa: E402

TOOLS = Path(__file__).resolve().parent
# Run 10 (486-03-03): pasture 49-53,43; imo 49-50,44; mushroom 49-53,45; tomato 49-53,46.
# Watering costs a charge per cell (TaskWater), so the can is refilled when under len(FIELD) + 1.
from home import FIELD  # noqa: E402  (the 38-cell field since run 12; one definition for every tool)
import home  # noqa: E402
from home import BOX_STR  # noqa: E402
from common import THRESHOLDS, last, ready, state, wait_idle, wait_until  # noqa: E402,F401  (state: re-exported to springday and water)
from common import run as _run, walk as common_walk  # noqa: E402
from packcheck import has_word, split_listing  # noqa: E402

MAIL_POST = "61,50"
LAKE_STAND, LAKE_WATER = (48, 41), (47, 40)
BONFIRE_STAND = home.BONFIRE_STAND  # run 18: the Kitchen
_BF = (str(home.BONFIRE[0] - BONFIRE_STAND[0]), str(home.BONFIRE[1] - BONFIRE_STAND[1]))
# Most filling first that's cheap to replace; the giant grape (4.5s) never finished eating (run 05).
# Whole words with plurals (the review of 2026-10-23: "imo" fitted "kimono" and "pie" "pieces" as
# substrings), so "roast" covers roasts and "jerky" jerkies; run 14: the plural first ("mushroom"
# hit a loose raw white one).
RATION_RESERVE = 5  # run 44: travel rations kept back for Fast Travel fares (1 + hours/24 each); the rest are food


def rations_carried():
    """Travel rations in the pack and every carried container (the Cooler Box included)."""
    import re as _re
    from common import data
    n = 0
    for it in data("stock").get("pack") or []:
        for x in [it] + (it.get("items") or []):
            if "travel ration" in (x.get("name") or "").lower():
                m = _re.match(r"(\d+) ", x["name"])
                n += int(m.group(1)) if m else 1
    return n


MEALS = ("roasted", "roast", "on the bone", "skewer", "imo", "weed stew", "soup", "bread", "salad", "tomato", "mushrooms", "mushroom",
         "truffle", "api nut",  # run 10: tomatoes, mushrooms
         # run 20: the last food in the Cooler Box was 3 jerkies and eat_one returned None at hunger 78
         # (run 18's starvation was the same gap, "roasts"): the preserved and bought foods
         "jerky", "jerkies", "travel ration", "sashimi", "steak", "sandwich", "pie", "curry", "noodle", "udon", "rice ball",
         "omelet", "omelette", "fried egg", "cake", "cookie", "cream puff",
         # run 24: the Cooler Box held melons, bananas, stir-fries and marshmallows that no word matched
         # (only the bread and rations would have been eaten: run 18's starvation gap again)
         "melon", "banana", "stir-fry", "stir-fries", "marshmallow", "manju", "croquette", "pizza", "fruit",
         # run 26: "8 fried potatoes" and "6 soybeans cookies" (plural) matched nothing: a hungry stop with a full box
         "potato", "potatoes", "cookies", "onigiri", "onigiris", "takoyaki", "stew", "stews", "roasts", "skewers",
         "soups", "potage", "potages", "sardine",
         # run 29: the Cooler Box's only food was 4 blocks of cheese, which matched nothing
         "cheese",
         # run 34: the ladder's nap found "nothing edible" at hunger 63 with soybeans (Nutrition 9, eaten raw by hand:
         # 61 -> 53), green herbs and milk in the Cooler Box: small, but food
         "soybeans", "green herb", "green herbs", "milk", "protein", "gelatin",
         "anpan", "anpans", "taiyaki", "taiyakis", "soybeans rice", "soybeans rices",  # run 34: Erobird's and the chests' meals
         # run 35: "nothing edible" at hunger 72 with 3 bush de noels (Christmas cakes) in the Cooler Box
         "bush de noel", "bush de noels",
         # run 38: Very Hungry (81) at home with an ally's half-eaten lunch box in the Cooler Box: no word matched it
         "lunch box", "lunch boxes",
         # run 39: "7 palulu shortcakes" (Upan) matched no word ("cake" is whole-word)
         "shortcake", "shortcakes",
         # run 41: the ladder stopped Hungry twice with 22 meals in the Cooler Box (moon dumplings, sacks, avocados, watermelons)
         "dumpling", "dumplings", "sack", "sacks", "avocado", "avocados", "watermelon", "watermelons", "mousse", "mousses",
         "mochi", "egg", "eggs", "meat")
NOT_MEALS = ("white mushroom", "red mushroom", "rotten")  # harmful raw mushrooms (foods.md), rotten food


def is_meal(name):
    """A stack name that eat_one may eat: a MEALS word as a whole word, none of NOT_MEALS."""
    # run 34 (the user: "Careful Raw Food Weapons/Armor are not things to eat"): gear of a food material ("A Raw Food
    # Claw (Miracle)", a "cheese" shield) carries weapon dice, armour values, a quality tag or a gear word
    import re
    if re.search(r"\(miracle\)|\(godly\)|\(superior\)|\[-?\d+, -?\d+\]|\(\d+d\d+|\(\+\d+", name, re.I):
        return False
    if re.search(r"\b(claw|sword|axe|shield|armor|mail|robe|shirt|boots|shoes|gloves|helm|hat|ring|amulet|necklace|"
                 r"girdle|cloak|staff|spear|dagger|mace|scythe|sickle|bow|trident|wakizashi|katana)s?\b", name, re.I):
        return False
    # run 39: "a horsetopia food", "a yeek archertopia food" (lunch_dystopia: a FoodMeal lunch, Nutrition 20, STR 30,
    # 1,550 orens) had no word: any "-topia food" is that lunch made from a corpse
    if re.search(r"topia foods?\b", name, re.I):
        return not has_word(name, NOT_MEALS)
    return has_word(name, MEALS) and not has_word(name, NOT_MEALS)


def run(*args, timeout=280):
    return _run(args[0], *args[1:], timeout=timeout)


def close_report(s=None):
    """The morning shipping report (LayerShippingResult) blocks every act until it is closed: read
    the income, close it, and return the state afterwards."""
    s = s or state()
    if (s.get("layers") or {}).get("top") == "LayerShippingResult":
        texts = call("texts", all=True, max=100000)["data"]["texts"]
        if "Today's Income" in texts:
            print(f"    shipping income: {texts[texts.index("Today's Income") + 1]} orens")
        call("closetop")
        wait_until("frames", n=10, timeout=2000)
        s = state()
    return s


def loop_gate(s=None):
    """Why to stop a home loop now, or None: the shipping report is closed first; then common.ready
    at the loop thresholds (HP under loop_hp, Hungry at `hungry`: the review of 2026-10-23 found
    this check at hunger 80 while rule zero says 70), a hostile in view, a window, a bad condition.
    Not common.threat: that one has no hunger gate and doesn't close the report."""
    s = close_report(s)
    return ready(s, hp=THRESHOLDS["loop_hp"], hunger=THRESHOLDS["hungry"], idle=False)


def walk(x, z):
    """Walk with the bridge's walkto (run 12 review); returns the player's state afterwards."""
    common_walk(x, z, r=0, hp=0, timeout=30000)
    return state()["pc"]


def pay_tax():
    out = run("box.py", MAIL_POST)
    if "Tax Bill" not in out:
        return None
    res = run("paytax.py")  # the chest is a drag grid now (run 08)
    gold = state()["pc"]["gold"]
    return f"tax: {last(res)}; gold now {gold}"


def field_status():
    from common import cells as read_cells
    info = read_cells(FIELD)  # one bridge call for the field (was one per cell)
    return [(x, z, c.get("obj"), c.get("growStage"), c.get("ripe")) for (x, z), c in info.items()]


def can_charges():
    for i in call("inv")["data"]["items"]:
        m = re.search(r"watering can \((\d+) Charge", i["name"])
        if m:
            return int(m.group(1))
    return None


def dry_cells(extra_cells=()):
    """Farm-field cells (the field and any extra cells) not yet watered today. Rain waters every
    unroofed field cell (Zone.RainWater): the user's rule, run 15, "raining means you don't need
    to water plants"."""
    from common import cells as read_cells
    info = read_cells(list(dict.fromkeys(list(FIELD) + list(extra_cells))))
    return [p for p, c in info.items() if c.get("floor") == "field" and not c.get("watered")]


def water():
    if not dry_cells():
        return "skipped: the field is already wet (rain)"
    ch = can_charges()
    if ch is None:
        return "no watering can"
    run("hotbar.py", "--deselect")
    run("item.py", "watering can", "Grab")
    run("close.py")
    if ch < len(FIELD) + 1:
        walk(*LAKE_STAND)
        p = state()["pc"]
        run("act.py", str(LAKE_WATER[0] - p["x"]), str(LAKE_WATER[1] - p["z"]), "Draw Water", "right")
        wait_idle(timeout=10000)
    walk(FIELD[0][0] + 1, FIELD[0][1] - 1)
    p = state()["pc"]
    # "Water crops" waters the whole field; a field watered today offers only "Water" (one cell)
    out = run("act.py", str(FIELD[0][0] - p["x"]), str(FIELD[0][1] - p["z"]), "Water crops", "right")
    if "no act" in out:  # watered already today: only the single-cell act is offered
        out = run("act.py", str(FIELD[0][0] - p["x"]), str(FIELD[0][1] - p["z"]), "Water", "right")
    wait_idle(timeout=60000)  # the watering task ends on its own (was a 25 x 1.2 s poll)
    run("item.py", "watering can", "Put away")
    run("close.py")
    return f"watered ({last(out)}); can {can_charges()} charges"


def meals_in_cooler():
    out = run("bag.py", "Cooler Box")
    run("close.py")
    n = 0
    for part in split_listing(out):
        if is_meal(part):
            m = re.match(r"(\d+) ", part)
            n += int(m.group(1)) if m else 1
    return n


def cook_stews(k):
    # The bonfire burns a branch from the pack per fire; with none it silently cooks nothing
    # (run 05: three days of "cook" with an empty Cooler Box). Bring branches from the wood box.
    if not any("branch" in i["name"] for i in call("inv")["data"]["items"]):
        run("box.py", BOX_STR(home.WOOD_BOX), "--take", "branches")  # the wood box (G12, run 11); box.py closes itself
    walk(*BONFIRE_STAND)
    run("hotbar.py", "--deselect")
    out = run("craft.py", *_BF, "Weed stew", str(k), "--use", "tufts of grass")
    run("close.py")
    run("bag.py", "Cooler Box", "weed stew")
    run("close.py")
    return last(out)[:120]


def home_guard(what, limit=65, hard=80):
    """Before each step of a long job at home: the meal rule below, HP, and hostiles (run 41: **the second death of the day**: an orc warrior
    Lv11 and a scorpion Lv7 walked in during packcheck --move, box.py refused with a hostile in view and the mover went on to the next box
    for 3.4 real minutes, 263 -> -1 HP without one swing). A foe at or under my level gets fight.py; anything else is exit 3."""
    # run 41: the game's "winter is coming" drama sat open and every box call failed without a word for ~10 real minutes (the user saw it):
    # read a dialog through; one that asks a choice is mine
    s = state()
    if s.get("drama") or (s.get("layers") or {}).get("top") == "LayerDrama":
        print("  a dialog during " + what + ": " + last(run("talk.py", "4")))
        s = state()
        if s.get("drama") or (s.get("layers") or {}).get("top") == "LayerDrama":
            sys.exit(f"stop: a dialog is open during {what}: talk.py")
    feed_or_stop(what, limit, hard)
    for _ in range(6):
        s = state()
        p = s.get("pc") or {}
        foes = [c for c in s.get("nearby") or [] if c.get("hostile")]
        if p.get("hp", 0) < 0.6 * (p.get("maxHp") or 1):
            sys.exit(f"stop: HP {p.get('hp')}/{p.get('maxHp')} during {what}: heal first")
        if not foes:
            return
        f = min(foes, key=lambda c: c.get("dist", 99))
        if "cat" in str(f.get("id")) or (f.get("lv") or 99) > p.get("lv", 0):
            sys.exit(f"stop: {f.get('name')} Lv{f.get('lv')} at {f.get('dist')} during {what}: my decision")
        print(f"  {f.get('name')} Lv{f.get('lv')} during {what}: fighting it")
        # a slime's melee splash eats the gear's enchants (fight.py refuses): the Putit
        tool = ("throw.py", f.get("name", "").split()[-1], "Putit In Amber", "8") if "slime" in str(f.get("id")) else ("fight.py", f.get("id") or f["name"])
        r = run(*tool, timeout=300)
        if getattr(r, "rc", 0) == 3:
            sys.exit(f"stop: {tool[0]} stopped during {what}")
    sys.exit(f"stop: still hostiles in view during {what}")


def feed_or_stop(what, limit=65, hard=80):
    """A long walk at home has a hunger stop too (run 41: **death by starvation**: arrive.py's box walk ran 3,274 turns from hunger 70
    to 93 and HP -3 with meals in the Cooler Box and 400 mushrooms in the fridge; run 18's rule, for every unattended loop, had never
    reached this one). At `limit` a meal; at `hard` with no meal landed, exit 3 naming what stopped."""
    s = state()
    h = (s.get("pc") or {}).get("hunger", 0)
    if h < limit:
        return
    meal = eat_one()
    print(f"  hunger {h} during {what}: ate {meal}")
    h = state()["pc"].get("hunger", 0)
    if not meal and h >= hard:
        sys.exit(f"stop: hunger {h} during {what} and no meal landed: get food before anything else")


def eat_one():
    # run 17 (the user: "I don't think you can eat and ignore the popup can you"): a bandit's
    # demand dialog was open on an ambush map and the meal silently did nothing (hunger 65 -> 65);
    # a dialog or report must be answered first
    s = state()
    top = (s.get("layers") or {}).get("top")
    if (top and top not in ("LayerInventory",)) or s.get("drama"):
        print(f"  not eating: {top or 'a dialog'} is open (answer it first: talk.py)")
        return None
    # run 26: with the pack grid full (packcheck.GRID_CARDS, 35) a meal taken from the Cooler Box "overflows from
    # your backpack and falls to the ground" uneaten (two rations and two soups lost that way): say so and stop
    from common import data
    carried = [i for i in data("inv")["items"] if not i.get("equipped")]
    pack_meals = None
    if len(carried) >= 35:
        # run 27: a single-item meal already in the pack needs no free card: eat it by its full name. A
        # bigger stack is split to eat one, and the split piece "overflows from your backpack" like a Cooler
        # Box meal (7 piles of bread: hunger 62 -> 62, one bread on the floor), so only stacks of one count
        pack_meals = [i["name"] for i in carried if is_meal(i["name"]) and "rotten" not in i["name"].lower()
                      and (i.get("num") or 1) == 1
                      # run 28 (twice): the last travel ration is the Fast Travel fare; only past Very Hungry
                      and ("ration" not in i["name"].lower() or s["pc"].get("hunger", 0) >= 80 or rations_carried() > RATION_RESERVE)]
        if not pack_meals:
            # run 28: the full grid stopped five meals in one night; move non-kit stacks into the bags and try again
            try:
                from purge import unclutter, free_cards
                unclutter()
                carried = [i for i in data("inv")["items"] if not i.get("equipped")]
                # run 39 (Enchanted Cave B2): all three bags at 35, unclutter moved nothing, and the mushroom taken
                # from the Cooler Box fell to the floor twice (the ladder's Hungry stop); off the home map, drop the
                # cheap or over-cap stacks (purge's own rules) until two cards are free
                if len(carried) >= 35 and not (s.get("zone") or {}).get("isHome") \
                        and "startSite" not in str((s.get("zone") or {}).get("full")):
                    free_cards(2)
                    carried = [i for i in data("inv")["items"] if not i.get("equipped")]
            except Exception as e:  # noqa: BLE001 (a meal is never worth a crash)
                print(f"  unclutter failed: {e}")
            if len(carried) >= 35:
                # run 38: Very Hungry twice at home (81, 85) with a full grid and 30+ mushrooms in the Cooler Box, and
                # this refused both times; item.py's Eat on the open box's stack then ate one each time at 35 cards
                # (75 -> 62 -> 49 -> 36). Try it: the hunger check below stops at a meal that didn't land
                print("  the pack grid is full (35 cards): trying the Cooler Box anyway (run 38: meals landed at 35)")
            pack_meals = None
        else:
            # run 28: the one travel ration in the pack was eaten before a pack of soybeans; rations pay the Fast
            # Travel fare (inns only sell them), so they are the last pack meal tried
            pack_meals.sort(key=lambda n: "ration" in n.lower())
            print("  the pack grid is full: eating a meal carried in the pack, not one from the Cooler Box")
    # run 26: a hostile in view cancels the meal, and this printed "ate" with hunger unchanged three times
    foes = [c for c in s.get("nearby") or [] if c.get("hostile")]
    if foes:
        print(f"  not eating: {foes[0].get('name')} is in view (a hostile cancels the meal)")
        return None
    if pack_meals:
        foods = pack_meals  # the Cooler Box stays closed: item.py sees only the pack's stacks
    else:
        listing = run("bag.py", "Cooler Box")  # an open bag lets item.py find food inside it
        # run 14: a bare "mushrooms" matched loose raw white/red ones too (refused as ambiguous or
        # harmful); eat the Cooler Box's own stacks by their full names, never the harmful or rotten
        named = [x for x in split_listing(listing) if is_meal(x)]
        # run 41 (run 18's gap a fourth time): what's in the Cooler Box is food unless it says otherwise, so an unknown word comes
        # last instead of ending the loop Hungry; item.py still refuses harmful foods
        # run 44: "a marbled meat of 『Public performer』" was eaten on a nefia's floor: "Eeeek! It's human flesh!", insanity.
        # A named creature's meat (『』) and anything of a person is never food
        named += [x for x in split_listing(listing) if x not in named and not re.search(r"corpse|remnant|rotten|offal", x.lower())
                  and "『" not in x and not re.search(r"\bflesh\b|\b(of|from) [A-Z][a-z]+ the\b", x)]
        foods = named + list(MEALS)
    for food in foods:
        h0 = state()["pc"]["hunger"]
        # run 29: the Cooler Box held no meal, the MEALS fallback reached "travel ration" and wgo's meal stop ate
        # one of two at hunger 33 (the run 28 rule covered only the full-grid path): a ration is the Fast Travel
        # fare, never a meal under hunger 80 on any path
        # run 44: with 11 rations and nothing else, "never under 80" stopped a ladder at hunger 67 on a danger-12 floor:
        # only the reserve (RATION_RESERVE, the next fare and one spare) is kept back
        if "ration" in food.lower() and h0 < 80 and rations_carried() <= RATION_RESERVE:
            continue
        # run 39 (Warded Ruin B2): the mushrooms had rotted and the Cooler Box held only milk: milk is drunk, not eaten
        # ("It is drinkable", Nutrition 5), so the Eat act was never offered and the ladder stopped Hungry
        verb = "Drink" if re.search(r"\bmilks?\b", food.lower()) else "Eat"
        out = run("item.py", food, verb)
        if f"{verb} -" in out:  # item.py prints the food's tooltip first
            wait_idle(timeout=30000)  # let the meal finish: closing windows early cancelled it
            run("close.py")
            h1 = state()['pc']['hunger']
            for _ in range(10):  # the meal can register a few seconds after wait_idle returns
                if h1 < h0:
                    break
                time.sleep(0.6)
                h1 = state()['pc']['hunger']
            if h1 >= h0:  # the meal didn't land (cancelled, or the stack fell out of a full pack)
                print(f"  {food}: hunger {h0} -> {h1}: the meal didn't land")
                return None
            return f"{food} (hunger {h0} -> {h1})"
    run("close.py")
    # run 30: twice this returned None without a word while the Cooler Box held only corpses, offal and milk and
    # the last stew and cheese rode in the loot bag (not looked in): say what was tried
    print(f"  no meal eaten: nothing edible matched in the pack or the Cooler Box (tried {len(foods)} names); "
          "food in the loot bag or spoils bag must be taken out first (bag.py), or buy food")
    return None
