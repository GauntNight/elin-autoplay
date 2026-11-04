"""Cook the residents' dishes from the farm's fresh food (run 18, backlog P15): residents eat only
prepared food from shared boxes, about 8 dishes a day while I'm home (fact #671).

- imo -> "Stone roasted sweet imo" at the Kitchen's bonfire (1 imo + 2 pebbles: the stone-wall
  Mining practice leaves pebbles; they live in the stone box)
- mushrooms, tomatoes and other vegetables -> "Mini salad" at the Kitchen's cutting board (1
  vegetable, 2 SP)
- every dish goes into the Kitchen's shared Dishes box

Rotten food is never used (a resident who vomits while Starving dies: fact #674).
usage: python -I tools/cookdishes.py [MAX_DISHES=10] [min_sp=20]
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, data, ready, run, setup, stop, walk  # noqa: E402
from item import harmful_foods  # noqa: E402
from packcheck import has_word, split_listing  # noqa: E402
import home  # noqa: E402

CUTTING_BOARD = (68, 58)
BOARD_STAND = (67, 58)
VEG = re.compile(r"(mushroom|tomato|cabbage|carrot|radish|eggplant|corn|leccho|cabocchi|bamboo shoot|gourd|red pepper)", re.I)
DISH = re.compile(r"salad|roasted sweet imo|on the bone|skewer|boiled egg|stew", re.I)
COOKED = re.compile(r"mini .*salad|roasted sweet imo", re.I)  # the two recipes this tool makes


def stacks(where):
    return split_listing(run("box.py", where))  # box.py closes its window itself


def count(name):
    m = re.match(r"(\d+) ", name)
    return int(m.group(1)) if m else 1


def dishes_in_pack():
    return [i["name"] for i in call("inv")["data"]["items"]
            if DISH.search(i["name"]) and "rotten" not in i["name"]]


def cooler_cooked():
    """{stack name: count} of this tool's dishes in the Cooler Box: with the pack full, a crafted
    dish lands there (run 20: 8 salads cooked, none reached the fridge)."""
    out = run("bag.py", "Cooler Box")
    run("close.py")
    return {re.sub(r"^\d+ ", "", x): count(x) for x in split_listing(out) if COOKED.search(x)}


def main(argv):
    setup()
    why = ready(hp=None, hunger=None)  # a window, busy, a bad condition, a hostile in view (at home)
    if why:
        stop(why)
    cooler_before = cooler_cooked()
    nums = [int(a) for a in argv if a.isdigit()]
    cap = nums[0] if nums else 10
    min_sp = nums[1] if len(nums) > 1 else 20
    made = 0
    # run 20: fresh crops now wait in the fridge (springday.store_food); craft.py reaches both
    food = [s for s in stacks(f"{home.HARVEST_BOX[0]},{home.HARVEST_BOX[1]}") + stacks(f"{home.DISH_BOX[0]},{home.DISH_BOX[1]}")
            + stacks(f"{home.HARVEST_FRIDGE[0]},{home.HARVEST_FRIDGE[1]}")  # run 33: the harvest fridge
            if "rotten" not in s and not DISH.search(s)]
    imos = [s for s in food if re.search(r"\bimos?\b", s) and "seed" not in s]
    # run 19: a salad keeps its mushroom's harm: Kaberg and the snow putit were poisoned by mini red
    # mushroom salads from the shared fridge. Never cook what foods.md lists as harmful.
    harmful = harmful_foods()
    vegs = [s for s in food if VEG.search(s) and "seed" not in s and not any(h in s.lower() for h in harmful)]
    if imos and made < cap:
        pebbles = [s for s in stacks(f"{home.STONE_BOX[0]},{home.STONE_BOX[1]}") if has_word(s, ("pebble",))]  # whole word
        if pebbles:
            walk(*home.BONFIRE_STAND, r=0, timeout=40000)
            run("hotbar.py", "--deselect")
            dx, dz = home.BONFIRE[0] - home.BONFIRE_STAND[0], home.BONFIRE[1] - home.BONFIRE_STAND[1]
            for s in imos:
                k = min(count(s), cap - made, max(0, (data("state")["pc"]["sp"] - min_sp) // 2), count(pebbles[0]) // 2)
                if k <= 0:
                    break
                out = run("craft.py", str(dx), str(dz), "Stone roasted sweet imo", str(k), "--use", s, "--allow-default", timeout=600)
                made += k if "crafted" in out.lower() else 0
            run("close.py")
    if vegs and made < cap:
        walk(*BOARD_STAND, r=0, timeout=40000)
        dx, dz = CUTTING_BOARD[0] - BOARD_STAND[0], CUTTING_BOARD[1] - BOARD_STAND[1]
        for s in vegs:
            k = min(count(s), cap - made, max(0, (data("state")["pc"]["sp"] - min_sp) // 2))
            if k <= 0:
                break
            out = run("craft.py", str(dx), str(dz), "mini salad", str(k), "--use", s, timeout=600)
            made += k if "crafted" in out.lower() else 0
        run("close.py")
    # run 20: only what this run cooks goes to the fridge (it moved my road food, a snail on the bone)
    got = [n for n in dishes_in_pack() if COOKED.search(n)]
    grown = [k for k, v in cooler_cooked().items() if v > cooler_before.get(k, 0)]
    if grown:  # the whole stack goes: a dish of mine already there joins the residents' (rare)
        run("bag.py", "Cooler Box", "--take", *grown)
        got += [n for n in dishes_in_pack() if COOKED.search(n) and n not in got]
    if got:
        run("box.py", f"{home.DISH_BOX[0]},{home.DISH_BOX[1]}", *got)
    inbox = [s for s in stacks(f"{home.DISH_BOX[0]},{home.DISH_BOX[1]}") if "rotten" not in s]
    print(f"cooked {made}; the Dishes box holds {sum(count(s) for s in inbox)}: {', '.join(inbox)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
