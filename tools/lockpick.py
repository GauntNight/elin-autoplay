"""Lockpicking practice on the home's practice chest (the user's tip, run 16: "you could buy a
practice chest and practice lock picking skill"). Lockpicking is a low skill (1.8 in run 15), so
its level-ups come cheap, and each is 10-14 character exp.

How the game runs it (fact #577; Trait.TryOpenLock, TraitChestPractice): holding a lockpick, the
power is Lockpicking + 10 and no charge is spent; the chest's lock is power/4*3 - 1; a try
succeeds if rnd(power + 6) > lock + 5 (about 35%), paying 100 + 10 x lock skill exp, a failure 50.
After a success the chest stays open until its 2-hourly tick locks it again. So: try until it
opens, close it, and come back after the tick; meanwhile do other work (the no-waiting rule).

usage: python -I tools/lockpick.py [MAX_TRIES=30] [min_sp=10]
Exit 0 opened (or already open: relocks on its tick), 3 stopped (SP, a hostile, a window).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, cells, grab, matches, pc, put_away, ready, refuse, setup, state, stop, wait_idle, wait_until, walk_beside  # noqa: E402
from home import PRACTICE_CHEST  # noqa: E402


def lock_level():
    info = cells([PRACTICE_CHEST])[PRACTICE_CHEST]
    for t in info.get("thingInfo") or []:
        if "practice chest" in t["name"]:
            return t["lockLv"]
    refuse(f"no practice chest at {PRACTICE_CHEST}")


def hold_lockpick():
    """The lockpick in hand through common.grab (a whole-word match; cursed stacks skipped)."""
    if matches("lockpick", [pc().get("held") or ""]):
        return
    if not grab("lockpick", prefer="charges", what="tool"):
        refuse("no lockpick in the pack")


def main():
    setup()
    nums = [int(a) for a in sys.argv[1:] if a.isdigit()]
    tries_max = nums[0] if nums else 30
    min_sp = nums[1] if len(nums) > 1 else 10
    r = walk_beside(*PRACTICE_CHEST)
    if not r.get("done"):
        stop(f"couldn't reach the practice chest: {r.get('why')}")
    lv = lock_level()
    if lv <= 0:
        print("the chest is open (lock 0): it relocks on its 2-hourly tick; do other work meanwhile")
        return
    wait_idle(timeout=10000)  # run 16: 'busy: the player is doing something' right after the walk
    why = ready(hp=None, hunger=None, sp=min_sp)  # a window, busy, a bad condition, a hostile, SP
    if why:
        stop(why)
    hold_lockpick()
    exp0 = pc().get("exp")
    for k in range(1, tries_max + 1):
        s = state()
        p = s["pc"]
        if any(c.get("hostile") for c in s.get("nearby") or []):
            stop("a hostile in view")
        if p.get("sp") is not None and p["sp"] < min_sp:
            stop(f"SP {p['sp']} under {min_sp}")
        p = pc()
        acts = call("acts", dx=PRACTICE_CHEST[0] - p["x"], dz=PRACTICE_CHEST[1] - p["z"], mode="all")["data"]["acts"]
        op = [a for a in acts if a["text"].startswith(("Pick Lock", "Open"))]  # "Pick Lock" while locked
        if not op:
            refuse("no Open act on the practice chest: " + " | ".join(a["text"] for a in acts))
        call("do", i=op[0]["i"])
        wait_until("frames", n=15, timeout=2000)  # the try is one turn; a success opens the window
        s = state()
        top = (s.get("layers") or {}).get("top")
        log = " / ".join((s.get("log") or [])[-3:])
        if top:  # the container window: it opened
            call("closetop")
            wait_until("frames", n=8, timeout=1000)
            print(f"opened on try {k} (lock {lv}); exp {exp0} -> {pc().get('exp')}; relocks on its 2-hourly tick")
            put_away()
            return
        if re.search(r"skill increases", log, re.I):
            print(f"  try {k}: {log}")
    put_away()
    print(f"not opened in {tries_max} tries (lock {lv}); exp {exp0} -> {pc().get('exp')}")


if __name__ == "__main__":
    main()
