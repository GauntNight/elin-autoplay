"""Threat profiles by monster kind (the user, run 16: "threat models are not linear... high damage
enemies and casters need to be killed first. High defense enemies should be avoided and killed last").

power.py's danger table scales one fitted line with the foe's level (2.2 x level a hit), so a yeek
warrior and a putit of the same level look alike. This builds a profile per creature kind from the
game's own tables (knowledge/game: charas, races, jobs) and the fights we recorded
(knowledge/fights.csv), in two indexes normalised to 1.0 for an average creature of its level:

  offense  how much it hurts per turn of mine: melee (race + job STR and DEX, x1.4 when the job
           arms it with weapons), spells (its actCombat list: bolts, arrows, balls, breaths, hands,
           with their cast chance, scaled by MAG), all times race speed / 100 (yeeks are 130)
  defense  how long it takes to kill: race life % x (2 END + STR) x armour (race PV and DV)

and its tricks from actCombat and its tactics: caster, ranged, summoner, exploder, blinder,
paralyser, poisoner, healer, debuffer, drainer, steals (gold or items: kill it or keep away), fast, slow. The game's formulas behind it: Chara
MaxHP = (2 END + STR + WIL/2) x min(LV, 25)/25 + END + 10, x race life (Chara.cs 728); speed is the
race's SPD; PV/DV add race PV x 5 and DV x 5 % (Chara.cs 761, 790).

Groups (and what to do; elin-play's target-order rule):
  kill first  offense >= 1.25 and defense < 1.25, or any caster/summoner/blinder/paralyser:
              open on it, from range where possible (casters, archers, yeek warriors)
  avoid       offense >= 1.25 and defense >= 1.25: range only, or leave; never trade melee hits
  kill last   offense < 1.25 and defense >= 1.25: ignore it while others hit me; finish it at the end
  exploder    never adjacent: soak it Wet with a thrown potion, throw from 3+ cells (run 12)
  normal      the rest
Observed fights win over the indexes: a kind that once cost 40% of max HP in one fight is at least
"kill first", and its worst HP lost in a turn is shown.

usage: python -I tools/threat.py NAME [LV]        one creature's card (name or id)
       python -I tools/threat.py --table [LV]     every spawnable kind at level LV (default: its own)
       python -I tools/threat.py --write          knowledge/threat.csv (kb.py show prints the row)
In code: from threat import priority, profile   (delve.py picks its target with priority())
"""
import csv
import json
import re
import statistics
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "knowledge" / "game"
OUT = ROOT / "knowledge" / "threat.csv"

ATTACK_SPELL = re.compile(r"^(bolt|arrow|ball|breathe|hand|funnel|miasma|missile|sword|weapon|bit|comet|flare|puddle)_")
FLAGS = [
    ("exploder", re.compile(r"^ActSuicide$")),
    ("summoner", re.compile(r"^(SpSummon|ActSummon|ActSwarm)")),
    ("blinder", re.compile(r"(Darkness$|^SpDarkness$|^ActGazeDim$)")),
    ("paralyser", re.compile(r"(Nerve$|^ActTouchSleep$|^SongSleep$|^ActRestrain$|^ActEntangle$|^SpWeb$)")),
    ("poisoner", re.compile(r"(Poison$|poison$)")),
    ("healer", re.compile(r"^(SpHeal|SpHOT|SpRestore)")),
    ("debuffer", re.compile(r"^(SpWeak|SpSpeedDown|SpSilence|ActCurse|SpGravity|ActWeaken|ActFear|SpNightmare|SpBane|SpShutterHex|ActBurnMana|ActGaze)")),
    ("drainer", re.compile(r"^(ActBloodsuck|ActDrainBlood|ActManaAbsorb|ActGazeMana)")),
    ("thrower", re.compile(r"^(ActThrowPotion|ActThrow)$")),
    ("blinks", re.compile(r"^SpTeleport")),
    ("steals", re.compile(r"^(ActSteal|ActStealMoney|ActStealFood)$")),  # run 16: Aldnord the thief trailed me with 2,030 orens carried
]
PRIORITY_FLAGS = ("caster", "summoner", "blinder", "paralyser", "healer", "thrower", "steals")


