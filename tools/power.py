"""The party's fighting power, from the numbers the game shows (bridge `power`: the character
sheet and the tooltips' attack evaluations) and the game's own hit and armour formulas. Foes'
stats aren't on screen, so a foe of level L is a reference built from a prior that logged
fights (knowledge/fights.csv) replace as they come in. The model: knowledge/power-model.md.

usage: python -I tools/power.py                 the power card and a danger table by foe level
       python -I tools/power.py --log RUN [--tag TAG]
                                                also append a row to runs/power.csv (session start/end;
                                                the row carries the real clock, and --tag names the
                                                activity whose edge this is: nefia, jobs, home, travel,
                                                train, build, town, mine, farm; stats.py reads both);
                                                the run's first --log also records the game version in
                                                runs/versions.csv, and a version that changed since the
                                                run before gets its own `game` row in runs/events.csv
       python -I tools/power.py fight FOE LV N TURNS HP_LOST RESULT RUN [NOTE]
                                                record a fight (N foes at once, HP I lost) for calibration
"""
import csv
import datetime as dt
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIGHTS = ROOT / "knowledge" / "fights.csv"
POWER = ROOT / "runs" / "power.csv"
VERSIONS = ROOT / "runs" / "versions.csv"
EVENTS = ROOT / "runs" / "events.csv"

# Priors for a foe of level L (hypotheses, replaced by fights.csv where it has data):
# PV and DV are L + equipment for non-allies (Chara.PV/DV); evasion adds 25 and a small skill
# curve (AttackProcess.Prepare); HP is a guess near a player's own HP at that level.
def foe_ref(lv):
    return {"evasion": 28 + 2.5 * lv, "protection": 2 + 1.5 * lv, "hp": 8 + 7 * lv}


def curve(a, start, step, rate=75):  # EClass.curve: diminishing returns past `start`
    if a <= start:
        return a
    for i in range(10):
        knee = start + i * step
        if a <= knee:
            break
        a = knee + (a - knee) * rate // 100
    return a


def hit_chance(to_hit, evasion, ranged):
    """CalcHit: 5% auto-hit, 5% auto-miss, else a miss when rnd(toHit) < rnd(evasion * 1.25
    (melee) or 1.5 (ranged))."""
    a, b = max(to_hit, 1), evasion * (150 if ranged else 125) / 100
    miss = b / (2 * a) if a >= b else 1 - a / (2 * b)
    return 0.05 + 0.90 * (1 - miss)


def after_armour(raw, protection, penetration):
    """Card.ApplyProtection: the part not passing through is cut to 100/(100+P), then a
    roll of (P/4/10+1) dice is taken off."""
    n3 = int(protection) // 4
    n = n3 // 10 + 1
    sides = n3 // n + 1
    flat = n * (sides + 1) / 2 if protection > 0 else 1
    pen = penetration / 100
    rest = raw * (1 - pen)
    return raw * pen + max(0.0, rest * 100 / (100 + protection) - flat)


def raw_damage(a):
    d = a["dNum"] * (a["dDim"] + 1) / 2 + a["dBonus"]
    if a.get("dNumAmmo"):
        d += a["dNumAmmo"] * (a["dDimAmmo"] + 1) / 2 + a["dBonusAmmo"]
    return max(0.0, d * a["dMulti"])


def per_turn(a, lv, speed):
    ref = foe_ref(lv)
    p = hit_chance(a["toHit"], ref["evasion"], a["kind"] in ("ranged", "throw"))
    return p, after_armour(raw_damage(a), ref["protection"], a["penetration"]) * p * speed / 100


def protection(c):
    return c["PV"] + c["armorSkillLv"] + c["attrs"]["DEX"] // 10


