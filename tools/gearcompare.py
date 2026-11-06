"""Compare a piece of gear with what's worn by wearing it (run 42, the user: "make a skill/method to validate equipment cleanly between worn/wielded. Pen% value is huge on armored
opponents"; the method is the elin-gear skill). A tooltip read from the pack misses what a piece does once worn: its attributes change the multiplier and the to-hit, its Mind's Eye
the crits, its PV and DV the armour. So this swaps the piece on, reads the game's own numbers (bridge `power`: AttackProcess.Prepare and the sheet), swaps back and checks every
worn piece is where it was. Nothing stays changed: choosing is mine, with item.py.

What it scores, from the game's code, against a panel of foes of level L at my speed:
  damage a turn   hit chance x expected hit x swings x speed/100
    hit chance    AttackProcess.CalcHit: 5% always, 5% never, else a miss when rnd(toHit) < rnd(evasion x 1.25)
    expected hit  dice x multiplier; the part penetration lets past skips armour, the rest is cut to 100/(100+P) less a flat roll (Card.ApplyProtection); then physical reduction
                  (a race's PDR, Card.DamageHP); a crit rolls the dice's maximum at x1.25 (CalcHit: (critical + sqrt(Mind's Eye))/200, plus (PER+50)/5000); vorpal is 100% penetration
    swings        flurry: each further swing at flurry/(25 + 5^(i+2)) (ActMelee.AttackWithFlurry), the two-hand bonus already in the number; every swing rolls to hit again
    enchants      an attack element on the weapon: 25% a hit for up to raw x (100 + 10 x value)/500 + 5 more, before the foe's resistance (AttackProcess.Perform)
  HP lost a kill  the trade: turns to kill x what a foe does a turn through my armour and evasion (power.py's fit from fights.csv). This is the one number that holds a weapon's
                  damage, its DV and PV, its effect on speed and max HP in one place. Lower is better.
A foe's armour and evasion aren't shown in play, so the panel uses the priors from power-model.md scaled by armour class: it says how a choice depends on armour, not any one foe's
truth. `--foe NAME` uses a kind's race table (PV and DV multipliers, PDR, life). The trial in play settles it: `--judge DATE` reads fights.csv.

usage: python -I tools/gearcompare.py NAME [NAME ...] [--against WORN] [--level L] [--foe KIND ...] [--dry]   wear each NAME in place of WORN (default: what fills its slot)
       python -I tools/gearcompare.py --worn [--level L] [--foe KIND ...]     the panel for what's worn now, nothing moved
       python -I tools/gearcompare.py --judge DATE [--before DATE0]           fights from game date DATE on against those before it, same character level or better
Refuses with a hostile in view or a window open. Exit 0 done, 1 refused, 3 stopped (a swap that didn't go; what's worn is printed).
"""
import csv
import math
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data, ready, refuse, run, setup, stop, top, wait_until  # noqa: E402
from gearcheck import SLOTS, slot_of, lines_of  # noqa: E402
from power import after_armour, evasion, foe_hit, foe_ref, hit_chance, protection, threat_fit  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "runs" / "gearcompare.csv"
FIGHTS = ROOT / "knowledge" / "fights.csv"
# (label, armour x, evasion x, physical reduction %, life x) on the priors of power-model.md
PANEL = [("soft", 0.5, 1.0, 0, 1.0), ("normal", 1.0, 1.0, 0, 1.0), ("armoured", 2.0, 1.0, 0, 1.0), ("plated", 4.0, 1.0, 0, 1.0), ("evasive", 1.0, 2.0, 0, 1.0)]
KEY_LINE = re.compile(r"negates|prevents|protects|Resistance|sustains|float|breathe|See Invisible|sees? invisible|anticipate|consecutive|counter|Pen", re.I)
_ = SLOTS  # imported so a change of slot names shows up here too


_FIT = []


