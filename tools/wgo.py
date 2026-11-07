"""World-map travel with the game's own pathing (the user's tip, run 08: clicking a place walks
there around cliffs). Sends AI_Goto to the named place's cell, polls until I arrive, land on a
local map (an ambush), see a hostile within 4, or HP drops under 60%; then cancels the walk so it
doesn't resume after an ambush (run 08: a leftover goto walked me 14 game hours further).

usage: python -I tools/wgo.py NAME [--weak-ok] [--ambush]   a place from `bridge.py places` (name or id)
       python -I tools/wgo.py X Z [--weak-ok] [--ambush]    an absolute world-map cell
  --near N   stop for a hostile within N cells (default 4)
  --weak-ok  keep walking past hostiles 3+ levels below me (a lone crab kept stopping the walk;
             if one ambushes, the fight is easy); anything stronger still stops it
  --ambush   handle an ambush map instead of handing back (the review of 2026-10-23: travel was the
             largest real-time sink and every ambush stopped the tool): the swarm rule and the
             level rule of elin-play's table, then fight.py one foe at a time (nearest first),
             loot.py 20, purge.py --free 3 (run 35), leave.py, and the walk goes on. Anything the rules refuse stops (exit 3).
NAME: an exact name or id wins; else a part of the name, which must fit one place name only
(several places of that one name: the nearest); two or more different names refuse (exit 1, the
way common.pick does). Refuses off the world map (zone.region, bridge 0.30.0) and for an
underwater dungeon without --breathe. Exit 0 on arrival; exit 3 (stop) on an ambush (a local
map: look.py), a hostile close, HP under 60%, a window, hunger or SP, or when not moving.
Every leg is logged (the user, run 12: travel time belongs in the graph): a row in
knowledge/travel.csv and, for a leg of 3+ steps, a `kb.py add` fact with the game hours, the
steps walked and how it ended. Run 12 measured about 2.5-3 game hours a world-map step.
"""
import csv
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import THRESHOLDS, base_ready, last, ready, refuse, run, stop, wait_until, walk  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TRAVEL_CSV = ROOT / "knowledge" / "travel.csv"
SWING_TILES = 6  # run 34: a leg 6+ tiles farther from the target than the walk's closest point stops it
MAX_AMBUSH_FIGHTS = 12
LEG_MS = 2500  # run 21: a leg of 2-3 world-map steps, then the hunger and sleep checks run again


def meal_stop():
    """Eat on the local map under me (the world map has no Eat), then come back up (run 21: two walks
    starved me, 154 -> 89 and 159 -> 50 HP, because a long leg ran from Hungry into Starving).
    Returns None when fed, or the reason it couldn't eat (a hostile there, no food)."""
    import farmday
    acts = call("acts", dx=0, dz=0, mode="all").get("data", {}).get("acts") or []
    enter = [a for a in acts if a["text"].startswith("Enter")]
    if not enter:
        return "no local map to eat on here"
    call("do", i=enter[0]["i"])
    from common import wait_until
    wait_until("zone", timeout=10000)
    wait_until("frames", n=30, timeout=3000)
    s = call("state")["data"]
    # run 26: six meal stops ended on a Lv1-8 hostile and I cleared each by hand: hostiles 10+ levels
    # under me get fight.py first (two passes); anything stronger still means leave
    me = s["pc"]["lv"]
    for _ in range(6):
        foes = [c for c in s.get("nearby") or [] if c.get("hostile")]
        if not foes or any(c.get("lv", 99) > me - 10 for c in foes):
            break
        name = re.sub(r"^(a|an) ", "", foes[0].get("name") or "")
        run("fight.py", name, "60", timeout=300)
        s = call("state")["data"]
    if any(c.get("hostile") for c in s.get("nearby") or []):
        run("leave.py", "--force", "--riding-ok", timeout=300)
        return "a hostile on the meal stop's map"
    fed = None
    for _ in range(2):
        fed = farmday.eat_one() or fed
        if call("state")["data"]["pc"]["hunger"] < THRESHOLDS["eat_at"] - 15:
            break
    # run 43: a meal stop on a conquered nefia's tile went down its stairs, and leave.py found no edge: "not moving", a stopped circuit
    if (call("state")["data"].get("zone") or {}).get("nefia"):
        run("stairs.py", "up", timeout=300)
    else:
        run("leave.py", "--riding-ok", timeout=300)
    print(f"  meal stop: {fed or 'nothing eaten'}")
    # run 27: this said "no meal in the Cooler Box" when eat_one refused a full pack grid; its own line says why
    return None if fed else "nothing eaten (eat_one's line above says why: no meal, a full grid, a hostile)"


