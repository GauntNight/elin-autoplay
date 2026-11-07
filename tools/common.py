"""Shared helpers for the tool scripts (run 12 review: fourteen copies of run(), six of walk(),
eight idle-polls and about 150 fixed sleeps were spread over the scripts).

Import with `from common import ...` (every tool adds its own folder to sys.path).

Exit-code contract for the tools (parents branch on rc, not on the text):
  0  done            1  refused (a rule, a bad argument: `refuse`)
  2  bridge error    3  stopped for a decision (`stop`: HP, a hostile, a window, a limit)

    setup()                     utf-8 on stdout and stderr (-I ignores PYTHONIOENCODING)
    run(tool, *args, timeout)   a tool as a subprocess: closes the bridge first, returns its
                                output (str) with .rc; never raises on a non-zero exit
    data(op, **kw)              call() that raises BridgeError on ok=false
    state() / pc() / top()      the state, the player, the top UI layer's name
    walk(x, z, ...)             walkto: returns the reply dict (why: arrived, stopped, hostile,
                                hp, window, zone, timeout); falls back to goto+poll on old mods
    wait_idle(timeout)          until the player has no task (a harvest, a craft, a walk)
    wait_until(until, ...)      the bridge's wait op (idle, zone, layer, moved, frames)
    cells(points)               many cell reads in one call: {(x, z): info}
    threat(hp_pct)              why to stop now, or None: HP under the floor, a hostile in view,
                                a window open
    hold(name) / put_away()     take an item in hand / empty the hands (the hotbar's Deselect)
    pick(want, candidates)      the one candidate for a name, or refuse: exact, then whole-word
                                with plurals, then a word start; ambiguity is an error, so
                                "(1" no longer picks "(11 Charges)" (run 12)
    last(text)                  the last non-empty line of a tool's output, or ""
    refuse(msg) / stop(msg)     exit 1 / exit 3 with the message on stderr
"""
import re
import subprocess
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import bridge  # noqa: E402
from bridge import call, norm  # noqa: E402,F401


class BridgeError(RuntimeError):
    pass


class Output(str):
    """A tool's combined stdout+stderr, with the exit code on .rc."""
    rc = 0


# Carried bags' slots (run 41: a bag takes one vertical and one horizontal storage wrench, 7x5 -> 8x6; the game gives no way to read
# a carried bag's size through the bridge, so the wrenched ones are listed here)
BAG_SLOTS = {"a loot bag": 48}


def bag_slots(name):
    return BAG_SLOTS.get(name, 35)


def setup():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def refuse(msg):
    print("refused: " + msg, file=sys.stderr)
    sys.exit(1)


def stop(msg):
    print("stop: " + msg)
    sys.exit(3)


WAIVERS = TOOLS.parent / "runs" / "waivers.csv"


def waiver_reason(flag):
    """The reason written after FLAG on the command line, None without the flag; a bare FLAG is refused. The user,
    2026-11-06: run 42 passed --blanket-ok on every circuit (21 ladder starts on one blanket, 14 on none, against the
    user's 3) and the close-out only said they had run out. A flag that skips a rule now says why, and log_waiver
    leaves a row that the close-out reads out."""
    if flag not in sys.argv:
        return None
    i = sys.argv.index(flag)
    why = sys.argv[i + 1].strip() if i + 1 < len(sys.argv) else ""
    if why.startswith("--") or len(why) < 8 or not re.search(r"[A-Za-z]", why):
        refuse(f"{flag} needs a reason, written after it: {flag} 'what was checked and why this goes ahead' "
               "(it goes to runs/waivers.csv and the close-out reports it)")
    return why


def log_waiver(tool, what, why):
    """A row in runs/waivers.csv each time a rule really was skipped or came up short: the close-out's list."""
    import csv
    new = not WAIVERS.exists()
    with WAIVERS.open("a", encoding="utf-8", newline="") as f:
        out = csv.writer(f)
        if new:
            out.writerow(["at", "tool", "what", "why"])
        out.writerow([time.strftime("%Y-%m-%d %H:%M"), tool, what, why])


def last(text):
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def run(tool, *args, timeout=300):
    """Run tools/TOOL as a subprocess and return its output. The bridge connection is closed
    first (one client at a time was the rule before 0.23.0; closing stays the polite default)."""
    bridge.close()
    try:
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(TOOLS / tool), *map(str, args)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        out = Output((r.stdout + r.stderr).strip())
        out.rc = r.returncode
    except subprocess.TimeoutExpired as e:
        out = Output(((e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or ""))
                     + f"\nstop: {tool} timed out after {timeout}s")
        out.rc = 3
    return out


