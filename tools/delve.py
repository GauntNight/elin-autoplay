"""Work through a dungeon floor with the run 04 rules (elin-play: HP decides, not the count):
explore, and when a hostile shows up, fight it if it is at or below my level, loot, go on.
Hands control back as soon as a decision is mine, with exit 3 and a "stop: ..." line (the
review of 2026-10-23: every decision stop used to exit 0 and ladder.py parsed the text):
  - my HP under 70% (THRESHOLDS dungeon_hp: drink, or teleport if still under 50%)
  - Kaberg under 50% (heal.py) or not in the party
  - a hostile above my level, or 3+ at or above it in view (weak crowds are fine)
  - a swarm: 6+ hostiles in view, or 4+ with one at or above my level (THRESHOLDS swarm)
  - a window or dialog, blindness, a task still running, Hungry, Overweight (common.ready)
  - fight.py, shoot.py or throw.py stopping (rc 3) or refusing (rc 1)
Exit 0 with its own line for the floor's natural ends: "stop: stairs found", "stop: floor
explored", "stop: step limit". After one of those the corpses are butchered and the floor
looted (butcher_when_safe); after a refused floor or a decision stop nothing is looted (run 17:
loot.py walked an underwater floor the gate had refused).
Never rests or waits (the user's rule: no idling in a dungeon).

usage: python -I tools/delve.py [STEPS=8] [--solo] [--expendable] [--max-danger N] [--force] [--breathe]
  --solo  Kaberg stays home (run 04: she runs ahead into the dark and falls; solo at danger 2
          I take almost nothing with PV 27 and Taunt): don't stop for her absence
  --expendable  an ally along as a meat shield (the user, run 16: "if they die they just come back
          in a week"; Zone.Revive brings a dead member home within 0-7 days): her HP and her death
          don't stop the delve. Turn on the Strategy tab's "Always stay by you while in combat"
          (dontWander) first, and remember a scroll of teleport leaves her behind.
  --max-danger N / --force  the floor gate (MAX_DANGER, the thresholds table's max_danger)
  --breathe  an underwater floor, only with water breathing in hand (the user, run 17)
Targets come from tools/threat.py (the user, run 16: casters and high damage first, high defense
last): a kind in its "avoid" group within 8 levels of mine (4 until run 17) stops the delve instead of a melee.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import THRESHOLDS, cells, last, named, pick, ready, run, stop, wait_idle, wait_until  # noqa: E402
import threat  # noqa: E402

SOLO = "--solo" in sys.argv
EXPENDABLE = "--expendable" in sys.argv
HP_FLOOR = THRESHOLDS["dungeon_hp"]
# run 15: raised at Lv16 after a danger-7 extermination cleared with no drink (run 12: danger 8 B1
# fine at Lv12, danger 9 B2 cost 91 HP in one blast); the number lives in the thresholds table now
MAX_DANGER = THRESHOLDS["max_danger"]
EVOLVED_SKIPPED = set()  # run 34: neutral Evolved creatures far above me, left alone
# set after a normal step, cleared by every decision stop: the finally loots only when it is set
SAFE_TO_LOOT = False

# The potions that soak a suicide attacker (ConWet: GoalCombat skips "suicide" while wet), by their
# full names (the review of 2026-10-23: the fragments "of slow" / "of silence" also matched the
# kit's rod of slow and rod of silence, so throw.py could have thrown a rod)
SOAK = ("potion of blindness", "potion of confusion", "potion of slow", "potion of silence",
        "potion of paralysis", "cloudy potion", "pale potion",
        # run 24: Ether Hand (fact #845) turns bought cure potions into unidentified negative ones
        "gluey potion", "murky potion", "spotted potion",
        # run 41 (three blasts of 46-77%, no soak potion in the pack: purge drops them): any thrown potion wets; 31 cure minors ride along
        "potion of cure minor wound")


def inv_items():
    return call("inv")["data"]["items"]


def inv_names():
    """The pack's item names in one string (was a bridge.py subprocess per fight, run 12 review)."""
    return " ".join(i["name"] for i in inv_items())


