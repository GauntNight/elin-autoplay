"""Walk a wild map shearing every furry animal on the way (run 10, G6 threads): explore a few
moves, fight any hostile at or below my level (fight.py), shear whatever is in view (shear.py),
repeat. Stops (exit 3) on a hostile above my level, common.ready's reasons (HP under 70%, a
window, a task running, Hungry, Overweight), or fight.py stopping or refusing; exit 0 when the
map is explored or after ROUNDS rounds.
Wild animals' fur resets to the first tier whenever the zone resets, so a field map entered again
later can be sheared again (Zone.cs: c_fur = 0 for non-faction charas).

usage: python -I tools/shearwalk.py [ROUNDS=10] [MOVES=6]
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import THRESHOLDS, last, ready, run as _run, stop  # noqa: E402


def run(*args, timeout=600):
    return _run(args[0], *args[1:], timeout=timeout)


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    moves = sys.argv[2] if len(sys.argv) > 2 else "6"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for i in range(rounds):
        s = call("state")["data"]
        p = s["pc"]
        # the hostiles are this loop's business (hostile_r=-1): it fights the ones at or below my level
        why = ready(s, hp=THRESHOLDS["dungeon_hp"], hostile_r=-1)
        if why:
            stop(why)
        foes = [c for c in s.get("nearby") or [] if c.get("hostile")]
        strong = [c for c in foes if c.get("lv", 0) > p.get("lv", 10)]
        if strong:
            stop(f"{strong[0]['name']} Lv{strong[0]['lv']} is above my level")
        if foes:
            name = re.sub(r"^(an?|the) ", "", foes[0]["name"])
            out = run("fight.py", name, "60")
            print(f"[{i}] fight {name}: {last(out)}")
            if out.rc in (1, 3):  # refused (a rule) or stopped (HP, a big hit, a window): mine to decide
                stop(f"fight.py {'refused' if out.rc == 1 else 'stopped'}: {last(out)[:120]}")
            continue
        out = run("shear.py", "14")
        if "sheared 0" not in out:
            print(f"[{i}] " + " / ".join(ln.strip() for ln in out.splitlines()[-4:] if ln.strip()))
        ex = run("explore.py", moves)
        ex_last = last(ex)
        print(f"[{i}] explore: {ex_last}")
        if "no frontier" in ex_last or "explored" in ex_last:
            out = run("shear.py", "14")
            print("done: map explored; " + last(out))
            return
    print("done: round limit; " + last(run("shear.py", "14")))


if __name__ == "__main__":
    main()
