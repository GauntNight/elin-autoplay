"""Walk for character exp (run 43): the game pays 1 exp per 3 miles walked on arrival at a local map ("You have walked around 19 miles and have gained
experience": +6), at no stamina and a third of a hunger a game hour, about 18 exp a real minute at speed x5. It beat the dummy once skills passed about 10.
Shuttles between two places, entering each to bank the miles; wgo.py --ambush handles ambushes by its usual rules.

usage: python -I tools/roam.py PLACE_A PLACE_B [--legs N] [--food-keep N]   from the world map or inside either place
At home with a bed (runs/earlybase.json) and Sleepy or worse: one earlyday.py cycle (pray, crops, dummy, sleep).
Stops (exit 3): an ambush the rules refuse, no food left at hunger 60+, HP under the loop floor. Exit 0 when the legs are done.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import THRESHOLDS, last, pc, run, setup, state, stop, top, wait_idle  # noqa: E402
from earlyday import clear_hostiles, clear_windows, heal, meals, named, eat_named  # noqa: E402

STOP_HUNGER = 60


def eat():
    """Down under the eating line; a loop never walks hungry without food (run 18)."""
    while pc()["hunger"] >= THRESHOLDS["eat_at"]:
        words = [w for w, _ in meals() if named(w)]
        if not words:
            break
        eat_named(words[0], 0)
    h = pc()["hunger"]
    if h >= STOP_HUNGER:
        stop(f"hunger {h}: no food left in the pack")


def main():
    setup()
    a = sys.argv[1:]
    legs = int(a[a.index("--legs") + 1]) if "--legs" in a else 8
    places = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] != "--legs")]
    if len(places) != 2:
        stop("usage: roam.py PLACE_A PLACE_B [--legs N]")
    t0 = time.time()
    start = pc()
    for k in range(legs):
        target = places[k % 2]
        clear_windows()
        heal()
        eat()
        p = pc()
        if (p.get("sleepPhase") or 0) >= 1 and "startSite" in str((state().get("zone") or {}).get("full")):
            out = run("earlyday.py", 1, "--throw", "a boomerang", timeout=240)  # the night's sleep, and the bar on the dummy first
            print(f"  home cycle: {last(out)[:70]}", flush=True)
            if out.rc == 3:
                stop("home cycle: " + last(out)[:140])
            eat()
        for _ in range(3):
            out = run("leave.py", "--riding-ok", timeout=120)
            if "refused" not in out or "not on" in out:
                break
            clear_hostiles()  # run 43: a floating eye at home refused every leave and the legs ran empty
        else:
            stop("leave: " + last(out)[:160])
        out = run("wgo.py", target, "--near", 0, "--weak-ok", "--ambush", "--enter", timeout=300)
        clear_windows()
        q = pc()
        print(f"{k + 1}: {target}: Lv{q['lv']} {q['exp']}/{q['expNext']}  HP {q['hp']}/{q['maxHp']}  hunger {q['hunger']}  {q['date']}  {time.time() - t0:.0f}s  {last(out)[:70]}", flush=True)
        if out.rc == 3:
            stop("wgo: " + last(out)[:160])
    q = pc()
    gained = (q["lv"], q["exp"])
    print(f"done: {legs} legs in {time.time() - t0:.0f}s: from Lv{start['lv']} {start['exp']} to Lv{gained[0]} {gained[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