def _rows(name):
    return json.loads((GAME / f"{name}.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def tables():
    charas = _rows("charas")
    races = {r["id"]: r for r in _rows("races")}
    jobs = {r["id"]: r for r in _rows("jobs")}
    return charas, races, jobs


def n(x, d=0):
    return d if x is None else x


def raw(c, lv=None):
    """Unnormalised offense and defense per level, and the tricks, for one chara row."""
    _, races, jobs = tables()
    r, j = races.get(c.get("race"), {}), jobs.get(c.get("job"), {})
    STR = n(r.get("STR"), 5) + n(j.get("STR"))
    END = n(r.get("END"), 5) + n(j.get("END"))
    DEX = n(r.get("DEX"), 5) + n(j.get("DEX"))
    MAG = n(r.get("MAG"), 5) + n(j.get("MAG"))
    spd = n(r.get("SPD"), 100)
    armed = bool(j.get("weapon")) and j.get("id") not in ("none", "tourist", "farmer", "pianist", "bard")
    acts = [(a.split("/")[0], int(a.split("/")[1]) if "/" in a else 50) for a in c.get("actCombat") or []]
    spell = sum(ch for a, ch in acts if ATTACK_SPELL.match(a)) / 100
    flags = {f for f, rx in FLAGS for a, _ in acts if rx.search(a)}
    if spell >= 0.25:
        flags.add("caster")
    tac = str(c.get("tactics") or "")
    if j.get("id") in ("archer", "gunner") or tac in ("archer", "turret"):
        flags.add("ranged")
    if c.get("id") in ("hardgay", "kamikaze_yeek") or "suicide" in str(c.get("trait") or "").lower():
        flags.add("exploder")
    # run 34 (the user: "That kind of adversary we should know is hard to kill with swords/melee weapons"): a vampire bat
    # (race DV 40, speed 220) took 20% a round while my axe "miserably missed"; fairies (25, 180) and the metal bells
    # (20, 300) the same. The race's DV (median 0, top 10% at 20+) marks them: fight.py opens with magic and the Putit
    dv = n(r.get("DV"))
    if dv >= 20 or (dv >= 15 and spd >= 150):
        flags.add("evasive")
    if spd >= 120:
        flags.add("fast")
    if spd <= 70:
        flags.add("slow")
    melee = (STR + DEX / 2) * (1.4 if armed else 1.0)
    magic = spell * MAG * 1.5
    off = (melee + magic) * spd / 100
    armour = 1 + n(r.get("PV")) / 20 + n(r.get("DV")) / 40
    dfn = n(r.get("life"), 100) / 100 * (2 * END + STR) * armour
    return off, dfn, sorted(flags)


@lru_cache(maxsize=1)
def medians():
    charas, _, _ = tables()
    offs, dfns = [], []
    for c in charas:
        if c.get("chance", 0) and c.get("hostility") != "Friend":
            o, d, _ = raw(c)
            offs.append(o)
            dfns.append(d)
    return statistics.median(offs), statistics.median(dfns)


@lru_cache(maxsize=1)
def observed():
    """{foe name: (fights, worst % of my max HP in a fight, worst HP lost in a turn)}"""
    out = {}
    path = ROOT / "knowledge" / "fights.csv"
    if not path.exists():
        return out
    for row in csv.DictReader(path.open(encoding="utf-8")):
        try:
            lost, turns, mx, nf = int(row["hp_lost"]), max(1, int(row["turns"])), int(row["my_maxhp"]), max(1, int(row["n_foes"]))
        except (ValueError, KeyError):
            continue
        k = row["foe"].strip().lower()
        f, pct, turn = out.get(k, (0, 0, 0))
        out[k] = (f + 1, max(pct, round(100 * lost / mx)), max(turn, round(lost / turns / nf, 1)))
    return out


def find(name):
    charas, _, _ = tables()
    w = name.strip().lower()
    for key in ("id", "name"):
        hit = [c for c in charas if str(c.get(key, "")).lower() == w]
        if hit:
            return hit[0]
    hit = [c for c in charas if w in str(c.get("name", "")).lower()]
    hit.sort(key=lambda c: (not c.get("chance"), len(c.get("name", ""))))
    return hit[0] if hit else None


def avoid(c, my_lv):
    """An avoid-group kind (high offense and defense) to range or leave, not melee: within THRESHOLDS avoid_levels of
    my level (run 17), or at any level once a recorded fight cost avoid_seen_pct of my HP (run 33: an alien Lv18 took
    32% in a round at Lv30, after run 32's 40%; 12 levels under the window both times). c: a creature dict (id/name, lv)."""
    from common import THRESHOLDS
    prof = profile(c.get("id") or c["name"]) or {}
    if prof.get("group") != "avoid":
        return False
    if c["lv"] >= my_lv - THRESHOLDS["avoid_levels"]:
        return True
    # run 43: a master 『Lizardman』 Lv19 stopped a circuit at Lv38, then died in 11 turns for 3 HP at PV 40 (weakened)
    if c["lv"] <= my_lv - THRESHOLDS["avoid_ignore_below"]:
        return False
    # only fights fought within 3 levels of mine count: run 17's 45% lizardmen were at Lv18 and cost 0-7 HP at Lv30
    worst = 0
    path = ROOT / "knowledge" / "fights.csv"
    for row in (csv.DictReader(path.open(encoding="utf-8")) if path.exists() else []):
        try:
            if row["foe"].strip().lower() == str(c["name"]).lower() and int(row["my_lv"]) >= my_lv - 3:
                worst = max(worst, 100 * int(row["hp_lost"]) // max(1, int(row["my_maxhp"])))
        except (ValueError, KeyError):
            continue
    return worst >= THRESHOLDS["avoid_seen_pct"]


def profile(name_or_row, lv=None):
    c = find(name_or_row) if isinstance(name_or_row, str) else name_or_row
    if not c:
        return None
    o, d, flags = raw(c)
    mo, md = medians()
    off, dfn = round(o / mo, 2), round(d / md, 2)
    obs = observed().get(str(c.get("name", "")).lower())
    if any(f in flags for f in ("exploder",)):
        group = "exploder"
    elif off >= 1.25 and dfn >= 1.25:
        group = "avoid"
    elif off >= 1.25 or any(f in flags for f in PRIORITY_FLAGS):
        group = "kill first"
    elif dfn >= 1.25:
        group = "kill last"
    else:
        group = "normal"
    if obs and obs[1] >= 40 and group in ("normal", "kill last"):
        group = "kill first"
    return {"id": c["id"], "name": c.get("name", c["id"]), "lv": lv or c.get("LV", 1), "race": c.get("race"),
            "job": c.get("job"), "offense": off, "defense": dfn, "flags": flags, "group": group,
            "observed": obs}


GROUP_RANK = {"exploder": 0, "kill first": 1, "normal": 2, "avoid": 3, "kill last": 4}


def priority(c):
    """Sort key for a hostile from the bridge's state (name, id, lv, dist): lowest first. Nearby
    (within 4) beats far; within that, the group, then offense per unit of defense (damage stopped
    per turn spent killing it), then distance. 'avoid' sorts after 'normal' so it isn't engaged
    first; delve.py stops on it instead of meleeing (see avoid_in_view)."""
    p = profile(c.get("id") or c.get("name", "")) if (c.get("id") or c.get("name")) else None
    if not p:
        return (0 if c.get("dist", 9) <= 4 else 1, 2, 0, c.get("dist", 9))
    ratio = p["offense"] / max(0.2, p["defense"])
    return (0 if c.get("dist", 9) <= 4 else 1, GROUP_RANK[p["group"]], -ratio, c.get("dist", 9))


def seen_specials(name):
    """The tricks the fight log saw this kind use (tools/fightlog.py: the user's special column, run 29)."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))  # python -I adds no script directory
        import fightlog
        sm = fightlog.summary().get(str(name).lower())
        return sorted(sm["specials"]) if sm else []
    except Exception:  # noqa: BLE001
        return []


def card(p):
    obs = p["observed"]
    o = f"; seen {obs[0]} fight(s): worst {obs[1]}% of my HP in a fight, {obs[2]} HP in a turn" if obs else ""
    sp = seen_specials(p["name"])
    o += f"; seen to: {', '.join(sp)}" if sp else ""
    return (f"{p['name']} [{p['id']}] Lv{p['lv']} {p['race']}/{p['job']}: offense {p['offense']}, defense "
            f"{p['defense']} -> {p['group'].upper()}" + (f"  ({', '.join(p['flags'])})" if p["flags"] else "") + o)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] in ("--table", "--write"):
        charas, _, _ = tables()
        ps = [profile(c) for c in charas if c.get("chance") and c.get("hostility") != "Friend"]
        ps.sort(key=lambda p: (GROUP_RANK[p["group"]], -p["offense"] / max(0.2, p["defense"])))
        if a[0] == "--write":
            with OUT.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["id", "name", "lv", "race", "job", "offense", "defense", "group", "flags", "observed"])
                for p in ps:
                    w.writerow([p["id"], p["name"], p["lv"], p["race"], p["job"], p["offense"], p["defense"],
                                p["group"], " ".join(p["flags"]), "" if not p["observed"] else
                                f"{p['observed'][0]} fights, worst {p['observed'][1]}%, {p['observed'][2]}/turn"])
            print(f"wrote {OUT.relative_to(ROOT)}: {len(ps)} kinds")
            return
        maxlv = int(a[1]) if len(a) > 1 else 999
        for p in ps:
            if p["lv"] <= maxlv:
                print(card(p))
        return
    p = profile(a[0], int(a[1]) if len(a) > 1 else None)
    if not p:
        sys.exit(f"no creature matches {a[0]!r}")
    print(card(p))


if __name__ == "__main__":
    main()
