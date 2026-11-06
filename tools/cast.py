"""Cast an attack spell at a hostile from range (bridge 0.33.0 `cast`: the game's own ButtonAbility.TryUse
path, pc.UseAbility then EndTurn, with every rule of the game kept: range, line of sight, the spell
stock, cooldowns). Run 27's 『Kobold』 (23% a round in melee, PV-heavy) had no ranged answer, and the
stocked attack spells were barely cast (the user's tip after run 27). Each cast trains Casting by twice
the MP spent (Chara.UseAbility: elements.ModExp(304, MP x 2)), and only a Casting level-up pays character
exp: a weak exp engine at 69 MP, a free ranged attack all the same.

MP is shared with the heals (Cure Minor Wound, Nature's Embrace): casting stops at the MP floor (default
30, about five cure casts) so a fight never spends the heal reserve.

usage: python -I tools/cast.py [SPELL=arrow_Cold] [NAME] [CASTS=10] [--mp-floor N] [--hp N] [--until PCT]
  --until PCT  (run 29, G20's monster ball) stop once the target is at or under PCT% HP (exit 0), or when the
               biggest drop a cast round has made could kill it from where it stands (exit 3)
  SPELL  the ability's alias (power.py lists them with their stock: arrow_Cold, arrow_Nerve, bolt_Fire)
  NAME   a word of the target's name (whole words); default the nearest hostile
Exit 0 the target died (or none left), 1 refused (no such spell, the bridge refused the cast),
3 stopped (MP at the floor, HP under the floor, a window, the target out of sight).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import THRESHOLDS, matches, refuse, setup, state, stop, wait_idle  # noqa: E402
import threat  # noqa: E402


def exploder(c):
    """delve.py's test: threat.py's exploder flag, or 'kamikaze' in the id, or a hot guy by name."""
    prof = threat.profile(c.get("id") or c.get("name") or "") or {"flags": []}
    return ("exploder" in prof["flags"] or "kamikaze" in (c.get("id") or "").replace("samurai_kamikaze", "")
            or any(w in (c.get("name") or "").lower() for w in ("kamikaze", "hot guy")))


def target(name, uid=None):
    s = state()
    foes = [c for c in s.get("nearby") or [] if c.get("hostile")]
    if uid is not None:
        foes = [c for c in foes if c.get("uid") == uid]
    elif name:
        foes = matches(name, foes, key="name")
    return (min(foes, key=lambda c: c["dist"]) if foes else None), s


def opt(args, flag, default):
    if flag in args:
        i = args.index(flag)
        v = int(args[i + 1])
        del args[i:i + 2]
        return v
    return default


def main():
    setup()
    args = sys.argv[1:]
    mp_floor = opt(args, "--mp-floor", 30)
    hp_floor = opt(args, "--hp", 60)
    until = opt(args, "--until", None)
    spell = args[0] if args else "arrow_Cold"
    name = args[1] if len(args) > 1 else ""
    casts = int(args[2]) if len(args) > 2 else 10
    t, s = target(name)
    if t is None:
        print("no hostile in view")
        return
    uid, who = t["uid"], t["name"]
    done, drops = 0, []
    while done < casts:
        if until is not None:
            if t["hpPct"] <= until:
                print(f"{who} (uid {uid}) is at {t['hpPct']}%: at or under {until}% (drops a round: {drops})")
                return
            if drops and max(drops) >= t["hpPct"]:
                stop(f"{who} is at {t['hpPct']}% and a round took up to {max(drops)}%: the next could kill it")
        p = s["pc"]
        if p["hp"] * 100 < hp_floor * p["maxHp"]:
            stop(f"HP {p['hp']}/{p['maxHp']} under {hp_floor}%: heal or leave (elin-play thresholds)")
        if p["mp"] <= mp_floor:
            stop(f"MP {p['mp']} at the floor {mp_floor} (the heals' reserve) after {done} casts")
        if (s.get("layers") or {}).get("top") or s.get("drama"):
            stop(f"a window is open: {(s.get('layers') or {}).get('top') or 'a dialog'}")
        # run 38: a Short Teleport landed beside a hot guy and this cast an arrow at it from 1 cell (a kill at 2 still
        # cost 30 HP in run 24): an exploder inside the kamikaze distance is a step-away first, never a cast
        if t["dist"] < THRESHOLDS["kamikaze_dist"] and exploder(t):
            stop(f"{who} is an exploder at {t['dist']}: get to {THRESHOLDS['kamikaze_dist']}+ cells first "
                 "(a teleport scroll; a Short Teleport can land beside it)")
        r = call("cast", spell=spell, uid=uid)
        if not r.get("ok"):
            err = r.get("error") or ""
            if "not in sight" in err or "no living creature" in err:
                print(f"{who}: {err}")
                break
            refuse(f"cast refused: {err}")
        d = r["data"]
        done += 1
        print(f"  {spell} -> {d['target']} (dist {d['dist']}): {'cast' if d['cast'] else 'NOT cast'}  "
              f"MP {d['mp']}  stock {d['stock']}  HP {d['hp']}")
        if not d["cast"]:
            refuse("the game refused the cast (range, line of sight, no stock?)")
        wait_idle(timeout=10000)
        before = t["hpPct"]
        t, s = target(name, uid)
        if t is not None and t["hpPct"] < before:
            drops.append(before - t["hpPct"])
        if t is None:
            print(f"target gone: {who}")
            return
        print(f"     {who} {t.get('hpPct')}% at {t['dist']}")
    print(f"{done} casts")


if __name__ == "__main__":
    main()