def fit():
    """power.py's a + b L, once: the grid search over thousands of fights takes seconds."""
    if not _FIT:
        cache = ROOT / "runs" / "jobs" / "threatfit.txt"
        stamp = str(FIGHTS.stat().st_size // 20000) if FIGHTS.exists() else "0"  # refit when fights.csv has grown by ~300 fights
        try:
            old = cache.read_text(encoding="utf-8").split()
            if old[0] == stamp:
                _FIT.extend([float(old[1]), float(old[2])])
        except (OSError, IndexError, ValueError):
            pass
        if not _FIT:
            _FIT.extend(threat_fit()[:2])
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(f"{stamp} {_FIT[0]} {_FIT[1]}\n", encoding="utf-8")
    return _FIT[0], _FIT[1]


def my_power():
    return data("power")["party"][0]


def worn_names():
    return sorted(i["name"] for i in data("inv")["items"] if i.get("equipped"))


def main_attack(p):
    melee = [a for a in p["attacks"] if a["kind"] == "melee"]
    return melee[0] if melee else p["attacks"][-1]


def swings(flurry):
    total, chance = 1.0, 1.0
    for i in range(10):
        chance *= min(1.0, max(flurry, 0) / (25 + 5 ** (i + 2)))
        total += chance
    return total


def crit_chance(a):
    lucky = (a.get("per", 0) + 50) / 5000
    sharp = min(1.0, (a.get("critBase", 0) + math.sqrt(max(a.get("eye", 0), 0))) / 200)
    return lucky + (1 - lucky) * sharp


def expected_hit(a, prot, pdr):
    """One landed swing's damage after armour, with crits and vorpal."""
    mean = (a["dNum"] * (a["dDim"] + 1) / 2 + a["dBonus"]) * a["dMulti"]
    top_roll = (a["dNum"] * a["dDim"] + a["dBonus"]) * a["dMulti"] * 1.25
    c, v, pen = crit_chance(a), min(a.get("vorpal", 0), 100) / 100, a["penetration"]
    hit = (1 - c) * after_armour(mean, prot, pen) + c * after_armour(top_roll, prot, pen)
    hit_vorpal = (1 - c) * mean + c * top_roll
    out = (1 - v) * hit + v * hit_vorpal
    # an attack element: 25% a hit, a roll up to out x (100 + 10 x value)/500 + 5 (Perform; the foe's resistance isn't known)
    extra = 0.0
    for e in a.get("elements") or []:
        m = re.match(r"(\S+) (-?\d+)$", str(e))
        if m and int(m.group(2)) > 0:
            extra += 0.25 * (out * (100 + 10 * int(m.group(2))) / 500 + 5) / 2
    return (out + extra) * (100 - pdr) / 100


def row(p, lv, armour, ev_x, pdr, life):
    a = main_attack(p)
    ref = foe_ref(lv)
    prot, ev = ref["protection"] * armour, ref["evasion"] * ev_x
    hit = hit_chance(a["toHit"], ev, False)
    per_swing = expected_hit(a, prot, pdr)
    speed = p["speed"] / 100
    swing_n = swings(a.get("flurry", 0))
    per_turn = hit * per_swing * swing_n * speed
    hp = ref["hp"] * life
    # a hit past the foe's HP buys nothing: count the landed swings it takes, whole, at the rate they land (a low-level foe dies to one hit from either weapon, so to-hit and flurry decide)
    turns = math.ceil(hp / max(per_swing, 0.01)) / max(hit * swing_n * speed, 0.01)
    a_, b_ = fit()
    my_prot, my_ev = protection(p), evasion(p)
    loss_turn = after_armour(a_ + b_ * lv, my_prot, 0) * foe_hit(lv, my_ev)
    return {"hit": hit, "swing": per_swing, "turn": per_turn, "turns": turns, "loss": turns * loss_turn}


def foe_rows(kinds, lv):
    """A kind's race multipliers on the priors: PV and DV (Chara.PV: x (100 + L + race x 5)/100), PDR (element 55) and life."""
    if not kinds:
        return PANEL
    from threat import tables
    charas, races, _jobs = tables()
    out = []
    for k in kinds:
        hit = [c for c in (charas.values() if isinstance(charas, dict) else charas) if k.lower() in (str(c.get("id")) + " " + str(c.get("name"))).lower()]
        if not hit:
            refuse(f"no kind '{k}' in the game's table")
        c = hit[0]
        r = races.get(c.get("race"), {})
        base = (100 + lv) / 100
        out.append((f"{c.get('id')}", (100 + lv + (r.get("PV") or 0) * 5) / 100 / base, (100 + lv + (r.get("DV") or 0) * 5) / 100 / base, r.get("PDR") or 0, (r.get("life") or 100) / 100))
    return out


def card(p, label, lv, kinds):
    a = main_attack(p)
    print(f"\n{label}: {a['weapon']}")
    print(f"  {a['dNum']}d{a['dDim']}+{a['dBonus']} x{a['dMulti']}  toHit {a['toHit']}  Pen {a['penetration']}%  crit {crit_chance(a)*100:.1f}%  vorpal {a.get('vorpal', 0)}%  "
          f"flurry {a.get('flurry', 0)} (swings {swings(a.get('flurry', 0)):.2f})  chase {a.get('chase', 0)} cleave {a.get('cleave', 0)} feint {a.get('feint', 0)} splash {a.get('splash', 0)}")
    print(f"  HP {p['maxHp']}  speed {p['speed']}  PV {p['PV']} DV {p['DV']}  protection {protection(p)}  evasion {evasion(p)}  STR {p['attrs']['STR']} DEX {p['attrs']['DEX']} PER {p['attrs']['PER']}")
    rows = {}
    for name, ax, ex, pdr, life in foe_rows(kinds, lv):
        r = row(p, lv, ax, ex, pdr, life)
        rows[name] = r
        print(f"  Lv{lv} {name:<10} hit {r['hit']*100:3.0f}%  a swing {r['swing']:6.1f}  a turn {r['turn']:6.1f}  turns to kill {r['turns']:5.1f}  HP lost a kill {r['loss']:6.1f}")
    return rows


def where_is(name):
    """(the name as carried, the bag it's in or None)."""
    for i in data("stock")["pack"]:
        if name.lower() in i["name"].lower() and i.get("items") is None and not i.get("equipped"):
            return i["name"], None
        for x in i.get("items") or []:
            if name.lower() in x["name"].lower():
                return x["name"], i["name"]
    return None, None


def worn_in_slot(slot):
    return [i["name"] for i in data("inv")["items"] if i.get("equipped") and slot_of(i["name"]) == slot]


def swap(off, on):
    out = run("item.py", off, "Unequip", timeout=60)
    if out.rc:
        return f"Unequip {off}: {str(out)[-140:]}"
    wait_until("frames", n=10, timeout=1500)
    out = run("item.py", on, "Equip", timeout=60)
    if out.rc:
        back = run("item.py", off, "Equip", timeout=60)
        return f"Equip {on}: {str(out)[-140:]} (put back: rc {back.rc})"
    wait_until("frames", n=10, timeout=1500)
    return None


def judge(args):
    since = args[args.index("--judge") + 1]
    before = args[args.index("--before") + 1] if "--before" in args else None
    rows = list(csv.DictReader(FIGHTS.open(encoding="utf-8")))
    lv = max(int(r["my_lv"] or 0) for r in rows if r.get("my_lv", "").isdigit())

    def band(r):
        if not (r.get("turns") or "").isdigit() or not (r.get("foe_lv") or "").isdigit() or r.get("result") != "killed" or r.get("source") != "fight.py":
            return None
        return min((int(r["foe_lv"]) // 10) * 10, 40)

    new = [r for r in rows if r["game_date"] >= since and band(r) is not None]
    old = [r for r in rows if r["game_date"] < since and (not before or r["game_date"] >= before) and int(r["my_lv"] or 0) >= lv - 1 and band(r) is not None]
    print(f"fights since {since}: {len(new)}; before, at character level {lv - 1}+: {len(old)}")
    print("foe level   before: n  turns  HP lost   since: n  turns  HP lost")
    for b in sorted({band(r) for r in new + old}):
        def stats(group):
            g = [r for r in group if band(r) == b]
            if not g:
                return "    -      -       -"
            return f"{len(g):5d} {sum(int(r['turns']) for r in g)/len(g):6.1f} {sum(float(r['hp_lost'] or 0) for r in g)/len(g):7.1f}"
        print(f"{b:>3}-{b+9:<3}    {stats(old)}    {stats(new)}")
    print("Fights differ in crowd and kind: read it with the run log, and want 20+ fights a side before calling it.")
    return 0


def main():
    setup()
    args = sys.argv[1:]
    if "--judge" in args:
        return judge(args)

    def opts(name):
        out, i = [], 0
        while i < len(args):
            if args[i] == name and i + 1 < len(args):
                out.append(args[i + 1])
                i += 1
            i += 1
        return out
    level = int(opts("--level")[0]) if opts("--level") else None
    kinds = opts("--foe")
    against = opts("--against")
    skip = {"--level", "--foe", "--against"}
    names = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in skip)]
    base = my_power()
    lv = level or base["lv"]
    if "--worn" in args or not names:
        card(base, "worn", lv, kinds)
        return 0
    why = ready(hp=50, hunger=None, burden=None)
    if why and "world map" not in why:
        refuse(f"not now: {why}")
    if top():
        refuse(f"{top()} is open")
    start = worn_names()
    print("-- worn now --")
    base_rows = card(base, "worn", lv, kinds)
    results = []
    for want in names:
        carried, bag = where_is(want)
        if not carried:
            refuse(f"no '{want}' in the pack or its bags")
        slot = slot_of(carried)
        if not slot:
            refuse(f"{carried}: no slot known for it (gearcheck.SLOTS)")
        rivals = against or worn_in_slot(slot)
        if not rivals:
            refuse(f"nothing worn in slot {slot}: wear it with item.py")
        if bag:
            out = run("bag.py", bag, "--take", carried, timeout=60)
            run("close.py", timeout=30)
            if out.rc:
                stop(f"bag.py --take {carried}: {str(out)[-140:]}")
        for rival in rivals:
            if "--dry" in args:
                print(f"would wear {carried} in place of {rival}")
                continue
            fail = swap(rival, carried)
            if fail:
                stop(fail)
            try:
                now = my_power()
                rows = card(now, f"with {carried} in place of {rival}", lv, kinds)
                results.append((carried, rival, rows))
            finally:
                fail = swap(carried, rival)
                if fail:
                    stop(f"NOT RESTORED: {fail}")
            a, b = set(lines_of(rival)), set(lines_of(carried))
            print(f"  only {carried[:30]}: " + " / ".join(ln for ln in sorted(b - a) if KEY_LINE.search(ln))[:400])
            print(f"  only {rival[:30]}: " + " / ".join(ln for ln in sorted(a - b) if KEY_LINE.search(ln))[:400])
        if bag:
            run("bag.py", bag, carried, timeout=60)
            run("close.py", timeout=30)
    end = worn_names()
    if end != start:
        stop(f"worn gear changed: was {sorted(set(start) - set(end))}, now {sorted(set(end) - set(start))}")
    print("\nall worn gear back in place")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    new = not LOG.exists()
    with LOG.open("a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["when", "lv", "candidate", "rival", "foe", "turn_rival", "turn_cand", "loss_rival", "loss_cand"])
        for cand, rival, rows in results:
            for foe, r in rows.items():
                b = base_rows.get(foe) or {}
                w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M"), lv, cand, rival, foe, f"{b.get('turn', 0):.1f}", f"{r['turn']:.1f}", f"{b.get('loss', 0):.1f}", f"{r['loss']:.1f}"])
    for cand, rival, rows in results:
        print(f"\n{cand}  against  {rival}  at Lv{lv} (rival -> candidate; + the candidate is better)")
        print(f"  {'foe':<13} {'damage a turn':>16}    {'turns to kill':>16}    {'HP lost a kill':>16}")
        for foe, r in rows.items():
            b = base_rows[foe]
            print(f"  {foe:<13} {b['turn']:6.1f} -> {r['turn']:6.1f} {'+' if r['turn'] > b['turn'] else '-'}"
                  f"   {b['turns']:6.1f} -> {r['turns']:6.1f} {'+' if r['turns'] < b['turns'] else '-'}"
                  f"   {b['loss']:6.1f} -> {r['loss']:6.1f} {'+' if r['loss'] < b['loss'] else '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
