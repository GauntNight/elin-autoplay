"""Cast self buffs before a hard floor or fight (run 59: ~100-270 casts each of Hero, Holy Veil, Resist Element, Holy Shield and
Speed sat unused while floors at the gate fell to 71% HP; no tool cast them). Each spell is cast until its condition shows in
`state` (or, for a spell with no condition such as Magic Map, until a cast spends MP), at most 4 tries, never under the MP floor
that keeps the heals, and never with a hostile in view (the turns belong to the fight then) unless --fight-ok.

usage: python -I tools/buff.py [--mp-floor N=110] [--fight-ok] [SPELL ...]
  SPELL  an ability alias (power.py lists them); default: the GATE set below, what a gate floor gets at its door
Exit 0 all on (or already on), 1 refused (no such spell), 2 the bridge, 3 stopped (MP at the floor, a hostile, a window).
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import THRESHOLDS, hostiles, named, refuse, setup, state, stop, top  # noqa: E402

# spell -> the condition it leaves as `state` names it (run 59: Holy Shield reads BaseBuff, Speed Up ConBuffStats); None: none to read
CON = {"SpHero": "ConHero", "SpHolyVeil": "ConHolyVeil", "SpResEle": "ConResEle", "SpHolyShield": "BaseBuff",
       "SpSpeedUp": "ConBuffStats", "SpSeeInvisible": "ConSeeInvisible", "SpWisdom": "ConWisdom", "SpCatsEye": "ConNightVision",
       "SpHOT": "ConHOT", "SpLevitate": "ConLevitate", "SpMagicMap": None}
# run 59: Resist Element is +5 fire, cold and lightning for 16 MP (fire 0 -> 5: the Heat Sensitivity mutation cancels the girdle's fire
# rank, and a red dragon's breath took 480 -> 261 on Chilly Cave B1); the order is what a floor at the gate needs most
GATE = ["SpResEle", "SpHolyShield", "SpHero", "SpSpeedUp", "SpHolyVeil", "SpSeeInvisible"]


def conditions():
    return set(state()["pc"].get("conditions") or [])


def buff(spell, mp_floor, tries=4):
    """Cast SPELL on myself until it shows. (ok, a line for the log): ok is False at the MP floor or on a refused cast."""
    con = CON.get(spell)  # run 59: a guessed "ConUncurse" cost three extra casts (110 MP): a spell not in the table is cast once
    if con and con in conditions():
        return True, f"{spell}: already on"
    for n in range(1, tries + 1):
        pc = state()["pc"]
        if pc["mp"] < mp_floor:
            return False, f"{spell}: MP {pc['mp']} under the floor {mp_floor}"
        before = conditions()
        r = call("cast", spell=spell)
        if not r.get("ok") or not (r.get("data") or {}).get("cast"):
            return False, f"{spell}: the cast was refused: {r.get('error') or r.get('data')}"
        time.sleep(0.4)
        now = state()["pc"]
        gained = conditions() - before
        if (con and con in conditions()) or gained or (con is None and now["mp"] < pc["mp"]):
            return True, f"{spell}: on after {n} cast(s), MP {pc['mp']} -> {now['mp']}" + (f" ({', '.join(sorted(gained))})" if gained else "")
    return True, f"{spell}: no effect seen after {tries} casts (MP {state()['pc']['mp']})"


# run 59: the durations are short (the game's stats table, p = the cast's power): Elemental Shield p/15+8 turns, Holy Veil p/6+5, Speed
# p/8+5, Hero p/4+10, Holy Shield p/3+10 (PV +15 and more): cast at a floor's door they ran out before the hard fight
ELEMENT = re.compile(r"\b(red|white|blue|fire|ice|cold|frost|lightning|thunder|electric)\b.*\b(dragon|hound|drake|ent|wyvern|cloud)\b", re.I)


def fight_set(t, group, mp_floor=110):
    """One line each for the buffs cast in front of a hard foe (delve.py): within `buff_below` levels of mine, named or an avoid kind.
    Holy Shield and Hero, and Elemental Shield first against a fire, cold or lightning breather; at most two tries a spell."""
    pc = state()["pc"]
    below = THRESHOLDS["buff_below"] + (8 if group == "avoid" or named(t) else 0)
    if t["lv"] < pc["lv"] - below:
        return []
    spells = (["SpResEle"] if ELEMENT.search(t.get("name") or "") else []) + ["SpHolyShield", "SpHero"]
    out = []
    for s in spells:
        if CON.get(s) in conditions():
            continue
        ok, line = buff(s, mp_floor, tries=2)
        out.append(line)
        if not ok:
            break
    return out


def main():
    setup()
    args = sys.argv[1:]
    floor = int(args[args.index("--mp-floor") + 1]) if "--mp-floor" in args else 110
    fight_ok = "--fight-ok" in args
    skip = {str(floor)} if "--mp-floor" in args else set()
    spells = [a for a in args if not a.startswith("--") and a not in skip] or GATE
    for s in spells:
        if top() not in (None, "None"):
            stop(f"a window is open: {top()}")
        if hostiles() and not fight_ok:
            stop("a hostile in view: fight or leave first (--fight-ok casts anyway)")
        ok, line = buff(s, floor)
        print(line)
        if not ok:
            (refuse if "refused" in line else stop)(line)


if __name__ == "__main__":
    main()