def answer_demand(s):
    """Run 34: two road bandit demands ("Give me X, or your life is forfeit!") stopped --ambush for a hand-typed "Try me"
    against Lv7-12 goblins and eyes at my Lv31 (elin-town-trip: weak bandits get "Try me"; exploders get paid). Clicks
    "Try me." only when every creature that isn't mine is 12+ levels under me (swarm_weak_below) and none is an exploder;
    returns None when it answered, else the reason the dialog stays for a decision."""
    import json
    import threat
    if "life is forfeit" not in json.dumps(s.get("drama") or {}, ensure_ascii=False):
        return "a dialog is open (not a bandit demand): talk.py"
    lv = s["pc"]["lv"]
    them = [c for c in s.get("nearby") or [] if not c.get("party") and c.get("hostility") not in ("Ally", "Friend", "Neutral")]
    for c in them:
        if (c.get("lv") or 0) > lv - THRESHOLDS["swarm_weak_below"]:
            return f"a bandit demand with {c.get('name')} Lv{c.get('lv')} near my level: decide by hand (talk.py)"
        prof = threat.profile(c.get("id") or c.get("name"), c.get("lv")) or {}
        if "exploder" in (prof.get("flags") or []) or "kamikaze" in str(c.get("id") or "").lower().replace("samurai_kamikaze", ""):
            return f"a bandit demand with an exploder ({c.get('name')}): pay it if cheap (elin-town-trip)"
    bs = call("buttons")["data"]["buttons"]
    tm = next((b for b in bs if (b.get("text") or "").strip().startswith("Try me")), None)
    if not tm:
        return "a bandit demand without a 'Try me.' choice: talk.py"
    call("click", i=tm["i"], expect="Try me")
    run("talk.py", timeout=60)
    print(f"  ambush: answered a bandit demand 'Try me.' ({len(them)} weak demanders)")
    return None


