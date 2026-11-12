"""Heal myself with the Cure Minor Wound spell from the ability bar (run 25: 90 -> 166 HP for 33 MP,
~10-15 HP a cast at Lv25; a free heal no tool used before, while the kit held one cure potion).
Casts until HP reaches the target, MP falls under the floor, or a hostile comes into view (the
cast itself is safe with a weak foe near: pass --fight-ok to go on with hostiles in view).
The ability button is listed again right before every click (elin-play: never click a stale index).
usage: python -I tools/cure.py [TARGET_PCT=80] [MIN_MP=10] [--fight-ok] [--dry]
Exit 0 healed (or already there), 1 refused (no spell button), 3 stopped (a hostile, MP out).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, hostiles as common_hostiles, pc, refuse, setup, state, stop  # noqa: E402

SPELL = "Cure Minor Wound"
ALIAS = "SpHealLight"  # run 34: the bridge's cast op (0.33.0) needs no hotbar button


def button():
    bs = call("buttons", all=True)["data"]["buttons"]
    for b in bs:
        if "ButtonAbility" in (b.get("name") or "") and (b.get("card") or b.get("text") or "") == SPELL:
            return b["i"]
    for b in bs:  # older listings put the name in the text column
        if "ButtonAbility" in (b.get("name") or "") and SPELL in (b.get("text") or ""):
            return b["i"]
    return None


def hostiles():
    return common_hostiles()


def main():
    setup()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    target = int(args[0]) if args else 80
    min_mp = int(args[1]) if len(args) > 1 else 10
    fight_ok = "--fight-ok" in sys.argv
    dry = "--dry" in sys.argv
    p = pc()
    hp, mx, mp = p["hp"], p["maxHp"], p["mp"]
    i = button()
    # run 34: a spell learned from a book this session had no hotbar button, so cure.py refused while 69 casts sat
    # in stock; the bridge's cast op (no uid: myself) takes the game's own UseAbility path with no button
    global ALIAS
    spells = {s["spell"]: s["stock"] for s in call("power")["data"]["party"][0].get("spells") or []}
    # run 34: Healing Touch (Koflord's book) when Cure Minor Wound's stock is spent
    ALIAS = next((a for a in ("SpHealLight", "SpHealTouch") if spells.get(a, 0) > 0), ALIAS)
    stock = spells.get(ALIAS, 0)
    if i is None and not stock:
        refuse(f"no '{SPELL}' button on the ability bar and no {ALIAS} stock")
    print(f"HP {hp}/{mx}  MP {mp}  target {target}%  " + (f"spell button {i}" if i is not None else f"cast op ({ALIAS} stock {stock})")
          + ("  (dry)" if dry else ""))
    if dry or hp * 100 >= target * mx:
        print("done: at the target" if not dry else "dry: nothing cast")
        return
    if (state().get("zone") or {}).get("region"):  # run 26: no cast lands on the world map; the loop spun for 10 minutes
        refuse("on the world map the spell does nothing: enter a local map first")
    casts = 0
    while True:
        p = pc()
        hp, mx, mp = p["hp"], p["maxHp"], p["mp"]
        if hp * 100 >= target * mx:
            break
        if mp < min_mp:
            stop(f"MP {mp} under {min_mp} at HP {hp}/{mx} after {casts} casts")
        if not fight_ok and hostiles():
            stop(f"hostile in view at HP {hp}/{mx} after {casts} casts: fight or leave first")
        i = button()
        mp_before = mp
        if i is None:
            r = call("cast", spell=ALIAS)
            if not r.get("ok") or not (r.get("data") or {}).get("cast"):
                stop(f"cast op refused after {casts} casts: {r.get('error') or r.get('data')}")
        else:
            call("rclick", i=i)
        casts += 1
        time.sleep(1.2)
        if casts >= 4 and pc()["mp"] >= mp_before:
            stop(f"casts don't land (MP {mp_before} unchanged after a cast): look.py")
    p = pc()
    print(f"healed: HP {p['hp']}/{p['maxHp']}  MP {p['mp']}  casts {casts}")


if __name__ == "__main__":
    main()
