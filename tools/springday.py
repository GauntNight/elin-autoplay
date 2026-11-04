"""Day loop for the home field in spring (run 10, G3): grow, harvest, keep the seed stock.

Each day after 06:00 (the growth tick), in order:
  1. a shipping report is read and closed; a tax bill in the mail post is paid at the tax chest;
     a hostile in view, HP under 80%, Hungry (70+) or another window stops the loop (common.ready)
  2. mushrooms (the seed engine): reap the REAP row with the sickle (1-3 seeds each, the plant
     goes), cut the CUT cells with the axe (one mushroom each, into the Cooler Box), replant all
  3. ripe crops: per crop kind, reap REAP_SHARE of the ripe plants for seeds and hand-harvest the
     rest for food (1-3 imo, 1-4 tomatoes), cut the harvested stubs (a seed ~12% of the time) and
     replant every emptied cell with that crop's seeds (best quality first)
  4. pasture at stage 3+: cut most of it for pasture (1+rnd(stage) each) into the shared box for
     the livestock putit (one a day grows its fur), reap the rest for seeds, replant
  5. water the whole field, with a second pass on the cells the 17-charge can doesn't reach
  6. eat at hunger 45 from the Cooler Box (before the work too, so a night's hunger never stops
     the day); when nothing can be eaten at hunger 60+ the loop STOPS (exit 3; run 18's starvation);
     shear any furry visitor in view (shear.py)
  7. sleep when sleepy (sleep.py --home-ok), else stop (the no-waiting rule)
Never harvests unripe crops; keeps fertility above zero (prints the census each day).

usage: python -I tools/springday.py [DAYS=3] [UNTIL=486-04-02] [--mushrooms-every N] [--once]
  --once: one farm round and a meal after 06:00, then return (no sleeping or waiting: the user's
          no-waiting rule; other work fills the day)
Exit 0 at a limit (--once done, UNTIL reached, stopjob asked), 3 stopped for a decision (a threat,
a window, hunger, a full pack, nothing left but waiting).
(run 10: a full day took ~20 real minutes, most of it the mushroom round; every 4th day is plenty)
Stop it early with `python -I tools/stopjob.py springday` (it returns at the next check).
"""
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from activity import mark  # noqa: E402
from common import THRESHOLDS, last, ready, stop, wait_idle  # noqa: E402
from common import cells as read_cells  # noqa: E402
from farmday import close_report, eat_one, pay_tax, run, state, walk  # noqa: E402
from job import register, stop_requested  # noqa: E402
import home  # noqa: E402
from reap import SICKLE  # noqa: E402  (the farm sickle's name; a local "reap" in farm_round shadows a module name)
from home import BOX_STR  # noqa: E402
from packcheck import has_word, split_listing  # noqa: E402

MUSH_REAP = [(49, 45), (50, 45), (51, 45), (52, 45), (53, 45), (48, 45),
             (49, 48), (50, 48), (51, 48), (52, 48), (53, 48)]  # run 12: the field grew south
