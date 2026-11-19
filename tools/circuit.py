"""The nefia circuit as one loop (the review of 2026-10-30, the user's ok): run 30's 820 points an hour was this
done by hand. From the world map: `places` -> the nearest unconquered nefia of base danger LO-HI within R
tiles (no underwater ones) -> wgo.py there -> Enter -> ladder.py (the gate, FLOORS floors) -> on "conquered"
evac.py out -> repeat, until N nefias, or a ladder stop that isn't a conquest, or the unload is due.

The home unload every UNLOAD_EVERY nefias (four since run 40: the bags fill) is NOT done here: the loop stops with
"go home: ..." and recall.py + arrive.py are the next steps by hand (an unload is ten minutes of box moves
that arrive.py already does). A ladder stop for a decision (rc 3) stops the circuit too: it is a decision.
Marks itself as one activity ("circuit") on top of the ladder's own marks.

usage: python -I tools/circuit.py [N=4] [--danger LO-HI=3-7] [--r 15] [--floors 5] [--unattended] [--solo] [--wrecks] [--danger-ok N] [--skip NAME ...] [--blanket-ok 'why']
  --blanket-ok 'why'  passed to each ladder: a nefia with no charged blanket, a row in runs/waivers.csv each time (the user, 2026-11-06)
  --wrecks  mine the wrecks on each floor (ladder.py without --no-wrecks; run 34, G35: iron wrecks drop a battery and a
            microchip each, the Gene Machine's power parts)
  --danger-ok N  passed to wgo.py: a deliberate crossing of ambush levels up to N (elin-play's route rule)
  --skip NAME    leave out a nefia whose name contains NAME (repeatable): one whose master lies below the gate
  --until HH:MM  no new nefia after this clock time (run 42: the shipping and the close-out wait on the circuit; a nefia is ~10 real minutes)
It registers as a job (runs/jobs/circuit.json: journal.py refuses while it runs) and runs/jobs/circuit.stop ends it between nefias.
Started on a nefia's floor it runs the ladder there first (run 40). A nefia that expires before the walk and a conquest is skipped,
and a nap at the door happens only when the nefia outlives it (run 48, bridge 0.42.0 expireH). An empty list gets one nap to refill it (run 40).
Exit 0 after N conquests, 1 refused (not on the world map or a nefia, the kit), 3 stopped (a ladder decision, no nefia
in range, the unload due).
"""
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from activity import mark  # noqa: E402
import bridge  # noqa: E402
from common import bag_slots, TOOLS, THRESHOLDS, Output, call, data, last, refuse, run, run_live, state, stop, wait_until, waiver_reason  # noqa: E402
from job import register, stop_requested  # noqa: E402

UNLOAD_EVERY = 4  # run 40: was 2; three bags carry 3-4 conquests, and a full bag stops the circuit by itself (below)
BAG_FULL = 2  # run 36: a bag this close to its slots counts as full (common.bag_slots: 35, the wrenched loot bag 48)


CONQUESTS = TOOLS.parent / "runs" / "conquests.csv"