def data(op, **kw):
    reply = call(op, **kw)
    if not reply.get("ok"):
        raise BridgeError(f"{op}: {reply.get('error')}")
    return reply["data"]


def state():
    return data("state")


def base_ready():
    """False in a new game until its base exists and tools/home.py says where (tools/newgame.py makes the marker)."""
    return not (Path(__file__).resolve().parent.parent / "runs" / "no-base.txt").exists()


def pc():
    return state()["pc"]


def overweight_stop(what):
    """Refuse a zone change at burden phase 3+ (run 42, a near-death at home: a return scroll at 161% cost 269 -> 57). Scene.cs: entering any zone
    from anything but the world map at phase 3 rolls 1 in 5 for a tumble (phase 4 always), Chara.Stumble: MaxHP x burden% / 200, or / 100 on an
    up stairway, which at 100%+ is a whole bar. Walking on a local map at phase 3 costs only ~a tenth of that, 1 turn in 30. `--burden-ok` to pass."""
    p = pc()
    if p.get("burdenPhase", 0) >= 3 and "--burden-ok" not in sys.argv:
        refuse(f"{what}: burden {p.get('burden')}% (phase {p.get('burdenPhase')}): a zone change can tumble for MaxHP x burden% / 200 "
               f"({int((p.get('maxHp') or 0) * (p.get('burden') or 0) / 200)} HP here): shed weight first, or --burden-ok")


def top():
    return (state().get("layers") or {}).get("top")


def crawl_up(word="Onward"):
    """Answer the death prompt: the last word, then Crawl up (never Buried). Start Run 3: a loop's clear_windows closed the prompt instead, which left the game with HP under 0,
    no dialog and no way on. True when the choice was clicked."""
    if top() == "Dialog":
        call("input", text=word)
    for _ in range(25):
        time.sleep(0.2)
        hit = [b for b in call("buttons")["data"]["buttons"] if (b.get("text") or "").endswith("Crawl up")]
        if hit:
            call("click", i=hit[0]["i"])
            time.sleep(1.5)
            return True
    return False


def wait_until(until="idle", n=1, timeout=15000, **kw):
    """The bridge's deferred wait. Returns the reply data (done, why, x, z, hp, zone, top, ai)."""
    reply = call("wait", until=until, n=n, timeout=timeout, **kw)
    if reply.get("ok"):
        return reply["data"]
    if "unknown op" in (reply.get("error") or ""):  # a mod older than 0.23.0: poll
        t0 = time.time()
        while time.time() - t0 < timeout / 1000:
            p = pc()
            if until == "idle" and (p.get("ai") or "").startswith("NoGoal"):
                return {"done": True, "why": "done", "x": p["x"], "z": p["z"], "hp": p["hp"]}
            time.sleep(0.5)
        p = pc()
        return {"done": False, "why": "timeout", "x": p["x"], "z": p["z"], "hp": p["hp"]}
    raise BridgeError(f"wait: {reply.get('error')}")


def wait_idle(timeout=20000):
    return wait_until("idle", timeout=timeout)


def walk(x, z, r=4, hp=60, timeout=30000, stairs=False, weak_ok=False):
    """Walk to an explored cell. The reply says how it ended: arrived, stopped (the path ended
    short: blocked or occupied), hostile (within r: the walk was cancelled), hp, window, zone,
    timeout. `stairs=True` allows a stairway as the target (it takes the stairs)."""
    reply = call("walkto", x=x, z=z, r=r, hp=hp, timeout=timeout, stairs=stairs, weakOk=weak_ok)
    if reply.get("ok"):
        return reply["data"]
    err = reply.get("error") or ""
    if "unknown op" in err:  # a mod older than 0.23.0
        g = call("goto", x=x, z=z)
        if not g.get("ok"):
            return {"done": False, "why": "refused", "error": g.get("error")}
        t0, last_pos, still = time.time(), None, 0
        while time.time() - t0 < timeout / 1000:
            p = pc()
            pos = (p["x"], p["z"])
            if pos == (x, z):
                return {"done": True, "why": "arrived", "x": x, "z": z, "hp": p["hp"]}
            still = still + 1 if pos == last_pos else 0
            if still >= 6 or (p.get("ai") or "").startswith("NoGoal"):
                return {"done": False, "why": "stopped", "x": pos[0], "z": pos[1], "hp": p["hp"]}
            last_pos = pos
            time.sleep(0.5)
        return {"done": False, "why": "timeout", "x": p["x"], "z": p["z"], "hp": p["hp"]}
    return {"done": False, "why": "refused", "error": err}