MUSH_CUT = [(54, 46), (48, 43), (48, 46), (53, 49)]  # run 18: six cut cells became imo (resident dishes)
# run 15 (G14, travel rations): the south row 49-52,49 grows wheat (4 seeds from Yowyn's Ecopo
# shop): 2 wheat -> flour at the millstone, flour + a nut (crim, api nut, coffee bean) -> a ration
# run 11 (486-04-15): a round with a full pack kept no seeds, so the field was replanted from the
# seeds at hand: tomato on 5 cells, imo on 4, pasture on 1, mushrooms on the rest
CROPS = {
    "tomato": [(49, 46), (50, 46), (51, 46), (52, 46), (53, 46), (49, 47), (50, 47), (52, 47)],
    "imo": [(49, 44), (50, 44), (52, 43), (53, 43),
            (51, 44), (52, 44), (54, 44), (48, 44), (49, 43), (51, 43)],  # run 18: stone roasted sweet imo (imo + 2 pebbles) feeds the residents
    "wheat": [(49, 49), (50, 49), (51, 49), (52, 49)],
}
PASTURE = [(50, 43)]
REAP_SHARE = 0.30   # run 18: 0.30 while the seed stock is large and the residents need food; break-even for the seed stock is ~51-62% (run 10: 1.6-2.2 seeds a reap)
PASTURE_REAP = 0.25
# run 12: the field is 38 cells (rows 43-49) and the can holds 17: after "Water crops" the second
# pass waters every field cell that is still dry, refilling at the lake whenever the can empties
EXTRA_WATER = [f"{x},{z}" for z in range(43, 50) for x in range(48, 55)]
SEED_BOX = BOX_STR(home.FARM_BOX)  # the Farm box (G12, run 11): seeds and farm tools beside the field
TOOL_BOX = BOX_STR(home.FARM_BOX)
SHARED = BOX_STR(home.FODDER_BOX)
MUSH_EVERY = 1  # --mushrooms-every N (0: never)
PASTURE_SPOTS = [(57, 47), (58, 47), (57, 46), (58, 46)]
STOP_HUNGER = 60  # a failed meal at this hunger or worse ends the loop (errors.csv row 37, run 18)


def close_backpack():
    """Picked-up harvest went into an open backpack (run 10: 6 pastures and the +2 seeds hid there):
    keep it closed during the farm round."""
    for b in call("buttons", all=True)["data"]["buttons"]:
        if b.get("in") == "pack" and "backpack" in (b.get("card") or "").lower():
            acts = {a["text"]: a["i"] for a in call("invacts", i=b["i"])["data"]["acts"]}
            if "Close" in acts:
                call("invdo", i=acts["Close"])
            break
    run("close.py")


def held_seeds():
    return [i["name"] for i in call("inv")["data"]["items"] if "seed" in i["name"]]


def seeds_of(kind):
    """Seed stacks of one kind in the pack, best quality first ('+2' before '+1' before plain)."""
    names = [n for n in held_seeds() if f"of {kind}" in n]
    lvl = lambda n: int(m.group(1)) if (m := re.search(r"\+(\d+)", n)) else 0  # noqa: E731
    return sorted(names, key=lvl, reverse=True)


def fetch_seeds(kind):
    # one --take per kind: box.py's matcher reads "seeds of X" and "seed of X" as the same stack
    # (common.stack_hits folds the plural), so the second call of the old pair was a second walk
    run("box.py", SEED_BOX, "--take", f"seed of {kind}")


def plant(kind, cells):
    """Plant every empty field cell in cells with seeds of kind (from the pack, then the seed box)."""
    info = read_cells(cells)
    empty = [(x, z) for x, z in cells if not info[(x, z)].get("obj")
             and not any("seed" in t for t in info[(x, z)].get("things") or [])]
    if not empty:
        return 0
    if not seeds_of(kind):
        fetch_seeds(kind)
    n = 0
    for refill in (False, True):
        if refill:
            if not empty:
                break
            # run 12 (the user saw it): 10 fresh seeds in the pack planted 10 of 13 cells and the
            # rest stayed bare; when the pack runs out, fetch more from the seed box and go on
            fetch_seeds(kind)
        for name in seeds_of(kind):
            if not empty:
                break
            stem = re.sub(r"^(an?|\d+) ", "", name)
            run("farm.py", "plant", stem, *[f"{x},{z}" for x, z in empty], timeout=900)
            info = read_cells(empty)
            done = [(x, z) for x, z in empty if any("seed" in t for t in info[(x, z)].get("things") or [])]
            n += len(done)
            empty = [c for c in empty if c not in done]
    return n


FIELD = [(x, z) for x in range(47, 56) for z in range(42, 48)]  # the home field and its margin


def plant_bare():
    """Mushrooms on every tilled cell left bare (run 12: 48,43 and 48,46 were in no list, and the
    pasture cell had no seeds): a bare field cell grows weeds that eat fertility."""
    info = read_cells(FIELD)
    bare = [(x, z) for x, z in FIELD if "field" in (info[(x, z)].get("floor") or "")
            and not info[(x, z)].get("obj") and not any("seed" in t for t in info[(x, z)].get("things") or [])]
    return plant("mushroom", bare) if bare else 0


