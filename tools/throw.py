"""Throw a throwable at a hostile through the game's own Throw act (hold the item, right-click
the target's cell). Putit In Amber (2d8+3, cold and lightning, about 6.4 a turn) is my best
ranged attack and was never used until the user asked why (run 04); mica throwing daggers
(19, impact) and granite pebbles are the stack options. A thrown item lands near the target:
`loot.py` after the fight brings it back (the Putit is a single precious item).

usage: python -I tools/throw.py [NAME] [ITEM="Putit In Amber"] [THROWS=6] [MIN_HP_PCT=60]
  NAME  a word of the target's name (whole words, common.matches; default: the nearest hostile)
  ITEM  held through common.grab: whole-word matching, a refusal (exit 1) when it fits two
        different names, and never a cursed or doomed stack unless the name asks for one (run
        17: "cure major wound" took a cursed potion and hurt the escort)
Without the Putit it throws granite pebbles. Exit 0 when the target dies or the item runs out; 1 when
there was nothing to throw at all (the caller melees); exit 3 under the HP floor or when a window opens.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import THRESHOLDS, grab, matches, stop  # noqa: E402

DEFAULT_ITEM = "Putit In Amber"
FALLBACK_ITEM = "granite pebble"


def target(name):
    s = call("state")["data"]
    foes = [c for c in s.get("nearby") or [] if c.get("hostile")]
    if name:
        foes = matches(name, foes, key="name")  # whole words: "rat" is not a pirate (run 12 review)
    return (min(foes, key=lambda c: c["dist"]) if foes else None), s


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    name = a[0] if a else ""
    item = a[1] if len(a) > 1 else DEFAULT_ITEM
    throws = int(a[2]) if len(a) > 2 else 6
    floor = int(a[3]) if len(a) > 3 else 60
    for k in range(1, throws + 1):
        t, s = target(name)
        p = s["pc"]
        if not t:
            print("no target left")
            return
        if p["hp"] * 100 < floor * p["maxHp"]:
            stop(f"HP {p['hp']}/{p['maxHp']} under {floor}%")
        if (s.get("layers") or {}).get("top"):
            stop(f"window open ({s['layers']['top']})")
        # held through common.grab (the hold() wrapper went in the 2026-10-23 cleanup). The new-game test: a character without
        # the Putit made every caller's ranged attack a silent no-op with exit 0, so fall back to pebbles, and refuse (1)
        # when nothing was thrown at all, which is the caller's cue to melee.
        if not grab(item) and not (item == DEFAULT_ITEM and grab(FALLBACK_ITEM)):
            print(f"no {item!r} in the pack: nothing thrown this round; loot.py after a fight brings thrown ones back")
            if k == 1:
                sys.exit(1)
            return
        acts = call("acts", dx=t["dx"], dz=t["dz"], mode="right")["data"]["acts"]
        th = [x for x in acts if x["text"].startswith("Throw")]
        if not th:
            print(f"no Throw at {t['name']} d{t['dist']}: " + " | ".join(x["text"] for x in acts))
            return
        call("do", i=th[0]["i"])
        time.sleep(1.0)
        t2, s2 = target(t["name"])
        print(f"{k:2} {t['name']} d{t['dist']} -> {str(t2['hpPct']) + '%' if t2 else 'dead'}  HP {s2['pc']['hp']}")
        # run 34 (Capricious Ruin B4): a mimic's poison missiles and a crowd took 200 -> 75 while this loop checked only
        # its 55% floor: the round rule fight.py uses (THRESHOLDS hit_pct / hit_pct_any), with a teleport as the answer
        lost = (p["hp"] - s2["pc"]["hp"]) * 100 / max(1, p["maxHp"])
        left = s2["pc"]["hp"] * 100 / max(1, s2["pc"]["maxHp"])
        if lost > THRESHOLDS["hit_pct_any"] or (lost > THRESHOLDS["hit_pct"] and left < THRESHOLDS["dungeon_hp"]):
            stop(f"a throw round cost {lost:.0f}% ({p['hp']} -> {s2['pc']['hp']}/{s2['pc']['maxHp']}): teleport")
    print("throw limit reached")


if __name__ == "__main__":
    main()