def walk_beside(x, z, **kw):
    """Walk to a free cell next to (x, z): installed things and creatures can't be stood on."""
    p = pc()
    here = (p["x"], p["z"])
    if max(abs(here[0] - x), abs(here[1] - z)) <= 1 and not (cells([here]).get(here) or {}).get("door"):
        return {"done": True, "why": "arrived", "x": here[0], "z": here[1]}
    cands = sorted(((x + dx, z + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1) if (dx, dz) != (0, 0)),
                   key=lambda c: abs(c[0] - here[0]) + abs(c[1] - here[1]))
    info = cells(cands)
    # run 18: from a doorway nothing beside it can be opened or placed (the Storehouse's boxes by
    # its door, the Farmhouse's farm box): door cells last
    cands.sort(key=lambda c: bool((info.get(c) or {}).get("door")))
    res = {"done": False, "why": "no free neighbour"}
    for c in cands:
        ci = info.get(c) or {}
        if ci.get("blocked") or ci.get("water") or not ci.get("floor"):
            continue
        res = walk(c[0], c[1], **kw)
        if res.get("why") in ("arrived", "hostile", "hp", "window", "zone"):
            return res
    return res


def cells(points):
    """{(x, z): cell info} for absolute map cells, one bridge call (bridge 0.23.0)."""
    p = pc()
    pts = list(points)
    reply = call("cells", cells=[[x - p["x"], z - p["z"]] for x, z in pts])
    if reply.get("ok"):
        return dict(zip(pts, reply["data"]["cells"]))
    out = {}
    for x, z in pts:  # an older mod: one call each
        r = call("cell", dx=x - p["x"], dz=z - p["z"])
        out[(x, z)] = r.get("data") or {}
    return out


# The numbers of elin-play's thresholds table, in one place (the review of 2026-10-23: the table
# said 8 for the floor gate while ladder.py said 7, 70 for Hungry while farmday said 80, 3 cells
# for a kamikaze while delve threw at 2). The tools read these; hygiene.py checks that the table
# and the tools agree with them.
THRESHOLDS = {
    "loop_hp": 80,          # a home loop stops under this (springday, trainday, minewalls)
    "dungeon_hp": 70,       # delve/ladder stop and drink here
    "walk_hp": 60,          # walkto's default floor
    "teleport_hp": 50,      # read teleport at once under this after drinking
    "heal_to": 80,          # after a bad fight, heal to this before going on
    "hit_pct": 15,          # a turn that cost more than this and left me under dungeon_hp: teleport
    "hit_pct_any": 25,      # run 24: a turn that cost more than this: teleport at any HP
    "last_swing_hp": 40,    # run 37: a lone foe at 10% or less gets one more round if the same hit again leaves this
    "hungry": 70,           # no loop works at Hungry (70+) and none sleeps hungry
    "sleep_hunger": 50,     # sleep.py refuses from here: eat first
    "eat_at": 45,           # the loops eat from here
    "max_danger": 15,       # run 43: raised one step at Lv38 / HP 277, unattended limit 13 -> 14: Traditional Cave B4, danger 13 (the
                            # unattended limit), cleared without a drink or a teleport, 12 HP lost on the floor.
                            # run 40: raised one step at Lv35 / HP 237, unattended limit 12 -> 13: Forgotten Ruin B5 and Isolated
                            # Machinarium B3, both danger 12 (the unattended limit), cleared without a drink or a teleport
                            # (the rule: elin-play's floor gate); the Swarm ability is new too.
                            # run 36: lowered one step: Dark Ruin B5 at danger 12 (unattended limit 13) took 218 -> 0 in one
                            # round with an orc and an explosion (the auto-combat net held at 0; two teleports, a potion,
                            # an evacuation under a countdown); unattended play now stops at 12. Before:
                            # run 34: Chilly Cave B3 at danger 13 (the limit) conquered without a drink or a teleport (Kaberg
                            # healed to 98 by the spell; my HP 202 -> 208); run 33: Vernis Mine B5 (10), B6 (11), B7 (12) without a drink from a fight (B6: one teleport from an alien; B7: one drink after a trolley ride, now cancelled by common.ready); the floor gate (delve.py MAX_DANGER); unattended play: one less
                            # (run 24: 8 -> 9 at Lv23 / PV 61 on run 21's danger-8 den, 0 HP lost, no drink;
                            # run 27: 9 -> 10 at Lv26 / HP 198 on the Rustic Ruin's danger-9 B2, 6 HP lost, no drink)
    "route_max": 20,        # run 21: the worst ambush level wgo.py walks across without --danger-ok (at
                            # Lv21: level 9-10 ambushes cost under 10% HP; a level 21 field had a Lv22 golem)
    "unattended_minus": 1,
    "kamikaze_dist": 5,     # throw at a suicide attacker from this far, never adjacent (run 41: 4 -> 5: Warped Ruin B5 262 -> 142 through a throw; run 40: 3 -> 4: a bomb rock's blast
                            # on Ominous Forest B1 took 234 -> 115, 49%, through delve's own throw; run 35's took 58%)
    "swarm": 6,             # 6+ hostiles, or 4+ with one at or above my level: teleport and leave
    "swarm_above": 4,
    "swarm_weak_below": 12, # run 21: hostiles this many levels under mine count half toward a swarm
    "avoid_ignore_below": 15,  # run 43: an avoid-group kind this far under my level is an ordinary foe (a Lv19 master, 3 HP at Lv38)
    "swarm_ignore_below": 25,  # run 43: twelve Lv4 geese at Lv37, PV 82 stopped a walk as a swarm of 6; this far under mine they don't count
                            # (two stops on Lv1-7 crowds at Lv21; "HP decides, not the count", run 04)
    "swarm_ability_min": 3, # run 40: the Swarm ability (a 0.9x blow on every hostile within 3 cells) replaces a swing from this many
    "swarm_ability_sp": 40, # run 40: SP comes back only from sleep; Swarm costs 12 and never spends the last of it
    "avoid_levels": 8,      # an "avoid" kind within this many levels of mine stops delve and fight
    "avoid_seen_pct": 30,   # run 33: an "avoid" kind at ANY level once a recorded fight cost this % of my HP (aliens Lv18 at Lv30, runs 32-33)
    "pack_max": 42,         # the 44th stack is refused; loot stops here
    "escape_teleports": 2,  # the escape reserve: leave the floor before spending it
    "escape_heals": 3,
    "burden_stop": 3,       # Overweight: no loop goes on; 4 is Squashed (the game refuses to move)
}
# A game's own numbers (2026-11-05, tools/trial.py): runs/thresholds.json is gitignored and leaves with that game's records, so
# level 1 trials get a level 1 floor gate and route limit without touching this table; elin-play's table is checked against TRACKED.
TRACKED_THRESHOLDS = dict(THRESHOLDS)
_LOCAL_NUMBERS = Path(__file__).resolve().parent.parent / "runs" / "thresholds.json"
if _LOCAL_NUMBERS.exists():
    import json as _json
    THRESHOLDS.update(_json.loads(_LOCAL_NUMBERS.read_text(encoding="utf-8")))