def bank_seeds():
    for name in held_seeds():
        if "weed" in name or "flower" in name:
            run("box.py", "56,52", re.sub(r"^(an?|\d+) ", "", name))  # ship wild seeds
        else:
            run("box.py", SEED_BOX, re.sub(r"^(an?|\d+) ", "", name))


def feed_pasture():
    """Place the pack's pasture on the ground next to 57,47: the livestock eat installed pasture
    (FactionBranch.DailyOutcome: Stocked.Find shared or Installed.Find); a stack in the shared box
    sat uneaten for three days (run 10)."""
    if not any("pasture" in i["name"] and "seed" not in i["name"] for i in call("inv")["data"]["items"]):
        return "no pasture in the pack"
    run("hotbar.py", "--deselect")
    run("item.py", "pastures", "Grab")
    run("item.py", "a pasture", "Grab")
    run("close.py")
    spots = read_cells(PASTURE_SPOTS)  # one call for the four spots
    for x, z in PASTURE_SPOTS:
        c = spots.get((x, z)) or {}
        if c.get("obj") or c.get("blocked"):
            continue
        walk(x, z + 1)
        p = state()["pc"]
        out = run("act.py", str(x - p["x"]), str(z - p["z"]), "Place", "right")
        if "no act" not in out:
            return f"placed at {x},{z}"
    return "no free spot"


# Farm food goes to the home's shared harvest box (residents eat from it; Delegated Farming fills it
# too), not the carried 9-slot Cooler Box: run 13 found the Cooler Box full of 35 farm mushrooms,
# so new food and fish stayed loose in the pack and rotted, and eating from the box dropped food on
# the ground (the user, run 13: "cooler pack may do better..."). Raw white and red mushrooms are
# harmful (foods.md): they go to the pantry as bait material.
HARVEST_BOX = BOX_STR(home.HARVEST_BOX)
PANTRY = BOX_STR(home.PANTRY)  # run 18: in the Kitchen
DISH_BOX = BOX_STR(home.DISH_BOX)  # run 18: the residents' shared Dishes box
# whole words (packcheck.has_word): "imo" no longer fits "kimono" (the review of 2026-10-23)
FARM_FOOD = ("mushroom", "truffle", "tomato", "imo", "bamboo", "wheat", "carrot", "cabbage", "potato", "pumpkin")
BAIT_FOOD = ("white mushroom", "red mushroom")
# The user, run 15: "we need a threshold for farming, right now we have a lot of mushrooms and food".
# On 486-08-22 the harvest box held 92 rotten mushrooms and ~20 other rotten stacks: Delegated
# Farming and the cut cells bring far more than the 2-3 a day I eat, and the rest rots. Each round:
# rotten food in the harvest box goes to the trash can, and fresh farm food above FOOD_KEEP items
# goes to the shipping chest (sold at 05:00) while it is still worth something, until the ration
# maker (G14) can turn the surplus mushrooms into rations that keep.
FOOD_KEEP = 30
GRAIN = ("wheat", "rice")  # ration inputs (G14): kept whatever the count, never shipped
SHIPPING = "56,52"


def store_food():
    names = [i["name"] for i in call("inv")["data"]["items"] if not i.get("equipped")]
    bait = [n for n in names if has_word(n, BAIT_FOOD) and "seed" not in n]
    food = [n for n in names if has_word(n, FARM_FOOD) and "seed" not in n and n not in bait]
    # run 20 (the user: "shouldn't we put food in the fridge?"): ~60 stacks had rotted in the
    # harvest box and the pantry. Fresh food goes into the powered fridge first (nothing rots there;
    # residents eat only prepared food, so raw crops are safe in it); grain and the overflow go to
    # the harvest box, where ration.py and cookdishes.py find them too.
    grain = [n for n in food if has_word(n, GRAIN)]
    fresh = [n for n in food if n not in grain]
    moved, left = [], []
    if fresh:
        out = run("box.py", DISH_BOX, *fresh)  # box.py closes its window itself
        moved += [ln.strip() for ln in out.splitlines() if "moved" in ln and "not moved" not in ln]
        left = [n for n in fresh if not any(n in ln for ln in moved)]
    for where, items in ((PANTRY, bait), (HARVEST_BOX, grain + left)):
        if items:
            out = run("box.py", where, *items)
            moved += [ln.strip() for ln in out.splitlines() if "moved" in ln]
    return "; ".join(moved)


