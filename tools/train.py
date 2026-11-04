"""Train melee on a training dummy next to the player, and stop safely. The game's own
training (AI_PracticeDummy) only stops when stamina drops below zero; this stops it at a
floor instead, and on any threat: a hostile in view, HP below 80%, or hunger.

usage: python -I tools/train.py [min_sp] [max_minutes] [--throw ITEM | --shoot BOW]
  min_sp       stop when SP falls to this (default 6)
  max_minutes  real-time cap (default 10)
Prints exp, SP and the skill lines from the log as it goes.
Exit 0 at the SP floor, the time cap or when the practice ends by itself; 3 when it stopped for a
decision (a hostile in view, HP under 80%, worse than Hungry, a window); 1 refused (no dummy, no
weapon or arrows). A hostile 10+ levels below me is ignored (run 14: a Lv1 silver cat).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import THRESHOLDS, grab, matches, ready, refuse, wait_idle, wait_until  # noqa: E402

WEAK_BELOW = 10


def start():
    hit = call("find", name="training dummy", r=1, n=1)["data"]["hits"]
    if not hit:
        refuse("no training dummy next to me")
    if "--shoot" in sys.argv:
        # run 16: holding a bow, the right-click Shoot on the dummy starts ranged practice (it spends
        # an arrow a shot): Bow and Marksman, both low, pay the most exp a hit. The bow is taken
        # through common.grab (a whole-word match: "bow" no longer fits a bowl)
        bow = sys.argv[sys.argv.index("--shoot") + 1]
        held = call("state")["data"]["pc"].get("held") or ""
        if not matches(bow, [held]):
            wait_idle(timeout=10000)  # run 16: "busy" right after the walk made invacts fail
            if not grab(bow, what="bow"):
                refuse(f"no {bow!r} in the pack")
        acts = call("acts", dx=hit[0]["dx"], dz=hit[0]["dz"], mode="right")["data"]["acts"]
        sh = [a for a in acts if a["text"].startswith("Shoot")]
        if not sh:
            sys.exit("no Shoot act on the dummy (no arrows?): " + ", ".join(a["text"] for a in acts))
        call("do", i=sh[0]["i"])
        return
    if "--throw" in sys.argv:
        # run 14: holding a throwing weapon, the right-click Throw on the dummy starts the same
        # practice (AI_PracticeDummy.throwItem) and trains Throwing instead of a melee skill
        item = sys.argv[sys.argv.index("--throw") + 1]
        # run 15: Grab toggles, so grabbing the Putit while it was still in hand from the day
        # before put it away, and a whole training day was lost ("no Throw act on the dummy")
        held = call("state")["data"]["pc"].get("held") or ""
        if not matches(item, [held]) and not grab(item, what="throwing weapon"):
            refuse(f"no {item!r} in the pack")
        acts = call("acts", dx=hit[0]["dx"], dz=hit[0]["dz"], mode="right")["data"]["acts"]
        tr = [a for a in acts if a["text"].startswith("Throw")]
        if not tr:
            sys.exit("no Throw act on the dummy: " + ", ".join(a["text"] for a in acts))
        call("do", i=tr[0]["i"])
        return
    acts = call("acts", dx=hit[0]["dx"], dz=hit[0]["dz"], mode="all")["data"]["acts"]
    tr = [a for a in acts if a["text"].startswith("Train")]
    if not tr:
        sys.exit("the dummy offers no Train act: " + ", ".join(a["text"] for a in acts))
    call("do", i=tr[0]["i"])


def stop():
    """Interrupt the practice as a player's click does (bridge `cancel`, 0.9.1+). Injected keys
    and moves don't reach the game while a task runs (run 03: SP ran to -1)."""
    rep = call("cancel")
    time.sleep(0.5)
    return "cancel" if rep.get("ok") and "Practice" not in (call("state")["data"]["pc"]["ai"] or "") else None


def main():
    nums = [a for a in sys.argv[1:3] if a.replace(".", "", 1).isdigit()]
    min_sp = int(nums[0]) if nums else 6
    cap = float(nums[1]) if len(nums) > 1 else 10
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    s = call("state")["data"]
    p0 = s["pc"]
    if p0["sp"] <= min_sp:
        sys.exit(f"SP {p0['sp']} is already at the floor {min_sp}")
    # the shared check before the first act: a window, busy, a bad condition, HP under 80%,
    # Hungry, a hostile in view (one WEAK_BELOW levels under mine taken out first: run 14's cat)
    s2 = dict(s)
    s2["nearby"] = [c for c in s.get("nearby") or [] if not (c.get("hostile") and (c.get("lv") or 0) <= p0["lv"] - WEAK_BELOW)]
    why = ready(s2, hp=THRESHOLDS["loop_hp"], hunger=THRESHOLDS["hungry"])
    if why:
        print("stopped: " + why)
        sys.exit(3)
    start()
    wait_until("frames", n=10, timeout=1500)  # the practice task starts
    seen = set(s.get("log") or [])
    t0, why = time.time(), "time cap"
    while time.time() - t0 < cap * 60:
        time.sleep(0.3)
        s = call("state")["data"]
        p = s["pc"]
        for line in s.get("log") or []:
            if line not in seen:
                seen.add(line)
                if "skill" in line.lower() or "level" in line.lower() or "improve" in line.lower():
                    print("  " + line)
        if "Practice" not in (p["ai"] or ""):
            why = f"training ended by itself ({p['ai']})"
            break
        top = (s.get("layers") or {}).get("top")
        if top or s.get("drama"):  # e.g. the morning shipping report (run 03: ran to the time cap)
            why = f"a window opened ({top})"
            break
        if p["sp"] <= min_sp:
            why = f"SP floor {min_sp}"
            break
        # run 14: a Lv1 hostile silver cat at home stopped training for days, and cats are never
        # killed (karma); anything 10+ levels below me is ignored (the HP check below still holds)
        if any(c["hostile"] and c["lv"] > p["lv"] - 10 for c in s.get("nearby") or []):
            why = "hostile in view"
            break
        # Plain "Hungry" is harmless; stop at anything worse (Very hungry, Starving).
        # run 24: a big meal left me Bloated (hunger 2-7) and this stopped two training days: full is
        # no risk to training (wgo.py's walk takes Bloated too)
        if p["hp"] * 100 < 80 * p["maxHp"] or p.get("hungerText") not in ("", "Normal", "Filled", "Hungry", "Bloated", None):
            why = f"HP/hunger check ({p['hp']}/{p['maxHp']}, {p.get('hungerText')})"
            break
    how = stop() if "Practice" in (call("state")["data"]["pc"]["ai"] or "") else "-"
    p = call("state")["data"]["pc"]
    print(f"stopped: {why} (via {how}); Lv{p['lv']} exp {p0['exp']}->{p['exp']}/{p['expNext']}  "
          f"SP {p0['sp']}->{p['sp']}  HP {p['hp']}/{p['maxHp']}  {p['date']}")
    # the exit-code contract (common.py): 3 when the caller must decide (trainday reads .rc now)
    if why.startswith(("hostile", "HP/hunger", "a window")):
        sys.exit(3)


if __name__ == "__main__":
    main()