# Conditions under which no action can be trusted (blind: no targeting; paralysed, asleep,
# fainted: nothing happens; confused: steps go astray; suffocating: get out first).
BAD_CONDITIONS = ("ConBlind", "ConParalyze", "ConSleep", "ConFaint", "ConConfuse", "ConDim", "ConSuffocation")


def ready(s=None, *, hp=60, hunger=70, sp=None, idle=True, world_ok=False, nefia_ok=True,
          hostile_r=None, weak_ok=False, allow=("LayerInventory",), burden=3, returning_ok=True,
          hostiles=True):
    """Why NOT to act now, or None: one state read, the irreversible things first (the review of
    2026-10-23: eight tools had their own partial copy, and the recorded errors fell between them).
      a window other than a container's, a context menu, a dialog (the game swallows the action);
      the player is mid-task (idle=True): a craft, a walk, a sleep, Pass Time, auto-combat;
      a BAD_CONDITION; a zone switch in progress; HP under hp% (None: skip);
      Starving / Very Hungry, or hunger >= `hunger` (None: skip); SP under sp;
      burden phase >= `burden` (3 Overweight, 4 Squashed; None: skip);
      the world map unless world_ok; a nefia unless nefia_ok (sleep); a walk heading into deep water;
      a hostile in view within hostile_r (None: anywhere in view; hostiles=False skips the check:
      fight and delve decide that themselves), weak ones skipped with weak_ok (3+ levels below
      mine); a return countdown unless returning_ok (reading scrolls).
    Tools do `why = ready(...); if why: stop(why)` (exit 3)."""
    s = s or state()
    if not s.get("inGame", True):
        return "not in game"
    layers = s.get("layers") or {}
    top_layer = layers.get("top")
    if top_layer == "LayerShippingResult":
        # run 21: the morning shipping report stopped five walks and a ladder floor; it's only a
        # report (the income is already paid): close it and read the state again
        call("closetop")
        wait_until("frames", n=10, timeout=1500)
        s = state()
        layers = s.get("layers") or {}
        top_layer = layers.get("top")
    if top_layer and top_layer not in allow:
        return f"a window is open ({top_layer}): talk.py / read.py, then close.py"
    if layers.get("menu"):
        return "a context menu is open: click an entry or closetop"
    if s.get("drama"):
        return "a dialog is open: talk.py first"
    p = s["pc"]
    if (p.get("ai") or "").startswith("AI_Trolley"):
        # run 33: a walk over a mine trolley boards it (TraitTrolley.OnActivateTrap) and the ride ignores damage until
        # HP < 1/3 (AI_Trolley.CancelWhenDamaged); it rolled on after the ladder stopped and a samurai took 204 -> 113
        # twice in the Vernis Mine. Get off at once (CanManualCancel), whatever the caller is.
        call("cancel")
        wait_idle(3000)
        s = state()
        p = s["pc"]
    if idle and (p.get("ai") or "").endswith((":Success", ":Fail")):
        # run 21: a walk that had just ended (AI_Goto:Success) refused reap.py and talkto.py as busy;
        # the goal clears on the next tick
        wait_idle(3000)
        s = state()
        p = s["pc"]
    if idle and not (p.get("ai") or "NoGoal").startswith(("NoGoal", "GoalEndTurn")):
        return f"busy: {p.get('ai')} (wait_idle first)"
    bad = [c for c in p.get("conditions") or [] if c in BAD_CONDITIONS]
    if bad:
        return f"condition {bad[0]}: wait it out"
    if s.get("transit"):
        return "a zone switch is in progress"
    if hp is not None and p.get("maxHp") and p["hp"] * 100 < hp * p["maxHp"]:
        return f"HP {p['hp']}/{p['maxHp']} under {hp}%"
    if hunger is not None:
        text = (p.get("hungerText") or "").lower()
        if "starving" in text or "very hungry" in text or (p.get("hunger") or 0) >= hunger:
            return f"hungry ({p.get('hungerText') or p.get('hunger')}): eat first"
    if sp is not None and (p.get("sp") or 0) < sp:
        return f"SP {p.get('sp')} under {sp}"
    if burden is not None and (p.get("burdenPhase") or 0) >= burden:
        return f"{p.get('burdenText') or 'burden'} (phase {p.get('burdenPhase')}): drop or store weight"
    z = s.get("zone") or {}
    on_world = z.get("region") if "region" in z else "ntyris" in (z.get("full") or "")
    if on_world and not world_ok:
        return "on the world map: enter a local map first"
    if z.get("nefia") and not nefia_ok:
        return "in a nefia: never here"
    if p.get("pathWater"):
        return f"the walk heads into deep water at {p['pathWater']}: cancel it"
    if not returning_ok and p.get("return"):
        return f"a return is counting down ({p['return'].get('turns')} turns): never read another scroll"
    if not hostiles or (hostile_r is not None and hostile_r < 0):
        return None
    foes = [c for c in s.get("nearby") or [] if c.get("hostile")]
    if weak_ok:
        foes = [c for c in foes if (c.get("lv") or 0) > (p.get("lv") or 0) - 3]
    if hostile_r is not None:
        foes = [c for c in foes if c.get("dist", 99) <= hostile_r]
    if foes:
        f = min(foes, key=lambda c: c["dist"])
        return f"hostile in view: {f['name']} Lv{f.get('lv')} at {f['dist']}"
    return None


