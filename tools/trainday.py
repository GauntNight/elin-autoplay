"""Days at home spent on a low weapon skill at the training dummy (run 14, G10).

The dummy is LV10, and a hit pays the weapon skill clamp((10 + 10 - skill)/2, 1, 10) + 1 raw exp
(G10's research): a level-1 skill earns ~9x what the Long Sword (18) earns, and a skill level is
10-14 character exp. Measured in run 14: Staff 1.00 -> 1.61 for 29 SP. Every day:
  1. the farm round (springday.py --once) once a day after 06:00, which also pays a tax bill
  2. a meal from the Cooler Box when hunger is 45+ (farmday.eat_one); stop if there's none
  3. lockpick.py at the practice chest (61,46; run 16, the user's tip), then train.py at the dummy
     (stand 59,46) down to MIN_SP
  4. another lockpick round (the chest relocks every 2 game hours), then sleep in the pine bed
     (60,52): never at hunger 50+ (eat first); the morning shipping report is closed
Stops (exit 3) on a hostile in view (one 10+ levels below me is ignored: run 14's silver cat), HP
under 80% (THRESHOLDS["loop_hp"]), Hungry (70+), no food, a window it doesn't know, a farm round
or a training that stopped for a decision, or `python -I tools/stopjob.py trainday`. Never waits:
SP goes to work, then sleep.

usage: python -I tools/trainday.py [DAYS=3] [--min-sp 6] [--throw "Putit In Amber" | --shoot "forest long bow"]
  --shoot needs arrows: Quick Craft "makeshift arrow" makes 40 from a leaf and a branch for 3 SP (run 16)
The weapon is whatever is equipped: equip the low-skill weapon first (and the Rigid Hand Axe
and the buckler again before any trip).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from activity import mark  # noqa: E402
from common import THRESHOLDS, call, last, pc, ready, run, setup, stop, top, walk, wait_idle, wait_until  # noqa: E402
from farmday import close_report, eat_one  # noqa: E402
from job import register, stop_requested  # noqa: E402
from packcheck import has_word, split_listing  # noqa: E402

DUMMY_STAND = (59, 46)
BED = (60, 52)
WEAK_BELOW = 10  # a hostile this many levels under mine is ignored at home (run 14: a Lv1 silver cat)


def last_line(out):
    return last(out)[:140] or "-"


def hour(p):
    return int(p["date"].split()[1].split(":")[0])


HARVEST_BOX = "%d,%d" % __import__("home").HARVEST_BOX
FARM_FOOD = ("tomato", "imo", "truffle")  # whole words (packcheck.has_word); farm mushrooms are the "+N" stacks below
FARM_MUSHROOM = re.compile(r"\bmushrooms? \+\d")


def base_name(x):
    return re.sub(r"^(\d+|an?) ", "", x.strip())


def farm_food(x):
    low = x.lower()
    return ((has_word(low, FARM_FOOD) or FARM_MUSHROOM.search(low))
            and not has_word(low, ("white mushroom", "red mushroom", "rotten", "stale")))


def borrow():
    """The biggest farm-food stack from the shared harvest box into the Cooler Box for one meal
    (run 14: springday sends the day's food there, and the Cooler Box ran dry twice); raw
    white/red mushrooms stay put. Run 17: the residents eat from this box too, and run 16's
    restock kept every stack (52 mushrooms) in the Cooler Box until Kettle starved, so the rest
    goes back right after the meal (give_back). Returns the stack's name without its count."""
    food = [x for x in split_listing(run("box.py", HARVEST_BOX)) if farm_food(x)]
    if not food:
        print("  borrowed: nothing in the harvest box")
        return None

    def qty(x):
        m = re.match(r"(\d+) ", x)
        return int(m.group(1)) if m else 1
    x = max(food, key=qty)
    run("box.py", HARVEST_BOX, "--take", x)  # box.py closes its window itself
    run("bag.py", "Cooler Box", x)
    # this close is bag.py's, not a second one for box.py: bag.py leaves the Cooler Box open on
    # purpose (eat_one reads the food through the open bag), as give_back() below closes it too
    run("close.py")
    print(f"  borrowed: {x}")
    return base_name(x)


def give_back(name):
    """What is left of the borrowed stack back into the harvest box (by its full name now)."""
    if not name:
        return
    listing = run("bag.py", "Cooler Box")
    run("close.py")
    left = [x for x in split_listing(listing) if base_name(x) == name]
    if left:
        run("bag.py", "Cooler Box", "--take", left[0])
        run("close.py")
        print("  gave back: " + last_line(run("box.py", HARVEST_BOX, left[0])))


def sleep():
    # the review of 2026-10-23: this path had no hunger gate (sleep.py has one), so a day whose
    # meals failed still slept hungry, the run-18 pattern; a sleep adds 20-30 hunger
    h = pc()["hunger"]
    if h >= THRESHOLDS["sleep_hunger"]:
        return f"not sleeping: hunger {h} (eat first)"
    walk(*BED, r=0, weak_ok=True)
    acts = call("acts", dx=0, dz=0, mode="all")["data"]["acts"]
    s = [a for a in acts if a["text"].startswith("Sleep")]
    if not s:
        return "no Sleep act on the bed"
    call("do", i=s[0]["i"])
    if top() != "LayerSleep":
        wait_until("layer", timeout=6000)  # the sleep layer comes up a moment after the act (day 1 returned early)
    for _ in range(40):
        t = top()
        if t != "LayerSleep":
            break
        wait_until("layer", timeout=15000)
    if top() in ("LayerShippingResult",) or call("state")["data"].get("drama"):
        run("talk.py")
        run("close.py")
    log = call("state")["data"].get("log") or []
    return " / ".join(ln for ln in log[-5:] if "slept" in ln or "not sleepy" in ln or "wake" in ln)


def day_gate(hunger=THRESHOLDS["hungry"]):
    """Why the day must not start, or None: common.ready at the loop thresholds (hunger=None
    before breakfast), with hostiles WEAK_BELOW levels under mine taken out of the state first."""
    s = close_report()
    me = s["pc"]["lv"]
    s = dict(s)
    s["nearby"] = [c for c in s.get("nearby") or [] if not (c.get("hostile") and (c.get("lv") or 0) <= me - WEAK_BELOW)]
    return ready(s, hp=THRESHOLDS["loop_hp"], hunger=hunger)


def eat():
    ate = eat_one()
    if not ate:
        name = borrow()
        ate = eat_one()
        give_back(name)
    if not ate:
        stop("hungry and no meal in the Cooler Box or the harvest box: cook or buy food first")
    print("  ate: " + ate)


def main():
    setup()
    register("trainday")
    nums = [int(a) for a in sys.argv[1:] if a.isdigit()]
    days = nums[0] if nums else 3
    min_sp = int(sys.argv[sys.argv.index("--min-sp") + 1]) if "--min-sp" in sys.argv else 6
    farmed = None
    mark("train", "start", note=f"{days} days")
    try:
        for d in range(days):
            if stop_requested("trainday"):
                stop("stop file: trainday")
            p = pc()
            print(f"== day {d + 1}: {p['date']}  Lv{p['lv']} {p['exp']}/{p['expNext']}  SP {p['sp']}  hunger {p['hunger']}")
            wait_idle(timeout=10000)
            why = day_gate(hunger=None)  # a hostile, HP, a window, a bad condition: before any walk
            if why:
                stop(why)
            # breakfast before the hunger gate: a night's sleep adds 20-30 hunger, and the Hungry
            # gate would otherwise stop a day that only needed a meal
            if pc()["hunger"] >= THRESHOLDS["eat_at"]:
                eat()
            why = day_gate()
            if why:
                stop(why)
            p = pc()
            day = p["date"].split()[0]
            if hour(p) >= 6 and farmed != day:
                out = run("springday.py", "1", "999-12-30", "--once", timeout=900)  # run 17: a fixed 486 date stopped every farm round in 487
                farmed = day
                print("  farm: " + " | ".join(ln.strip()[:90] for ln in out.splitlines() if ln.strip().startswith(("mushrooms", "tax", "ate", "stop")))[:300])
                if out.rc == 3:  # the farm round stopped for a decision (a threat, hunger, a full pack)
                    stop("the farm round stopped: " + last_line(out))
                run("packcheck.py", "--move", timeout=900)
            if pc()["hunger"] >= THRESHOLDS["eat_at"]:
                eat()
            # run 16 (the user's tip): the practice chest by the dummy; a lockpick try costs no SP and it
            # relocks every 2 game hours, so a round before the dummy and another before bed
            print("  lockpick: " + last_line(run("lockpick.py", "40", str(min_sp), timeout=600)))
            if pc()["sp"] > min_sp + 2:
                # run 14: the stand cell was taken four days running ("no training dummy next to me"):
                # try the other cells around the dummy (60,46) until one is beside it
                for stand in (DUMMY_STAND, (60, 47), (59, 47), (61, 47), (61, 45)):  # 61,46: the practice chest (run 16)
                    walk(*stand, r=0, weak_ok=True)  # the hostile Lv1 silver cat stopped every walk
                    if call("find", name="training dummy", r=1, n=1)["data"]["hits"]:
                        break
                extra = ["--throw", sys.argv[sys.argv.index("--throw") + 1]] if "--throw" in sys.argv else []
                if "--shoot" in sys.argv:  # run 16: bow practice (Bow + Marksman, both new): +28 exp a bar of SP
                    extra = ["--shoot", sys.argv[sys.argv.index("--shoot") + 1]]
                    # one SP bar shot ~170 arrows; Quick Craft makes 40 from a leaf and a branch (3 SP)
                    have = sum(int(m.group(1)) for b in call("buttons", all=True)["data"]["buttons"]
                               if "ButtonGrid inventory" in b["name"]
                               for m in [re.match(r"(\d+) [a-z ]*makeshift arrows", b.get("card") or "")] if m)
                    n = (200 - have) // 40 + 1
                    # run 16: four batches at SP 19 drove SP to -2 ("You suffer a minor injury"): craft only
                    # what SP covers with the floor and a bar's worth of shooting left (craft.py checks
                    # the window's Stamina Cost x count against SP itself since the 2026-10-23 review)
                    n = min(n, max(0, (pc()["sp"] - min_sp - 20) // 3))
                    # run 32: a gun shoots bullets, not arrows: no arrow crafting for it
                    if have < 160 and n > 0 and re.search(r"\bbow\b", extra[1].lower()):
                        out = run("craft.py", "quick", "makeshift arrow", str(n), "--use", "grass,oak,birch,cedar,palulu,rosewood,leaves", timeout=600)
                        print("  arrows: " + last_line(out))
                        run("close.py")
                out = run("train.py", str(min_sp), "12", *extra, timeout=900)
                print("  " + last_line(out)[:160])
                if out.rc == 3:  # train.py stopped for a decision: a hostile, HP or hunger, a window
                    stop("training stopped: " + last_line(out))
                if extra and extra[0] == "--shoot" and pc()["sp"] > min_sp + 2:
                    # run 16: out of arrows with too little SP to craft more, and not sleepy: five "days"
                    # passed with nothing done. Spend the rest of the bar in melee at the dummy instead
                    from common import put_away
                    put_away()
                    out = run("train.py", str(min_sp), "12", timeout=900)
                    print("  melee: " + last_line(out))
                    if out.rc == 3:
                        stop("training stopped: " + last_line(out))
            if top():
                run("talk.py")
                run("close.py")
                if top():
                    stop(f"a window I don't know: {top()}")
            print("  lockpick: " + last_line(run("lockpick.py", "40", "0", timeout=600)))
            if pc()["hunger"] >= THRESHOLDS["eat_at"]:
                eat()  # never to bed hungry (run 18); sleep() refuses at sleep_hunger anyway
            slept = sleep()
            print("  sleep: " + slept)
            if "not sleeping" in slept:
                stop(slept)
            if "not sleepy" in slept and pc()["sp"] > min_sp + 2:
                stop(f"nothing left to do today: SP {pc()['sp']} above the floor and not sleepy (no arrows?)")
        p = pc()
        print(f"done: {days} days; Lv{p['lv']} {p['exp']}/{p['expNext']}  {p['date']}")
    finally:
        mark("train", "end")


if __name__ == "__main__":
    main()