def log_conquest(ladder_text):
    """One row a conquest in runs/conquests.csv: where, the floor's danger, the gate in force and the lowest HP the
    ladder printed on the way. The review of 2026-11-11: the floor gate stood at 16 at Lv40 and nothing recorded
    what the floors cost (runs/nefias.csv was kept by hand and stops at run 40). The user, 2026-11-12: the gate
    rises a step at a time on this evidence (elin-delve). Never breaks a circuit."""
    try:
        import csv
        s = state()
        z, p = s.get("zone") or {}, s.get("pc") or {}
        low = min((int(a) * 100 // max(int(b), 1) for a, b in re.findall(r"HP (\d+)/(\d+)", ladder_text)), default="")
        new = not CONQUESTS.exists()
        with CONQUESTS.open("a", encoding="utf-8", newline="") as f:
            out = csv.writer(f)
            if new:
                out.writerow(["at", "game_date", "name", "zone", "danger", "gate", "lv", "lowest_hp_pct", "unattended"])
            out.writerow([time.strftime("%Y-%m-%d %H:%M"), p.get("date"), z.get("name"), z.get("full"), z.get("danger"),
                          THRESHOLDS["max_danger"], p.get("lv"), low, int("--unattended" in sys.argv)])
    except Exception as e:  # noqa: BLE001
        print(f"  conquest not logged: {e}", flush=True)


def clear_weak(max_fights=4):
    """Run 39 (Tangled Ruin B3): after the conquest evac.py refused over a Lv1 putit, a Lv2 yeek and a Lv7 wasp in
    view, and the circuit stopped for a hand-run evacuation. Before the evacuation, fight hostiles 10+ levels under
    mine one at a time (fight.py and its own rules: exploders refused, the round rule), at most `max_fights`; anything
    stronger is left for evac.py's refusal and the stop it brings."""
    for _ in range(max_fights):
        s = data("state")
        me = (s.get("pc") or {}).get("lv") or 0
        foes = [c for c in s.get("nearby") or [] if c.get("hostile")]
        if not foes or any((c.get("lv") or 0) > me - 10 for c in foes):
            return
        f = min(foes, key=lambda c: c.get("dist", 99))
        r = run("fight.py", f.get("id") or f["name"], timeout=300)
        print(f"  clear_weak: {f['name']} Lv{f.get('lv')} at {f.get('dist')}: fight.py rc {r.rc}", flush=True)
        if r.rc != 0:
            return


def on_world():
    z = state().get("zone") or {}
    return z["region"] if "region" in z else "ntyris" in str(z.get("full") or "")


def fed_nap():
    """A nap on the world map, after a meal when hunger is 50+ (run 44: 'sleepy at the door: refused: hunger 58/62: eat first'
    three times in one evening; sleep.py won't nap hungry and the world map has no Eat). wgo.meal_stop enters the local map
    under me (a nefia's tile goes in and back up its stairs), eats to the mark, and comes back up."""
    if ((state().get("pc") or {}).get("hunger") or 0) >= 50:
        import os
        import wgo
        # run 51: the meal stop ate six 【Waking】 coffee-bean pies on Traditional Ruin's B1 (item.py allows them on a nefia
        # floor) and the nap that followed was refused "not sleepy": a nap follows this meal, so item.py refuses them here
        os.environ["ELIN_NAP_NEXT"] = "1"
        try:
            why = wgo.meal_stop()
        finally:
            os.environ.pop("ELIN_NAP_NEXT", None)
        print(f"  a meal before the nap: {why or 'fed'}", flush=True)
        # run 44 (Savage Ruin): the meal stop ate on B1 with a drone in view and its stairs up didn't take, so the nap was
        # refused "in a nefia" and the circuit looked for the world map's Enter from inside the floor
        for _ in range(2):
            if not (state().get("zone") or {}).get("nefia"):
                break
            print("  still on the nefia's floor after the meal: stairs up", flush=True)
            # run 45 (Mystical Cave's neighbour, B1): a puppet Lv12 beside the stairs refused both climbs; a foe at or under my level
            # is fought first (fight.py keeps its own HP rules), anything stronger still stops at the ladder's door
            s = state()
            me = (s.get("pc") or {}).get("lv") or 0
            foes = sorted((c for c in s.get("nearby") or [] if c.get("hostile") and (c.get("lv") or 99) <= me),
                          key=lambda c: c.get("dist", 99))
            if foes:
                f = run("fight.py", foes[0].get("id") or foes[0]["name"], timeout=300)
                print(f"  fought {foes[0]['name']} Lv{foes[0].get('lv')} by the stairs: rc {f.rc}", flush=True)
            run("stairs.py", "up", timeout=300)
    return run("sleep.py", timeout=600)


WALK_H_PER_TILE = 3.2  # run 48: 12 tiles in 37.8 game hours, 16 in ~48, 3 in 7.6 (wgo legs, x5 speed)
CONQUEST_H = 20        # run 48: Traditional Ruin and Historic Cave took ~20 game hours from the door to the evacuation
NAP_H = 16             # a nap at the door runs 9-15 game hours (runs 47-48)


def expire_here():
    """Hours left on the nefia of this world-map tile (bridge 0.42.0), or None (an older mod, a place that never expires)."""
    for p in (call("places", r=0).get("data") or {}).get("places") or []:
        if p.get("dist") == 0 and "Danger Lv." in (p.get("name") or ""):
            return p.get("expireH")
    return None


def candidates(lo, hi, r, skip=()):
    rep = call("places", r=r)
    for i in range(6):  # run 54: "ArgumentException: Can not convert Object to Int32" twice, just after an evacuation's landing; the same call answered later (three tries 30 frames apart weren't enough)
        if rep.get("ok"):
            break
        print(f"  places: {rep.get('error')}: again", flush=True)
        import time as _time
        _time.sleep(2 + 2 * i)
        rep = call("places", r=r)
    if not rep.get("ok"):
        stop(f"places kept failing after the landing ({rep.get('error')}): run circuit.py again")
    try:  # the terrain grid for route(), read once here from where I stand (run 49)
        import wgo
        wgo._GRID.clear()
        wgo.prime_grid(r + 25)
    except Exception:  # noqa: BLE001 (route() falls back to twice the straight distance)
        pass
    out = []
    for p in rep["data"]["places"]:
        m = re.search(r"\(Danger Lv\.(\d+)\)", p["name"])
        if not m or "Conquered" in p["name"] or "Underwater" in p["name"] or "water" in str(p.get("id") or ""):
            continue
        if any(k.lower() in p["name"].lower() for k in skip):  # run 34: a master below the gate (Ancient Grassland)
            continue
        d = int(m.group(1))
        if not lo <= d <= hi:
            continue
        # run 48 (bridge 0.42.0 expireH): Isolated Ruin was 36 tiles off; the walk (~3.2 game hours a tile) and the nap at its
        # door outlived it, the fourth time (runs 47-48). A nefia that expires before the walk and a conquest (~20 h) is skipped
        left = p.get("expireH")
        # run 49: Strange Grassland and Silent Ruin were 14-17 tiles off in a straight line and both walks wandered round
        # water for 8-9 game days and expired on the way: the walk is the route's steps round blocked tiles (wgo.route_steps),
        # and with no route in the box, twice the straight distance
        steps = route(p)
        p["steps"] = steps
        if left is not None and p["dist"] > 0 and left < steps * WALK_H_PER_TILE + CONQUEST_H:
            print(f"  skipped: {p['name']} expires in {left} h; the walk alone is ~{round(steps * WALK_H_PER_TILE)} h "
                  f"({steps} steps for {p['dist']} tiles)", flush=True)
            continue
        # distance 0 is the nefia just left (evac lands on its tile), unless it was never entered: run 37 walked onto
        # Ancient Machinarium's tile by hand and the circuit stopped "no nefia within 5"
        if lo <= d <= hi and (p["dist"] > 0 or not p.get("known")):
            out.append((p.get("steps") or p["dist"], d, p))  # run 49: nearest by the route, not the straight line
    return sorted(out, key=lambda t: (t[0], t[1]))  # run 34: a tie compared the place dicts (TypeError)


def route(p):
    """A place's walk in world-map steps round blocked tiles (wgo.route_steps), else twice the straight distance."""
    if p["dist"] <= 0:
        return 0
    try:
        import wgo
        s = wgo.route_steps(p["dx"], p["dz"])
    except Exception:  # noqa: BLE001 (an older mod without the terrain op: the straight line, doubled)
        s = None
    return s if s is not None else 2 * p["dist"]


def over_gate(hi, r):
    """Land nefias within r tiles whose base danger is over `hi` (the fame-sale signal)."""
    rep = call("places", r=r)
    n = 0
    for p in (rep.get("data") or {}).get("places") or []:
        m = re.search(r"\(Danger Lv\.(\d+)\)", p["name"])
        if m and "Underwater" not in p["name"] and int(m.group(1)) > hi:
            n += 1
    return n


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if {"-h", "--help"} & set(args):  # run 34: `circuit.py --help` started a 4-nefia circuit
        print(__doc__)
        return
    n = next((int(a) for a in args if re.fullmatch(r"\d+", a)), 4)
    lo, hi = 3, 7
    if "--danger" in args:
        lo, hi = (int(x) for x in args[args.index("--danger") + 1].split("-"))
    r = int(args[args.index("--r") + 1]) if "--r" in args else 15
    floors = int(args[args.index("--floors") + 1]) if "--floors" in args else 5
    # run 54: `--skip A B C` skipped only A (one name a flag), and the circuit walked back into Terrifying Cave, whose named
    # kamikaze yeek had made me teleport off B4 an hour before: every name after --skip up to the next flag is skipped
    skip = []
    for i, a in enumerate(args):
        if a == "--skip":
            for b in args[i + 1:]:
                if b.startswith("--"):
                    break
                skip.append(b)
    # run 36: --blanket-ok passes through to the ladder, only on purpose (the blanket burned out and neither Aquli Teola
    # seller had one; the escape kit itself is fire-safe: rods of teleport and the Evacuation spell)
    # 2026-11-06, the user: the flag now carries its reason, and run 42 passed it on every circuit without one
    extra = [a for a in ("--unattended", "--solo", "--expendable") if a in args]
    blanket_why = waiver_reason("--blanket-ok")
    if blanket_why:
        extra += ["--blanket-ok", blanket_why]
    # run 40: seven hand-run ladders in one morning after a stop inside a nefia: from a nefia's floor it picks up where it stopped
    resume = not on_world() and bool((state().get("zone") or {}).get("nefia"))
    if not on_world() and not resume:
        refuse("not on the world map: leave.py (or evac.py) first")
    napped = False
    until = args[args.index("--until") + 1] if "--until" in args else None
    deadline = None
    if until:
        # run 45: "--until 00:00" at 18:28 stopped at once ("18:28" >= "00:00" as strings): a time already past today is tomorrow's
        import datetime as _dt
        hh, mm = map(int, until.split(":"))
        now = _dt.datetime.now()
        deadline = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if deadline <= now:
            deadline += _dt.timedelta(days=1)
    # run 53 (the user: "Boots/Cloak/Necklace are all empty"): an antibody drunk on the road freed the neck slot, and the
    # Dreadbane Necklace sat in a home box; leave.py's gear check runs only at home. Name an empty, unblocked slot here
    # (a warning: the piece is usually at home, so the circuit goes on and the next home stop wears it)
    try:
        from common import empty_slots
        gaps = empty_slots()
        if gaps:
            print("  WARNING: empty gear slot(s): " + ", ".join(gaps) + " (wear the best piece in hand; at home leave.py "
                  "refuses until it is filled)", flush=True)
    except Exception as e:  # noqa: BLE001 - a warning only
        print(f"  (gear check skipped: {e})", flush=True)
    register("circuit")
    mark("circuit", "start", note=f"{n} nefias, danger {lo}-{hi}, r {r}")
    done = 0
    try:
        while done < n:
            if stop_requested("circuit") or (deadline and _dt.datetime.now() >= deadline):
                stop(f"asked to stop between nefias ({until or 'circuit.stop'}): {done} conquered")
            # run 50: the full-bags stop ran only after a conquest, so circuits started with every bag full of unidentified
            # and ☆ pieces and stalled on "42+ stacks" floor after floor (Damp Forest four times; lesson 48 repeated):
            # check before walking to the next nefia as well
            if not resume:
                bags = [i for i in data("stock", r=0)["pack"] if i.get("name") in ("a backpack", "a loot bag", "a spoils bag", "a haul bag")]
                if bags and all(len(b.get("items") or []) >= bag_slots(b["name"]) - BAG_FULL for b in bags):
                    stop(f"go home first: the bags are full ({', '.join(str(len(b.get('items') or [])) for b in bags)} stacks): "
                         "identify (Aliyun, or SpIdentify) and ship, then circuit.py again")
            if not resume:
                cands = candidates(lo, hi, r, skip)
                # run 40 (fact: "nefia list refills on a sleep"): 2 nefias within 42 tiles of Palmia, then 23 within 28 after one
                # nap on the spot. Once a circuit, when the game lets me sleep
                if not cands and not napped:
                    napped = True
                    sl = fed_nap()
                    print(f"  no nefia in range: a nap to refill the list: sleep.py rc {sl.rc}: {last(sl)[:70]}", flush=True)
                    if (state().get("layers") or {}).get("top"):
                        run("close.py", timeout=60)
                    cands = candidates(lo, hi, r, skip)
                if not cands:
                    # runs 26, 31, 34 (twice): new nefias come at FameLv x 75-125% (fact #881), so after ~7 conquests the
                    # refill near home runs over the unattended gate; two fame sales brought six of danger 4-10 (fact #1085)
                    k = over_gate(hi, r)
                    hint = (f"; {k} nefias within {r} tiles are over danger {hi}: sell fame twice (Gizon in Olvina, 2 rations "
                            "by Fast Travel, or Ishbear in Palmia; facts #1067, #1078)") if k >= 3 else ""
                    # run 50: this stop at 14:24 of a window to 15:54 became the end of play; while the window has time
                    # left, it names what comes next
                    from session_end import ends_at, now as clock
                    end = ends_at()
                    left = int((end - clock()).total_seconds()) // 60 if end else 0
                    if left > 30:
                        hint += (f"; the play window has {left} minutes left: Fast Travel to a region not circuited lately, "
                                 "a fame sale, or the dummy (elin-train), never the close-out (run 50)")
                    stop(f"no unconquered nefia of danger {lo}-{hi} within {r} tiles (places); the refill only tops the region "
                         f"up to 70, so the near ones change as the old ones expire (about a week){hint}")
                # run 34: a deliberate crossing above route_max (elin-play's route rule) is passed through, never assumed
                dok = ["--danger-ok", args[args.index("--danger-ok") + 1]] if "--danger-ok" in args else []
                # run 36: north of home every danger-5 nefia but one lay past ambush fields of 15-23; wgo refuses those
                # routes before the first step (rc 1), so the next candidate is tried instead of ending the circuit
                for dist, danger, p in cands:
                    print(f"[{done + 1}/{n}] {p['name']} at {dist} tiles", flush=True)
                    w = run("wgo.py", p["name"], "--ambush", "--weak-ok", *dok, timeout=900)
                    # run 45: "no place 'Rustic Forest (Danger Lv.11)' listed" twice: it expired between this list and wgo's own
                    if w.rc == 1 and ("the route crosses ambush level" in w or "no place" in w and "listed" in w):
                        print(f"  skipped: {last(w)[:110]}", flush=True)
                        skip.append(p["name"])
                        continue
                    # run 37 (Ruined Machinarium, Warped Forest): the straight line passed the check and the game's own
                    # path then strayed into a field of 20-22; wgo stops there (rc 3): try the next one from where I stand
                    if w.rc == 3 and ("the game's path reached ambush level" in w or "no longer listed" in w):
                        print(f"  skipped: {last(w)[:110]}", flush=True)
                        skip.append(p["name"])
                        # run 37: the skip after an ambush left me on its field map, and the next wgo refused there
                        if not (state().get("zone") or {}).get("region"):
                            lv = run("leave.py", timeout=600)
                            if lv.rc != 0:
                                stop(f"leave.py rc {lv.rc} after a skip: {last(lv)[:100]}")
                        continue
                    break
                else:
                    stop(f"every nefia of danger {lo}-{hi} within {r} tiles lies past ambush fields over the route limit "
                         "(wgo.py): a fame sale brings new ones nearer (Ishbear in Palmia, Gizon in Olvina)")
                if w.rc != 0:
                    stop(f"wgo.py rc {w.rc}: {last(w)[:120]}")
                # run 34: the 05:00 shipping report opened on arrival and the game ignored the Enter ('do' refused)
                if (state().get("layers") or {}).get("top"):
                    run("close.py", timeout=60)
                # run 39 (Guiding Cave) and run 38 (Tragedic Machinarium): Sleepy on arrival, and the ladder stopped on
                # B1 ("sleep first, on the overworld"); sleep here on the nefia's tile first (sleep.py refuses at hunger
                # 50+: then the ladder's own stop stands)
                # run 47: three naps at the door outlived their nefias (each lives 7 game days) and the Enter landed on the
                # tile's field, so the nap was moved to Very Sleepy; the same night the ladder then stopped mid-floor on
                # "Sleepy: sleep first" (it doesn't nap there). Back to Sleepy: an expired nefia costs a walk, the circuit's
                # own "not a nefia" stop says so, and a re-run picks the next one
                sleepy_ok = []
                if ((state().get("pc") or {}).get("sleepPhase") or 0) >= 1:
                    # run 48: the fourth nap that outlived its nefia (Isolated Ruin, after a 36-tile walk). Nap here only when
                    # the nefia outlives the nap and a conquest; otherwise go in Sleepy and let the ladder nap at Very Sleepy
                    left = expire_here()
                    if left is not None and left < NAP_H + CONQUEST_H:
                        print(f"  sleepy at the door, but it expires in {left} h: no nap; the ladder goes on until Very Sleepy", flush=True)
                        sleepy_ok = ["--sleepy-ok"]
                    else:
                        # run 42: "refused: hunger 61/71: eat first" at the door, twice: the world map offers no meal, so step in for one and out again is the ladder's job: count it here
                        sl = fed_nap()
                        print(f"  sleepy at the door: sleep.py rc {sl.rc}: {last(sl)[:80]}", flush=True)
                acts = (call("acts", dx=0, dz=0, mode="all").get("data") or {}).get("acts") or []
                ent = [a for a in acts if a["text"] == "Enter"]
                if not ent:
                    stop(f"no Enter on this tile after the walk: look.py ({[a['text'] for a in acts]})")
                call("do", i=ent[0]["i"])
                wait_until("zone", timeout=20000)
                z = state().get("zone") or {}
                if not z.get("nefia"):  # run 34: an expired nefia's tile enters its Wilds field instead
                    stop(f"entered {z.get('full')} ({z.get('name')}), not a nefia: leave.py and run the circuit again")
            if resume:
                sleepy_ok = []
            resume = False
            # run 34: ladder.py takes MAX_DANGER first and FLOORS second; passing only the floors capped the danger
            # at 5 and ran 3 floors (ladder lowers the cap by one itself under --unattended)
            wreck_flag = [] if "--wrecks" in args else ["--no-wrecks"]
            lad = run_live("ladder.py", str(THRESHOLDS["max_danger"]), str(floors), *wreck_flag, *extra, *sleepy_ok, timeout=7200)  # 5 floors ran past an hour in run 33
            # run 36: Misty Cave (5) used its five floors (a nap outside counts one) and ended "done:" on B4 at full HP;
            # a clean finish without the master is another batch of floors, twice at most, not the circuit's end
            for _more in range(2):
                if lad.rc != 0 or "conquered:" in lad or not last(lad).startswith("done:"):
                    break
                print(f"  floors used up before the master ({last(lad)[:80]}): {floors} more", flush=True)
                lad = run_live("ladder.py", str(THRESHOLDS["max_danger"]), str(floors), *wreck_flag, *extra, timeout=7200)
            text = lad.strip()
            if "conquered:" not in text:
                # run 48 (Chilly Cave B4): the master (an Evolved Crab) died, the zone read *Conquered*, and the floor's
                # summoned offspring of Shub-Niggurath (an avoid kind) stopped delve before the ladder looked: the circuit
                # said "without a conquest" and logged nothing. The stop is still a decision, but a conquest is one
                zname = (state().get("zone") or {}).get("name") or ""
                if "Conquered" in zname:
                    log_conquest(text)
                    stop(f"conquered ({zname.strip()}) but the ladder stopped: {last(lad)[:120]}. By hand: the boss chest "
                         f"(ladder.chests), clear of the foe (teleport), evac.py, then circuit.py again")
                stop(f"ladder rc {lad.rc} without a conquest: {last(lad)[:140]}")
            done += 1
            log_conquest(text)
            # run 34: the boss chest's loot filled the grid after the last floor's purge, and the next nefia's ladder refused
            # at its room check (-2 free cards): free 3 before leaving the conquered floor
            run("purge.py", "--free", "3", timeout=600)
            clear_weak()
            ev = run("evac.py", timeout=900)
            # run 43 (Warded Ruin B2): a hot guy clear_weak won't touch stopped the circuit at the conquered floor: the table's answer is a teleport, then the scroll
            for _ in range(2):
                if ev.rc != 1 or "hostile" not in str(ev):
                    break
                # run 53 (Guiding Cave B5): a hot guy at 2 and no plain "scrolls of teleport" left (the kit's teleports are the
                # spell and a rod): the read did nothing and the circuit stopped. The Short Teleport spell first, then a scroll
                r = call("cast", spell="SpTeleportShort")
                if r.get("ok") and (r.get("data") or {}).get("cast"):
                    print("  a foe in view at the evacuation: Short Teleport (the spell)", flush=True)
                else:
                    t = run("item.py", "scroll of teleport", "Read", timeout=60)
                    print(f"  a foe in view at the evacuation: teleport ({last(t)[:40]})", flush=True)
                wait_until("frames", n=15, timeout=2000)
                ev = run("evac.py", timeout=900)
            if ev.rc != 0 or not on_world():
                stop(f"evac.py rc {ev.rc}: {last(ev)[:120]} (get out by hand: stairs.py up)")
            if done % UNLOAD_EVERY == 0 and done < n:
                stop(f"go home: {done} nefias conquered, the unload is due (recall.py, arrive.py), then circuit.py again")
            # run 36: the count above restarts with every circuit call, and after five calls all three bags held 35
            # stacks each: two floors stalled on "a meal would fall to the floor". Full bags end the circuit too
            bags = [i for i in data("stock", r=0)["pack"] if i.get("name") in ("a backpack", "a loot bag", "a spoils bag", "a haul bag")]
            if bags and all(len(b.get("items") or []) >= bag_slots(b["name"]) - BAG_FULL for b in bags) and done < n:
                stop(f"go home: the bags are full ({', '.join(str(len(b.get('items') or [])) for b in bags)} stacks): "
                     "recall.py, arrive.py, then circuit.py again")
        print(f"done: {done} nefias conquered")
    finally:
        mark("circuit", "end", note=f"{done} conquered")


if __name__ == "__main__":
    main()
