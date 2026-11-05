"""A new character's exp loop at home, from the first minutes (run 41, the Lv1 trials). Character exp is skill level-ups only, a
level-1 skill levels fast, and at the game's speed x5 a full bar of SP on the dummy takes 5 real seconds and a sleep 4, so real time
stops binding and food takes over: a sleep costs 20 hunger. Weeds close the loop: they pay Gathering and give grass, 5 grass and 3 SP
make a weed stew (11 food, the bonfire burns a log from the pack).

A cycle from waking: ripe crops (+100 skill exp a SP, three times the dummy, and food), a meal from the pack if there is one (bread, jerky,
rations: run 41 found 1.15 food an oren at the general store) or else stews, the rest of the SP on the dummy, then sleep.

The eat step was tested by hand on these stews (run 41: 79 -> 68 -> 57), as every loop's must be (run 18 starved in a loop).
Stops (exit 3) on common.ready's reasons: a hostile in view, HP under 80%, a window it can't read, a bad condition; Hungry with no way
to cook; a meal that didn't lower hunger; a sleep that didn't restore SP. It sleeps up to hunger 60 (LOOP_SLEEP), above the general 50: run 41's
first batch deadlocked at SP 3 and hunger 50, too tired to gather and too hungry to sleep, and this loop wakes beside its food. Never at 60+.

usage: python -I tools/earlyday.py [CYCLES=5] [--throw "a boomerang"]
The base is runs/earlybase.json: {"stand": [X, Z], "bed": [X, Z], "fire": [X, Z]}, stand being one cell next to the dummy and the bonfire.
"""
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import THRESHOLDS, call, data, last, pc, ready, run, setup, state, stop, top, wait_idle, walk  # noqa: E402

BASE = Path(__file__).resolve().parent.parent / "runs" / "earlybase.json"
STEW_FOOD, STEW_SP, STEW_GRASS = 11, 3, 5
HUNGER_AFTER_MEAL = 38  # a sleep adds 20: wake under Hungry (70) with room to work
SP_FLOOR = 4  # the bridge's guard cancels work at 3
LOOP_SLEEP = 60  # the loop's own limit: see the docstring
WEED_RADIUS = 60
MEALS = (("watermelon", 11), ("apple", 13), ("jerk", 19), ("orange", 22), ("pile of bread", 31), ("piles of bread", 31), ("ration", 51))  # a word of the name, food: smallest first (run 41: breads have several ids)
CROPS = (("berry", "berry"), ("crim", "crim"))


def count(item_id):
    return sum((i.get("num") or 1) for i in data("inv")["items"] if i.get("id") == item_id and not i.get("equipped"))


def clear_windows():
    """A tip, a dream, a report: read it through. Anything left is the caller's stop."""
    for _ in range(4):
        s = state()
        if not (s.get("drama") or (s.get("layers") or {}).get("top")):
            return
        run("talk.py", "8", timeout=60)
        run("close.py", timeout=30)
        time.sleep(0.2)


def empty_hands():
    call("act", action="EmptyHand")
    time.sleep(0.15)


def clear_hostiles():
    """Kill what wanders in at or below my level (fights pay exp at no SP cost and count for Regular patrol); stop for anything stronger."""
    for _ in range(8):
        s = state()
        foes = sorted((c for c in s.get("nearby") or [] if c.get("hostile")), key=lambda c: c.get("dist", 99))
        if not foes:
            return
        f = foes[0]
        if (f.get("lv") or 0) > s["pc"]["lv"]:
            stop(f"a hostile above my level: {f['name']} Lv{f.get('lv')} at {f.get('dist')}")
        out = run("fight.py", f["name"].split()[-1], THRESHOLDS["walk_hp"], timeout=120)
        print(f"  fought {f['name']} Lv{f.get('lv')}: {last(out)[:70] if out.strip() else ''}", flush=True)
        run("loot.py", "8", "--all", timeout=120)
        clear_windows()
        if out.rc == 3:
            stop("fight: " + last(out)[:120])
    stop("eight fights in a row: look.py")


def heal():
    """Rest heals fast and free (2 -> 10 HP in 10 game minutes on the test character): a loop never stops for what a Rest fixes."""
    for _ in range(3):
        p = pc()
        if p["hp"] * 100 >= THRESHOLDS["loop_hp"] * p["maxHp"]:
            return
        run("ability.py", "Rest", timeout=30)
        for _ in range(40):
            time.sleep(0.25)
            clear_windows()
            q = pc()
            if q["hp"] * 100 >= THRESHOLDS["loop_hp"] * q["maxHp"]:
                break
            if "ConSleep" not in str(q.get("conditions") or "") and "Rest" not in (q.get("ai") or "") and "Meditate" not in (q.get("ai") or "") and _ > 6:
                break


def gate(hunger=None):
    clear_windows()
    wait_idle(timeout=8000)
    clear_hostiles()
    heal()
    why = ready(hp=THRESHOLDS["loop_hp"], hunger=hunger)
    if why:
        stop(why)


def gather_grass(want):
    """Weeds until the pack holds `want` tufts. False when SP or the map's weeds ran out."""
    out = run("gather.py", "weed", "tuft of grass", want, SP_FLOOR + 1, WEED_RADIUS, "--food-run", timeout=240)
    if out.rc == 3:
        stop("gather: " + last(out)[:120])
    clear_windows()
    return count("grass") >= want


def cook(n, dx, dz):
    empty_hands()
    out = run("craft.py", dx, dz, "Weed stew", n, timeout=60)
    clear_windows()
    empty_hands()
    return out


