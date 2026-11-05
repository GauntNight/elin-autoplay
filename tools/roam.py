"""Walk for character exp (run 43): the game pays 1 exp per 3 miles walked on arrival at a local map ("You have walked around 19 miles and have gained
experience": +6), at no stamina and a third of a hunger a game hour, about 18 exp a real minute at speed x5. It beat the dummy once skills passed about 10.
Shuttles between two places, entering each to bank the miles. Ambushes: its own field() below, a new character's rules, not wgo.py --ambush's.

usage: python -I tools/roam.py PLACE_A PLACE_B [--legs N] [--danger-ok N]   from the world map or inside either place
At home with a bed (runs/earlybase.json) and Sleepy or worse: one earlyday.py cycle (pray, crops, dummy, sleep).
Stops (exit 3): an ambush the rules refuse, no food left at hunger 60+, HP under the loop floor. Exit 0 when the legs are done.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import THRESHOLDS, last, pc, run, setup, state, stop, top  # noqa: E402
from earlyday import clear_hostiles, clear_windows, heal, meals, named, eat_named  # noqa: E402

STOP_HUNGER = 60
SPELL = "Teleport"  # a character without it: ability.py refuses and the walk out still runs
TELEPORT_MP = 12
KEEP = ("gold bar", "platinum", "ticket", "orens", "scimitar", "boomerang")  # a bandit's demand for these is refused


def eat():
    """Down under the eating line; a loop never walks hungry without food (run 18). Not with a hostile in view: a hit interrupts the meal (run 44)."""
    for _ in range(6):
        if pc()["hunger"] < THRESHOLDS["eat_at"] or any(c.get("hostile") for c in state().get("nearby") or []):
            break
        words = [w for w, _ in meals() if named(w)]
        if not words:
            break
        eat_named(words[0], 0)
    h = pc()["hunger"]
    if h >= STOP_HUNGER and not any(named(w) for w, _ in meals()):
        stop(f"hunger {h}: no food left in the pack")


def surrender():
    """A road bandit's demand: run 44 gave up 3 branches to a goblin wizard Lv8 and he walked off. Run 43's gang is why the walk out comes straight after."""
    hit = [b for b in call("buttons")["data"]["buttons"] if "surrender" in (b.get("text") or "").lower()]
    if hit and any(w in hit[0]["text"].lower() for w in KEEP):  # run 44: this gave a bandit all 8 gold bars: the demand is read now, and valuables mean a fight or a teleport
        no = [b for b in call("buttons")["data"]["buttons"] if (b.get("text") or "").startswith("Try me")]
        print(f"  refused the demand: {hit[0]['text'][:50]}", flush=True)
        if no:
            call("click", i=no[0]["i"])
            time.sleep(0.4)
            run("talk.py", 4, timeout=20)
        return True
    if hit:
        print(f"  surrendered: {hit[0]['text'][:50]}", flush=True)
        call("click", i=hit[0]["i"])
        time.sleep(0.4)
        run("talk.py", 4, timeout=20)
    return bool(hit)


def escape():
    """Teleport if the MP is there, then off the map. True when back on the world map."""
    if pc()["mp"] >= TELEPORT_MP:
        run("ability.py", SPELL, timeout=15)
        time.sleep(0.2)
    run("leave.py", "--force", "--riding-ok", timeout=60)
    return "ntyris" in str((state().get("zone") or {}).get("full"))


def field():
    """An ambush map, from runs 43-44: a boomerang at the nearest foe (it killed a Lv6 at Lv2 and pays Throwing), Teleport under 45% HP, with 3+ beside me or a foe far above me.
    A fight that can't throw falls back on the sword. Ends back on the world map, or on a death: clear_windows crawls up and stops."""
    for _ in range(50):
        clear_windows()
        s = state()
        p = s["pc"]
        if p["hp"] <= 0:
            clear_windows()
        if "ntyris" in str((s.get("zone") or {}).get("full")):
            return
        foes = sorted((c for c in s.get("nearby") or [] if c.get("hostile")), key=lambda c: c.get("dist", 99))
        if not foes:
            run("loot.py", 8, timeout=60)
            if run("leave.py", "--force", "--riding-ok", timeout=60).rc == 0:
                return
            continue
        close = [c for c in foes if c.get("dist", 9) <= 1]
        if p["hp"] * 100 < 45 * p["maxHp"] or len(close) >= 3 or max(c.get("lv") or 0 for c in foes) > p["lv"] + 6:
            if escape():
                return
            continue
        out = run("throw.py", foes[0]["name"].split()[-1], "boomerang", 2, 25, timeout=30)
        if "no " in str(out)[:12] or out.rc == 1:
            run("fight.py", foes[0]["name"].split()[-1], 25, timeout=60)
    stop("50 rounds on one ambush map: look.py")


def rest():
    """Rest on the world map heals in seconds, for free (run 44: 3 -> 28 HP)."""
    p = pc()
    if p["hp"] * 100 >= 70 * p["maxHp"]:
        return
    run("ability.py", "Rest", timeout=15)
    for _ in range(40):
        time.sleep(0.25)
        if top() or state().get("drama"):
            clear_windows()
        q = pc()
        if q["hp"] * 100 >= 90 * q["maxHp"] or "Meditate" not in str(q.get("ai")):
            if _ > 4:
                break


def main():
    setup()
    a = sys.argv[1:]
    legs = int(a[a.index("--legs") + 1]) if "--legs" in a else 8
    danger = ["--danger-ok", a[a.index("--danger-ok") + 1]] if "--danger-ok" in a else []
    places = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] not in ("--legs", "--danger-ok"))]
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
            if "refused" not in out and "stop" not in out:
                break
            if "ntyris" in str((state().get("zone") or {}).get("full")):
                break
            clear_hostiles()  # run 43: a floating eye at home refused every leave and the legs ran empty
        else:
            stop("leave: " + last(out)[:160])
        run("ability.py", "Pray", timeout=20)  # a free 80-100 Faith exp a day, and a leg is a day or two
        clear_windows()
        for _ in range(12):  # the walk with what stops it handled: an ambush, a bandit, wounds
            rest()
            out = run("wgo.py", target, "--near", 0, "--weak-ok", "--enter", *danger, timeout=120)
            clear_windows()
            if surrender():
                field()
                continue
            if "entered" in out:
                break
            if "local map" in out or "hostile close" in out or "field" in str((state().get("zone") or {}).get("full")):
                field()
                continue
            if out.rc == 3 and "Hungry" in out:
                eat()
                continue
            stop("wgo: " + last(out)[:160])
        q = pc()
        print(f"{k + 1}: {target}: Lv{q['lv']} {q['exp']}/{q['expNext']}  HP {q['hp']}/{q['maxHp']}  hunger {q['hunger']}  {q['date']}  {time.time() - t0:.0f}s  {last(out)[:60]}", flush=True)
    q = pc()
    gained = (q["lv"], q["exp"])
    print(f"done: {legs} legs in {time.time() - t0:.0f}s: from Lv{start['lv']} {start['exp']} to Lv{gained[0]} {gained[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
