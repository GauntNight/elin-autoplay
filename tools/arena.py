"""Clear a job's arena instance ("Monster's Den": Monster extermination, Monster hunting, Troubled home) to "You have wiped out the nearby monsters!"
(run 42: hunt.py stops at 70% HP and walks toward the edge, where "Leave Monster's Den?" would forfeit the job). Loop: fight the nearest foe, Rest when
nothing is in view and HP is under 70%, else walk the map's corners and middle. Ends at the wipe, then loots, leaves and picks up the reward.

Survival: a foe more than 3 levels above me, or HP under 25% with foes around, stops (exit 3) for a decision: nothing here flees by itself.
usage: python -I tools/arena.py [--no-leave] [--any] [--wiped]   --wiped: already wiped, only loot, leave and pick the reward
Exit 0 wiped (and left), 1 refused (not in an arena), 3 stopped.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import last, pc, run, setup, state, stop, top  # noqa: E402

FLOOR = 25


def texts():
    return call("texts", all=True)["data"]["texts"]


def wipe_line():
    """The wipe line's position in the visible log, -1 when it isn't there. Run 43: the log still held the last job's line, so a second arena in a row counted as
    wiped at once; and the window is short, so counting lines failed too (the old one scrolled off as the new one came): a line further down than any seen is new."""
    return max((i for i, t in enumerate(texts()) if "wiped out the nearby monsters" in t), default=-1)


def answer_no():
    """A walk that reached the edge asks 'Leave Monster's Den?': never yes before the wipe."""
    b = [x for x in call("buttons")["data"]["buttons"] if (x.get("text") or "").endswith("No.")]
    if b:
        call("click", i=b[0]["i"])
        time.sleep(0.2)
    if top() or state().get("drama"):
        run("talk.py", "4", timeout=30)


def rest():
    run("ability.py", "Rest", timeout=20)
    for _ in range(30):
        time.sleep(0.3)
        answer_no()
        s = state()
        p = s["pc"]
        if p["hp"] * 100 >= 90 * p["maxHp"] or any(c.get("hostile") for c in s.get("nearby") or []):
            return


def main():
    setup()
    s = state()
    z = s.get("zone") or {}
    if "arena" not in (z.get("full") or "") and "--any" not in sys.argv:  # --any: the same loop on a nefia floor, no wipe to wait for
        print(f"refused: not in an arena: {z.get('full')}")
        return 1
    i = 0
    t0 = time.time()
    high = wipe_line()
    while time.time() - t0 < 180 and "--wiped" not in sys.argv:
        answer_no()
        now = wipe_line()
        if now > high:
            break
        high = now if now >= 0 else high  # the old line scrolls up: follow it down to where a new one would show
        s = state()
        p = s["pc"]
        foes = sorted((c for c in s.get("nearby") or [] if c.get("hostile")), key=lambda c: c.get("dist", 99))
        if foes:
            f = foes[0]
            if (f.get("lv") or 0) > p["lv"] + 3:
                stop(f"{f['name']} Lv{f.get('lv')} at {f.get('dist')}: above my limit")
            if p["hp"] * 100 < FLOOR * p["maxHp"]:
                stop(f"HP {p['hp']}/{p['maxHp']} with {len(foes)} foes in view")
            out = run("fight.py", f["name"].split()[-1], FLOOR, timeout=90)
            print(f"  {f['name']} Lv{f.get('lv')}: HP {pc()['hp']}  {last(out)[:50]}", flush=True)
            if out.rc == 1:  # run 43: the fight tool refuses an avoid kind and this loop asked again for 3 minutes
                stop(f"fight.py refused {f['name']}: {last(out)[:80]}")
            continue
        if p["hp"] * 100 < 70 * p["maxHp"]:
            rest()
            continue
        # run 42: walkto refuses unexplored cells and the loop spun for 7 minutes; hunt.py's legs missed the last one: explore.py found it at once
        i += 1
        run("explore.py", timeout=60)
        answer_no()
        if i > 8:
            if "--any" in sys.argv:
                print("explored eight times: floor done")
                return 0
            stop("explored eight times and none left in view: look.py")
    else:
        if "--wiped" not in sys.argv:
            stop("3 minutes in the arena: look.py")
    print("wiped out")
    if "--no-leave" in sys.argv:
        return 0
    run("loot.py", 30, "--all", timeout=120)
    out = run("leave.py", "--force", timeout=120)
    print(last(out)[:70])
    b = [x for x in call("buttons")["data"]["buttons"] if (x.get("text") or "").endswith("Yes.")]
    if b:
        call("click", i=b[0]["i"])
        call("wait", until="zone", timeout=4000)
    for _ in range(4):
        run("talk.py", "12", timeout=30)
        acts = call("acts", dx=0, dz=0, mode="all")["data"]["acts"]
        hit = [a for a in acts if a["text"].startswith("Pick all") or a["text"].startswith("Pick (")]
        if hit:
            call("do", i=hit[0]["i"])
            time.sleep(0.4)
        if not (top() or state().get("drama")) and not hit:
            break
    p = pc()
    print(f"left: Lv{p['lv']} {p['exp']}/{p['expNext']}  HP {p['hp']}/{p['maxHp']}  {p.get('gold')} orens")
    return 0


if __name__ == "__main__":
    sys.exit(main())