def party(s):
    """The party without me: state.party (bridge 0.30.0), else power's list minus its pc flag
    (the review of 2026-10-23: the filter was the literal character name before)."""
    if isinstance(s.get("party"), list):
        return s["party"]
    return [m for m in call("power")["data"]["party"] if not m.get("pc")]


def status():
    s = call("state")["data"]
    p = s["pc"]
    foes = [c for c in s.get("nearby") or [] if c.get("hostile")]
    kab = party(s)
    kab_seen = any("Kaberg" in c["name"] for c in s.get("nearby") or [])
    return s, p, foes, kab, kab_seen


def swarm(foes, lv, total=None):
    """The thresholds table's swarm rule, one copy for delve and hunt: 6+ hostiles in view, or
    4+ with one at or above my level, is the reason to teleport and leave (else None). `total` is
    state.threat.hostiles (bridge 0.30.0, no radius cap) when the mod reports it; `foes` is the
    nearby list (12 cells)."""
    counted = [c for c in foes if (c.get("lv") or 0) > lv - THRESHOLDS["swarm_weak_below"]]
    # run 21: twelve Lv4-8 foes at Machinarium B3 took 140 -> 106 and passed the full exclusion: far
    # weaker ones count half (12 of them make 6, a swarm; run 21's crowds of 6-7 make 3)
    # run 43: 25+ levels under mine (twelve Lv4 geese at Lv37) don't count at all
    tiny = sum(1 for c in foes if (c.get("lv") or 0) <= lv - THRESHOLDS["swarm_ignore_below"])
    n = len(counted) + (len(foes) - len(counted) - tiny) // 2 + max(0, (total or 0) - len(foes))
    above = sum(1 for c in foes if (c.get("lv") or 0) >= lv)
    if n >= THRESHOLDS["swarm"] or (n >= THRESHOLDS["swarm_above"] and above):
        weak = len(foes) - len(counted)
        return (f"swarm: {n} hostiles in view, {above} at or above my level"
                + (f" ({weak} far weaker counted half)" if weak else "") + ": teleport and leave")
    return None


def check(s, p, foes, kab, kab_seen):
    # run 14: a master yeek's darkness bolt blinded me and the fight loop spent 15 turns on "no
    # Attack act" (an unseen foe can't be targeted, and a step into its cell doesn't attack)
    if "ConBlind" in (p.get("conditions") or []):
        return "blind: no targeting or reading; step away from the foe until it clears (drink at 70%)"
    # the shared precondition (common.ready): a window or dialog, a task still running, a bad
    # condition, HP under the dungeon floor, Hungry (rule zero), Overweight, the world map. The
    # hostiles themselves are delve's business, so the hostile check is switched off (hostile_r=-1).
    why = ready(s, hp=HP_FLOOR, hunger=THRESHOLDS["hungry"], hostile_r=-1)
    if why:
        return why + (f": drink (teleport if under {THRESHOLDS['teleport_hp']}% after)" if why.startswith("HP") else "")
    for m in kab:
        # --solo: a pet that tagged along (run 07: a snow putit from a New Year's gift) doesn't stop me
        # run 28: Kaberg left a floor behind (in the party, not in view) stopped every delve: heal.py can't reach her
        here = any(c.get("party") and c.get("name") == m["name"] for c in s.get("nearby") or [])
        if m["hp"] * 100 < 50 * m["maxHp"] and (not SOLO or m["name"] == "Kaberg") and not EXPENDABLE and here:
            return f"{m['name']} HP {m['hp']}/{m['maxHp']} under 50%: heal.py"
    # run 46: solo is the default since run 38 (the user, 2026-11-01), and with the snow putit left at home an empty party
    # stopped the circuit on its first floor with "Kaberg is not in the party" (the old stop here): an empty party is a
    # solo run now, whether or not --solo was passed
    # run 16 (the user): high offense and high defense together is a kind to avoid, not trade hits with
    # run 17: two Lv12 lizardmen (avoid) took 45% of my HP in two turns at Lv18: within 8 levels now
    # run 33: or at any level once its record holds a fight that cost 30% (threat.avoid)
    tough = [c for c in foes if c["dist"] <= 6 and threat.avoid(c, p["lv"])]
    if tough:
        return "avoid-group foe (high offense and defense, threat.py): " + ", ".join(f"{c['name']} Lv{c['lv']} d{c['dist']}" for c in tough) + ": range it or leave"
    above = [c for c in foes if c["lv"] > p["lv"]]
    if above:
        return "foe above my level: " + ", ".join(f"{c['name']} Lv{c['lv']} d{c['dist']}" for c in above)
    sw = swarm(foes, p["lv"], (s.get("threat") or {}).get("hostiles"))
    if sw:
        return sw
    # HP decides, not the count (the user, run 04): weak foes in numbers are fine while HP holds
    strong = [c for c in foes if c["lv"] >= p["lv"]]
    if len(strong) >= 3:
        return f"{len(strong)} hostiles at or above my level in view"
    return None