def handle_ambush(_retry=False):
    """On the ambush map (--ambush): elin-play's swarm and level rules, then fight.py on the nearest
    hostile until none is in view, loot.py, leave.py. Returns "cleared" (back on the world map) or
    the reason to stop. The thresholds are common.THRESHOLDS (the table in elin-play)."""
    wait_until("frames", n=20, timeout=3000)  # run 34: a bandit's demand opens a few frames after the zone change
    for _ in range(MAX_AMBUSH_FIGHTS):
        s = call("state")["data"]
        p = s["pc"]
        # run 26: two ambush maps (lake fields) put me in deep water; ready() said "wait it out" for
        # ConSuffocation, which only drowns: a scroll of teleport lands on dry ground (it did both times)
        # run 42: a water breather (gloves that "let you breathe underwater") loses nothing there: a whole sea-bed map stopped the circuit with 2 scrolls spent
        if (p.get("inWater") or "ConSuffocation" in (p.get("conditions") or [])) and not p.get("breathesWater"):
            run("item.py", "scrolls of teleport", "Read", timeout=60)
            wait_until("frames", n=30, timeout=3000)
            s = call("state")["data"]
            p = s["pc"]
            if p.get("inWater") or "ConSuffocation" in (p.get("conditions") or []):
                return "in deep water after a teleport: read another or leave by hand"
        if s.get("drama"):
            why = answer_demand(s)
            if why:
                return why
            s = call("state")["data"]
            p = s["pc"]
        why = ready(s, hp=THRESHOLDS["dungeon_hp"], hunger=None, hostiles=False)
        if why:
            return why
        foes = [c for c in s.get("nearby") or [] if c.get("hostile")]
        total = (s.get("threat") or {}).get("hostiles", len(foes))
        if not foes and not total:
            break
        # run 21: foes 12+ levels under mine don't make a swarm (THRESHOLDS swarm_weak_below)
        counted = [c for c in foes if (c.get("lv") or 0) > p["lv"] - THRESHOLDS["swarm_weak_below"]]
        tiny = sum(1 for c in foes if (c.get("lv") or 0) <= p["lv"] - THRESHOLDS["swarm_ignore_below"])  # run 43: twelve Lv4 geese
        n = len(counted) + (len(foes) - len(counted) - tiny) // 2 + max(0, total - len(foes))  # far weaker ones count half, the tiny none
        above = any((c.get("lv") or 0) >= p["lv"] for c in foes)
        if n >= THRESHOLDS["swarm"] or (n >= THRESHOLDS["swarm_above"] and above):
            return f"swarm: {n} hostiles in view ({'one at or above my level' if above else 'all below me'}): teleport, then leave.py --force"
        strong = [c for c in foes if (c.get("lv") or 0) >= p["lv"] + 3]
        if strong:
            c = strong[0]
            return f"{c['name']} Lv{c['lv']} is 3+ levels above me: leave.py --force"
        if not foes:  # in view by the count but not in the 12-cell list: let the fight tool look
            break
        target = min(foes, key=lambda c: c["dist"])
        if "slime" in str(target.get("id") or ""):
            # run 34: fight.py refuses slimes (melee acid lowers worn gear) and the walk stopped: the Putit kills them
            tname = target["name"].split(" ", 1)[-1] if target["name"].startswith(("a ", "an ")) else target["name"]
            out = run("throw.py", tname, "Putit In Amber", "8", str(THRESHOLDS["dungeon_hp"]), timeout=300)
            print(f"  ambush: threw at {target['name']} Lv{target.get('lv')}: {last(out)[:80]}")
            if out.rc == 3:
                return "throw.py stopped: " + last(out)
            continue
        out = run("fight.py", target["name"], str(THRESHOLDS["dungeon_hp"]), timeout=300)
        if out.rc == 3:
            return "fight.py stopped: " + last(out)
        if out.rc == 1:
            # run 40: a hot guy 2 cells off on an ambush field stopped the whole circuit. Nothing on an ambush map is worth a 50%
            # blast: the thresholds table's answer (a scroll of teleport, then the edge) by itself, then walk on
            if "exploder" in last(out) or "avoid-group" in last(out):
                print(f"  ambush: {target['name']} refused ({last(out)[:50]}): teleport and leave", flush=True)
                run("item.py", "scrolls of teleport", "Read", timeout=60)
                time.sleep(1.0)
                lv = run("leave.py", "--force", "--riding-ok", timeout=300)
                if lv.rc == 0:
                    return "cleared"
                return "leave.py --force after the teleport: " + last(lv)
            return "fight.py refused: " + last(out)
        print(f"  ambush: fought {target['name']} Lv{target.get('lv')}: {last(out)[:80]}")
    else:
        return f"{MAX_AMBUSH_FIGHTS} fights on one ambush map: look.py"
    # Start Run 1: a new game's materials are its valuables (elin-setup): take everything, and never purge: this purge threw away
    # the only axe, the potions and the pebbles of a level 2 character with 23 stacks in the pack
    new_game = not base_ready()
    out = run("loot.py", "20", *(["--all"] if new_game else []), timeout=300)
    print(f"  ambush: loot: {last(out)[:100]}")
    # run 35: two ambushes' loot filled the grid on the way to Ruined Ruin; the ladder refused at the door (-1 free
    # cards), and its own purge stopped on a kamikaze yeek standing beside me: free the cards here, where it's quiet
    if not new_game:
        out = run("purge.py", "--free", "3", timeout=600)
        print(f"  ambush: purge: {last(out)[:100]}")
    out = run("leave.py", "--riding-ok", timeout=300)
    if out.rc != 0 and "hostile" in last(out) and int(_retry) < 3:  # run 41: once wasn't enough, a third arrival stopped a circuit
        # run 21: twice a late arrival (a snow putit, a giant fish) came up while leave.py walked
        # to the edge: fight it and leave again (once), rather than stop the trip
        print(f"  ambush: {last(out)[:80]}: fighting again")
        return handle_ambush(_retry=int(_retry) + 1)
    if out.rc != 0:
        return "leave.py: " + last(out)
    return "cleared"


