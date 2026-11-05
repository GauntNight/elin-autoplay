"""The money-and-food circle of a Start Run, once there is armor and an ally (Start Runs 5-6, by hand each time, and each dropped stitch cost a death): Mysilia's inn and board, the camp's
board, home's dummy. Every leg passes two or three game days, so the boards refill as I go. Takes each instance job, buys food with what it earns, spends the stamina at home.

usage: python -I tools/startloop.py MINUTES [--cycles N]   N dummy cycles on each home visit (default 3)
Stops (exit 3): a refused ambush, no food and no money with the road too far, a death (crawled up: read the log), the time.
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import data, last, pc, run, setup, state, stop, walk_beside  # noqa: E402
from earlyday import battle_ready, clear_hostiles, clear_windows, eat_named, meals, named, tidy  # noqa: E402
import roam  # noqa: E402
from board import INSTANCE  # noqa: E402

INN = (85, 68)


def zone():
    return str((state().get("zone") or {}).get("full"))


def mount():
    """Riding, once learned, on every leg: 31 exp in 26 seconds at Riding 1 (Start Run 5)."""
    s = state()
    if s["pc"].get("riding") or "riding" not in call("skills")["data"]["skills"]:
        return
    for a in s.get("party") or []:
        if a.get("here") and a.get("dist", 9) <= 3 and a.get("hp", 0) * 10 >= a.get("maxHp", 1) * 5:
            call("ride", uid=a["uid"])
            return


def walk_to(place):
    """One leg, its ambushes handled by roam's own routine. True on arrival."""
    mount()
    run("leave.py", "--riding-ok", timeout=60)
    for _ in range(12):
        clear_windows()
        roam.rest()
        roam.eat(place)
        out = run("wgo.py", place, "--near", 0, "--weak-ok", "--enter", "--danger-ok", 5, timeout=120)
        clear_windows()
        if roam.surrender():
            roam.field()
            continue
        if "entered" in out:
            return True
        if "field" in zone() or "local map" in out or "hostile close" in out:
            roam.field()
            continue
        print(f"  walk: {last(out)[:90]}", flush=True)
        return False
    return False


def jobs():
    """Every instance job on this town's board that the rules allow."""
    for _ in range(3):
        out = run("board.py", timeout=40)
        names = [n for n in INSTANCE if re.search(r"\d+: " + n, str(out))]
        run("close.py", timeout=10)
        if not names:
            return
        if pc().get("riding"):
            call("ride", off=True)  # a mount slows me in a fight (speed 78 against 100) and the ally can't fight under me
        out = run("board.py", "--take", names[0], timeout=40)
        if "took" not in out:
            print(f"  job: {last(out)[:90]}", flush=True)
            return
        tidy()
        got = run("arena.py", timeout=240)
        print(f"  {names[0]}: {last(got)[:70]}", flush=True)
        clear_windows()
        if got.rc == 3:
            stop(f"arena: {last(got)[:120]}")


def shop_food():
    if pc().get("gold", 0) < 40:
        return
    call("walkto", x=INN[0], z=INN[1])
    time.sleep(0.8)
    out = run("buyfood.py", "--keep", 20, timeout=120)
    print(f"  food: {last(out)[:90]}", flush=True)
    for w, _ in meals():
        while pc()["hunger"] >= 35 and named(w):
            if not eat_named(w, 0):
                break


def main():
    setup()
    nums = [a for a in sys.argv[1:] if a.isdigit()]
    minutes = float(nums[0]) if nums else 10
    cycles = sys.argv[sys.argv.index("--cycles") + 1] if "--cycles" in sys.argv else "3"
    t0 = time.time()
    route = ["Mysilia", "Tinker", "Meadow"]
    here = zone()
    k = 1 if "mysilia" in here else 2 if "tinker" in here.lower() else 0
    while time.time() - t0 < minutes * 60:
        battle_ready()
        d = pc()["date"].split()[0]
        if "-08-2" in d or "-08-3" in d:  # FACTION.OnAdvanceMonth: Karma -50 at 4 unpaid bills, on the first of the fourth month: then town guards kill on sight (Start Run 6)
            print(f"  tax: {d}: the fourth unpaid bill comes on the first of next month: pay one, or keep out of Mysilia after it", flush=True)
        place = route[k % 3]
        if not walk_to(place):
            stop(f"couldn't reach {place}")
        p = pc()
        print(f"{place}: Lv{p['lv']} {p['exp']}/{p['expNext']}  HP {p['hp']}/{p['maxHp']}  hunger {p['hunger']}  {p.get('gold')} orens  {(time.time() - t0) / 60:.1f} min", flush=True)
        if place == "Meadow":
            out = run("earlyday.py", cycles, "--rotate", timeout=300)
            print(f"  home: {last(out)[:90]}", flush=True)
            if out.rc == 3 and "meals left" not in out:
                stop("home: " + last(out)[:120])
        else:
            jobs()
            if place == "Mysilia":
                shop_food()
        k += 1
    p = pc()
    print(f"done: Lv{p['lv']} {p['exp']}/{p['expNext']}  {p.get('gold')} orens  {(time.time() - t0) / 60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