# Target order (the user, run 06): fragile high-damage foes first (casters, archers, potion
# throwers), hard-to-kill ones last; distance breaks ties, and nothing far beats something close.
FRAGILE = ("wizard", "shaman", "mage", "master yeek", "archer", "gnome", "priest", "witch",
           "sorcerer", "warlock", "drone")
TANKY = ("slime", "putit", "golem")


def priority(c):
    """threat.py's profile (run 16) first; the old keyword ranks only for a kind it doesn't know."""
    if threat.profile(c.get("id") or c["name"]):
        return threat.priority(c)
    n = c["name"].lower()
    rank = 0 if any(w in n for w in FRAGILE) else 2 if any(w in n for w in TANKY) else 1
    return (0 if c["dist"] <= 4 else 1, rank, 0, c["dist"])


def floor_gate():
    """Refuse a floor above the measured limit unless --max-danger N or --force says so (the
    history review: the limit used to be raised after each incident instead of checked before).
    Called before main's try/finally, so a refused floor is never looted."""
    limit = MAX_DANGER
    if "--max-danger" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--max-danger") + 1])
    z = call("state")["data"].get("zone") or {}
    # run 17 (the user: "you can't do those kinds of dungeons"): an underwater nefia suffocates
    # (ConSuffocation) every turn on top of the fight: 112 -> 20 HP on B1 of a danger 4 one.
    # --breathe only once water breathing is in hand (the user's next question: what gives it)
    underwater = z["underwater"] if "underwater" in z else "water" in str(z.get("full") or "").lower()
    if underwater and "--breathe" not in sys.argv:
        stop(f"{z.get('full')} is an underwater dungeon: suffocation (the user, run 17); --breathe only with water breathing")
    if z.get("nefia") and (z.get("danger") or 0) > limit and "--force" not in sys.argv:
        stop(f"this floor is danger {z.get('danger')}, over the limit {limit} (--max-danger N or --force to go on; the rule: go back up)")


STALL = {"turn": 0, "hp": 0, "uid": None}  # run 45: fight steps that changed nothing


def halt(msg):
    """A decision stop (exit 3): nothing is looted after it."""
    global SAFE_TO_LOOT
    SAFE_TO_LOOT = False
    stop(msg)


def step_away(t):
    """Open the distance to a suicide attacker before the soak (THRESHOLDS kamikaze_dist: throw
    from 3 cells, never adjacent): up to two steps straight away from it, onto free dry cells
    only. Returns its distance after (99 when it is out of view)."""
    for _ in range(2):
        if t["dist"] >= THRESHOLDS["kamikaze_dist"]:
            break
        p = call("state")["data"]["pc"]
        sx = -1 if t["dx"] > 0 else 1 if t["dx"] < 0 else 0
        sz = -1 if t["dz"] > 0 else 1 if t["dz"] < 0 else 0
        opts = [(sx, sz), (sx, 0), (0, sz)] if sx and sz else [(sx, sz), (sx, 1), (sx, -1)] if sx else [(sx, sz), (1, sz), (-1, sz)]
        info = cells([(p["x"] + dx, p["z"] + dz) for dx, dz in opts])
        moved = False
        for dx, dz in opts:
            c = info.get((p["x"] + dx, p["z"] + dz)) or {}
            if c.get("blocked") or c.get("water") or not c.get("floor") or c.get("things"):
                continue
            call("step", dx=dx, dz=dz)
            wait_until("frames", n=5)
            moved = True
            break
        if not moved:
            break
        s = call("state")["data"]
        t2 = next((c for c in s.get("nearby") or [] if c.get("uid") == t.get("uid")), None)
        if not t2:
            return 99
        t = t2
    return t["dist"]