def surplus():
    """Rotten food out of the harvest box to the trash can; fresh farm food above FOOD_KEEP
    items to the shipping chest (whole stacks, the biggest kept first)."""
    inside = split_listing(run("box.py", HARVEST_BOX))
    rotten = [x for x in inside if "rotten" in x.lower()]
    fresh = [x for x in inside if "rotten" not in x.lower() and "seed" not in x.lower()
             and has_word(x, FARM_FOOD) and not has_word(x, GRAIN) and not has_word(x, BAIT_FOOD)]

    def qty(x):
        m = re.match(r"(\d+) ", x)
        return int(m.group(1)) if m else 1
    kept, ship = 0, []
    for x in sorted(fresh, key=qty, reverse=True):
        if kept < FOOD_KEEP:
            kept += qty(x)
        else:
            ship.append(x)
    notes = []
    for i in range(0, len(rotten), 10):  # ten stacks a trip: the pack's stack limit
        run("box.py", HARVEST_BOX, "--take", *rotten[i:i + 10])
        run("trash.py", "dump")
    if rotten:
        notes.append(f"{len(rotten)} rotten stacks to the trash can")
    for i in range(0, len(ship), 10):
        run("box.py", HARVEST_BOX, "--take", *ship[i:i + 10])
        run("box.py", SHIPPING, *ship[i:i + 10])
    if ship:
        notes.append(f"kept {kept} fresh, shipped {sum(qty(x) for x in ship)} ({len(ship)} stacks)")
    # run 16: the reap gives ~20 mushroom seeds a round and the replant takes them back; the 1-3 left
    # over found no room in the full Farm box and blocked leave.py every day: they go to the can
    left = [i["name"] for i in call("inv")["data"]["items"] if re.search(r"seeds? of mushroom", i["name"])]
    if left:
        run("trash.py", "dump", *left)
        notes.append("spare mushroom seeds to the trash can: " + ", ".join(left))
    return "; ".join(notes)


# Run 17: Kettle starved at home. Residents eat only prepared food (TraitFoodPrepared: dishes,
# bread, fruit, jerky) from shared containers (Chara.CanEat, Zone.TryGetThingFromSharedContainer);
# raw mushrooms, eggs, nuts, seasonings and travel rations don't count, so the harvest box fed
# nobody. Keep RESIDENT_DISHES dishes in it: weed stews at the bonfire, 5 grass tufts each.
RESIDENT_DISHES = 6
DISHES = ("stew", "soup", "boiled egg", "roasted", "grilled", "on the bone", "bread", "jerky", "jerkies", "fried",
          "salad", "cookie", "anpan", "taiyaki", "orange", "banana", "apple", "grape", "guava", "pineapple")  # run 18: bought dishes and fruit
FODDER_BOX = BOX_STR(home.FODDER_BOX)
BONFIRE_STAND = home.BONFIRE_STAND
_BF = (str(home.BONFIRE[0] - BONFIRE_STAND[0]), str(home.BONFIRE[1] - BONFIRE_STAND[1]))


