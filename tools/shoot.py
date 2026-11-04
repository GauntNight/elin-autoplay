"""Shoot a hostile with the held bow/sling (or hold the bow first), keeping my distance:
ranged first is the survival rule for anything that hits hard, paralyses (floating eye) or is
above my level. Stops (exit 3) at an HP floor; exit 0 when the target dies, nothing is left to
shoot, the act isn't offered, or after N shots.

usage: python -I tools/shoot.py [NAME] [min_hp_pct=60] [shots=12]
  NAME  a word of the target's name (whole words, common.matches; default: the nearest hostile;
        several hostiles of fitting names: the nearest)
Needs arrows (bow) or pebbles (sling) in the pack. Run 03: bow 2d6 + makeshift arrows took
about 30% of a yeek per hit. Refuses (exit 1) without ammo or a bow; the review of 2026-10-23:
common.ready first (a window, a dialog, a task running, the world map: not the hostile check),
and the bow is held through common.grab (a whole word: "forest long bow", never "bowl").
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import grab, matches, put_away, ready, refuse, stop  # noqa: E402

BOW = re.compile(r"(?<![a-z])(bow|crossbow|sling)(?![a-z])")


def hold_ranged():
    held = call("state")["data"]["pc"]["held"] or ""
    if BOW.search(held.lower()):
        return held
    for want in ("bow", "crossbow", "sling"):
        got = grab(want, what="weapon")
        if got and BOW.search(got.lower()):
            return got
        if got:  # matches' word-start level took something like a bowl: not a weapon
            put_away()
    return None


def main():
    args = [a for a in sys.argv[1:]]
    name = args[0].lower() if args and not args[0].isdigit() else None
    nums = [int(a) for a in args if a.isdigit()]
    min_hp = nums[0] if nums else 60
    shots = nums[1] if len(nums) > 1 else 12
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # a window, a dialog, a context menu, a task still running, the world map, a bad condition:
    # HP and hunger are the fight's own business here, and so is the hostile (hostile_r=-1)
    why = ready(hp=None, hunger=None, hostile_r=-1, burden=None)
    if why:
        stop(why)
    # run 12 (the user caught it): the bow had no arrows for a whole trip and every "shot" was a
    # wasted call; say so at once so callers fall back to the Putit or throwing daggers
    names = " ".join(i["name"].lower() for i in call("inv")["data"]["items"])
    if not re.search(r"\b(arrows?|bolts? of|pebbles?|bullets?)\b", names):
        refuse("no ammo: no arrows, pebbles or bullets in the pack (throw.py instead)")
    w = hold_ranged()
    if not w:
        refuse("no bow or sling in the pack")
    for k in range(shots):
        s = call("state")["data"]
        p = s["pc"]
        foes = [c for c in s.get("nearby") or [] if c["hostile"]]
        if name:
            foes = matches(name, foes, key="name")
        if not foes:
            print("no target left")
            return
        t = min(foes, key=lambda c: c["dist"])
        if p["hp"] * 100 < min_hp * p["maxHp"]:
            stop(f"HP {p['hp']}/{p['maxHp']} under {min_hp}%")
        acts = call("acts", dx=t["dx"], dz=t["dz"], mode="right")["data"]["acts"]
        sh = [a for a in acts if a["text"].startswith(("Shoot", "Throw"))]
        if not sh:
            print("can't shoot it: " + ", ".join(a["text"] for a in acts))
            return
        call("do", i=sh[0]["i"])
        time.sleep(1.0)
        s = call("state")["data"]
        t2 = [c for c in s.get("nearby") or [] if c["hostile"] and c["uid"] == t["uid"]]
        print(f"{k + 1:2} {t['name']} d{t['dist']} -> {t2[0]['hpPct'] if t2 else 'dead'}%  HP {s['pc']['hp']}")
    print("shot limit reached")


if __name__ == "__main__":
    main()