def main():
    global SAFE_TO_LOOT
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    argv = sys.argv[1:]
    nums = [a for i, a in enumerate(argv) if a.isdigit() and (i == 0 or argv[i - 1] != "--max-danger")]
    steps = int(nums[0]) if nums else 8
    party_seen, dead_said = None, set()
    for k in range(1, steps + 1):
        wait_idle(5000)  # a pick-up or a step from the last tool still running (ready() says busy)
        s, p, foes, kab, kab_seen = status()
        # run 18 (errors row 33): the pet died and nothing said so; the party list shrinking, or
        # allyDead (bridge 0.30.0) naming someone, is printed once
        names = {m["name"] for m in kab}
        if party_seen is not None and party_seen - names:
            print(f"[{k}] party: {', '.join(sorted(party_seen - names))} no longer in the party")
        party_seen = names
        for n in s.get("allyDead") or []:
            if n not in dead_said:
                dead_said.add(n)
                print(f"[{k}] ally dead: {n} (Zone.Revive brings a member home within a week; its corpse stays here)")
        why = check(s, p, foes, kab, kab_seen)
        if why:
            halt(why)
        if (s.get("layers") or {}).get("top") == "LayerShippingResult":
            # run 22: the 05:00 shipping report ended a ladder floor (common.ready closes it; this
            # loop reads the state itself): only a report, the income is already paid
            call("closetop")
            continue
        if (s.get("layers") or {}).get("top"):
            halt(f"window open ({s['layers']['top']})")
        # run 33 (the user: "add that to our dungeon crawl so we collect special genes from these mobs"): an Evolved
        # creature carries its gene, and a superior gene half the time (Zone.TryGenerateEvolved); they're often neutral,
        # so delve walked past them. At or below my level it's a foe; above, the ladder stops for a hand decision (run 33:
        # an Evolved Scorpion Lv34 at Lv31 died to the crew for 14 HP, gene and superior gene dropped)
        for c in s.get("nearby") or []:
            if "evolved" in c["name"].lower() and not c.get("party"):
                # run 34: a neutral Evolved Beetle Lv44 at my Lv31 stopped the ladder; fight.py refuses 3+ levels above and
                # a neutral one doesn't attack, so one that far above and not hostile is walked past (said once a floor)
                # run 37: a neutral Evolved Goblin Wizard Lv36 (offense 1.28) at my Lv33 took 44% in one round with
                # Holy Shield and Hero up and the stalker beside me: a hard hitter above my level is walked past too
                hard =(threat.profile(c.get("id") or c["name"]) or {}).get("offense", 0) >= 1.0
                if (c["lv"] > p["lv"] + 3 or (hard and c["lv"] > p["lv"])) and not c.get("hostile"):
                    if c.get("uid") not in EVOLVED_SKIPPED:
                        EVOLVED_SKIPPED.add(c.get("uid"))
                        print(f"  left alone: {c['name']} Lv{c['lv']} (neutral, {c['lv'] - p['lv']} levels above me)")
                    continue
                if c["lv"] > p["lv"]:
                    halt(f"{c['name']} Lv{c['lv']} d{c['dist']} is Evolved (its gene, a superior one half the time) and "
                         "above my level: decide by hand (QuickSave, buffs, fight.py NAME 70 --force with the crew)")
                if c not in foes:
                    foes.append(c)
        if foes:
            t = min(foes, key=priority)
            tname = t["name"].split(" ", 1)[-1] if t["name"].startswith(("a ", "an ")) else t["name"]
            # A kamikaze yeek explodes when adjacent unless Wet: soak it with a thrown potion first
            # (GoalCombat skips "suicide" while ConWet; run 04: one blew me from 44 to 26 HP).
            # run 12: a "hot guy" (id hardgay, Lv10, ActSuicide) exploded beside me: 100 -> 9 HP and
            # burned a rod, the sleeping bag and two scrolls; treat every suicide attacker alike
            # run 24: a bomb rock (an exploder by threat.py, Lv14) blew me from 145 to 0 HP (the
            # auto-combat net held) and a kamikaze samurai (id samurai_kamikaze, named "samurai")
            # hit 18% a round: both went to melee because only names were checked
            prof = threat.profile(t.get("id") or tname) or {"flags": []}
            exploder = "exploder" in prof["flags"] or "kamikaze" in (t.get("id") or "").replace("samurai_kamikaze", "")
            # run 33 (**death**): Silent Grassland's master 『Kamikaze yeek』 died to two Putit throws at close range and its
            # death blast took 214 -> -342 HP; a named (『』) exploder's blast is past any HP of mine, and its capital K
            # slipped past the name check. Named exploders stop the ladder: kill from 5+ cells by hand (cast.py bolts),
            # teleport if it closes within 4, never throw or melee near it
            exploder = exploder or any(w in tname.lower() for w in ("kamikaze", "hot guy")) or t.get("id") == "hardgay"
            # run 47, Ominous Cave B2: a mine dog met inside a delve pass, fought, and a mine it had laid took HP 280 -> 106; the
            # ladder's levitate_over_mines runs only between passes. A levitating chara ignores a mine (fact #1413): cast it here
            if "minelayer" in prof["flags"]:
                me = call("state")["data"]["pc"]
                for n in range(4):
                    if "ConLevitate" in (me.get("conditions") or []):
                        break
                    call("cast", spell="SpLevitate")
                    wait_until("frames", n=20, timeout=3000)
                    me = call("state")["data"]["pc"]
                print(f"  {t['name']} lays mines: Levitate {'on' if 'ConLevitate' in (me.get('conditions') or []) else 'FAILED (Gravity?)'}")
            # run 37 (**death** again): the state names it "Hot guy" without 『』: common.named reads the capital
            if exploder and named(t):
                halt(f"{t['name']} is a NAMED exploder at {t['dist']}: its death blast killed me in runs 33 and 37; "
                     "kill it from 5+ cells with cast.py, teleport if it closes within 4, never throw or melee near it")
            if exploder:
                items = inv_items()
                pot = next((n for n in SOAK if pick(n, items, key="name", quiet=True)), None)
                # run 22: with no soak potion in the pack the step back was skipped too, the Putit and
                # melee went in at 1-2 cells, and a kamikaze yeek's blast took 159 -> 107: step back
                # first whatever is in hand, then soak if there is a potion, else throw from range
                d = step_away(t) if t["dist"] < THRESHOLDS["kamikaze_dist"] else t["dist"]
                if d <= 1:
                    # run 43 (Ominous Forest B1): this stop ended a circuit for a Lv6 yeek; the table's answer is a teleport, so read it
                    out = run("item.py", "scrolls of teleport", "Read", timeout=60)
                    if out.rc:
                        halt(f"{t['name']} adjacent and no room to step away: a hit from here is a blast, and no teleport: {last(out)[:60]}")
                    print(f"  {t['name']} adjacent and no room to step away: read a teleport", flush=True)
                    wait_until("frames", n=10, timeout=2000)
                    continue
                if pot:
                    run("throw.py", tname, pot, "1", "50")
            # Open at range with the Putit In Amber (2d8+3, cold + lightning: my best ranged hit;
            # the user, run 04), then switch to the sword; loot.py after the fight brings it back.
            if t["dist"] >= 2 and "Putit In Amber" in inv_names():
                run("throw.py", tname, "Putit In Amber", "1", "70")
            # floating eyes paralyse in melee: always from range (elin-play). Drones shoot hard (run 07:
            # 26-37 HP each when meleed) but die to 3-5 Putit throws with no damage: throw until dead.
            # run 12: yeek warriors took 35-44 HP in melee but died to two Putit throws with no
            # damage; a goblin shaman's fire burned a rod, the sleeping bag and two scrolls
            THROW_AT = ("drone", "yeek warrior", "shaman", "wizard", "mage", "mummy", "kamikaze", "hot guy", "slime")  # run 26: slimes' acid lowers worn gear in melee
            inv = inv_names()
            ammo = re.search(r"\b(arrows?|pebbles?|bullets?)\b", inv.lower())
            ranged_foe = any(f in prof["flags"] for f in ("caster", "ranged", "blinder", "paralyser"))  # run 16: threat.py
            if (any(k in tname.lower() for k in THROW_AT) or t.get("id") in ("robot", "drone") or ranged_foe or exploder)                     and "Putit In Amber" in inv:
                tool, out = "throw.py", run("throw.py", tname, "Putit In Amber", "10", "55")
            elif "floating eye" in tname:
                # the user, run 12: the bow had no arrows; throw the Putit when there's no ammo
                tool = "shoot.py" if ammo else "throw.py"
                out = run("shoot.py", tname, str(HP_FLOOR), "12") if ammo else run("throw.py", tname, "Putit In Amber", "10", "55")
            else:
                # the review of 2026-11-11: a neutral Evolved at or under my level was listed as a foe above, but
                # fight.py only matches hostiles: "target not in view" at rc 0, 25 times, and the floor read as explored
                force = [] if t.get("hostile") else ["--force"]
                tool, out = "fight.py", run("fight.py", tname, str(HP_FLOOR), *force)
            before = (p.get("turn"), t.get("uid"), t.get("hpPct"))
            s, p, foes2, kab, kab_seen = status()
            # run 45: 15 silent minutes of fight steps that changed nothing. Two steps in a row with the turn
            # counter still, or four on one target without a point of damage, is a stop
            now = next((c for c in s.get("nearby") or [] if c.get("uid") == before[1]), None)
            if now and before[0] is not None and p.get("turn") == before[0]:
                STALL["turn"] += 1
            else:
                STALL["turn"] = 0
            if now and now.get("hpPct") == before[2] and STALL["uid"] == before[1]:
                STALL["hp"] += 1
            else:
                STALL["hp"], STALL["uid"] = 0, before[1]
            if STALL["turn"] >= 2 or STALL["hp"] >= 4:
                halt(f"no progress on {t['name']} Lv{t['lv']} d{now.get('dist')} ({now.get('hpPct')}%): "
                     + ("the turn counter hasn't moved in two fight steps" if STALL["turn"] >= 2
                        else "four fight steps without damage") + f"; last: {tool}: {last(out)[:80]}")
            print(f"[{k}] fought {t['name']} Lv{t['lv']}: {last(out)[:110]}  | HP {p['hp']}/{p['maxHp']}"
                  + "".join(f", {m['name']} {m['hp']}/{m['maxHp']}" for m in kab))
            # the fight tool stopped for a decision (HP, a hit over 15% in one round, a window) or
            # refused (a rule): mine to make, not the next step's
            if out.rc in (1, 3):
                halt(f"{tool} {'refused' if out.rc == 1 else 'stopped'}: {last(out)[:140]}")
            if not foes2:
                run("loot.py", "8", "--no-butcher")  # the user, run 15: no butchering mid-combat
            SAFE_TO_LOOT = True
            continue
        out = run("explore.py", "6", str(HP_FLOOR))
        print(f"[{k}] explore: " + " / ".join(ln.strip() for ln in out.splitlines()[-3:] if ln.strip()))
        SAFE_TO_LOOT = True
        if "stairs (not the way in)" in out:
            print(f"[{k}] stop: stairs found")
            return
        if "no frontier left" in out:
            print(f"[{k}] stop: floor explored")
            return
    print("stop: step limit")


def butcher_when_safe():
    """The user, run 15: butcher after combat, when safe, and don't leave the meat behind. Every
    natural end of the delve comes here: with no hostile in view, the corpses around and in the
    pack go through loot.py (which re-checks for hostiles; butcher.py stops if one appears)."""
    s = call("state")["data"]
    if any(c.get("hostile") for c in s.get("nearby") or []):
        print("corpses wait: a hostile is in view")
        return
    b = run("loot.py", "20")
    print("after the delve: " + " / ".join(ln.strip() for ln in b.splitlines()[-2:] if ln.strip()))


if __name__ == "__main__":
    floor_gate()  # before the try: a refused floor is never looted (the review of 2026-10-23)
    try:
        main()
    finally:
        if SAFE_TO_LOOT:
            butcher_when_safe()