def game_hours(date):
    """'486-04-22 14:10' -> hours since year 0 (Elin months have 30 days)."""
    d, t = date.split()[:2]
    y, m, dd = (int(v) for v in d.split("-"))
    hh, mm = (int(v) for v in t.split(":")[:2])
    return ((y * 12 + m - 1) * 30 + dd - 1) * 24 + hh + mm / 60


def log_leg(start, frm, to, steps, outcome):
    """Never let the log break a trip: any error here is printed and ignored."""
    try:
        end = call("state")["data"]["pc"]["date"]
        hours = game_hours(end) - game_hours(start)
        new = not TRAVEL_CSV.exists()
        with TRAVEL_CSV.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["start", "end", "from", "to", "steps", "game_hours", "hours_per_step", "outcome"])
            w.writerow([start, end, frm, to, steps, f"{hours:.1f}", f"{hours / steps:.2f}" if steps else "", outcome])
        print(f"  leg: {steps} steps in {hours:.1f} game hours ({start} -> {end}), {outcome}")
        if steps >= 3 and "at least" not in outcome:
            run("kb.py", "add", f"travel {frm} -> {to}", "took (world map)",
                f"{hours:.0f} game hours for {steps} steps ({hours / steps:.1f} h a step), {start} -> {end}, {outcome}",
                "--where", "North Tyris", timeout=60)
    except Exception as e:  # noqa: BLE001
        print(f"  (travel log failed: {e})")


TERRAIN_LETTERS = ("a", "e", "i", "o", "u", "y", "r", "n", "s", "l")  # dangergrid.py's sweep of every biome


def route_danger(dx, dz):
    """The ambush level a walk to (dx, dz) must cross: along the straight line, the best tile within
    one step of each point (the path can sidestep), then the worst of those. Run 21: the walk north
    to the Tangled Forest and the Ruined Cave ran into danger 21 fields (a stone golem Lv22, a cupid
    Lv18) although elin-play says to walk only fields within the limit; nothing checked it."""
    r = max(abs(dx), abs(dz)) + 2
    cells = {}
    for want in TERRAIN_LETTERS:
        for h in (call("terrain", r=r, want=want, n=40000).get("data") or {}).get("hits") or []:
            cells[(h["dx"], h["dz"])] = h
    n = max(abs(dx), abs(dz)) or 1
    worst, at = 0, (0, 0)
    for i in range(1, n + 1):
        px, pz = round(dx * i / n), round(dz * i / n)
        near = [max(0, h["danger"] - 5) for ox in (-1, 0, 1) for oz in (-1, 0, 1)
                if (h := cells.get((px + ox, pz + oz))) and not h["blocked"]]
        if near and min(near) > worst:
            worst, at = min(near), (px, pz)
    return worst, at