def evasion(c):
    return curve(c["attrs"]["PER"] // 3 + c["skills"].get("evasion", 0), 50, 10) + c["DV"] + 25


def foe_hit(lv, my_evasion):
    """A foe's chance to hit me. Non-allies get +250 to-hit on martial attacks (+50 with a
    weapon) in AttackProcess.Prepare, so they rarely miss; prior to-hit 200 + 5 L."""
    return hit_chance(200 + 5 * lv, my_evasion, False)


def loss_per_foe_turn(h, prot, my_evasion, lv):
    """HP one foe takes off me in a turn: its raw hit h through my armour (the flat roll
    zeroes weak hits) times its hit chance."""
    return after_armour(h, prot, 0) * foe_hit(lv, my_evasion)


def threat_fit():
    """A foe of level L hits for h = a + b L before armour. Fitted (grid search, least
    squares) to fights.csv: HP I lost per foe-turn, with (n+1)/2 foes alive on average and my
    protection then (PV + 3). The prior until 3 foe levels have data."""
    pts = []
    if FIGHTS.exists():
        for r in csv.DictReader(FIGHTS.open(encoding="utf-8")):
            try:
                n, t, lost = int(r["n_foes"]), float(r["turns"]), float(r["hp_lost"])
                lv, pv = float(r["foe_lv"]), float(r["my_pv"])
            except (ValueError, KeyError):
                continue
            if n and t:
                pts.append((lv, pv + 3, lost / ((n + 1) / 2 * t)))
    if len({q[0] for q in pts}) < 3:
        return 3.0, 1.0, len(pts), "prior"
    best = None
    for ai in range(0, 81):
        a = ai * 0.25
        for bi in range(0, 61):
            b = bi * 0.05
            err = sum((loss_per_foe_turn(a + b * lv, prot, 40, lv) - obs) ** 2 for lv, prot, obs in pts)
            if best is None or err < best[0]:
                best = (err, a, b)
    return best[1], best[2], len(pts), "fit"


SOLO_FROM = 5  # Kaberg stays home from run 05 on: earlier fights had her drawing hits


def species(foe, n):
    """'Yeek warrior (special)' -> 'yeek warrior'; None for mixed groups (ambushes, dens)."""
    if any(s in foe for s in ("+", ",", "ambush", "den ", "summons")):
        return None
    name = re.sub(r"\(.*?\)", "", foe).lower()
    name = " ".join(w for w in name.split() if w not in ("boss", "special", "two", "three"))
    return name[:-1] if n > 1 and name.endswith("s") else name


def observed_threats():
    """The fight log by foe kind (solo fights): the level-only fit averages over kinds, but
    the damage is in a few of them (yeek warriors, drones, kobolds, kamikazes, casters)."""
    kinds = defaultdict(list)
    if FIGHTS.exists():
        for r in csv.DictReader(FIGHTS.open(encoding="utf-8")):
            try:
                if int(r["run"]) < SOLO_FROM:
                    continue
                n, t, lost, lv = int(r["n_foes"]), float(r["turns"]), float(r["hp_lost"]), int(r["foe_lv"])
            except (ValueError, KeyError):
                continue
            name = species(r["foe"], n)
            if name:
                kinds[name].append((lv, lost, lost / max(t, 1)))
    rows = sorted(kinds.items(), key=lambda kv: -max(x[1] for x in kv[1]))
    return rows


def qty(card):
    """A slot's stack size from its card name ("14 scrolls of evacuation" -> 14, "blessed 3 ..." -> 3)."""
    m = re.match(r"(?:\w+ )?(\d+) ", card or "")
    return int(m.group(1)) if m else 1


def kit():
    """The escape kit: the top-level inventory (`inv`) plus every open carried bag's grid (run 20:
    2 evacuation scrolls bought with 14 already in the backpack, which `inv` doesn't list). A bag
    counts while its window is open: in the `buttons all=True` listing, a slot with a card,
    "ButtonGrid inventory" in its name, mine, whose container (`in`) isn't the pack (an older mod
    without `in`: a path other than the pack's own "UIInventory/List"). `bags_counted` says whether
    any bag grid was seen, so a caller (ladder.py) can say "backpack not counted" instead of
    trusting a low number. The keys the card and the power.csv row read are unchanged."""
    items = [(i["name"], i["num"]) for i in call("inv")["data"]["items"]]
    grid = []
    bags = False
    heal_casts = 0
    try:
        for b in call("buttons", all=True)["data"]["buttons"]:
            # run 25: the heal that carried the Dangerous Ruin was the Cure Minor Wound spell (~12 HP for
            # 5 MP a cast; 90 -> 166 for 33 MP) while the kit counted one potion and no rod charge: a cast
            # is a heal too, bounded by the spell's stock (the ability button's number) and the MP in hand
            if "ButtonAbility" in (b.get("name") or "") and (b.get("card") or b.get("text") or "") == "Cure Minor Wound":
                # the button's "text" is the spell's stock ({"text": "27", "card": "Cure Minor Wound"})
                try:
                    stock = int(str(b.get("text") or "0").strip() or 0)
                except (TypeError, ValueError):
                    stock = 0
                mp = int((call("state")["data"].get("pc") or {}).get("mp") or 0)
                heal_casts = min(stock, mp // 5) if stock else mp // 5
            if not b.get("card") or "ButtonGrid inventory" not in (b.get("name") or ""):
                continue
            path = b.get("path") or ""
            mine = b["mine"] if "mine" in b else "UIInventory/List" in path
            in_pack = b["in"] == "pack" if "in" in b else "UIInventory/List" in path
            if not mine or in_pack:
                continue
            bags = True
            grid.append((b["card"], qty(b["card"])))
    except Exception:  # noqa: BLE001 - the bag count never stops the card; inv alone is the old reading
        pass
    if not heal_casts:
        # run 57: Cure Minor Wound's stock out, Cure Critical Wound's 121 casts unseen ("heal casts: 0"): cure.py casts
        # the heavier spells now, so they count, by the MP in hand at about 15 a cast
        try:
            spells = {sp["spell"]: sp["stock"] for sp in call("power")["data"]["party"][0].get("spells") or []}
            mp = int((call("state")["data"].get("pc") or {}).get("mp") or 0)
            for alias, cost in (("SpHealTouch", 5), ("SpHealHeavy", 10), ("SpHealCritical", 15)):
                if spells.get(alias, 0) > 0:
                    heal_casts = min(spells[alias], mp // cost)
                    break
        except Exception:  # noqa: BLE001
            pass
    # run 40: only an open bag's window counted: unclutter had moved 7 evacuation scrolls into the spoils bag, the backpack alone
    # was open, and the ladder refused "no scroll of evacuation" at Traditional Cave's door. `stock` reads every carried bag
    try:
        rows = [(s["name"], s.get("num") or 1) for it in call("stock")["data"].get("pack") or []
                if it.get("items") is not None and not it.get("equipped") for s in it["items"]]
        items.extend(rows)
        bags = bags or bool(rows)
    except Exception:  # noqa: BLE001 - an older mod without `stock`: the open windows' reading
        items.extend(grid)
    if not heal_casts:  # run 34: a spell read from a book has no hotbar button; cure.py casts it through the cast op
        try:
            stock = {s["spell"]: s["stock"] for s in call("power")["data"]["party"][0].get("spells") or []}.get("SpHealLight", 0)
            if not stock:  # run 34: Healing Touch counts too (cure.py casts it when Cure Minor Wound is spent)
                stock = {s["spell"]: s["stock"] for s in call("power")["data"]["party"][0].get("spells") or []}.get("SpHealTouch", 0)
            if stock:
                mp = int((call("state")["data"].get("pc") or {}).get("mp") or 0)
                heal_casts = min(stock, mp // 5)
        except Exception:  # noqa: BLE001 - the count never stops the card
            pass

    def count(*words):
        return sum(n for name, n in items if all(w in name.lower() for w in words))

    def evac_casts():
        # run 34: 20 MP a cast, and one of the first two failed: the MP in hand bounds the count
        try:
            stock = {x["spell"]: x["stock"] for x in call("power")["data"]["party"][0].get("spells") or []}.get("SpEvac", 0)
            mp = int((call("state")["data"].get("pc") or {}).get("mp") or 0)
            return min(stock, mp // 40)
        except Exception:  # noqa: BLE001 - the count never stops the card
            return 0
    status = [name for name, n in items if "potion of" in name.lower() and any(
        w in name.lower() for w in ("confusion", "blind", "sleep", "paralys", "poison"))]
    # run 21: subtracting every "short teleport" (the rod and the spellbook too) showed 3 of 6 scrolls
    def charges(kind):
        return sum(int(m.group(1)) for name, n in items if kind in name.lower()
                   for m in [re.search(r"\((\d+) Charges?\)", name)] if m)
    # run 24: a rod of teleport zapped at myself is a teleport (fight.py's emergency_teleport uses one)
    return {"teleport": count("scroll", "teleport") - count("scroll", "short teleport") + charges("rod of teleport"),
            "short teleport": count("short teleport"), "return": count("scroll", "return"),
            # ladder.py's kit check (the review of 2026-10-23); run 34: evac.py casts the Evacuation spell when no scroll
            # is in the pack, so its casts count (the scrolls ran out after twelve conquests with 31 casts in stock)
            "evacuation": count("scroll", "evacuation") + evac_casts(),
            # run 32: "cure potions" counted 14 potions of cure mutation while the cure wound ones were gone
            "cure potions": count("potion", "cure") - count("potion", "cure mutation"), "bandages": count("bandage"),
            # run 24: Ether Hand turns picked-up potions bad and Potion Addict drinks them (facts #845,
            # #846): the healing rods' charges are the heals that keep (one charge, one heal)
            "cure rod charges": sum(int(m.group(1)) for name, n in items if "rod of cure" in name.lower()
                                    for m in [re.search(r"\((\d+) Charges?\)", name)] if m),
            "heal casts": heal_casts,  # run 25: Cure Minor Wound casts the MP in hand pays for
            "status throwables": ", ".join(status), "bags_counted": bags}


# G41 (the user, 2026-11-01): my melee from 22.8 to 30 a turn against a fixed Lv33 foe, so a level-up doesn't move it
G41_LV = 33


def my_melee_vs(c, lv_ref):
    return max((per_turn(a, lv_ref, c["speed"])[1] for a in c["attacks"] if a["kind"] in ("melee", "martial")), default=0)


def card(c, lv_ref):
    prot, eva = protection(c), evasion(c)
    print(f"{c['name']} Lv{c['lv']}  HP {c['hp']}/{c['maxHp']}  speed {c['speed']}  PV {c['PV']} DV {c['DV']}"
          f"  protection {prot}  evasion {eva}" + (f"  element {c['mainElement']}" if c.get("mainElement") else ""))
    best = {}
    for a in c["attacks"]:
        p, dpt = per_turn(a, lv_ref, c["speed"])
        tag = a["kind"] + (" x" + str(a["num"]) if a["kind"] == "throw" else "")
        els = (" " + ", ".join(a["elements"])) if a["elements"] else ""
        ammo = f" + {a['ammo']}" if a.get("ammo") else (" (no ammo loaded: shots add the arrow's dice)" if a["kind"] == "ranged" else "")
        print(f"   {a['weapon'][:34]:34} {tag:9} {a['attackType']:7}{els}  {a['eval'] or ''}{ammo}")
        print(f"   {'':34} hit {p:4.0%} vs Lv{lv_ref}, {dpt:4.1f} a turn")
        if a["kind"] != "throw" or a["num"] >= 5:
            best[a["kind"]] = max(best.get(a["kind"], 0), dpt)
    if c["resists"]:
        print("   resists: " + ", ".join(f"{k[3:]} {v}" for k, v in c["resists"].items()))
    if c["spells"]:
        print("   spells: " + ", ".join(f"{s['spell']} ({s['stock']})" for s in c["spells"]))
    return prot, eva, best


SPELL_ELEMENT = {"Fire": "fire", "Cold": "cold", "Lightning": "lightning", "Darkness": "darkness",
                 "Mind": "mind", "Poison": "poison", "Nether": "nether", "Sound": "sound", "Nerve": "nerve",
                 "Holy": "holy", "Chaos": "chaos", "Magic": "magic", "Acid": "acid", "Cut": "cut", "Impact": "impact"}


def damage_types(party, status=""):
    """Physical attack types, elements (weapon enchants, natural element, spells with stock)
    and status throwables: more kinds means fewer foes that shrug everything off (the hermit
    crab's shell stopped the sword; Putit In Amber's lightning worked)."""
    phys, elem = set(), set()
    for c in party:
        for a in c["attacks"]:
            phys.add(a["attackType"])
            elem.update(e.split()[0].replace("ele", "").lower() for e in a["elements"])
        if c.get("mainElement"):
            elem.add(c["mainElement"].replace("ele", "").lower())
        for sp in c["spells"]:
            if sp["stock"]:
                elem.add(SPELL_ELEMENT.get(sp["spell"].split("_")[-1], sp["spell"]))
    out = {"physical": sorted(phys), "elements": sorted(elem)}
    if status:
        out["status"] = [status]
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if args and args[0] == "fight":
        foe, lv, n, turns, lost, result, run = args[1:8]
        note = " ".join(args[8:])
        me = [c for c in call("power")["data"]["party"] if c["pc"]][0]
        date = call("state")["data"]["pc"]["date"].split()[0]
        # run 29: fight.py logs every fight itself (fightlog.Tracker); this hand entry is for a fight it didn't run
        # (a spell or bow fight, an ambush handled by hand), through the same writer and header
        import fightlog
        fightlog.record({"run": run, "game_date": date, "my_lv": me["lv"], "my_pv": me["PV"], "my_maxhp": me["maxHp"],
                         "foe": foe, "foe_lv": lv, "n_foes": n, "turns": turns, "hp_lost": lost, "result": result,
                         "note": note, "source": "power.py fight"})
        print(f"recorded: {foe} Lv{lv} x{n}, {turns} turns, lost {lost} HP, {result}")
        return
    d = call("power")["data"]
    party = d["party"]
    me = [c for c in party if c["pc"]][0]
    lv = me["lv"]
    print(f"Power card {d['date']}  (model: knowledge/power-model.md; foe stats are priors or fits)")
    stats = {}
    for c in party:
        stats[c["name"]] = card(c, lv)
    prot, eva, best = stats[me["name"]]
    a, b, n_pts, how = threat_fit()
    k = kit()
    types = damage_types(party, k["status throwables"])
    print("damage types: " + "; ".join(f"{key} {', '.join(v)}" for key, v in types.items()))
    print(f"escape kit: teleport {k['teleport']}, short teleport {k['short teleport']}, return {k['return']},"
          f" evacuation {k['evacuation']}; cure potions {k['cure potions']}, bandages {k['bandages']}"
          + ("" if k["bags_counted"] else " (no bag window open: the backpack not counted)"))
    from common import empty_slots  # the user's full-set rule (run 29)
    gaps = empty_slots()
    print("gear slots: " + ("all filled" if not gaps else "EMPTY: " + ", ".join(gaps)))
    melee = sum(max(v[2].get("melee", 0), v[2].get("martial", 0)) for v in stats.values())
    ranged = best.get("ranged", 0)
    ehp = me["maxHp"] * (100 + prot) / 100
    print(f"threat model ({how}, {n_pts} fights): a level-L foe hits for {a:.1f} + {b:.2f} L before armour"
          f" (Kaberg present in most fights); my armour turns a 5 into {after_armour(5, prot, 0):.1f}, a 10 into"
          f" {after_armour(10, prot, 0):.1f}")
    print(f"party melee {melee:.1f} a turn, my bow {ranged:.1f} a turn (vs Lv{lv}); effective HP {ehp:.0f}")
    vs_fixed = my_melee_vs(me, G41_LV)
    print(f"my melee vs Lv{G41_LV} (G41's yardstick: 30 a turn): {vs_fixed:.1f}")
    # run 42: the line above leaves out crits, flurry, vorpal and weapon elements, and an artifact with all of them sat unread; for choosing gear, gearcompare.py and elin-gear
    try:
        from gearcompare import row as full_row
        print(f"with crits, flurry and enchants vs Lv{G41_LV}: {full_row(me, G41_LV, 1.0, 1.0, 0, 1.0)['turn']:.1f} a turn; armour x4: {full_row(me, G41_LV, 4.0, 1.0, 0, 1.0)['turn']:.1f} (gearcompare.py)")
    except Exception as e:  # noqa: BLE001 - a card must print whatever this does
        print(f"(gearcompare's line: {e})")
    print("\n foe Lv | turns to kill one | HP I lose: 1 foe   3 at once   6 at once   (60% floor = lose < 40%)")
    hp = me["maxHp"]

    def sustained(c, L):  # weapons, the bow and throwables I carry 5+ of; not one-off throws
        opts = [x for x in c["attacks"] if x["kind"] != "throw" or x["num"] >= 5]
        return max(per_turn(x, L, c["speed"])[1] for x in opts)

    for L in sorted({max(1, lv - 3), lv - 1, lv, lv + 2, lv + 3, lv + 5}):
        dpt = sum(sustained(c, L) for c in party)
        ttk = foe_ref(L)["hp"] / max(dpt, 0.1)
        thr = loss_per_foe_turn(a + b * L, prot, eva, L)
        row = []
        for n in (1, 3, 6):
            lost = thr * ttk * n * (n + 1) / 2  # foes die one at a time; all n engage at once
            row.append(f"{lost:5.0f} ({min(lost / hp, 9.99):4.0%}){'!' if lost >= 0.4 * hp else ' '}")
        print(f"  {L:5} | {ttk:17.1f} | " + "  ".join(row))
    print(" ! = past the 60% floor: fight those only from range, or leave (teleport).")
    # run 16 (the user: "threat models are not linear"): this one-line-by-level model predicted the
    # median recorded fight 50x too high and missed the exploders; decisions use threat.py per kind
    print(" (advice only: the level line overstates ordinary foes ~50x; `threat.py NAME` decides per kind, knowledge/risk.md)")
    threats = observed_threats()
    print(f"\n observed, solo fights since run {SOLO_FROM:02} (fights.csv), worst first; % of today's max HP {hp}")
    print(" foe kind              fights  levels  HP lost: typical  worst        worst a turn")
    for name, xs in threats:
        losses = sorted(x[1] for x in xs)
        worst = losses[-1]
        lvs = sorted({x[0] for x in xs})
        lv_txt = f"{lvs[0]}-{lvs[-1]}" if len(lvs) > 1 else str(lvs[0])
        print(f"  {name[:20]:20} {len(xs):6}  {lv_txt:6}  {losses[len(losses) // 2]:7.0f} ({losses[len(losses) // 2] / hp:4.0%})"
              f"  {worst:4.0f} ({worst / hp:4.0%}){'!' if worst >= 0.4 * hp else ' '}  {max(x[2] for x in xs):6.1f}")
    bad = [name for name, xs in threats if max(x[1] for x in xs) >= 0.4 * hp]
    print(f" ! = one fight cost 40%+ of today's HP: {len(bad)} of {len(threats)} kinds. Open on these from range,"
          " drink at 70%, and leave when two of them close in, whatever the table above says.")
    if "--log" in args:
        run = args[args.index("--log") + 1]
        # --tag (the review of 2026-10-23): which activity's edge this row is; with logged_at (the
        # real clock) stats.py turns consecutive rows into exp and orens per real hour
        tag = args[args.index("--tag") + 1] if "--tag" in args and args.index("--tag") + 1 < len(args) else ""
        kab = [c for c in party if not c["pc"]]
        pc = call("state")["data"]["pc"]  # exp, karma and gold for the run tracker (tools/stats.py, run 14)
        new = not POWER.exists()
        with POWER.open("a", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            if new:
                w.writerow(["run", "game_date", "lv", "max_hp", "pv", "dv", "protection", "evasion", "ehp",
                            "melee_per_turn", "bow_per_turn", "damage_types", "teleport", "cure_potions",
                            "pet_lv", "pet_max_hp", "threat_model", "speed", "exp", "exp_next", "karma", "gold",
                            "logged_at", "tag", "my_melee", "my_melee_vs33"])
            w.writerow([run, d["date"].split()[0], lv, me["maxHp"], me["PV"], me["DV"], prot, eva, round(ehp),
                        round(melee, 1), round(ranged, 1), len(types["physical"]) + len(types["elements"]), k["teleport"],
                        k["cure potions"], kab[0]["lv"] if kab else "", kab[0]["maxHp"] if kab else "",
                        f"{how} {a:.1f}+{b:.2f}L n={n_pts}", me["speed"], pc.get("exp", ""),
                        pc.get("expNext", ""), pc.get("karma", ""), pc.get("gold", ""),
                        dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tag,
                        # run 37's close: melee_per_turn is the party's sum, so an ally hid my own fall
                        # from ~24 to ~9.5 a turn (a shield in the off hand since run 30) for seven runs
                        round(max(best.get("melee", 0), best.get("martial", 0)), 1), round(vs_fixed, 1)])
        print(f"logged to {POWER.relative_to(ROOT)}" + (f" (tag {tag})" if tag else ""))
        note_version(run)


def note_version(run):
    """runs/versions.csv: the game version each run played on, written once a run; a change since the run before also
    writes a `game` row in runs/events.csv, which stats.py and the tracker mark (the user, run 58: "in the larger tracking
    system we mark the game update (in case of an unusual number of fixes or other events)")."""
    import json
    from kb import INSTALL_VERSION
    if not INSTALL_VERSION.exists():
        print(f"game version: not recorded ({INSTALL_VERSION} is missing)")
        return
    v = json.loads(INSTALL_VERSION.read_text(encoding="utf-8-sig"))
    text, built = v.get("versionText") or v.get("version") or "?", (v.get("buildDate") or "")[:10]
    rows = []
    if VERSIONS.exists():
        with VERSIONS.open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
    if any(r["run"] == run for r in rows):
        return
    new = not VERSIONS.exists()
    with VERSIONS.open("a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        if new:
            w.writerow(["run", "version", "build_date", "channel"])
        w.writerow([run, text, built, v.get("channel") or ""])
    before = rows[-1] if rows else None
    print(f"game version: {text} (build {built}), recorded for run {run}")
    if before and before["version"] != text and EVENTS.exists():
        with EVENTS.open(encoding="utf-8", newline="") as fh:
            evs = list(csv.DictReader(fh))
        gid = f"G{sum(1 for e in evs if e['kind'] == 'game') + 1}"
        with EVENTS.open("a", encoding="utf-8", newline="") as fh:
            csv.writer(fh, lineterminator="\n").writerow(
                [gid, before["run"], built, "game", f"Game update {before['version']} -> {text}", "", "", "",
                 f"run {run} is the first on {text}; what it changed for play goes here"])
        print(f"  the game changed since run {before['run']} ({before['version']}): {gid} in runs/events.csv; write what it "
              "changed for play in its note, and rebuild the graph (kb.py build)")


if __name__ == "__main__":
    main()
