"""Go down a multi-floor dungeon one floor at a time (run 20, the user: "we need some dungeons ... to
level up two weapon skill"): on each floor delve.py until the floor is explored, loot.py, wrecks.py,
a QuickSave, then the stairway that isn't the way in, and down. Lesimas and other quest dungeons
aren't nefias, so delve.py's floor gate skips them: the gate here covers every floor.

Before the first floor (unless --kit-ok) the escape kit is counted through power.kit() with the
backpack open (errors row 44: the backpack's scrolls were invisible): fewer than 2 scrolls of
teleport (THRESHOLDS escape_teleports), fewer than 3 cure potions (escape_heals), no scroll of
evacuation or no scroll of return is a refusal (exit 1).

Stops (exit 3, "stop: ...") for a decision, never fights past one:
  - the floor's danger is over the cap (go back up the stairs I came down: the arrival cell)
  - delve.py stopped (rc 3: HP, a swarm, an avoid kind, a window, blindness) or refused (rc 1);
    its own floor ends ("step limit", "floor explored", "stairs found") are rc 0 and go on
  - HP under 80% after a floor (THRESHOLDS heal_to), SP under 10, Sleepy (sleep first, on the
    overworld: never in a dungeon), a meal that didn't lower hunger
  - no way down (the bottom, or a locked stairway: Use it by hand when the story says so)
  - `stopjob.py ladder` asked for it (job.register, the way springday registers)
Exit 0 after FLOORS floors. The run is marked in runs/activity.csv (activity.mark "nefia", with
the floors done at every exit).

usage: python -I tools/ladder.py [MAX_DANGER=delve.MAX_DANGER] [FLOORS=3] [--solo] [--expendable]
                                 [--no-wrecks] [--in X,Z] [--unattended] [--kit-ok] [--blanket-ok]
  --expendable  the ally is a shield (delve.py --expendable, the user's rule from run 16): her HP stops nothing
  --in X,Z  the way in on the first floor when I am no longer standing on it
  --unattended  the danger cap one lower (THRESHOLDS unattended_minus): nobody is watching the screen
  --kit-ok  skip the escape-kit count (a deliberate short trip)
  --blanket-ok  waive only the fireproof blanket (run 36: none for sale; the rest of the kit is still counted)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import THRESHOLDS, Output, call, data, last, named, pc, refuse, run, setup, state, stop, wait_idle, wait_until, walk, walk_beside  # noqa: E402
from activity import mark  # noqa: E402
from job import register, stop_requested  # noqa: E402
import delve  # noqa: E402
import farmday  # noqa: E402
import power  # noqa: E402

DEFAULT_MAX_DANGER = delve.MAX_DANGER  # one number for both tools (hygiene.py checks the table against it)
# run 24: a cap given here reached only this file's own check, and delve.py refused the floor on its
# own gate: every delve call carries the cap (set in main)
GATE = []
OK_STOPS = ("step limit", "floor explored", "stairs found")
FLOORS_DONE = 0
POTIONS_THIS_FLOOR = 0  # run 35: potions drunk at heal stops on the current floor (spell_heal)
POTION_FLOOR = [None]


def zone():
    return state().get("zone") or {}


def depth(full):
    """How deep a zone id is: Zone_dungeon@-3 -> 3; a surface map (@0) or the world map -> 0."""
    m = re.search(r"@-(\d+)$", str(full or ""))
    return int(m.group(1)) if m else 0


def asked():
    if stop_requested("ladder"):
        stop("asked (stopjob.py ladder)")


def kit_check():
    """Count the escape kit with the backpack open (power.kit counts the open bag windows too, or
    will: a key it doesn't report is not counted and said so). Refuses when short unless --kit-ok."""
    run("bag.py", "backpack")  # the scrolls ride in the backpack (errors row 44)
    try:
        k = power.kit() or {}
    finally:
        run("close.py")
    short = []

    def need(key, n, label=None):
        v = k.get(key)
        if isinstance(v, (int, float)) and v < n:
            short.append(label or f"{key} {v} (want {n})")
    need("teleport", THRESHOLDS["escape_teleports"])
    # run 24: cure potions don't keep (Ether Hand, Potion Addict): a healing rod's charges count too
    # run 25: the Cure Minor Wound spell's casts count too (power.kit "heal casts": stock and MP / 5)
    heals = (k.get("cure potions") or 0) + (k.get("cure rod charges") or 0) + (k.get("heal casts") or 0)
    if heals < THRESHOLDS["escape_heals"]:
        short.append(f"heals {heals}: cure potions + healing-rod charges + heal casts (want {THRESHOLDS['escape_heals']})")
    need("return", 1, "no scroll of return")
    evac_key = next((x for x in k if "evac" in x.lower()), None)
    if evac_key:
        need(evac_key, 1, "no scroll of evacuation")
    # run 34 (errors.csv, 490-01-25): a fire hound's breath burned an ancient book and used up both blankets, and
    # the next nefias ran with none (leave.py only warns): a nefia needs one charged fireproof blanket carried
    blankets = 0
    try:
        def walk_(items):
            n = 0
            for it in items or []:
                low = it["name"].lower()
                m = re.search(r"\((\d+) charges?\)", low)
                if "fireproof blanket" in low and (m is None or int(m.group(1)) > 0):
                    n += it.get("num") or 1
                n += walk_(it.get("items"))
            return n
        blankets = walk_(data("stock")["pack"])
    except Exception:  # noqa: BLE001 - an unread pack is reported, not refused
        blankets = -1
    # run 36: the blanket burned out and neither Aquli Teola seller had one: --blanket-ok waives only this line (the
    # escape kit itself is fire-safe: rods of teleport, the Evacuation spell), never the teleports, heals or return
    if blankets == 0 and "--blanket-ok" in sys.argv:
        print("  kit: no charged fireproof blanket (--blanket-ok: scrolls and books can burn)")
    elif blankets == 0:
        short.append("no charged fireproof blanket (fire burns the scrolls and books: Gizbird in Mysilia, Sesa or Sayig in Aquli Teola, the loom)")
    shown = [f"{x}: {k[x]}" for x in ("teleport", "cure potions", "cure rod charges", "heal casts", "return") if x in k]
    shown.append(f"evacuation: {k[evac_key]}" if evac_key else "evacuation: not counted by power.kit")
    shown.append(f"blankets: {blankets if blankets >= 0 else 'unread'}")
    print("  kit: " + ", ".join(shown))
    if short:
        refuse("the escape kit is short: " + "; ".join(short) + " (buy or fetch it, or --kit-ok for a deliberate short trip)")


def room_check():
    """run 33 (errors.csv): the bags were never unloaded between nefias and the pack grid sat full on most floors:
    meals refused ('a meal would fall to the floor'), two skill books nearly left in boss chests. elin-play's rule
    (unload at home every two nefias) was text; a ladder now starts only with 3+ free grid cards."""
    grid = sum(1 for i in call("inv")["data"]["items"] if not i.get("equipped"))
    free = 35 - grid  # packcheck.GRID_CARDS
    if free < 3:
        # run 34: four refusals in one run for one or two cards that purge.py --free 3 found at once: try it first
        print(f"  room: {free} free cards: purge.py --free 3")
        # run 35: twice purge stopped on a hostile at the entrance (a kamikaze yeek, a hot guy, both adjacent) and the
        # ladder refused, leaving me beside an exploder: clear the view by delve's rules first, then purge
        if any(c.get("hostile") for c in state().get("nearby") or []):
            clear_view("--solo" in sys.argv)
        run("purge.py", "--free", "3", timeout=600)
        grid = sum(1 for i in call("inv")["data"]["items"] if not i.get("equipped"))
        free = 35 - grid
    if free < 3:
        refuse(f"the pack grid has {free} free cards (want 3): unload at home (packcheck.py --move, stock.py --ship) "
               "or drop junk before a dungeon")


def ether_check():
    # run 33: an ether disease (Enlarged Head at corruption 101) cut END 37 -> 21 and max HP 199 -> 150 on a world-map
    # walk, and a whole nefia ran on it unnoticed (every HP rule reads a percentage). Checked even with --kit-ok.
    eth = (call("skills").get("data") or {}).get("ether") or {}
    # run 37: Gravity Point (etherGravity, 1550) is Feat.Apply's ModBase(404, -10 x lv): Weight Reduction only, no HP or
    # attribute; the burden stops already cover it
    # run 38: Hunger for Slaughter (1556) is ModBase(DV, -(10 + LV)) and ModBase(DMG, 5 + LV / 2): at Lv34 DV 35 -> -9
    # (evasion 91 -> 47) for +22 damage a hit (my melee 35 -> 78.5 a turn); no HP or attribute: power.py's table had
    # me losing less per fight (kills twice as fast). Allowed like Gravity Point; the antibody (Miral) still cures it
    # the user, 2026-11-02: keep it while it is worth more than its cost, cure it when a bad one comes (fact #1161)
    eth = {k: v for k, v in eth.items() if v.get("id") not in (1550, 1556)}
    if eth:
        refuse("an ether disease: " + ", ".join(f"{v.get('name')} Lv{v.get('lv')}" for v in eth.values())
               + ": max HP or attributes may be down; the ether antibody cures it (Miral 10 medals, Yowyn's Ecopo shop)")


def spell_heal():
    """Cure Minor Wound to 85% when nothing hostile is in view (cure.py stops on one itself, and at its MP
    floor). True when HP is back over 70%: delve goes on. Run 28: Damp Machinarium B2's Imp stop."""
    out = run("cure.py", "85", timeout=300)
    p = call("state")["data"]["pc"]
    if p["hp"] * 100 < 70 * p["maxHp"] and ("vanished" in out or "no 'Cure Minor Wound' button" in out):
        # run 28: the spell's 65 casts ran out on me and Kaberg; a cure rod (zap.py: self-safe rods only) next
        # run 32: Cure Critical Wound from Shuzastan's book (Palmia); the bridge's cast needs no ability-bar button
        for _ in range(3):
            if p["hp"] * 100 >= 70 * p["maxHp"]:
                break
            r = call("cast", spell="SpHealCritical")
            if not r.get("ok") or not r["data"].get("cast"):
                break
            wait_idle(timeout=5000)
            p = call("state")["data"]["pc"]
        out = run("zap.py", "rod of cure minor wound", "4", timeout=300)
        p = call("state")["data"]["pc"]
        if p["hp"] * 100 < 70 * p["maxHp"]:
            # run 32: zap.py keeps 3 charges, so with the spell gone every 70% stop ended the ladder: the threshold
            # table says drink at 70%, so drink the strongest cure potion (heal.hold_potion looks in the bags too)
            from heal import POTIONS, hold_potion
            # run 35 (Crumbling Cave B5): a named 『Lizardman』 (avoid kind) knocked me under 70% again after each potion;
            # two potions went before the reserve stopped it. The second potion on one floor ends the ladder instead:
            # a foe that outlasts my heals is elin-play's "leave the floor" case
            global POTIONS_THIS_FLOOR
            floor_now = zone().get("full")
            POTIONS_THIS_FLOOR = POTIONS_THIS_FLOOR + 1 if POTION_FLOOR[0] == floor_now else 1
            POTION_FLOOR[0] = floor_now
            name = hold_potion(POTIONS) if POTIONS_THIS_FLOOR < 2 else None
            if POTIONS_THIS_FLOOR >= 2:
                print("  heal: a second potion on this floor: leave it (a foe outlasts the heals)", flush=True)
            if name:
                out = run("item.py", name, "Drink", timeout=120)
                p = call("state")["data"]["pc"]
        out.rc = 0 if p["hp"] * 100 >= 70 * p["maxHp"] else 3
    ok = out.rc == 0 and p["hp"] * 100 >= 70 * p["maxHp"]
    print(f"  heal: {last(out)[:90]} -> {'on' if ok else 'stop'}")
    return ok


def blind_wait():
    """elin-play's blind rule (run 14): no targeting, so get away and let it clear (~7-30 turns). A Short Teleport
    cast on myself (bridge cast: a self-cast works blind), then single turns until ConBlind is gone; False (stop)
    when HP falls under 70% or it lasts 40 turns."""
    call("cast", spell="SpTeleportShort")
    wait_until("idle", timeout=4000)
    for _ in range(40):
        p = pc()
        if "ConBlind" not in (p.get("conditions") or p.get("cond") or ""):
            print("  blind: cleared")
            return True
        if p["hp"] * 100 < 70 * p["maxHp"]:
            return False
        call("act", action="Wait")  # queued: the turn passes over the next frames
        wait_until("frames", n=20, timeout=3000)
    return False


def condition_wait():
    """elin-play's status rule (confused or afraid: stay put until it clears) for common.ready's "wait it out" stops
    (run 37: ConInsane and ConDim from an Eye of Insanity, gone in 11 turns): single turns while no hostile is in view;
    False (stop) on a hostile, HP under 70%, or 30 turns."""
    from common import BAD_CONDITIONS
    step_off()  # run 41: a Wait on the arrival stairway takes it (out and back in, the turn count standing still, in a storm's confusion)
    for _ in range(30):
        s = state()
        p = s["pc"]
        if not [c for c in p.get("conditions") or [] if c in BAD_CONDITIONS]:
            print("  condition: cleared")
            return True
        foes = [c for c in s.get("nearby") or [] if c.get("hostile")]
        # run 41: a Lv5 gangster ended the wait and the circuit at ConDim: foes 10+ levels under me get fought through it
        if foes and p["hp"] * 100 >= 70 * p["maxHp"] and all((c.get("lv") or 99) <= p["lv"] - 10 for c in foes):
            if fight_nearest(3):
                continue
        if foes or p["hp"] * 100 < 70 * p["maxHp"]:
            return False
        call("act", action="Wait")  # queued: the turn passes over the next frames
        wait_until("frames", n=20, timeout=3000)
    return False


def wood():
    """Logs for a craft push (run 42, G48: Carpentry and Blacksmith out of wood at home; fact #996: a mature tree on a nefia floor gives about 3 logs): when runs/jobs/wood.txt names a
    target, cut the trees in reach on an explored floor with nothing near, up to 12 logs a floor. They ride in the haul bag, where purge's --free can't drop them."""
    from pathlib import Path as _P
    try:
        want = int((_P(__file__).resolve().parent.parent / "runs" / "jobs" / "wood.txt").read_text().strip())
    except (OSError, ValueError):
        return
    log_stack = re.compile(r"^(\d+|an?) (\w+ )*?logs?$")

    def held_logs():
        n = 0
        for i in data("stock")["pack"]:
            for x in [i] + list(i.get("items") or []):
                if log_stack.match(x["name"]) and "carbon" not in x["name"]:
                    n += x.get("num") or 1
        return n
    have = held_logs()
    if have >= want or (pc().get("burdenPhase") or 0) >= 1 or hostile_near(8) or pc().get("sp", 0) < 50:
        return
    trees = [h for h in data("find", name="tree", r=40, n=30)["hits"] if h.get("kind") == "obj" and not h.get("edge")]
    if not trees:
        return
    in_pack = sum(i.get("num") or 1 for i in data("inv")["items"] if i.get("id") == "log")
    out = run("gather.py", "tree", "log", str(in_pack + min(want - have, 12)), "40", "40", "--weak-ok", timeout=300)
    run("hotbar.py", "--deselect", timeout=30)
    names = [i["name"] for i in data("inv")["items"] if log_stack.match(i["name"]) and "carbon" not in i["name"]]
    if names:
        run("bag.py", "a haul bag", *names, timeout=120)
        run("close.py", timeout=30)
    print(f"  wood: {held_logs()} of {want} logs; {len(trees)} trees seen ({last(out)[:70]})", flush=True)


def scrap_walls():
    """Scrap for a Blacksmith push (run 42, G48: bolts take 1 scrap and 2 SP): when runs/jobs/scrap.txt names a target, mine a Machinarium's metal walls on an explored floor, ~1 SP each (wallmine.py)."""
    from pathlib import Path as _P
    try:
        want = int((_P(__file__).resolve().parent.parent / "runs" / "jobs" / "scrap.txt").read_text().strip())
    except (OSError, ValueError):
        return
    if "factory" not in str(zone().get("full") or "") or hostile_near(8) or pc().get("sp", 0) < 60 or (pc().get("burdenPhase") or 0) >= 1:
        return

    def have():
        n = 0
        for i in data("stock")["pack"]:
            for x in [i] + list(i.get("items") or []):
                if re.match(r"^(\d+|an?) (\w+ )*?scraps?$", x["name"]) and "paper" not in x["name"]:
                    n += x.get("num") or 1
        return n
    now = have()
    if now >= want:
        return
    out = run("wallmine.py", str(min(want - now, 25)), "40", "10", "--kind", "metal", timeout=600)
    run("hotbar.py", "--deselect", timeout=30)
    names = [i["name"] for i in data("inv")["items"] if re.match(r"^(\d+|an?) (\w+ )*?scraps?$", i["name"]) and "paper" not in i["name"]]
    if names:
        run("bag.py", "a haul bag", *names, timeout=120)
        run("close.py", timeout=30)
    print(f"  scrap: {have()} of {want} ({last(out)[:70]})", flush=True)


def explore_floor(solo):
    spot = None
    thrown = 0
    for _ in range(8):
        asked()
        args = ["25"] + (["--solo"] if solo else []) + (["--expendable"] if "--expendable" in sys.argv else []) + GATE
        out = run("delve.py", *args, timeout=1500)
        why = next((ln.split("stop:", 1)[1].strip() for ln in reversed(out.splitlines()) if "stop:" in ln), "")
        print(f"  delve: {why or last(out)[:100]}", flush=True)
        # run 42: 20-odd step limits on one cell, a game day and a half and 17 real minutes, a soil block away from the rest of the floor: a walk that ends where it began is over
        here = (pc().get("x"), pc().get("z"))
        if "step limit" in why and here == spot:
            # run 42: candle ghosts sitting inside the walls: melee can't reach them and each one in view holds every step: throw at them, then go on
            foes = [c for c in state().get("nearby") or [] if c.get("hostile")]
            if foes and thrown < 4:
                thrown += 1
                f = min(foes, key=lambda c: c.get("dist", 99))
                # a throw at one in a wall finds no line ("no Throw at a candle ghost"); walking up to it and fight.py killed it
                out = run("fight.py", f.get("id") or f.get("name", ""), timeout=180)
                if out.rc:
                    out = run("throw.py", str(f.get("name", "")).split()[-1], "Putit In Amber", "8", timeout=180)
                run("hotbar.py", "--deselect", timeout=30)
                print(f"  delve: still at {here[0]},{here[1]} with {f.get('name')} in view: {last(out)[:80]}", flush=True)
                spot = None
                continue
            print(f"  delve: still at {here[0]},{here[1]} after a step limit: this exploring is done", flush=True)
            return
        spot = here
        # the exit code decides (the review of 2026-10-23): 3 is a decision stop, 1 a refusal,
        # 0 one of the floor's own ends, which the text names
        if out.rc == 3 and ("under 70%" in why or re.search(r"HP \d+/\d+ is below", why)) and spell_heal():
            continue  # run 28: the HP stop with no foe in view is the spell's job (elin-play: cure.py before a potion)
        if out.rc == 3 and "adjacent and no room to step away" in why:
            # run 28 (a hot guy, a kamikaze yeek): a Short Teleport opens the distance; delve then soaks or
            # throws from 3+ cells as it does with room (the exploder rule)
            r = call("cast", spell="SpTeleportShort")
            wait_until("idle", timeout=4000)
            print(f"  exploder adjacent: Short Teleport ({'cast' if r.get('ok') and r['data'].get('cast') else r.get('error')})")
            if r.get("ok") and r["data"].get("cast"):
                continue
        if out.rc == 3 and "LayerShippingResult" in why:
            farmday.close_report()  # run 28: the 05:00 report stopped a floor; it's only a report (wgo closes it too)
            continue
        if out.rc == 3 and "(Dialog)" in why and stay_in_nefia():
            continue  # run 41: a step onto the way back asks "Really give up conquering the Nefia?" (Strange Cave, Isolated Cave)
        if out.rc == 3 and why.startswith("hungry") and farmday.eat_one():
            continue  # run 28: delve's hunger stop mid-floor; eat_one refuses with a hostile in view
        # run 36 (Dark Ruin B1): weak wanderers in view cancelled the meal four times and the floor ended Very Hungry:
        # clear the view by delve's own rules, then eat
        if out.rc == 3 and why.startswith("hungry"):
            clear_view(solo)
            if farmday.eat_one():
                continue
        if "burden phase 2" in why and not getattr(explore_floor, "purged", False):
            # run 34: five burden-2 stops in one night (a dog house, a shrine's spear, boss-chest gear): drop junk once
            explore_floor.purged = True
            run("purge.py", timeout=600)
            if (pc().get("burdenPhase") or 0) < 2:
                print("  burden: purged the junk, going on")
                continue
        if out.rc == 3 and why.startswith("blind") and blind_wait():
            continue  # run 28: twice in an hour (hands of the dead) since the Godbane Necklace replaced the Immortal
        if out.rc == 3 and why.startswith("condition") and "wait it out" in why and condition_wait():
            continue  # run 37 (Capricious Grassland B2): Insane and Dim from an eye, cleared in 11 single turns
        if out.rc == 3 and "under 50%: heal.py" in why:
            # run 31: with a crew of three, the hurt one is named in delve's stop ("a mercenary warrior HP 40/168 under
            # 50%"); heal.py's default is Kaberg
            # run 32: the why can come without the "delve:" prefix ("a stalker HP 82/177 under 50%"): Kaberg was healed instead
            m = re.search(r"(?:delve(?: stopped)?: )?([^:]+?) HP \d+/\d+ under 50%", why)
            h = run("heal.py", *([m.group(1)] if m else []), timeout=300)  # run 28: the spell first (bridge cast), then a rod, then a potion
            print(f"  ally heal: {last(h)[:90]} ({h.rc})")
            if h.rc == 0:
                continue
        if out.rc == 3:
            stop(f"delve stopped: {why or last(out)[:120]}")
        if out.rc != 0:
            stop(f"delve {'refused' if out.rc == 1 else 'failed'} (rc {out.rc}): {last(out)[:120]}")
        if why.startswith("hostile in view"):  # run 26: an explore leg's own stop line ended the pass (rc 0): delve again
            continue
        if not any(k in why for k in OK_STOPS):
            stop(f"delve ended without a floor end: {why or last(out)[:120]}")
        if "step limit" not in why:
            return


def nap_outside():
    """elin-play (the user, run 17): sleepy at a dungeon's door, sleep on the world map first. Run 28 did it by hand
    six times: on B1 only, eat if 45+ (sleep.py refuses at 50 and nothing is eaten on the world map), take the up
    stairs, sleep.py, Enter the same tile again. True when back on B1 rested; False leaves the stop to the caller."""
    # run 33's review: on B2+ this returned False and the ladder stopped five times in one run, each a hand-run
    # evacuation, sleep and re-entry (~6 real minutes and the re-descent). Now any floor: free pack cards and eat
    # (sleep.py refuses at hunger 50; a full grid drops the meal), then an evacuation scroll (evac.py) off a deeper
    # floor or the up stairs from B1, sleep on the world map, Enter the tile; the explored floors re-walk fast
    import stairs
    z = (state().get("zone") or {}).get("full") or ""
    nefia_name = re.sub(r"\s*(?:\*Conquered\*.*|B\d+F.*)$", "", str((state().get("zone") or {}).get("name") or "")).strip()
    # run 36 (Mossy Ruin B1): eaten at 44 or not at all, the walk out reached 50 and sleep.py refused on the world map,
    # where nothing can be eaten: eat down under 35 before leaving the floor (a mushroom is ~13)
    if pc()["hunger"] >= 35:
        run("purge.py", "--free", "3", timeout=600)
        # run 39 (Old Grassland B1): "not eating: an orc is in view", then "stop: Sleepy": clear weak foes first
        fight_nearest()
        for _ in range(3):
            if pc()["hunger"] < 35 or not farmday.eat_one():
                break
    if z.endswith("@-1"):
        if not stairs.take("up"):
            return False
    else:
        # run 34: a Lv4 mushroom in view refused the evacuation (no foe in view when reading) and the nap stopped
        clear_view("--solo" in sys.argv)
        out = run("evac.py", timeout=900)
        print(f"  evacuation: {last(out)[:90]}")
        if out.rc != 0:
            return False
    if "ntyris" not in str((state().get("zone") or {}).get("full")):
        if not stairs.take("up"):  # an evacuation that landed on B1's entrance stairway
            return False
    out = run("sleep.py", timeout=600)
    print(f"  nap outside: {last(out)[:90]}")
    # run 35: the 05:00 shipping report opened during the nap, the game ignored the Enter, and the next check read the
    # world map as "not a nefia: expired" (circuit.py closes a report before its Enter since run 34)
    if (state().get("layers") or {}).get("top"):
        run("close.py", timeout=60)
    # run 40 (Earthy Cave): a story tip ("Oh no, there's trash everywhere!") opened during the nap; close.py leaves a drama open,
    # the game ignored the Enter, and the check below read the nefia as expired
    if ((state().get("layers") or {}).get("top") or "") == "LayerDrama":
        run("talk.py", timeout=120)
    # run 40: the way out of Tainted Forest landed one tile off, the Enter led into that tile's field, and the check below
    # read the nefia as expired while it stood next door. Step back onto it first (one step: no route to judge)
    if nefia_name:
        for p in data("places", r=1).get("places") or []:
            if p["dist"] == 1 and p["name"].startswith(nefia_name) and (p["dx"] == 0 or p["dz"] == 0):
                way = {(0, 1): "n", (0, -1): "s", (1, 0): "e", (-1, 0): "w"}[(p["dx"], p["dz"])]
                print(f"  the way out landed one tile off {nefia_name}: stepping {way}", flush=True)
                run("bridge.py", "move", way, timeout=60)
                wait_idle(timeout=20000)
                break
    acts = data("acts", dx=0, dz=0, mode="all").get("acts") or []
    ent = [a for a in acts if a["text"] == "Enter"]
    if not ent:
        stop("napped outside but no Enter on this tile: look.py")
    call("do", i=ent[0]["i"])
    wait_until("zone", timeout=20000)
    # run 34: Rustic Forest expired during a 9-hour nap; the tile's Enter then led into its Wilds field, and the
    # ladder delved the field for stairs ("no way down"). A re-entry that isn't a nefia ends the nefia here
    z2 = state().get("zone") or {}
    if not z2.get("nefia"):
        stop(f"re-entered {z2.get('full')} ({z2.get('name')}), not a nefia: the nefia is gone (expired during the nap?); "
             "leave.py and pick another")
    p = pc()
    return "sleepy" not in (p.get("sleepText") or "").lower()


def upkeep():
    p = pc()
    heal_to = THRESHOLDS["heal_to"]
    if p["hp"] * 100 < heal_to * p["maxHp"]:
        # run 34 (Warped Cave B2): the stop came with a heal spell and rods in hand; cure.py first (no foe in view)
        run("cure.py", str(heal_to + 5), timeout=300)
        p = pc()
    if p["hp"] * 100 < heal_to * p["maxHp"]:
        stop(f"HP {p['hp']}/{p['maxHp']} under {heal_to}% after the floor: heal before going on")
    if p["sp"] < 10:
        stop(f"SP {p['sp']}: sleep outside before going on (never in a dungeon)")
    # bridge 0.30.0 reports the sleepiness phase text; an older mod shows a condition at most
    sleepy = "sleepy" in (p.get("sleepText") or "").lower() or any("sleepy" in c.lower() for c in p.get("conditions") or [])
    if sleepy and not nap_outside():
        stop(f"{p.get('sleepText') or 'Sleepy'}: sleep first, on the overworld (never in a dungeon)")
    if p["hunger"] >= 65:
        before = p["hunger"]
        fight_nearest()  # run 41: a wasp Lv7 in view cancelled both meals and ended the ladder at hunger 67
        print("  meal: " + str(farmday.eat_one()))
        if pc()["hunger"] >= before:
            # run 35 (Damp Cave B2): "not eating: the pack grid is full" ended the ladder at hunger 67 with 114
            # mushrooms in the Cooler Box: free a card, then eat once more
            run("purge.py", "--free", "2", timeout=600)
            print("  meal (after a purge): " + str(farmday.eat_one()))
        if pc()["hunger"] >= before:
            stop(f"hunger {before}: the meal didn't happen (no food in the Cooler Box?)")


def way_down(arrival):
    hits = data("find", name="stair", r=999, n=10)["hits"]
    # bridge 0.29.0 reports each thing's trait: TraitStairsDown is the way down whatever --in says
    # (run 20: a restart mid-floor made the arrival cell guess pick the way up twice)
    if any(h.get("trait") for h in hits):
        downs = [h for h in hits if h.get("installed") and h.get("trait") == "TraitStairsDown"]
    else:
        downs = [h for h in hits if h.get("installed") and (h["x"], h["z"]) != arrival]
    locked = [h for h in data("find", name="locked corridor", r=999, n=3)["hits"]]
    if not downs and locked:
        stop(f"only a locked corridor at {locked[0]['x']},{locked[0]['z']}: Use it by hand if the story allows")
    if not downs:
        # run 37 (Bewitching Cave B2): the bottom floor's master stood there neutral, an Evolved Putit Lv22, and the
        # stop read like a missing stairway; run 35's Evolved Scorpion was the same. Name it: fight.py NAME 70 --force
        masters = [c for c in state().get("nearby") or [] if not c.get("hostile") and not c.get("party")
                   and (str(c.get("name", "")).startswith("Evolved") or named(c))]
        if masters and "Conquered" not in str(zone().get("name") or ""):
            m = masters[0]
            stop(f"the bottom floor: the master is likely {m['name']} Lv{m.get('lv')} (neutral, at {m.get('dx')},"
                 f"{m.get('dz')}): fight.py \"{m['name']}\" 70 --force, then the chest")
        stop("no way down: the bottom floor (or a stairway not found)")
    p = pc()
    return min(downs, key=lambda h: max(abs(h["x"] - p["x"]), abs(h["z"] - p["z"])))


def hostile_near(r=3):
    """A hostile within r cells (the walks answer "stopped" when one blocks the path)."""
    return any(c.get("hostile") and max(abs(c.get("dx", 99)), abs(c.get("dz", 99))) <= r
               for c in state().get("nearby") or [])


def step_off():
    """Run 26: a Wait or a throw on the arrival stairway opens "The Master of Nefia still remains. Really give
    up conquering?" and every later act fails under it: stand on a plain cell beside the stairs first."""
    for dx, dz in ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
        c = call("cell", dx=dx, dz=dz).get("data") or {}
        if c.get("block") or c.get("water") or any(re.search(r"stair", t.get("name", ""), re.I) for t in c.get("thingInfo") or []):
            continue
        p = pc()
        if walk(p["x"] + dx, p["z"] + dz, r=0, timeout=8000).get("why") == "arrived":
            return


def gather_party(near=3, turns=8):
    """Run 31: Kaberg and the new mercenary warrior were left on Crumbling Grassland B4 when the ladder took the
    stairs with them fighting far off (the crew's first nefia; they walk home later, fact #278). Before the stairs,
    wait up to `turns` turns for every party member on this map to come within `near` cells. Returns the names
    still away (said in the log, never a stop: a lost ally walks home)."""
    away = []
    for _ in range(turns):
        party = call("state")["data"].get("party") or []
        away = [p["name"] for p in party if p.get("here") and (p.get("dist") or 0) > near]
        if not away or hostile_near():
            break
        call("act", action="Wait")
        wait_until("frames", n=10, timeout=1500)
    if away:
        print(f"  party: {', '.join(away)} still away at the stairs", flush=True)
    return away


def descend(h, solo):
    """The stairs at x1 (run 41: at x5 the walk to them ended 'stopped' four times and the Enter didn't take, twice stopping a circuit;
    at x1 stairs.py took the same stairway at once)."""
    prior = data("speed").get("index")
    if prior != 1:
        call("speed", i=1)
    try:
        return descend_at_x1(h, solo)
    finally:
        if prior != 1:
            call("speed", i=prior)


def see_unseen():
    """An unseen foe beside me cancels every walk with "Enemy spotted" and no creature in view (run 41: an invisible pumpkin Lv10 on Crumbling
    Ruin B3 ended the walk to the stairs 4 times): See Invisible once a floor, then what it shows gets fought. True when it may have helped."""
    if getattr(see_unseen, "tried", None) == zone().get("full"):
        return False
    see_unseen.tried = zone().get("full")
    r = call("cast", spell="SpSeeInvisible")
    wait_until("frames", n=20, timeout=3000)
    print(f"  See Invisible: {'cast' if r.get('ok') else r.get('error')}", flush=True)
    fight_nearest(4)
    return bool(r.get("ok"))


def descend_at_x1(h, solo):
    before = zone().get("full")
    if not solo:
        walk(h["x"], h["z"], r=6, hp=THRESHOLDS["dungeon_hp"], stairs=True, timeout=60000, weak_ok=True)  # stops 6 short
        gather_party()
    for _ in range(4):
        r = walk(h["x"], h["z"], r=4, hp=THRESHOLDS["dungeon_hp"], stairs=True, timeout=60000, weak_ok=True)  # run 21: a Lv1 snail stopped it twice
        if zone().get("full") != before:
            step_off()
            return
        if r.get("why") == "arrived":
            break
        # run 22: a gnome, an orc, a goblin shaman and a kobold stood in the path ("stopped": blocked
        # or occupied) and each ended the ladder; a hostile within 3 gets the same fight as "hostile"
        if r.get("why") == "hostile" or (r.get("why") == "stopped" and hostile_near()):
            out = run("delve.py", "4", *(["--solo"] if solo else []), *(["--expendable"] if "--expendable" in sys.argv else []), *GATE, timeout=600)  # run 26: the shield's HP stopped the stair walk
            if out.rc == 3:
                stop(f"delve stopped on the way to the stairs: {last(out)[:120]}")
            continue
        if r.get("why") == "stopped":  # run 26: "Enemy spotted" (a Lv1 rat 6 cells off) interrupts the walk: walk again
            # run 39 (Capricious Ruin B3): an invisible pumpkin Lv10 stood in the path ("Something spreads spores at
            # you"): four walks "stopped" with nothing in view; a See Invisible cast (101 in stock) showed it
            s = state()
            if not hostile_near() and any("Something " in str(x) for x in (s.get("log") or [])[-12:]) \
                    and not any("SeeInvisible" in str(c) for c in (s.get("pc") or {}).get("conditions") or []):
                rr = call("cast", spell="SpSeeInvisible")
                print(f"  'Something' unseen in the way: See Invisible ({(rr.get('data') or {}).get('cast') or rr.get('error')})")
                wait_until("idle", timeout=4000)
            continue
        # run 39 (Capricious Ruin B3): the 05:00 shipping report opened on the way and the bridge refused the walk
        # ("window open"); it's only a report: close it and walk again (explore_floor does the same since run 28)
        if "LayerShippingResult" in str((state().get("layers") or {}).get("top")):
            farmday.close_report()
            continue
        stop(f"the walk to the stairs at {h['x']},{h['z']} ended: {r.get('why')}")
    else:
        if zone().get("full") == before and r.get("why") != "arrived":
            # run 34 (twice, Machinarium floors with trolleys by the stairs): the walk "stopped" four times while
            # stairs.py down got through each time at once
            out = run("stairs.py", "down", timeout=300)
            if zone().get("full") != before:
                print(f"  stairs: the walk stopped 4 times; stairs.py down took them", flush=True)
                step_off()
                return
            # run 35 (Tangled Machinarium B1, re-entered after a nap): the entrance sits in a pocket of metal walls and the
            # stairs at 6,12 lay outside it; Teleport casts until a walk arrives, then stairs.py (up to 4 casts)
            for _t in range(4):
                c = call("cast", spell="SpTeleport")
                if not (c.get("ok") and (c.get("data") or {}).get("cast")):
                    break
                wait_until("frames", n=20, timeout=3000)
                if walk(h["x"], h["z"], r=1, hp=THRESHOLDS["dungeon_hp"], stairs=True, timeout=60000,
                        weak_ok=True).get("why") == "arrived" or zone().get("full") != before:
                    if zone().get("full") == before:
                        run("stairs.py", "down", timeout=300)
                    if zone().get("full") != before:
                        print(f"  stairs: boxed in; {_t + 1} Teleport cast(s) and the walk took them", flush=True)
                        step_off()
                        return
            if see_unseen():
                return descend_at_x1(h, solo)
            stop(f"the walk to the stairs at {h['x']},{h['z']} ended 4 times: {r.get('why')}; stairs.py down: {last(out)[:80]}")
    # run 20: the walk can end beside the stairs (Kaberg on the cell): the stairway's own act walks there
    p = pc()
    acts = call("acts", dx=h["x"] - p["x"], dz=h["z"] - p["z"], mode="all")["data"]["acts"]
    enter = [a for a in acts if a["text"].startswith("Enter")]
    if not enter:
        # run 31: the walk took the stairs a moment after its reply (the late zone change, runs 27 and 30): an empty
        # act list on the old cell meant I was already a floor down
        wait_until("zone", timeout=3000)
        if zone().get("full") != before:
            step_off()
            return
        # run 33 (the user: "walk into it"): a mine entrance lists no Enter act; a bridge step into the cell takes it
        import stairs
        if stairs.step_into(h["x"], h["z"]):
            after = zone().get("full")
            if depth(after) <= depth(before):
                stop(f"the stairs led up or out ({before} -> {after}), not down: walk back by hand")
            step_off()
            return
        stop(f"no Enter on the stairway cell {h['x']},{h['z']}: {[a['text'] for a in acts]}")
    after = before
    for attempt in range(3):
        call("do", i=enter[0]["i"])
        wait_until("zone", timeout=15000)
        after = zone().get("full")
        if after != before:
            break
        # run 41 (Savage Ruin, Traditional Ruin at x5): a weak foe beside the stairs cancelled the Enter and stopped the whole circuit
        print(f"  stairs: the Enter didn't take (try {attempt + 1}): clearing the view")
        fight_nearest()
        p = pc()
        if (p["x"], p["z"]) != (h["x"], h["z"]) and walk(h["x"], h["z"], r=1, hp=THRESHOLDS["dungeon_hp"], stairs=True,
                                                         timeout=30000, weak_ok=True).get("why") == "zone":
            after = zone().get("full")
            break
        p = pc()
        acts = call("acts", dx=h["x"] - p["x"], dz=h["z"] - p["z"], mode="all")["data"]["acts"]
        enter = [a for a in acts if a["text"].startswith("Enter")] or enter
    if after == before:
        stop("took the stairs but the zone didn't change")
    # run 20: a wrong --in made the ladder take the way up and then delve the world map
    if depth(after) <= depth(before):
        stop(f"the stairs led up or out ({before} -> {after}), not down: walk back by hand")
    step_off()


# Run 21 (the user: "don't forget the shrine ... it is replenish"): look.py listed shrines but the
# ladder walked past them. These are safe to Use on every floor (fact #268): replenish heals the
# party and adds SP, armor enchants worn armour, knowledge/enlightenment and invention/wheel give a
# book or a recipe. Strife spawns a boss and Material changes an item's material: never automatic.
SAFE_SHRINES = ("replenish", "armor", "knowledge", "enlightenment", "invention", "wheel")


def shrines():
    hits = (data("find", name="Shrine", r=999, n=10) or {}).get("hits") or []
    for h in hits:
        name = h.get("name") or ""
        kind = re.search(r"《(.+?)》", name)
        kind = kind.group(1).lower() if kind else ""
        if "(Empty)" in name or not any(k in kind for k in SAFE_SHRINES):
            print(f"  shrine left alone: {name} at {h['x']},{h['z']}")
            continue
        use = []
        # run 22: the walk to Ominous Ruin's Enlightenment shrine ended at 13,18, two cells short ("no
        # Use act"); standing on its cell offered the Use. A second, closer walk before giving up
        for r in (1, 1, 0):
            w = walk(h["x"], h["z"], r=r, hp=THRESHOLDS["dungeon_hp"], timeout=30000)
            # run 22: an orc beside me stopped both walks to Tangled Cave's Armor and Wheel shrines
            # ("hostile", then "stopped"): fight what is near, as descend() does, then walk again
            if w.get("why") in ("hostile", "stopped") and hostile_near():
                run("delve.py", "4", "--solo", *GATE, timeout=600)
                continue
            p = pc()
            acts = data("acts", dx=h["x"] - p["x"], dz=h["z"] - p["z"], mode="all").get("acts") or []
            use = [a for a in acts if a["text"].startswith("Use (") and "hrine" in a["text"]]
            if use:
                break
        if not use:
            p = pc()  # run 28: every walk ended on "hostile" (a hot guy), so p was never read: a crash
            print(f"  shrine {name}: no Use act from {p['x']},{p['z']}")
            continue
        call("do", i=use[0]["i"])
        wait_until("frames", n=30, timeout=3000)
        if (state().get("layers") or {}).get("top") == "LayerDragGrid":
            # run 21: an Armor shrine opens a picker for the piece to enchant and the ladder stood
            # under it; the worn armour piece with the lowest plus goes in (a +3 breastplate
            # resisted a scroll: high pluses resist), never a weapon
            bs = data("buttons", all=True).get("buttons") or []
            slot = next((b["i"] for b in bs if (b.get("name") or "").startswith("ing1")), None)
            worn = [b for b in bs if "WidgetEquip" in (b.get("path") or "") and b.get("card")
                    and re.search(r"\[-?\d+, ?-?\d+\]", b["card"]) and not re.search(r"\(\d+d\d+", b["card"])]

            def plus(card):
                m = re.search(r" ([+-]\d+) \[", card)
                return int(m.group(1)) if m else 0
            if slot is not None and worn:
                pick_ = min(worn, key=lambda b: plus(b["card"]))
                call("drag", i=pick_["i"], j=slot)
                wait_until("frames", n=30, timeout=3000)
            if (state().get("layers") or {}).get("top") == "LayerDragGrid":
                run("close.py")
            # run 26: the Forest Gloves "resisted" the Armor shrine and stayed in the pack, unworn, for
            # two nefias (PV and the Axe bonus gone): whatever went into the picker is worn again
            if slot is not None and worn:
                # run 30: a successful enchant renames the piece (+3 -> +4), so the exact name found nothing and
                # the Forest Gloves stayed in the pack after Unnamed Ruin: match the name without its plus and
                # brackets, then check the slots themselves
                def bare(n):
                    return re.sub(r" [+-]\d+|\s*\[-?\d+, ?-?\d+\]|\s*\(\d+\)", "", n).strip()
                card = pick_["card"]
                gone = [i for i in call("inv")["data"]["items"]
                        if bare(i["name"]) == bare(card) and not i.get("equipped")]
                if gone:
                    out = run("item.py", gone[0]["name"], "Equip")
                    print(f"  re-equipped after the shrine: {gone[0]['name']} ({last(out)[:60]})")
                from common import empty_slots
                if empty_slots():
                    stop(f"an empty gear slot after the Armor shrine: {', '.join(empty_slots())} (the user's full-set rule)")
        print(f"  shrine used: {name}: " + " / ".join((state().get("log") or [])[-2:]))


def chests():
    """Open every unlocked treasure chest on the explored floor and Take All (run 21: the masters'
    exquisite chests on the Machinarium's B4 and the Tangled Forest's B2 were opened by hand after
    the ladder had walked past them). A locked one is picked (a lockpick held, or bare when Lockpicking/2 + 2 beats
    the lock: run 35), never pried (prying can destroy items)."""
    hits = (data("find", name="treasure chest", r=999, n=10) or {}).get("hits") or []
    for h in hits:
        # run 27: the hits' dx/dz are from where find ran; after the walk to the first chest the second
        # chest's stale delta read "cell: off the map" and the ladder crashed: read it from where I stand now
        p0 = pc()
        cell = data("cell", dx=h["x"] - p0["x"], dz=h["z"] - p0["z"]) or {}
        info = next((t for t in cell.get("thingInfo") or [] if "chest" in (t.get("name") or "")), {})
        walk_beside(h["x"], h["z"], r=0, hp=THRESHOLDS["dungeon_hp"], timeout=30000)
        p = pc()
        # run 36 (Sorrowful Ruin B2): the walk ended 7 cells short (a Big Daddy in the way) and the acts read from there
        # said "no Open act": the 909-orens master chest was opened by hand. One more walk, then say it plainly
        if max(abs(h["x"] - p["x"]), abs(h["z"] - p["z"])) > 1:
            wait_until("frames", n=30, timeout=3000)
            walk_beside(h["x"], h["z"], r=0, hp=THRESHOLDS["dungeon_hp"], timeout=30000)
            p = pc()
            # run 36 (Forgotten Machinarium B3): walk_beside ended 5 cells short twice; a walk to a named neighbour
            # cell (6,16 for a chest at 6,17) arrived at once
            for nx, nz in ((0, -1), (-1, 0), (1, 0), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
                if max(abs(h["x"] - p["x"]), abs(h["z"] - p["z"])) <= 1:
                    break
                walk(h["x"] + nx, h["z"] + nz, r=0, hp=THRESHOLDS["dungeon_hp"], timeout=15000)
                p = pc()
            if max(abs(h["x"] - p["x"]), abs(h["z"] - p["z"])) > 1:
                print(f"  chest not reached: {h['name']} at {h['x']},{h['z']} (the walk ended at {p['x']},{p['z']})")
                continue
        if info.get("lockLv"):
            # run 21: the Capricious Ruin's master chest (lock 11) opened on the first try with a
            # lockpick held (Trait.TryOpenLock: a pick never harms the contents; prying can)
            from common import grab
            if not grab("lockpick"):
                # run 35 (Damp Cave B3): a lock-8 master chest was left with Lockpicking 33; a bare Pick Lock opened it
                # by hand (983 orens, 3 platinum). Trait.TryOpenLock: bare power is skill/2 + 2, "too difficult" at or
                # under the lock, and a failure costs 1 SP and gives skill exp; only prying (TryPryOpenLock) harms items
                skill = ((data("skills").get("skills") or {}).get("lockpicking") or {}).get("lv") or 0
                if skill // 2 + 2 <= info["lockLv"]:
                    print(f"  chest left: {h['name']} at {h['x']},{h['z']} is locked (lock {info['lockLv']}), no lockpick, "
                          f"and bare power {skill // 2 + 2} doesn't beat it")
                    continue
            for _ in range(12):
                acts = data("acts", dx=h["x"] - p["x"], dz=h["z"] - p["z"], mode="all").get("acts") or []
                pick = [a for a in acts if a["text"].startswith("Pick Lock")]
                if not pick or pc()["sp"] < 10:
                    break
                call("do", i=pick[0]["i"])
                wait_until("idle", timeout=20000)
            run("item.py", "lockpick", "Put away")
        acts = data("acts", dx=h["x"] - p["x"], dz=h["z"] - p["z"], mode="all").get("acts") or []
        op = [a for a in acts if a["text"].startswith("Open (") and "chest" in a["text"]]
        if not op:
            print(f"  chest {h['name']}: no Open act from {p['x']},{p['z']}")
            continue
        call("do", i=op[0]["i"])
        wait_until("layer", timeout=4000)
        bs = data("buttons", all=True).get("buttons") or []
        inside = [b["card"] for b in bs if b.get("card") and not b.get("mine") and "inventory grid" in (b.get("name") or "")]
        take = [b for b in bs if (b.get("text") or "").startswith("Take All")]
        if take:
            call("click", i=take[0]["i"], expect="Take All")
            wait_until("frames", n=20, timeout=3000)
        bs = data("buttons", all=True).get("buttons") or []
        left = [b["card"] for b in bs if b.get("card") and not b.get("mine") and "inventory grid" in (b.get("name") or "")]
        run("close.py")
        # run 36: Terrifying Ruin's master chest kept ★2 Small Medals behind a full pack (taken by hand after a purge):
        # anything worth a card (★, medals, coins, bars, maps, books, genes, unidentified gear) gets a purge and a retake
        worth = [n for n in left if re.search(r"★|☆|medal|platinum|gold bar|map|book|gene|\((miracle|godly)\)", n.lower())]
        if worth:
            print("  chest: room for " + ", ".join(worth) + ": " + last(run("purge.py", "--free", str(len(worth) + 2), timeout=900))[:80])
            call("do", i=op[0]["i"])
            wait_until("layer", timeout=4000)
            take = [b for b in data("buttons", all=True).get("buttons") or [] if (b.get("text") or "").startswith("Take All")]
            if take:
                call("click", i=take[0]["i"], expect="Take All")
                wait_until("frames", n=20, timeout=3000)
            bs = data("buttons", all=True).get("buttons") or []
            left = [b["card"] for b in bs if b.get("card") and not b.get("mine") and "inventory grid" in (b.get("name") or "")]
            run("close.py")
        print(f"  chest opened: {h['name']}: {', '.join(inside) or 'empty'}" + (f"; LEFT (pack full?): {', '.join(left)}" if left else ""))
        # run 42: a kotatsu from the chest: 220%, and every way off the floor refuses at phase 3 (common.overweight_stop)
        if (pc().get("burdenPhase") or 0) >= 3:
            print("  chest: burden phase 3: " + last(run("purge.py", "--heavy", timeout=300))[:90])


def stay_in_nefia():
    """Answer No when the game asks whether to give up the conquest. False when the open dialog is something else."""
    if "give up conquering" not in str(data("texts").get("texts")):
        return False
    b = next((x for x in data("buttons")["buttons"] if str(x.get("text", "")).endswith("No.")), None)
    if not b:
        return False
    data("click", i=b["i"], expect="No.")
    print("  the game asked to give up the conquest: answered No")
    return True


def fight_nearest(max_fights=4):
    """Fight hostiles in view at or under my level, nearest first, with fight.py (run 39: the Hungry deadlock in
    clear_view). True when none is left in view; False on a stronger foe or a fight.py refusal or stop."""
    for _ in range(max_fights):
        s = state()
        me = (s.get("pc") or {}).get("lv") or 0
        foes = [c for c in s.get("nearby") or [] if c.get("hostile")]
        if not foes:
            return True
        if any((c.get("lv") or 0) > me for c in foes):
            return False
        f = min(foes, key=lambda c: c.get("dist", 99))
        r = run("fight.py", f.get("id") or f["name"], timeout=300)
        print(f"  fight_nearest: {f['name']} Lv{f.get('lv')} at {f.get('dist')}: fight.py rc {r.rc}", flush=True)
        if r.rc != 0:
            return False
    return not any(c.get("hostile") for c in state().get("nearby") or [])


def clear_view(solo):
    """Run 33's review: after "floor explored" a wanderer in view stopped purge, loot and the chests on most floors
    ("stop: hostile in view: a candle ghost Lv11 at 3") and the floor's loot waited on a hand-run fight. Up to three
    short delve passes deal with what is in view by delve's own rules; a delve stop (rc 3) is still a decision."""
    for _ in range(3):
        if not any(c.get("hostile") for c in state().get("nearby") or []):
            return
        args = ["4"] + (["--solo"] if solo else []) + (["--expendable"] if "--expendable" in sys.argv else []) + GATE
        out = run("delve.py", *args, timeout=600)
        # run 34: a Hungry stop here ended a solo Dark Ruin B2 that explore_floor would have fed and gone on
        if out.rc == 3 and "hungry" in last(out).lower() and farmday.eat_one():
            continue
        # run 39 (Mystical Ruin B1): delve won't fight while Hungry and a hostile in view cancels the meal, so this
        # loop stopped the circuit with a floating eye, a yeek and a beth failure (Lv2-5) in view; fight.py (its own
        # rules: exploders refused, the round rule) works while Hungry: the nearest foe at or under my level, then eat
        if out.rc == 3 and "hungry" in last(out).lower() and fight_nearest() and farmday.eat_one():
            continue
        # run 34 (Tragedic Cave B1): an ally's "under 50%: heal.py" stop ended the floor here too
        m = re.search(r"(?:delve(?: stopped)?: )?([^:]+?) HP \d+/\d+ under 50%", last(out))
        if out.rc == 3 and m:
            h = run("heal.py", m.group(1).strip(), timeout=300)
            print(f"  ally heal (clearing the view): {last(h)[:80]} ({h.rc})")
            if h.rc == 0:
                continue
        if out.rc == 3 and "under 70%" in last(out) and spell_heal():
            continue
        if out.rc == 3 and "wait it out" in last(out) and condition_wait():  # run 41: ConDim stopped a circuit here
            continue
        if out.rc == 3:
            stop(f"delve stopped clearing the floor's view: {last(out)[:120]}")


def floors_loop(max_danger, floors, solo):
    """Run 33's review: `floors` counts NEW floors (deeper than any reached in this run); a floor re-walked after a nap
    outside (nap_outside: evacuate, sleep, Enter) doesn't spend the quota."""
    global FLOORS_DONE
    done, deepest, f = 0, 0, 0
    while done < floors:
        f += 1
        asked()
        z = zone()
        if depth(z.get("full")) == 0:
            stop(f"{z.get('full')} is not a dungeon floor")
        new = depth(z.get("full")) > deepest
        underwater = z["underwater"] if "underwater" in z else "water" in str(z.get("full") or "").lower()
        if underwater:
            stop(f"{z.get('full')} is underwater (the user, run 17)")
        if (z.get("danger") or 0) > max_danger:
            stop(f"{z.get('name')} is danger {z.get('danger')}, over {max_danger}: go back up the stairs I came down")
        p = pc()
        arrival = (p["x"], p["z"])
        if f == 1 and "--in" in sys.argv:
            arrival = tuple(int(v) for v in sys.argv[sys.argv.index("--in") + 1].split(","))
        # run 34: allies who died mid-floor were read as "left at an evacuation" (fact #1060): each floor names the party
        crew = [f"{c.get('name')} {c.get('hp')}/{c.get('maxHp')}" for c in (state().get("party") or []) if not c.get("pc")]
        print(f"floor {f}: {z.get('name')} danger {z.get('danger')}  HP {p['hp']}/{p['maxHp']} SP {p['sp']}  {p['date']}"
              f"  party: {', '.join(crew) or 'none'}")
        explore_floor(solo)
        clear_view(solo)
        wood()
        scrap_walls()
        # run 28: the pack and all three bags filled within two nefias, and a boss chest's treasure map stayed
        # behind ("LEFT (pack full?)"): drop the junk (purge.py's rules) before the loot and the chests
        # run 33: and free 3 grid cards (cheap stacks dropped) so the meals and the chests' books have room
        print("  purge: " + last(run("purge.py", "--free", "3", timeout=900))[:100])
        print("  " + last(run("loot.py", "40", timeout=900))[:120])
        if "--no-wrecks" not in sys.argv:
            print("  wrecks: " + last(run("wrecks.py", "40", str(THRESHOLDS["dungeon_hp"]), "15", timeout=900))[:100])
            run("item.py", "pickaxe", "Put away")
        shrines()
        chests()
        call("act", action="QuickSave")
        # run 21: the Machinarium's master died on B4 and nothing said so; two days later I walked
        # back to a "*Conquered*" nefia. The zone's name carries the mark once the master is dead.
        if "Conquered" in str(zone().get("name") or ""):
            FLOORS_DONE = done + (1 if new else 0)
            p = pc()
            print(f"conquered: {zone().get('name')}: the master is dead (evacuation goes straight out)  "
                  f"HP {p['hp']}/{p['maxHp']}  {p['date']}")
            return  # a conquered, looted floor is a save point (the review of 2026-10-23)
        upkeep()
        if new:
            deepest = depth(zone().get("full")) if depth(zone().get("full")) > deepest else deepest
            done += 1
            FLOORS_DONE = done
        if done >= floors:
            break
        # run 34: Ancient Grassland's ladder stepped onto B4 (danger 15) over the gate of 14 and stopped there among
        # eleven hostiles with Goda beside the arrival; each floor is one danger deeper, so stop on this floor instead
        nxt = (zone().get("danger") or 0) + 1
        if nxt > max_danger:
            stop(f"the next floor would be danger {nxt}, over {max_danger}: this floor is the last (evac.py out)")
        # run 34 (Mossy Cave B2, Lively Cave B1): eight step-limited delve passes ended before the stairs were seen and the
        # ladder stopped "no way down"; a rerun found them each time: explore up to twice more before way_down stops.
        # Run 37 (Blasphemous Cave B1): the map and one pass saw none, then explore.py and delve found frontiers left and
        # the stairs: a second pass after the map
        for _again in range(3):
            hits = data("find", name="stair", r=999, n=10)["hits"]
            if any(h.get("installed") and h.get("trait") == "TraitStairsDown" for h in hits):
                break
            # run 34: on Lively Cave B1 a rod of magic map showed the stairs 8 cells away after two full explorations: map
            # the floor first (a scroll of magic map from the pack, else the rod), then explore again only if still none
            if _again == 0:
                # run 34: the spell first (no pack card, no bag): Magic Map from Koflord's-era book reads
                c = call("cast", spell="SpMagicMap")
                if c.get("ok") and (c.get("data") or {}).get("cast"):
                    r = Output("cast Magic Map")
                    r.rc = 0
                else:
                    r = run("item.py", "scrolls of magic map", "Read", timeout=60)
                if r.rc != 0:
                    r = run("zap.py", "rod of magic map", "1", "--keep", "0", timeout=120)
                wait_until("frames", n=20, timeout=3000)
                print(f"  no stairs down seen yet: magic map ({last(r)[:60]})")
                continue
            print("  no stairs down seen yet: exploring again")
            explore_floor(solo)
        # run 35 (Tangled Machinarium B1): a pocket of metal walls; the map and two explorations saw no stairs down, and
        # one Teleport cast (it works at Casting 6; it fizzled at 3) landed where the next pass found them at once
        hits = data("find", name="stair", r=999, n=10)["hits"]
        if not any(h.get("installed") and h.get("trait") == "TraitStairsDown" for h in hits) and not hostile_near(8):
            c = call("cast", spell="SpTeleport")
            if c.get("ok") and (c.get("data") or {}).get("cast"):
                wait_until("frames", n=20, timeout=3000)
                print("  no stairs down seen yet: boxed in? cast Teleport, exploring again")
                explore_floor(solo)
        # run 42 (the user: "you may be stuck in the dirt, may need to mine to get a path"): one soil block held a floor for 17 real minutes
        for _dig in range(3):
            hits = data("find", name="stair", r=999, n=10)["hits"]
            if any(h.get("installed") and h.get("trait") == "TraitStairsDown" for h in hits) or hostile_near(8):
                break
            r = run("tunnel.py", "--max", "6", timeout=300)
            print(f"  no stairs down seen yet: tunnel: {last(r)[:90]}", flush=True)
            if r.rc != 0 or "nothing to dig" in str(r):
                break
            explore_floor(solo)
        h = way_down(arrival)
        descend(h, solo)
    z, p = zone(), pc()
    print(f"done: {z.get('name')} danger {z.get('danger')}  HP {p['hp']}/{p['maxHp']} SP {p['sp']}  {p['date']}")


def main():
    setup()
    argv = sys.argv[1:]
    nums = [int(a) for i, a in enumerate(argv) if re.fullmatch(r"\d+", a) and (i == 0 or argv[i - 1] != "--in")]
    max_danger = nums[0] if nums else DEFAULT_MAX_DANGER
    global GATE
    if "--unattended" in sys.argv:
        max_danger -= THRESHOLDS["unattended_minus"]
    GATE = ["--max-danger", str(max_danger)]
    floors = nums[1] if len(nums) > 1 else 3
    solo = "--solo" in sys.argv
    register("ladder")  # stopjob.py ladder asks it to stop between floors (springday's pattern)
    if depth(zone().get("full")) == 0:
        stop(f"{zone().get('full')} is not a dungeon floor")
    ether_check()
    room_check()
    if "--kit-ok" not in sys.argv:
        kit_check()
    print(f"danger cap {max_danger}" + (" (unattended)" if "--unattended" in sys.argv else "") + f", {floors} floors")
    mark("nefia", "start")
    try:
        floors_loop(max_danger, floors, solo)
    finally:
        mark("nefia", "end", note=f"{FLOORS_DONE} floors")


if __name__ == "__main__":
    main()