def resident_food():
    inside = split_listing(run("box.py", DISH_BOX))
    have = sum(int(m.group(1)) if (m := re.match(r"(\d+) ", x)) else 1
               for x in inside if has_word(x, DISHES) and "rotten" not in x.lower())
    if have >= RESIDENT_DISHES:
        return ""
    # run 17: a corpse cooks into meat on the bone at the bonfire (a dish); in winter there is no
    # grass at home, so the corpses brought from fights feed the residents first
    corpses = [i["name"] for i in call("inv")["data"]["items"] if i["name"].startswith(("a corpse", "corpses"))
               or re.match(r"\d+ corpses", i["name"])]
    if corpses:
        walk(*BONFIRE_STAND)
        run("hotbar.py", "--deselect")
        out = run("craft.py", *_BF, "Meat on the bone", "1", "--use", corpses[0], timeout=600)
        run("close.py")
        made = [i["name"] for i in call("inv")["data"]["items"] if "on the bone" in i["name"]]
        if made:
            run("box.py", DISH_BOX, *made)
            return f"{have} dishes for the residents: cooked {', '.join(made)} from a corpse"
    grass = [x for x in split_listing(run("box.py", FODDER_BOX))
             if re.search(r"tufts of (forest )?grass$", x)
             and int(re.match(r"(\d+) ", x).group(1)) >= 5]
    if not grass:
        return f"{have} dishes for the residents and no grass to cook more (the fodder box)"
    stack = max(grass, key=lambda x: int(x.split()[0]))
    k = min(5, int(stack.split()[0]) // 5, RESIDENT_DISHES - have + 2)
    walk(*BONFIRE_STAND)
    run("hotbar.py", "--deselect")
    out = run("craft.py", *_BF, "Weed stew", str(k), "--use", stack, timeout=600)
    run("close.py")
    made = [i["name"] for i in call("inv")["data"]["items"] if "weed stew" in i["name"]]
    if made:
        run("box.py", DISH_BOX, *made)
    return f"{have} dishes for the residents: cooked {k} weed stews ({last(out)[-60:]})"


def counts(out):
    m = re.search(r"total: (.*); SP", out)
    return m.group(1) if m else last(out)


def farm_round():
    notes = []
    # run 11: with a full pack the reaped seeds and the imo couldn't be picked up, the garbage was,
    # and five cells were left empty; dump the junk first, and stop if the pack is still near full
    run("trash.py", "dump")
    loose = [i for i in call("inv")["data"]["items"] if not i.get("equipped")]
    if len(loose) >= 37:  # run 16: the kit is ~32 stacks now (bow, arrows, web rod, bags); 34 refused 4 rounds
        # run 15: the kit alone is ~27 stacks, so a few strays (garbage picked up, a gene, a chess
        # board) refused three rounds in a row and September's bill waited: put them away first
        run("packcheck.py", "--move", timeout=900)
        run("close.py")
        loose = [i for i in call("inv")["data"]["items"] if not i.get("equipped")]
    if len(loose) >= 37:  # run 16: the kit is ~32 stacks now (bow, arrows, web rod, bags); 34 refused 4 rounds
        stop(f"the pack holds {len(loose)} loose stacks; stash or ship before the farm round")
    close_backpack()
    run("box.py", TOOL_BOX, "--take", SICKLE)  # run 32: the bronze war sickle since the iron one was lost
    # 2. mushrooms (they don't wither: with ~20 seeds banked, --mushrooms-every N tends them every Nth day)
    if MUSH_EVERY and int(state()["pc"]["date"].split()[0].split("-")[2]) % MUSH_EVERY == 0:
        r = run("reap.py", "reap", *[f"{x},{z}" for x, z in MUSH_REAP], timeout=900)
        c = run("reap.py", "cut", *[f"{x},{z}" for x, z in MUSH_CUT], timeout=900)
        notes.append(f"mushrooms: reaped {counts(r)}; cut {counts(c)}; planted {plant('mushroom', MUSH_REAP + MUSH_CUT)}")
        # run 11: the bed grows red mushrooms too (id 700: poison, twice); they go to the pantry
        # as fishing bait, so eat_one never meets one in the Cooler Box
        if "red mushroom" in run("bag.py", "Cooler Box"):
            run("bag.py", "Cooler Box", "--take", "red mushroom")
            run("close.py")
            run("box.py", PANTRY, "red mushroom")
    # 3. ripe crops. One cells() call reads every crop cell and the pasture (the review of
    # 2026-10-23: a state + cell pair per cell was 46 calls a round); reaping one kind does not
    # change another kind's ripeness
    info = read_cells([c for cs in CROPS.values() for c in cs] + PASTURE)
    for kind, cells in CROPS.items():
        ripe = [(x, z) for x, z in cells if (info.get((x, z)) or {}).get("ripe") is True]
        if not ripe:
            continue
        k = math.ceil(REAP_SHARE * len(ripe)) if len(ripe) > 1 else 1
        reap, harvest = ripe[:k], ripe[k:]
        r = run("reap.py", "reap", *[f"{x},{z}" for x, z in reap], timeout=900)
        # Two passes of the same cut act on the harvested cells (run 10's design): the first cut
        # harvests the ripe crop (the food), which leaves the plant's stub standing; the second
        # cut takes the stub, which gives a seed back ~12% of the time (TryPopSeed) and empties the
        # cell for the replant. Neither pass is a duplicate.
        h = run("reap.py", "cut", *[f"{x},{z}" for x, z in harvest], timeout=900) if harvest else ""
        s = run("reap.py", "cut", *[f"{x},{z}" for x, z in harvest], timeout=900) if harvest else ""
        food = "to the harvest box"  # run 13: the Cooler Box is trip food only (store_food)
        notes.append(f"{kind}: {len(ripe)} ripe, reaped {counts(r)}"
                     + (f"; harvested {len(harvest)} cells: {counts(h)} ({food}); stubs {counts(s)}" if harvest else "")
                     + f"; replanted {plant(kind, cells)}")
    # 4. pasture
    grown = [(x, z) for x, z in PASTURE if ((info.get((x, z)) or {}).get("growStage") or 0) >= 3]
    if grown:
        k = int(PASTURE_REAP * len(grown))
        r = run("reap.py", "reap", *[f"{x},{z}" for x, z in grown[:k]], timeout=900) if k else ""
        c = run("reap.py", "cut", *[f"{x},{z}" for x, z in grown[k:]], timeout=900)
        moved = feed_pasture()
        notes.append(f"pasture: {len(grown)} ready; reaped {counts(r) if k else 'none'}; cut {counts(c)}; "
                     f"fed: {moved}; replanted {plant('pasture', PASTURE)}")
    bare = plant_bare()
    if bare:
        notes.append(f"bare field cells planted with mushrooms: {bare}")
    run("box.py", TOOL_BOX, SICKLE)
    bank_seeds()
    stored = store_food()
    if stored:
        notes.append("food stored: " + stored)
    extra = surplus()
    if extra:
        notes.append("surplus: " + extra)
    fed = resident_food()
    if fed:
        notes.append("residents: " + fed)
    # 5. water. Run 17 (the user: "frozen water cannot fill the watering can"): in snow cover
    # every unroofed water tile is ice (Cell.IsIceTile), so months 12-2 have no Draw Water (and no
    # fishing); the mushrooms grow at 5 a day instead of 10 until spring
    month = int(state()["pc"]["date"].split()[0].split("-")[1])
    if month in (12, 1, 2):
        notes.append("water: skipped (the lake is ice in winter)")
    else:
        w = run("water.py", "--extra", *EXTRA_WATER, timeout=1200)
        notes.append("water: " + " / ".join(l for l in w.splitlines() if "water" in l.lower())[-160:])
    run("hotbar.py", "--deselect")
    run("close.py")
    return notes


def meal():
    """Eat from the Cooler Box until under eat_at (45). One tomato is 11: run 10 saw hunger creep
    to 70; run 20: a bread or a jerky is ~30, and eating again at 32-40 left me Bloated at 2-5
    twice, so stop once under 45. Run 18 (errors.csv row 37): the loop went on to shear and sleep
    when nothing could be eaten and starved; a failed meal at STOP_HUNGER or worse now stops the
    loop (exit 3) for food to be cooked or bought."""
    for _ in range(4):
        h = state()["pc"]["hunger"]
        if h < THRESHOLDS["eat_at"]:
            return
        ate = eat_one()
        print("  ate: " + str(ate))
        if not ate:
            if h >= STOP_HUNGER:
                stop(f"no meal at hunger {h}: cook or buy food first (run 18: never go on hungry)")
            return


def gate(s=None):
    """Why the loop must stop now, or None. Weak wanderers (a yeek, a rat) are a normal part of
    home days: they are fought and the check made again; never cats, even hostile ones: a kill
    costs Karma -1 (Chara.Die; run 12 lost one to a kitten that clawed me at home), and a kitten
    does no real harm, so it is left be (and stops the loop, as before)."""
    s = close_report(s)
    why = ready(s, hp=THRESHOLDS["loop_hp"], hunger=None)
    if why and why.startswith("hostile in view"):
        foes = [c for c in s.get("nearby") or [] if c.get("hostile")
                and not re.search(r"\b(cat|kitten|kitty)\b", c.get("name", ""), re.I)]
        if foes and all(c.get("lv", 99) <= s["pc"]["lv"] for c in foes):
            for c in foes:
                name = re.sub(r"^(an?|the) ", "", c["name"])
                print(f"  fought {name} Lv{c['lv']}: {last(run('fight.py', name, '60'))[-80:]}")
            why = ready(hp=THRESHOLDS["loop_hp"], hunger=None)
    return why


def main():
    global MUSH_EVERY
    a = sys.argv[1:]
    once = "--once" in a  # one farm round and a meal, then return: no sleeping or waiting (run 12)
    a = [x for x in a if x != "--once"]
    if "--mushrooms-every" in a:
        k = a.index("--mushrooms-every")
        MUSH_EVERY = int(a[k + 1])
        a = a[:k] + a[k + 2:]
    days = int(a[0]) if a else 3
    until = a[1] if len(a) > 1 else "486-04-02"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    register("springday")  # run 10: a runaway loop couldn't be stopped; stopjob.py asks it now
    done_day = None
    for k in range(days * 3):  # a few passes a day: farm, eat, sleep/wait
        if stop_requested("springday"):
            print("stop: asked (stopjob.py)")
            return
        wait_idle(timeout=10000)  # a task left running by the last step (ready() refuses while busy)
        why = gate()
        if why:
            stop(why)
        # a meal before the work: a night's sleep adds 20-30 hunger, and the Hungry gate below
        # would otherwise stop a day that only needed breakfast
        meal()
        why = ready(hp=THRESHOLDS["loop_hp"], hunger=THRESHOLDS["hungry"])
        if why:
            stop(why)
        p = state()["pc"]
        day, hour = p["date"].split()[0], int(p["date"].split()[1][:2])
        if day >= until:
            print(f"stop: reached {until}")
            return
        tax = pay_tax()
        if tax:
            print("  " + tax)
        if once and hour < 6:
            print("stop: before the 06:00 growth tick (--once)")
            return
        if hour >= 6 and done_day != day:
            print(f"== {p['date']}  HP {p['hp']}/{p['maxHp']} SP {p['sp']} hunger {p['hunger']} gold {p['gold']}")
            mark("farm", "start")
            notes = []
            try:
                notes = farm_round()
            finally:
                mark("farm", "end", note=f"{len(notes)} notes")
            for n in notes:
                print("  " + n)
            done_day = day
        meal()
        if once:
            print("stop: one round done (--once)")
            return
        sh = run("shear.py", "20")
        if "sheared 0" not in sh:
            print("  " + " / ".join(sh.splitlines()[-3:]))
        if stop_requested("springday"):
            print("stop: asked (stopjob.py)")
            return
        p = state()["pc"]
        if p["sp"] * 5 < p["maxSp"] or "Sleep" in ",".join(p.get("conditions") or []) + (p.get("staminaText") or "") or int(p["date"].split()[1][:2]) >= 21:
            out = run("sleep.py", "--home-ok", timeout=900)  # the loop means to stay the night
            print("  sleep: " + last(out))
            if "SP" in last(out):
                continue
        # run 17: no waiting (the user, runs 05, 11, 17): wait.py refuses without their yes, so a day
        # with the farm done, a meal eaten and no sleep due ends the loop instead
        stop("nothing left today but waiting (no-waiting rule): train, travel or work instead")


if __name__ == "__main__":
    main()