def threat(hp_pct=60, s=None):
    """Why to stop now, or None (a window, HP under the floor, a hostile in view): the older,
    narrower check; ready() is the full one."""
    return ready(s, hp=hp_pct, hunger=None, idle=False, world_ok=True, burden=None)


def pack_full(limit=None, s=None):
    """True when the pack holds `limit` stacks or more (the 44th is refused by the game; loot.py
    stops at 42, run 12 lost a skin picked up into a full pack)."""
    limit = limit or THRESHOLDS["pack_max"]
    p = (s or state())["pc"]
    n = p.get("stacks")
    if n is None:  # a mod before 0.30.0
        n = sum(1 for i in data("inv")["items"] if not i.get("equipped"))
    return n >= limit


# The user's rule (run 29: "We should always have a full set of gear, the best gear of course, but always a
# full set", after the arm slot sat empty with ☆Forest Gloves in the pack): every slot the body has, filled.
# The race figure (races.json) is head, neck, torso, back, hand x2, finger x2, arm, waist, leg, foot; no item
# category equips to the leg (categories.json), and the back is the Single Ether Wing's (an ether disease:
# speed +14) while it lasts. Slot ids are the game's SLOT elements.
GEAR_SLOTS = {30: ("head", 1), 31: ("neck", 1), 32: ("torso", 1), 34: ("arm", 1), 35: ("hand", 2),
              36: ("finger", 2), 37: ("waist", 1), 39: ("foot", 1), 44: ("toolbelt", 1), 45: ("light source", 1)}