def tile_danger():
    """The worst ambush level of the tiles one step around me (run 28: the game's pathing swung east of the
    straight Mysilia -> Mifu line to ~74,99, and the ambush map there was danger 26 where the line's check
    said 19; Player.EnterLocalZone's formula itself matched). Checked after every leg."""
    worst = 0
    for want in TERRAIN_LETTERS:
        for h in (call("terrain", r=1, want=want, n=50).get("data") or {}).get("hits") or []:
            if not h["blocked"]:
                worst = max(worst, h["danger"] - 5)
    return worst


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    weak_ok = "--weak-ok" in sys.argv
    ambush = "--ambush" in sys.argv
    # --danger-ok [N]: a deliberate crossing up to ambush level N (default: the route's worst + 2); every leg
    # checks the tiles actually reached against it (run 28)
    danger_cap = None
    if "--danger-ok" in sys.argv:
        i = sys.argv.index("--danger-ok")
        if i + 1 < len(sys.argv) and sys.argv[i + 1].isdigit():
            danger_cap = int(sys.argv.pop(i + 1))
    # Start Run 1: a floating eye at my level followed at exactly 4 cells and stopped every step; --near 3 walks on until it comes closer
    near = int(sys.argv[sys.argv.index("--near") + 1]) if "--near" in sys.argv else 4
    if "--near" in sys.argv:
        del sys.argv[sys.argv.index("--near"):sys.argv.index("--near") + 2]
    a = [x for x in sys.argv[1:] if x not in ("--weak-ok", "--breathe", "--ambush", "--danger-ok", "--enter")]
    s0 = call("state")["data"]
    z = s0.get("zone") or {}
    on_world = z["region"] if "region" in z else "ntyris" in str(z.get("full") or "")
    if not on_world:
        refuse(f"not on the world map ({z.get('full')}): leave.py first")
    rep = call("places", r=80)
    if not rep.get("ok"):
        refuse(str(rep.get("error")))
    mx, mz = map(int, rep["data"]["me"].split(","))
    here = [p for p in rep["data"]["places"] if p["dist"] <= 1]
    frm = min(here, key=lambda p: p["dist"])["name"] if here else f"{mx},{mz}"
    start = s0["pc"]["date"]
    if len(a) == 2 and all(x.lstrip("-").isdigit() for x in a):
        tx, tz, label = int(a[0]), int(a[1]), f"{a[0]},{a[1]}"
    else:
        want = a[0].lower()
        places = rep["data"]["places"]
        # an exact name or id first; else a part of the name, one place name only (the review of
        # 2026-10-23: "ruin" picked the nearest of several different ruins without a word)
        hits = [p for p in places if p["name"].lower() == want or p["id"] == a[0]]
        hits = hits or [p for p in places if want in p["name"].lower()]
        if not hits:
            refuse(f"no place {a[0]!r} listed")
        names = sorted({p["name"] for p in hits})
        if len(names) > 1:
            refuse(f"{a[0]!r} fits {len(names)} places: " + " | ".join(names[:8]) + " (give the full name)")
        p = min(hits, key=lambda p: p["dist"])
        # run 17 (the user: "you can't do those kinds of dungeons"): an underwater ruin suffocates
        # every turn (112 -> 20 HP on a danger 4 B1); --breathe only with water breathing in hand
        if ("underwater" in p["name"].lower() or "water" in str(p.get("id") or "")) and "--breathe" not in sys.argv:
            refuse(f"{p['name']} is an underwater dungeon: suffocation (the user, run 17); --breathe only with water breathing")
        tx, tz, label = mx + p["dx"], mz + p["dz"], p["name"]
    worst, at = route_danger(tx - mx, tz - mz)
    # the new-game test: Lefess, Lv1 with 10 HP, walked a route of ambush level 4 under the limit of 5 and a level 1 puppy
    # killed her walking off the map; route_max was tuned on a sturdier character. A new one's limit grows with her level.
    limit = min(THRESHOLDS["route_max"], call("state")["data"]["pc"]["lv"] + 1)
    if worst > limit and "--danger-ok" not in sys.argv:
        refuse(f"the route crosses ambush level {worst} near {mx + at[0]},{mz + at[1]} (limit {limit}, THRESHOLDS route_max; elin-play's "
               f"route rule): Fast Travel, another route, or --danger-ok for a deliberate crossing")
    allowed = max(limit, danger_cap if danger_cap is not None else worst + 2) if "--danger-ok" in sys.argv else limit
    print(f"walking {mx},{mz} -> {tx},{tz} ({label}); the route's worst ambush level ~{worst} (allowed {allowed})")
    # run 33's review: travel was ~20% of the run's real time and only hand-run marks recorded any of it: the walk
    # marks itself (atexit: every exit path, stops included) so stats.py's travel rate is the real one
    import atexit
    from activity import mark
    mark("travel", "start", note=label)
    atexit.register(lambda: mark("travel", "end", note=label))
    last_pos, steps = (mx, mz), 0
    # run 34: toward Isolated Machinarium (21 tiles NW) the game's click-to-travel swung 23 tiles east over three game
    # days and into Goda's ambush: a walk that ends a leg 6+ tiles farther from the target than its closest point stops
    closest = max(abs(tx - mx), abs(tz - mz))
    while True:
        # bridge 0.23.0 walkto: the reply comes on arrival, a stop, a hostile within 4, HP under
        # 60%, a window or a zone change (an ambush); no 1.5 s polling (run 12 review)
        # run 21: one walkto ran 15 steps and 54 game hours from Hungry into Starving (HP 154 -> 89,
        # Very Sleepy 3): the hunger and sleep checks below ran only when it returned. A 20 s leg
        # hands control back every few steps (the walk goes on; the next call re-targets it).
        # run 21: even 20 s legs ran 7-27 steps and up to 79 game hours (hunger 45 -> 91, twice
        # Starving); waypoints a few tiles ahead are refused (unexplored tiles). A world-map step
        # takes ~0.75 real seconds: a 2.5 s leg is 2-3 steps, then the meal and sleep checks run
        # run 42: at x5 that 2.5 s leg was 10-15 steps, ~40 game hours: hunger 45 -> 83 and 89, twice, between checks. The leg follows the game's speed
        rate = (call("speed").get("data") or {}).get("base") or 1.0
        w = walk(tx, tz, r=near, hp=60, timeout=max(600, int(LEG_MS / max(rate, 1.0))), weak_ok=weak_ok)
        pos = (w.get("x", last_pos[0]), w.get("z", last_pos[1]))
        why = w.get("why")
        # run 42, twice: at x5 the ambush can land between two legs: the next order's world cell is "off the map" of the field, and this read as a refused walk and stopped the circuit
        if why == "refused" and "off the map" in str(w.get("error")):
            zn = (call("state")["data"].get("zone") or {})
            if not (zn["region"] if "region" in zn else "ntyris" in str(zn.get("full") or "")):
                why, w = "zone", {**w, "zone": zn.get("full")}
        if why == "zone":
            # an ambush hides the last steps (the world position isn't readable from the local
            # map): the leg's step count is a floor, not the count
            log_leg(start, frm, label, steps, f"ambush after {last_pos[0]},{last_pos[1]} (steps: at least this many)")
            if not ambush:
                stop(f"now on a local map: {w.get('zone')} - look.py!")
            outcome = handle_ambush()
            if outcome != "cleared":
                stop(f"ambush at {w.get('zone')}: {outcome}")
            s = call("state")["data"]
            z = s.get("zone") or {}
            if not (z["region"] if "region" in z else "ntyris" in str(z.get("full") or "")):
                stop(f"after the ambush still on {z.get('full')}: leave.py")
            rep = call("places", r=80)
            mx, mz = map(int, rep["data"]["me"].split(","))
            last_pos, frm, start, steps = (mx, mz), f"{mx},{mz}", s["pc"]["date"], 0
            print(f"  ambush cleared; walking on from {mx},{mz}")
            continue
        steps += max(abs(pos[0] - last_pos[0]), abs(pos[1] - last_pos[1]))
        last_pos = pos
        d_now = max(abs(tx - pos[0]), abs(tz - pos[1]))
        closest = min(closest, d_now)
        if d_now > closest + SWING_TILES:
            log_leg(start, frm, label, steps, f"swung away: {d_now} tiles off (closest {closest})")
            stop(f"the game's path swings away from {label}: {d_now} tiles off at {pos[0]},{pos[1]} (closest {closest}): "
                 "a waypoint (wgo.py X Z), another target, or Fast Travel")
        p = call("state")["data"]["pc"]
        # runs 30-31 (errors.csv): a nefia expired while I walked to it (a random site lives 7 days and places shows
        # no age), twice in two runs: each leg checks the target is still listed and stops the walk when it isn't
        # run 36: the leg ended on an ambush field, where `places` answers "not on the world map", and the empty reply
        # read as an expired Misty Cave that was still there: only a good reply can say a nefia is gone
        rep_pl = call("places", r=80) if label and "Danger Lv" in label else {}
        if rep_pl.get("ok"):
            listed = [q for q in (rep_pl.get("data") or {}).get("places") or []
                      if q.get("name", "").split(" *")[0] == label.split(" *")[0]]
            if not listed:
                log_leg(start, frm, label, steps, "the nefia expired on the way")
                stop(f"{label} is no longer listed: it expired on the way")
        if why == "arrived":
            print(f"arrived at {label} ({tx},{tz}); {p.get('date', '')}")
            log_leg(start, frm, label, steps, "arrived")
            if "--enter" in sys.argv:
                # run 28: a refused walk chained by hand into an Enter re-entered a conquered nefia; entering
                # here happens only on arrival at the named place
                acts = call("acts", dx=0, dz=0, mode="all")["data"]["acts"]
                ent = [x for x in acts if x["text"] == "Enter"]
                if not ent:
                    stop(f"arrived but no Enter at {tx},{tz}")
                call("do", i=ent[0]["i"])
                z2 = wait_until("zone", timeout=20000)
                print(f"entered: {z2.get('zone')}")
            return
        # every other end is a decision (exit 3; the review of 2026-10-23): the leg is logged first
        if why == "hostile":
            log_leg(start, frm, label, steps, f"stopped at {pos[0]},{pos[1]}: hostile close")
            stop(f"hostile close: {w.get('hostile')} Lv{w.get('hostileLv')} at {w.get('hostileDist')}")
        if why == "hp":
            log_leg(start, frm, label, steps, f"stopped at {pos[0]},{pos[1]}: HP")
            stop(f"HP {p['hp']}")
        if why == "window" and w.get("top") == "LayerShippingResult":
            # run 21: the morning shipping report stopped four walks in one evening; it's only a report
            run("close.py")
            print(f"  @ {pos[0]},{pos[1]}: closed the shipping report, walking on")
            continue
        if why in ("window", "refused", "water"):
            log_leg(start, frm, label, steps, f"stopped at {pos[0]},{pos[1]}: {why}")
            stop(f"{why}: {w.get('top') or w.get('error') or w.get('water')}")
        # travel.py's stop (retired in run 12): never walk on Hungry or with SP under 5
        if (p.get("hunger") or 0) >= THRESHOLDS["eat_at"]:
            call("cancel")
            why_not = meal_stop()  # run 21: eat on the way instead of starving or stopping
            if why_not:
                log_leg(start, frm, label, steps, f"stopped at {pos[0]},{pos[1]}: {why_not}")
                stop(f"hungry and {why_not}: look.py")
            p = call("state")["data"]["pc"]
        if (p.get("sleepPhase") or 0) >= 2 and p.get("hunger", 0) < THRESHOLDS["sleep_hunger"]:
            call("cancel")
            out = run("sleep.py", timeout=300)  # sleep.py works on the world map
            print(f"  slept on the way: {last(out)[:90]}")
            p = call("state")["data"]["pc"]
        if (p.get("burdenPhase") or 0) >= THRESHOLDS["burden_stop"]:
            # run 21: a walk from Vernis ran at Overweight and "your backpack is squashing you" took
            # 160 -> 24 HP (elin-play's status row: burden phase 3+ is fixed first); the bridge's
            # walkto refuses only at Squashed (4)
            call("cancel")
            log_leg(start, frm, label, steps, f"stopped at {pos[0]},{pos[1]}: Overweight")
            stop(f"burden phase {p.get('burdenPhase')} (Overweight): drop or store weight on a local map first")
        hungry = p.get("hungerText") not in ("", "Normal", "Filled", "Bloated", None)
        # run 34: the makeshift bed burned (a fire hound); --sleepy-ok walks a Very Sleepy me to an inn bed
        if p["sp"] < 5 or hungry or ((p.get("sleepPhase") or 0) >= 2 and "--sleepy-ok" not in sys.argv):  # run 21: Very Sleepy stops too
            call("cancel")
            log_leg(start, frm, label, steps, f"stopped at {pos[0]},{pos[1]}: hunger, sleep or SP")
            stop(f"SP {p['sp']} / hunger {p.get('hungerText')}: eat or sleep first (a bed in the pack: sleep.py)")
        if why == "stopped":
            log_leg(start, frm, label, steps, f"stopped at {pos[0]},{pos[1]}: not moving")
            stop(f"not moving at {pos}")
        here = tile_danger()
        if here > allowed:
            call("cancel")
            log_leg(start, frm, label, steps, f"stopped at {pos[0]},{pos[1]}: the path reached ambush level {here}")
            stop(f"the game's path reached ambush level {here} at {pos[0]},{pos[1]} (allowed {allowed}): "
                 f"walk via a lower waypoint (wgo.py X Z) or --danger-ok N")
        print(f"  @ {pos[0]},{pos[1]}  HP {p['hp']}  hunger {p.get('hunger')}  (still walking)")


if __name__ == "__main__":
    main()