def named(word):
    return [i["name"] for i in data("inv")["items"] if word in i["name"] and not i.get("equipped")]


def eat_named(word, food):
    """One of the first stack whose name holds this word (the name changes with the count). True when hunger fell."""
    names = named(word)
    if not names:
        return False
    before = pc()["hunger"]
    run("item.py", names[0], "Eat", timeout=30)
    wait_idle(timeout=6000)
    clear_windows()
    after = pc()["hunger"]
    if after >= before:
        stop(f"{names[0]} didn't lower hunger ({before})")
    return True


def eat_from_pack():
    """Down to HUNGER_AFTER_MEAL: crops first (they rot), then the smallest meal that fits."""
    for word, food in (("blueberr", 8), ("crim", 7)):
        while pc()["hunger"] - food >= HUNGER_AFTER_MEAL - 4 and named(word):
            eat_named(word, food)
    for word, food in MEALS:
        while pc()["hunger"] - food >= HUNGER_AFTER_MEAL - 6 and named(word):
            eat_named(word, food)


def main():
    setup()
    if not BASE.exists():
        stop("no runs/earlybase.json: see the usage")
    base = json.loads(BASE.read_text(encoding="utf-8"))
    stand, bed, fire = base["stand"], base["bed"], base["fire"]
    nums = [int(a) for a in sys.argv[1:] if a.isdigit()]
    cycles = nums[0] if nums else 5
    # the name after --throw is not a count, and it may hold a digit-free word only
    t0 = time.time()
    prayed = None
    for c in range(cycles):
        gate()
        p = pc()
        day = p["date"].split()[0]
        if day != prayed:  # a free 80-100 Faith exp once a day (research of 2026-11-04)
            run("ability.py", "Pray", timeout=30)
            clear_windows()
            prayed = day
        start_exp, start_lv, tc = p["exp"], p["lv"], time.time()

        # Ripe crops first: the best exp per SP on the map
        for obj, item in CROPS:
            if pc()["sp"] > SP_FLOOR + 4:
                o = run("gather.py", obj, item, count(item) + 6, SP_FLOOR + 3, WEED_RADIUS, "--food-run", timeout=120)
                clear_windows()
                if o.rc == 3:
                    if "hostile" in o:
                        clear_hostiles()
                    else:
                        stop("crops: " + last(o)[:120])

        # Food for tonight: meals from the pack, crops, then stews
        eat_from_pack()
        p = pc()
        hunger = p["hunger"]
        need = max(0, math.ceil((hunger - HUNGER_AFTER_MEAL) / STEW_FOOD))
        stews = count("zassouni")
        if stews < need:
            short = need - stews
            have = count("grass")
            if have < short * STEW_GRASS and p["sp"] > SP_FLOOR + short * STEW_SP:
                gather_grass(short * STEW_GRASS)
            have = count("grass")
            sp = pc()["sp"]
            n = min(short, have // STEW_GRASS, max(0, (sp - SP_FLOOR) // STEW_SP))
            if n:
                walk(*stand, r=0, weak_ok=True)
                o = cook(n, fire[0] - stand[0], fire[1] - stand[1])
                if count("zassouni") == stews:
                    stop("the stew wasn't cooked: " + last(o)[:140])
            stews = count("zassouni")
        for _ in range(min(need, stews)):
            before = pc()["hunger"]
            run("item.py", "weed stew", "Eat", timeout=30)
            wait_idle(timeout=6000)
            clear_windows()
            if pc()["hunger"] >= before:
                stop(f"a stew didn't lower hunger ({before})")

        # The rest of the bar on the dummy
        gate()
        walk(*stand, r=0, weak_ok=True)
        empty_hands()
        if pc()["sp"] > SP_FLOOR + 1:
            extra = ["--throw", sys.argv[sys.argv.index("--throw") + 1]] if "--throw" in sys.argv else []  # run 41: a boomerang comes back
            out = run("train.py", SP_FLOOR, 4, *extra, timeout=300)
            clear_windows()
            if out.rc == 3:
                if "hostile" in out:
                    clear_hostiles()
                else:
                    stop("train: " + last(out)[:140])

        # Sleep: a last meal if training left me over the line
        while pc()["hunger"] >= LOOP_SLEEP - 8 and any(named(w) for w, _ in MEALS):
            word = next(w for w, _ in MEALS if named(w))
            eat_named(word, 0)
        p = pc()
        if p["hunger"] >= LOOP_SLEEP:
            stop(f"hunger {p['hunger']}: no food left to sleep on, SP {p['sp']}")
        wait_idle(timeout=6000)
        out = run("act.py", bed[0] - p["x"], bed[1] - p["z"], "Sleep", timeout=30)
        if out.rc:
            stop("no Sleep: " + out.strip()[:120])
        for _ in range(60):
            time.sleep(0.25)
            if top() or state().get("drama"):
                clear_windows()
            q = pc()
            if q["sp"] > p["sp"] + 5 and "Sleep" not in (q.get("ai") or "") and not any("Sleep" in str(x) for x in (q.get("conds") or [])):
                break
        clear_windows()
        q = pc()
        print(f"{c + 1}: Lv{q['lv']} {start_exp}->{q['exp']}/{q['expNext']} (Lv{start_lv} at start)  SP {q['sp']}/{q.get('maxSp')}  hunger {q['hunger']}  "
              f"stews {count('zassouni')} grass {count('grass')}  {q['date']}  {time.time() - tc:.0f}s", flush=True)
        if q["sp"] <= p["sp"]:
            stop(f"the sleep didn't restore SP ({p['sp']} -> {q['sp']})")
    print(f"done: {cycles} cycles in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