def empty_slots():
    """The GEAR_SLOTS not filled by worn items, as names ("finger (1 of 2)"); [] when the set is full.
    Maps each worn item's id to its category's slot through the exported game tables (knowledge/game)."""
    import json
    game = Path(__file__).resolve().parent.parent / "knowledge" / "game"
    cats = {c["id"]: c for c in json.loads((game / "categories.json").read_text(encoding="utf-8"))}
    things = {t["id"]: t.get("category") for t in json.loads((game / "things.json").read_text(encoding="utf-8"))}

    def slot_of(cat):
        for _ in range(8):  # a category without its own slot takes its parent's
            c = cats.get(cat) or {}
            if c.get("slot"):
                return int(c["slot"])
            cat = c.get("parent")
            if not cat:
                return None
        return None

    worn, hands = {}, []
    for i in data("inv")["items"]:
        if i.get("equipped"):
            s = slot_of(things.get(i.get("id")))
            if s:
                worn[s] = worn.get(s, 0) + 1
            if s == 35:
                hands.append(things.get(i.get("id")))
    # run 37's close: a lone melee weapon is the game's two-hand style (CharaBody.GetAttackStyle: any other thing in
    # a hand, a shield too, switches it off), worth x1.5 damage and +25 to-hit: the axe alone 22.8 a turn vs Lv33
    # against 9.5 with the Dreadbane Small Shield (fact). The second hand is left empty on purpose, so it's full.
    if len(hands) == 1 and hands[0] != "shield":
        worn[35] = 2
    # run 30: the ether disease Thick Neck ("You can't equip an item on your neck currently") blocks the neck
    # slot as the Ether Wing blocks the back (left out of GEAR_SLOTS since run 29): a blocked slot isn't empty
    blocked = set()
    try:
        if "etherNeck" in (data("skills").get("ether") or {}):
            blocked.add(31)
    except Exception:  # noqa: BLE001 (an older bridge: count the slot)
        pass
    return [name if need == 1 else f"{name} ({worn.get(sid, 0)} of {need})"
            for sid, (name, need) in GEAR_SLOTS.items() if worn.get(sid, 0) < need and sid not in blocked]


