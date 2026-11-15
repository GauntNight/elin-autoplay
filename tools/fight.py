"""Melee a visible creature by name until it dies, using the game's own Attack act
(the act walks into range). Stops (exit 3) when my HP drops below a floor, when one round costs
more than 15% of my max HP (THRESHOLDS hit_pct: teleport), when a window opens; exit 0 when the
target is gone, not in view or unreachable, or after a turn limit.

Survival first (the user's #1 goal): refuses (exit 1) a target more than 2 levels above me
unless --force, an avoid-group kind within 8 levels, and the world map; stops at 60% HP by default.

usage: python -I tools/fight.py NAME [min_hp_pct] [max_rounds] [--force] [--single] [--town-ok] [--acid-ok]

Run 16: the fight goes through the game's own auto-combat (bridge 0.26.0 `autocombat`, warrior
tactics) whenever the bridge has it: in GoalAutoCombat a lethal hit on me or a party member who
was healthy when it started leaves us at 0 HP instead of dead, once (Card.DamageHP), and the
combat aborts. That 0-HP turn is the time to teleport: at or under 10% HP after a round this
tool reads a scroll of teleport itself (else zaps the rod of teleport) before it returns (exit 3).
--single: the old one Attack act a round.
--until PCT (run 29, G20's monster ball: capture needs the target at 10% HP or less, alive): one Attack a
round (no auto-combat), never the Putit; exit 0 once the target is at or under PCT%, exit 3 when the
biggest hit seen so far could kill it from where it stands (switch to a weaker attack) or it keeps away.
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import THRESHOLDS, grab, last, named, refuse, run, stop, walk_beside  # noqa: E402

NET_HP = 10  # at or under this percent after a round the next hit kills: teleport now
LAST_SWING = False  # run 37: the one extra round against a lone foe at 10% or less has been taken


def match(c, name, force=False):
    """A target by name, and only a hostile one that isn't mine (run 07: "putit" matched my new pet
    snow putit, an Ally, and fight.py killed it). --force still never attacks party or Ally."""
    if c.get("party") or c.get("hostility") == "Ally":
        return False
    if not force and not c.get("hostile"):
        return False
    # a whole word: "rat" is not a pirate, "bee" not a beetle (run 12 review)
    return re.search(r"(?<![a-z])" + re.escape(name) + r"(?![a-z])", c["name"].lower()) is not None or name == c["id"].lower()  # run 18: ids are camelCase (publicPerformer)


UNTIL = int(sys.argv[sys.argv.index("--until") + 1]) if "--until" in sys.argv else None
AUTO = "--single" not in sys.argv and UNTIL is None


def auto_fight(t, min_hp, timeout=25.0):
    """Auto-combat on target t until it dies, my HP passes the floor, a window opens or the game
    aborts it (its lethal-hit net fired, or nothing left to fight). True when it ran; False when the
    bridge has no autocombat op (older mod) or refused, so the caller falls back to one Attack."""
    r = call("autocombat", uid=t["uid"], tactics="warrior")
    if not r.get("ok"):
        return False
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(0.25)
        s = call("state")["data"]
        pc = s["pc"]
        alive = any(c["uid"] == t["uid"] for c in s.get("nearby") or [])
        low = pc["hp"] * 100 < min_hp * pc["maxHp"]
        if low or (s.get("layers") or {}).get("top") or not alive:
            call("abortcombat")
            return True
        if "AutoCombat" not in str(pc.get("ai") or ""):
            return True  # the game ended it (target lost, or its safety net fired)
    call("abortcombat")
    return True


def emergency_teleport():
    """The net rule: a scroll of teleport first (item.py: whole-word match, so never the short
    one), else the fullest rod of teleport zapped on my own cell. Returns what was done, or None."""
    out = run("item.py", "scroll of teleport", "Read")
    if out.rc == 0 and "Read" in out:
        return "read a scroll of teleport"
    held = grab("rod of teleport", prefer="charges")
    if held:
        acts = call("acts", dx=0, dz=0, mode="right")["data"]["acts"]
        zap = [a for a in acts if a["text"].startswith("Zap")]
        if zap:
            call("do", i=zap[0]["i"])
            return f"zapped the {held}"
    return None


def keep_log(s, what):
    """The game's log ring at a big hit, appended to runs/bighits.log (run 28: a rock thrower Lv8 on Ancient
    Grassland B4 took 190 -> 0 in one round, and by the time I looked the ring held only my heals: the cause,
    one thrown rock or a paralysis, was lost). Text only, game content."""
    from datetime import datetime
    try:
        with open(Path(__file__).resolve().parent.parent / "runs" / "bighits.log", "a", encoding="utf-8") as f:
            f.write(f"== {datetime.now():%Y-%m-%d %H:%M} {s['pc'].get('date', '')} {(s.get('zone') or {}).get('full', '')}: {what}\n")
            for line in s.get("log") or []:
                f.write(f"   {line}\n")
    except OSError:
        pass


def after_round(hp0, max_hp, min_hp, who):
    """My HP after a round against what it was before it (the review of 2026-10-23: a turn that
    costs more than THRESHOLDS hit_pct is the signal to teleport, whatever the floor says).
    Returns the fresh state."""
    s2 = call("state")["data"]
    p2 = s2["pc"]
    hp2, max_hp = p2["hp"], p2["maxHp"] or max_hp
    drop = (hp0 - hp2) * 100 / max_hp if max_hp else 0
    if drop > THRESHOLDS["hit_pct"] or hp2 * 100 <= NET_HP * max_hp:
        keep_log(s2, f"{hp0} -> {hp2}/{max_hp} ({drop:.0f}%) in a round with {who}")
    if hp2 * 100 <= NET_HP * max_hp:
        did = emergency_teleport()
        stop(f"HP {hp2}/{max_hp} after a round with {who}: {did or 'no scroll or rod of teleport found'} (the net rule): heal now")
    # run 24 (the user, run 16: "you may be teleporting out too early"): at 178 max HP the 15% rule
    # stopped fights with Lv11-13 foes at 84% HP (an orc warrior's 28 HP); the rounds that mattered
    # left me under 70% (the Goblin wizards: 60% -> 33%) or cost over 25%. A round over hit_pct stops
    # when it leaves me under the dungeon floor, or when it costs over hit_pct_any at any HP
    hp_after = hp2 * 100 / max_hp if max_hp else 0
    if drop > THRESHOLDS["hit_pct_any"] or (drop > THRESHOLDS["hit_pct"] and hp_after < THRESHOLDS["dungeon_hp"]):
        # run 37 (Unknown Ruin B3): the iron maiden, the floor's master, alone at 1% with me at 65% after its 24%
        # round: one more swing killed it for 4 HP, where two teleports had already reset the fight. A lone foe
        # (exploders never get this far: refused above) at 10% or less gets one more round, once a fight, while
        # the same round again would still leave me at 40% or more
        global LAST_SWING
        foes = [c for c in s2.get("nearby") or [] if c.get("hostile")]
        if (not LAST_SWING and len(foes) == 1 and (foes[0].get("hpPct") or 100) <= 10
                and hp_after - drop >= THRESHOLDS["last_swing_hp"]):
            LAST_SWING = True
            print(f"a hit of {drop:.0f}% in one round ({hp0} -> {hp2}/{max_hp}, {who}), but {foes[0]['name']} is alone "
                  f"at {foes[0].get('hpPct')}%: one more round")
            return s2
        # Start Run 3: with no teleport in the pack this stop's advice is empty, and at 59 max HP one 16-point bite from a Lv4 is over 25%: two deaths came from walking away
        # instead. While every foe is at or below my level and I hold 40%, the fight goes on.
        if hp_after >= 40 and all((c.get("lv") or 0) <= p2["lv"] for c in foes):
            names = [i["name"] for i in call("inv")["data"]["items"]]
            if not any("teleport" in n for n in names):
                print(f"a hit of {drop:.0f}% in one round ({hp0} -> {hp2}/{max_hp}, {who}); no teleport in the pack and no foe above my level: fighting on")
                return s2
        stop(f"a hit of {drop:.0f}% in one round ({hp0} -> {hp2}/{max_hp}, {who}): teleport")
    if hp2 * 100 < min_hp * max_hp:
        stop(f"HP {hp2}/{max_hp} is below {min_hp}%")
    return s2


def main():
    """The fight, recorded (the user, run 29: every fight logged, per monster in the graph): fightlog.Tracker writes
    one knowledge/fights.csv row per target attacked when the fight ends, whether it ended in a kill, a stop (exit 3)
    or the --until hold."""
    import fightlog

    def pv():
        me = [c for c in call("power")["data"]["party"] if c.get("pc")]
        return me[0].get("PV", "") if me else ""

    trk = fightlog.Tracker(pv=pv)
    result = None
    try:
        result = _fight(trk)
    except SystemExit as e:
        if e.code not in (0, None):
            result = f"stopped (exit {e.code})"
        raise
    finally:
        try:
            trk.see(call("state")["data"])
            trk.finish(result)
        except Exception as e:  # noqa: BLE001 (the log never breaks a fight)
            print(f"  fight log not written: {e}")


EVASIVE = {}  # uid -> bool (threat.py's "evasive" flag)
RANGED_MP_FLOOR = 25


def evasive(t):
    """run 34 (the user): a kind the race data marks hard to hit in melee (threat.py "evasive": race DV 20+, or 15+ at
    speed 150+: bats, fairies, the metal bells)."""
    if t["uid"] not in EVASIVE:
        import threat
        prof = threat.profile(t.get("id") or t["name"]) or {"flags": []}
        EVASIVE[t["uid"]] = "evasive" in prof["flags"]
    return EVASIVE[t["uid"]]


def ranged_round(t, s, min_hp):
    """One ranged attack at an evasive target instead of a swing (the user, run 34: "May be worth trying a throw or
    magic", "The thrown item you have is also very powerful"): a spell while MP lasts (an arrow when the crew could
    stand in a bolt's line, Fire Bolt solo), else the Putit In Amber (hit 128% against the axe's 105%). Returns what
    was used, or None when neither worked (melee goes on)."""
    pc = s["pc"]
    party = [c for c in s.get("party") or [] if not c.get("pc")]
    if pc.get("mp", 0) >= RANGED_MP_FLOOR:
        stock = {x["spell"]: x["stock"] for x in call("power")["data"]["party"][0].get("spells") or []}
        if party:
            spell = max(("arrow_Nerve", "arrow_Magic", "arrow_Cold", "arrow_Poison"), key=lambda k: stock.get(k, 0))
        else:
            spell = "bolt_Fire" if stock.get("bolt_Fire", 0) > 0 else max(("arrow_Nerve", "arrow_Magic", "arrow_Cold"),
                                                                            key=lambda k: stock.get(k, 0))
        if stock.get(spell, 0) > 0:
            r = call("cast", spell=spell, uid=t["uid"])
            if r.get("ok") and (r.get("data") or {}).get("cast"):
                return spell
    nm = t["name"].split(" ", 1)[-1] if t["name"].startswith(("a ", "an ")) else t["name"]
    out = run("throw.py", nm, "Putit In Amber", "1", str(min_hp), timeout=90)
    if out.rc == 3:
        stop(f"throw.py stopped: {last(out)[:100]}")
    return "a thrown item" if out.rc == 0 else None  # the new-game test: rc 1 is nothing to throw, so melee goes on


def swarm_round(t, s):
    """Run 40: the Swarm ability (Eligin, 50 platinum; ActSwarm in the code: one action, 12 SP, a blow at 0.9x melee on every
    hostile within 3 cells in line of sight). From 3 in range it beats one swing. Never beside an exploder (a blow kills it
    next to me) or a slime (melee splashes acid), and never under the SP floor. False: fight on as usual."""
    pc = s["pc"]
    near = [c for c in s.get("nearby") or [] if c.get("hostile") and c["dist"] <= 3]
    if t["dist"] > 3 or len(near) < THRESHOLDS["swarm_ability_min"] or pc.get("sp", 0) < THRESHOLDS["swarm_ability_sp"]:
        return False
    import threat
    for c in near:
        flags = (threat.profile(c.get("id") or c["name"]) or {"flags": []})["flags"]
        if "exploder" in flags or "kamikaze" in (c.get("id") or "").replace("samurai_kamikaze", "") or "slime" in (c.get("id") or ""):
            return False
    r = call("cast", spell="ActSwarm", uid=t["uid"])
    return bool(r.get("ok") and (r.get("data") or {}).get("cast"))


def _fight(trk):
    force = "--force" in sys.argv
    argv = sys.argv[1:]
    if "--until" in argv:
        i = argv.index("--until")
        argv = argv[:i] + argv[i + 2:]
    # run 38: "--melee" (read from sys.argv below) was left in the positional args and crashed int(args[1])
    args = [a for a in argv if a not in ("--force", "--single", "--melee", "--town-ok", "--acid-ok")]
    hits = []  # the target's HP lost to each of my attacks, in percent (--until)
    name = args[0].lower()
    min_hp = int(args[1]) if len(args) > 1 else 60
    rounds = int(args[2]) if len(args) > 2 else 40
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    s0 = call("state")["data"]
    turn0 = s0["pc"].get("turn")
    # Run 15: on the world map there is no Attack act, and the walk toward an adjacent cell is a
    # world-map step (2.6 game hours each): a Lv3 goblin was chased for 8 hours. Bumping into it
    # with `bridge.py move DIR` starts the encounter map, where fight.py works.
    z = s0.get("zone") or {}
    on_world = z["region"] if "region" in z else str(z.get("full") or "").startswith("Zone_ntyris")
    if on_world:
        refuse("on the world map: bump into the monster with `bridge.py move DIR` "
               "(n s e w) to start the encounter, then fight there")
    # run 48: Anastazija (Derphy's guild doorman, Lv32) caught a theft and turned hostile; fight.py killed her as she begged and
    # the death cost Karma -5, the karma the thefts were spending. In a town the answer is to walk off or take the stairs
    if z.get("town") and "--town-ok" not in sys.argv:
        refuse("in a town: a townsperson's death costs karma (run 48: Anastazija, -5): walk away, take the stairs or leave "
               "the map; --town-ok for a monster that came into town")
    foes0 = [c for c in s0.get("nearby") or [] if match(c, name, force)]
    if foes0 and not force:
        t0 = min(foes0, key=lambda c: c["dist"])
        if t0["lv"] > s0["pc"]["lv"] + 2:
            refuse(f"{t0['name']} is Lv{t0['lv']}, I am Lv{s0['pc']['lv']} "
                   "(survival rule; use range, or --force if it is restrained)")
        # run 17: two lizardmen (threat.py "avoid", Lv12 against my Lv18) took 125 -> 69 in two
        # turns of melee: an avoid-group kind within 8 levels is ranged or left, never meleed
        import threat
        if threat.avoid(t0, s0["pc"]["lv"]):  # run 33: within the window, or a recorded fight that cost 30%
            refuse(f"{t0['name']} Lv{t0['lv']} is an avoid-group kind (threat.py) within {THRESHOLDS['avoid_levels']} "
                   f"levels or with a recorded {THRESHOLDS['avoid_seen_pct']}% fight: range it (cast.py, throw.py, "
                   "shoot.py) or leave; --force only if it is restrained")
        # run 24: a bomb rock (exploder) took 145 -> 0 HP in melee: exploders are never meleed
        prof0 = threat.profile(t0.get("id") or t0["name"]) or {"flags": []}
        if "exploder" in prof0["flags"] or "kamikaze" in (t0.get("id") or "").replace("samurai_kamikaze", "") or "kamikaze" in t0["name"].lower():  # run 33: 『Kamikaze yeek』
            refuse(f"{t0['name']} is an exploder (threat.py): never adjacent; soak it with a thrown potion and "
                   f"throw from {THRESHOLDS['kamikaze_dist']}+ cells (delve.py does), or step away; --force if restrained")
        # run 26: a slime gang meleed by hand splashed acid on every swing and the night's curses landed too:
        # the axe +1 -> -1, the Mass Ring 0 -> -3, the scimitar 0 -> -2 (PV 63 -> 55). elin-play: slimes from range
        if "slime" in (t0.get("id") or "") and "--acid-ok" not in sys.argv:
            refuse(f"{t0['name']} is a slime: melee splashes acid that lowers the worn gear's enchantment; throw "
                   "(throw.py), shoot, or leave; --acid-ok to melee anyway")
    seen = False
    # run 15 (the user: "you got stuck doing nothing while the Putit was just attacking you"): a putit
    # frozen into an ice sculpture by the Putit In Amber's cold offered no Attack act; fight.py kept
    # choosing it as the nearest and gave up each round while the live one hit me. A target that
    # can't be attacked is skipped, and an adjacent foe (the one hitting me) goes first.
    skip, approach, last_dist = set(), {}, {}
    for _ in range(rounds):
        s = call("state")["data"]
        trk.see(s)
        pc = s["pc"]
        if pc["hp"] * 100 < min_hp * pc["maxHp"]:
            stop(f"HP {pc['hp']}/{pc['maxHp']} is below {min_hp}%")
        if (s.get("layers") or {}).get("top"):
            stop(f"a window or dialog is open: {s['layers']['top']}")
        foes = [c for c in s.get("nearby") or [] if match(c, name, force) and c["uid"] not in skip]
        if not foes:
            print(("target unreachable (no free cell beside it)" if skip else "target gone") if seen
                  else "target not in view")
            break
        seen = True
        t = min(foes, key=lambda c: (c["dist"] > 1, c["dist"]))
        if UNTIL is not None:
            if t["hpPct"] <= UNTIL:
                print(f"{t['name']} (uid {t['uid']}) is at {t['hpPct']}%: at or under {UNTIL}% (hits so far: {hits})")
                return f"held at {t['hpPct']}% (--until)"
            if hits and max(hits) >= t["hpPct"]:
                stop(f"{t['name']} is at {t['hpPct']}% and my hits took {hits}% each: the next one could kill it; "
                     "switch to a weaker attack")
        # run 34: named specials (『』) hit far above their level (Goda 31% a round, 『Orc warrior』 21%, 『Living armor』):
        # they get the ranged opener too. Run 37: the check read 『』, which the state never shows, so it never ran; with
        # common.named it does, as an opener only (2+ cells): adjacent, an arrow (1-2% a cast on run 37's named foes)
        # is a lost round under a 25-35% hitter
        if UNTIL is None and "--melee" not in sys.argv and (evasive(t) or (named(t) and t["dist"] >= 2)):
            hp0 = pc["hp"]
            trk.engage(t, s)
            how = ranged_round(t, s, min_hp)
            if how:
                time.sleep(1.0)
                s2 = after_round(hp0, pc["maxHp"], min_hp, t["name"])
                trk.see(s2)
                tt = [c for c in s2.get("nearby") or [] if c["uid"] == t["uid"]]
                print(f"HP {s2['pc']['hp']}/{s2['pc']['maxHp']}  {t['name']} {tt[0]['hpPct'] if tt else 0}% ({how}: ranged)")
                continue
        if UNTIL is None and "--single" not in sys.argv:
            hp0 = pc["hp"]
            trk.engage(t, s)
            if swarm_round(t, s):
                time.sleep(0.8)
                s2 = after_round(hp0, pc["maxHp"], min_hp, t["name"])
                trk.see(s2)
                tt = [c for c in s2.get("nearby") or [] if c["uid"] == t["uid"]]
                left = sum(1 for c in s2.get("nearby") or [] if c.get("hostile") and c["dist"] <= 3)
                print(f"HP {s2['pc']['hp']}/{s2['pc']['maxHp']}  {t['name']} {tt[0]['hpPct'] if tt else 0}% "
                      f"(swarm: SP {s2['pc'].get('sp')}, {left} left in range)")
                continue
        acts = call("acts", dx=t["dx"], dz=t["dz"], mode="all")["data"]["acts"]
        atk = [a for a in acts if a["text"].startswith("Attack")]
        if UNTIL is not None and not atk and t["dist"] > 1 and approach.get(t["uid"], 0) >= 3:
            trk.flag(t["uid"], "keeps its distance (runs or floats away)")
            stop(f"{t['name']} keeps its distance (d{t['dist']}, {t['hpPct']}%): no Putit with --until")
        if UNTIL is None and not atk and t["dist"] > 1 and (approach.get(t["uid"], 0) >= 1 or t["dist"] > last_dist.get(t["uid"], 99)):
            # the user (run 21): "if dealing with enemies that keep running away use your thrown
            # weapon, spells, or ranged attacks": a target that kept its distance after one chase,
            # or moved away, gets the Putit In Amber (it comes back) instead of another walk
            out = run("throw.py", t["name"].split(" ", 1)[-1] if t["name"].startswith(("a ", "an ")) else t["name"],
                      "Putit In Amber", "2", timeout=120)
            print(f"  {t['name']} keeps its distance (d{t['dist']}): thrown at: {last(out)[:90]}")
            trk.flag(t["uid"], "keeps its distance (runs or floats away)")
            last_dist[t["uid"]] = t["dist"]
            approach[t["uid"]] = approach.get(t["uid"], 0) + 1
            if approach[t["uid"]] > 5:
                skip.add(t["uid"])
            continue
        last_dist[t["uid"]] = t["dist"]
        if not atk and t["dist"] > 1:
            # Attack is offered only from an adjacent cell: walk to the one on our side; a target
            # the walk can't reach in 3 tries is skipped too (run 15's stall)
            approach[t["uid"]] = approach.get(t["uid"], 0) + 1
            if approach[t["uid"]] > 3:
                skip.add(t["uid"])
                continue
            # run 18: the one diagonal cell toward it was a tree (a goblin) or the lake (a hermit
            # crab) and the target was dropped as "gone"; any free neighbour of it will do.
            # r=0: the target itself is the hostile in range; the HP floor still stops the walk
            walk_beside(pc["x"] + t["dx"], pc["z"] + t["dz"], r=0, hp=min_hp, timeout=8000)
            continue
        if not atk:
            print("no Attack act on", t["name"], [a["text"] for a in acts], "- skipping it")
            skip.add(t["uid"])
            continue
        hp0 = pc["hp"]
        trk.engage(t, s)
        if AUTO and auto_fight(t, min_hp):
            s2 = after_round(hp0, pc["maxHp"], min_hp, t["name"])
            trk.see(s2)
            tt = [c for c in s2.get("nearby") or [] if c["uid"] == t["uid"]]
            print(f"HP {s2['pc']['hp']}/{s2['pc']['maxHp']}  {t['name']} {tt[0]['hpPct'] if tt else 0}% (auto-combat)")
            continue
        call("do", i=atk[0]["i"])
        time.sleep(1.0)
        s2 = after_round(hp0, pc["maxHp"], min_hp, t["name"])
        trk.see(s2)
        tt = [c for c in s2.get("nearby") or [] if c["uid"] == t["uid"]]
        if tt and tt[0]["hpPct"] < t["hpPct"]:
            hits.append(t["hpPct"] - tt[0]["hpPct"])
        print(f"HP {s2['pc']['hp']}/{s2['pc']['maxHp']}  {t['name']} {tt[0]['hpPct'] if tt else 0}%")
    end = call("state")["data"]
    log = end.get("log") or []
    print("log:", " / ".join(log[-5:]))
    # run 45 (Ancient Ruin B3): delve counted 25 fight steps that never swung as fought, 15 silent minutes with
    # two weak hostiles idle beside me. A call that leaves the target in view and the turn counter where it was
    # did nothing: that is a decision, not a round
    left = [c for c in end.get("nearby") or [] if match(c, name, force)]
    if left and turn0 is not None and end["pc"].get("turn") == turn0:
        stop(f"no round landed on {left[0]['name']} (d{left[0]['dist']}, {left[0]['hpPct']}%): the turn counter "
             f"is still at {turn0}; look.py, then by hand")


def fight_speed():
    """Fights run at the game's speed x1 (Start Run 1): a loop may run at x5 (bridge `speed`), and this tool's checks between polls then span several
    game rounds: four deaths in that run read "a hit of 49-66% in one round". The speed before it comes back when the tool exits."""
    import atexit
    rep = call("speed")
    prior = (rep.get("data") or {}).get("index", 1) if rep.get("ok") else 1
    if prior > 1:
        call("speed", i=1)
        atexit.register(lambda: call("speed", i=prior))


if __name__ == "__main__":
    fight_speed()
    main()