def party_cap(st=None):
    """(allies, cap, CHA): the party against the game's ally cap, Player.MaxAlly = min(max(CHA / 10, 1), 5) +
    Party Animal's rank (featParty). Run 35: CHA fell to 18 in run 34, the cap to 2, and three allies cost the whole
    party 20% speed (Chara.RefreshSpeed exceedParty) plus Lonely Soul's 3% on my speed and max HP: 110 -> 84 for half
    a run, unseen (fact #1093)."""
    st = st or state()
    allies = len(st.get("party") or [])
    cha = next(m for m in data("power")["party"] if m.get("pc"))["attrs"]["CHA"]
    cap = min(max(cha // 10, 1), 5) + int((data("skills").get("feats") or {}).get("featParty", 0))
    return allies, cap, cha


def grid_slots(mine=True):
    """The inventory grid's slots (opening the pack if needed), mine or the open container's."""
    bs = open_inventory()
    out = []
    for b in bs:
        if not b.get("card") or "ButtonGrid inventory" not in (b.get("name") or ""):
            continue
        is_mine = b["mine"] if "mine" in b else "UIInventory/List" in (b.get("path") or "")
        if bool(is_mine) == mine:
            out.append(b)
    return out


def _charges(card):
    m = re.search(r"\((\d+) charges?\)", (card or "").lower())
    return int(m.group(1)) if m else -1


def grab(name, exclude=("cursed", "doomed"), prefer=None, what="item"):
    """Take `name` in hand through its own Grab, in process (no item.py subprocess). Whole-word
    matching with a refusal on two different names (common.pick); a stack whose name holds an
    excluded word is skipped unless the name asks for it (run 17: a cursed cure potion was thrown
    at an escort); prefer="charges" takes the fullest rod. Returns the held item's name, or None
    when nothing matched; a stack already in hand counts as held."""
    held = pc().get("held")
    if held and matches(name, [held]):
        return held
    wait_idle(3000)  # invacts refuses "busy" right after a walk's arrival (the smoke test of 0.30.0)
    slots = grid_slots(mine=True)
    want = (name or "").lower()
    cands = [b for b in slots if not any(w in b["card"].lower() and w not in want for w in exclude)]
    hits, ambiguous = stack_hits(name, cands)
    if not hits:
        return None
    if ambiguous and prefer == "charges":
        # run 21: two rods of cure minor wound (11 and 6 charges) were refused as "several items" while
        # Kaberg lay at 0 HP: names that differ only in their charges are one item here; run 37: a blessed
        # and a plain rod of cure minor wound were refused the same way with the mercenary at 31%
        ambiguous = len({re.sub(r"\s*\(\d+ charges?\)", "", re.sub(r"\bblessed\s+", "", _key(b["card"])))
                         for b in hits}) > 1
    if ambiguous:
        refuse(f"{name!r} matches several {what}s: " + " | ".join(sorted({b['card'] for b in hits})[:8]) + " (give the full name)")
    if prefer == "charges":
        hits.sort(key=lambda b: -_charges(b["card"]))
    for b in hits:
        rep = call("invacts", i=b["i"])
        if not rep.get("ok"):
            print(f"grab: invacts refused ({rep.get('error')})", file=sys.stderr)
            continue
        acts = (rep.get("data") or {}).get("acts") or []
        g = [a for a in acts if a["text"].lower() == "grab"]  # never "Grab as furniture" (run 08)
        if not g:
            continue
        r = call("invdo", i=g[0]["i"])
        if not r.get("ok"):
            print(f"grab: invdo refused ({r.get('error')})", file=sys.stderr)
            continue
        for _ in range(10):
            held = pc().get("held")
            if held:
                return held
            time.sleep(0.2)
    return pc().get("held") or None


def hold(name):
    """Take an item in hand through its own Grab. Returns the held item's name or None."""
    out = run("item.py", name, "Grab")
    if out.rc != 0 and "held now" not in out:
        return None
    return (pc().get("held") or None)


def open_inventory():
    """Open the pack's grid if it isn't open. Run 17 (as run 15 with the other menus): after a
    while the injected MenuInventory key stopped opening it, and item.py, bag.py and hotbar.py
    all failed with "no inventory slot"; the hotbar's own Inventory button (a HotItemLayer whose
    hover reads "Inventory(Tab)") still works. Returns the buttons listing."""
    def pack_open(bs):
        return any(b.get("in") == "pack" and "UIInventory/List" in (b.get("path") or "") for b in bs)
    bs = call("buttons", all=True)["data"]["buttons"]
    if pack_open(bs):
        return bs
    call("act", action="MenuInventory")
    time.sleep(1.2)
    bs = call("buttons", all=True)["data"]["buttons"]
    if pack_open(bs):
        return bs
    for b in bs:
        if b.get("hot") == "HotItemLayer":
            tip = (call("hover", i=b["i"]).get("data") or {}).get("texts") or [""]
            if tip[0].startswith("Inventory"):
                call("buttons", all=True)
                call("click", i=b["i"])
                time.sleep(1.2)
                break
    return call("buttons", all=True)["data"]["buttons"]


def put_away():
    run("hotbar.py", "--deselect")


def act(x, z, text, mode="all"):
    """Do the act on the absolute cell (x, z) whose text starts with `text` (unpack.py's helper,
    shared since the 2026-10-23 review; seven tools used it). Returns the act's full text or None."""
    p = pc()
    acts = call("acts", dx=x - p["x"], dz=z - p["z"], mode=mode)["data"]["acts"]
    hit = [a for a in acts if a["text"].lower().startswith(text.lower())]
    if hit:
        call("do", i=hit[0]["i"])
        return hit[0]["text"]
    return None


def contents():
    """The cards in the open container's grid (a box or a package window)."""
    return [b["card"] for b in call("buttons")["data"]["buttons"]
            if b["name"].startswith("ButtonGrid inventory grid") and b.get("card")]


# Junk a hammer breaks into scrap (run 13, TaskHarvest.HarvestThing: an installed thing becomes its
# first ingredient, ~91% for one item; things.json: these junk ids are all ['scrap']). The gold lucky
# cat gives a gold ingot instead, also wanted. Scrap binds the blacksmith's table (G11, G6) and bolts,
# so these are never garbage: loot keeps them, trash.py doesn't dump them, scrap.py breaks them.
_SCRAP_WORDS = r"(empty cans?|toasters?|research equipments?|mining equipments?|light stands?|" \
               r"flotsams? from the north|modern arts?|lucky cats?)"
_SCRAP_PLAIN = r"(tools?|pots?)"  # too common as words: only as the whole name ("a tool", "2 pots")


# the same junk by thing id (things.json components ['scrap']; 1180 the gold lucky cat: ingots)
SCRAP_IDS = {"529", "1170", "236", "235", "533", "228", "229", "150", "151", "153", "170", "575",
             "534", "1186", "1203", "1245", "1180"}


def hammer_scrap(name, tid=None):
    """True for junk the hammer turns into scrap (or the gold lucky cat's ingot)."""
    if tid is not None and str(tid) in SCRAP_IDS:
        return True
    n = (name or "").strip().lower()
    if re.search(r"(?<![a-z])" + _SCRAP_WORDS + r"(?![a-z])", n):
        return True
    m = re.fullmatch(r"(an?|\d+) (?:(\w+) )?" + _SCRAP_PLAIN, n)
    return bool(m) and m.group(2) not in ("bottomless", "butcher's", "flower")


_PLURAL = (("scrolls of", "scroll of"), ("potions of", "potion of"), ("rods of", "rod of"),
           ("pieces of", "piece of"), ("tufts of", "tuft of"), ("seeds of", "seed of"), ("pairs of", "pair of"))


def _key(s):
    s = re.sub(r"^(an?|the|\d+)\s+", "", (s or "").strip().lower())
    for a, b in _PLURAL:
        s = s.replace(a, b)
    # run 21: "pile of bread" missed "4 piles of bread" and "corpse of" missed "2 corpses of ...":
    # any "<word>s of" reads as "<word> of" (both sides of a comparison get the same treatment)
    return re.sub(r"\b([a-z]+?)s of\b", r"\1 of", s)


def _name_of(c):
    return c if isinstance(c, str) else (c.get("name") or c.get("card") or "")


def named(c):
    """A special (named) creature from the bridge's state: run 37's **death** (Earthy Cave B3: the master 『Hot guy』's
    blast, 216 -> -478) showed the state lists it as plain "Hot guy": the 『』 marks are only in the message log, so
    run 33's `"『" in name` checks never fired. Ordinary kinds read "a hot guy" / "an orc"; a special one is capitalised
    with no article."""
    n = str(c.get("name") or "") if isinstance(c, dict) else str(c or "")
    return "『" in n or (n[:1].isupper() and not n.startswith(("A ", "An ", "The ")))


def matches(want, candidates, key="card"):
    """Every candidate whose name means `want`, at the best level that has any: an exact name;
    a whole word (a stack's plural counts as its singular, so "(1" matches "(1 Charge)" and not
    "(11 Charges)"); a word start. Candidates are strings or dicts (named by `key`, else "name")."""
    def nm(c):
        return c if isinstance(c, str) else (c.get(key) or c.get("name") or "")
    w = _key(want)
    if not w:
        return []
    levels = (
        lambda n: _key(n) == w,
        lambda n: re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", _key(n)) is not None,
        lambda n: re.search(r"(?<![a-z0-9])" + re.escape(w), _key(n)) is not None,
    )
    for test in levels:
        hits = [c for c in candidates if test(nm(c))]
        if hits:
            return hits
    return []


def stack_hits(want, candidates, key="card"):
    """(hits, ambiguous) for inventory slots: an exact full name (count included) wins; otherwise
    matches(). Stacks of one item that differ only in their count ("12 mushrooms +1", "9 mushrooms
    +1") are one thing, not an ambiguity (run 13: item.py and bag.py refused them)."""
    def nm(c):  # a slot's widget is "name"; the item is `key` ("card")
        return c if isinstance(c, str) else (c.get(key) or c.get("name") or "")
    w = (want or "").strip().lower()
    exact = [c for c in candidates if nm(c).strip().lower() == w]
    hits = exact or matches(want, candidates, key)
    return hits, len({_key(nm(c)) for c in hits}) > 1


def pick(want, candidates, what="item", quiet=False, key="card"):
    """The one thing `want` names among the candidates (several stacks of the same name count as
    one thing: the first is returned). Different names at the winning level are an error listing
    them (or None with quiet=True); no hit is None."""
    hits = matches(want, candidates, key)
    if not hits:
        return None
    names = sorted({_key(c if isinstance(c, str) else (c.get(key) or c.get("name") or "")) for c in hits})
    if len(names) > 1:
        if quiet:
            return None
        refuse(f"{want!r} matches {len(names)} {what}s: " + " | ".join(names[:8]) + " (give the full name)")
    return hits[0]
