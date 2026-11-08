"""The nefia circuit as one loop (the review of 2026-10-30, the user's ok): run 30's 820 points an hour was this
done by hand. From the world map: `places` -> the nearest unconquered nefia of base danger LO-HI within R
tiles (no underwater ones) -> wgo.py there -> Enter -> ladder.py (the gate, FLOORS floors) -> on "conquered"
evac.py out -> repeat, until N nefias, or a ladder stop that isn't a conquest, or the unload is due.

The home unload every two nefias (elin-play: the bags fill) is NOT done here: the loop stops with
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
Started on a nefia's floor it runs the ladder there first (run 40). An empty list gets one nap to refill it (run 40).
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
from common import bag_slots, TOOLS, THRESHOLDS, Output, call, data, last, refuse, run, state, stop, wait_until, waiver_reason  # noqa: E402
from job import register, stop_requested  # noqa: E402

UNLOAD_EVERY = 4  # run 40: was 2; three bags carry 3-4 conquests, and a full bag stops the circuit by itself (below)
BAG_FULL = 2  # run 36: a bag this close to its slots counts as full (common.bag_slots: 35, the wrenched loot bag 48)


def run_live(tool, *args, timeout=7200):
    """common.run, but each line is printed as it comes (run 34: the ladder ran up to an hour inside run() and the
    circuit's log showed nothing until it ended, so nobody could watch a stop happen). -u: a piped child Python
    block-buffers its prints otherwise. Run the circuit with its stdout to a file, never through `head`: a closed
    pipe stops the printing thread and the ladder then blocks on a full pipe (run 34)."""
    bridge.close()
    proc = subprocess.Popen([sys.executable, "-I", "-u", "-X", "utf8", str(TOOLS / tool), *map(str, args)],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                            errors="replace")
    lines = []

    def pump():
        for line in proc.stdout:
            lines.append(line)
            print("  | " + line.rstrip(), flush=True)

    t = threading.Thread(target=pump, daemon=True)
    t.start()
    try:
        proc.wait(timeout=timeout)
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        lines.append(f"\nstop: {tool} timed out after {timeout}s")
        rc = 3
    t.join(timeout=10)
    out = Output("".join(lines).strip())
    out.rc = rc
    return out


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
        import wgo
        why = wgo.meal_stop()
        print(f"  a meal before the nap: {why or 'fed'}", flush=True)
        # run 44 (Savage Ruin): the meal stop ate on B1 with a drone in view and its stairs up didn't take, so the nap was
        # refused "in a nefia" and the circuit looked for the world map's Enter from inside the floor
        for _ in range(2):
            if not (state().get("zone") or {}).get("nefia"):
                break
            print("  still on the nefia's floor after the meal: stairs up", flush=True)
            run("stairs.py", "up", timeout=300)
    return run("sleep.py", timeout=600)


def candidates(lo, hi, r, skip=()):
    rep = call("places", r=r)
    if not rep.get("ok"):
        refuse(str(rep.get("error")))
    out = []
    for p in rep["data"]["places"]:
        m = re.search(r"\(Danger Lv\.(\d+)\)", p["name"])
        if not m or "Conquered" in p["name"] or "Underwater" in p["name"] or "water" in str(p.get("id") or ""):
            continue
        if any(k.lower() in p["name"].lower() for k in skip):  # run 34: a master below the gate (Ancient Grassland)
            continue
        d = int(m.group(1))
        # distance 0 is the nefia just left (evac lands on its tile), unless it was never entered: run 37 walked onto
        # Ancient Machinarium's tile by hand and the circuit stopped "no nefia within 5"
        if lo <= d <= hi and (p["dist"] > 0 or not p.get("known")):
            out.append((p["dist"], d, p))
    return sorted(out, key=lambda t: (t[0], t[1]))  # run 34: a tie compared the place dicts (TypeError)


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
    skip = [args[i + 1] for i, a in enumerate(args) if a == "--skip" and i + 1 < len(args)]
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
    register("circuit")
    mark("circuit", "start", note=f"{n} nefias, danger {lo}-{hi}, r {r}")
    done = 0
    try:
        while done < n:
            if stop_requested("circuit") or (until and time.strftime("%H:%M") >= until):
                stop(f"asked to stop between nefias ({until or 'circuit.stop'}): {done} conquered")
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
                    stop(f"no unconquered nefia of danger {lo}-{hi} within {r} tiles (places); the refill only tops the region "
                         f"up to 70, so the near ones change as the old ones expire (about a week){hint}")
                # run 34: a deliberate crossing above route_max (elin-play's route rule) is passed through, never assumed
                dok = ["--danger-ok", args[args.index("--danger-ok") + 1]] if "--danger-ok" in args else []
                # run 36: north of home every danger-5 nefia but one lay past ambush fields of 15-23; wgo refuses those
                # routes before the first step (rc 1), so the next candidate is tried instead of ending the circuit
                for dist, danger, p in cands:
                    print(f"[{done + 1}/{n}] {p['name']} at {dist} tiles", flush=True)
                    w = run("wgo.py", p["name"], "--ambush", "--weak-ok", *dok, timeout=900)
                    if w.rc == 1 and "the route crosses ambush level" in w:
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
                if ((state().get("pc") or {}).get("sleepPhase") or 0) >= 1:
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
            resume = False
            # run 34: ladder.py takes MAX_DANGER first and FLOORS second; passing only the floors capped the danger
            # at 5 and ran 3 floors (ladder lowers the cap by one itself under --unattended)
            wreck_flag = [] if "--wrecks" in args else ["--no-wrecks"]
            lad = run_live("ladder.py", str(THRESHOLDS["max_danger"]), str(floors), *wreck_flag, *extra, timeout=7200)  # 5 floors ran past an hour in run 33
            # run 36: Misty Cave (5) used its five floors (a nap outside counts one) and ended "done:" on B4 at full HP;
            # a clean finish without the master is another batch of floors, twice at most, not the circuit's end
            for _more in range(2):
                if lad.rc != 0 or "conquered:" in lad or not last(lad).startswith("done:"):
                    break
                print(f"  floors used up before the master ({last(lad)[:80]}): {floors} more", flush=True)
                lad = run_live("ladder.py", str(THRESHOLDS["max_danger"]), str(floors), *wreck_flag, *extra, timeout=7200)
            text = lad.strip()
            if "conquered:" not in text:
                stop(f"ladder rc {lad.rc} without a conquest: {last(lad)[:140]}")
            done += 1
            # run 34: the boss chest's loot filled the grid after the last floor's purge, and the next nefia's ladder refused
            # at its room check (-2 free cards): free 3 before leaving the conquered floor
            run("purge.py", "--free", "3", timeout=600)
            clear_weak()
            ev = run("evac.py", timeout=900)
            # run 43 (Warded Ruin B2): a hot guy clear_weak won't touch stopped the circuit at the conquered floor: the table's answer is a teleport, then the scroll
            for _ in range(2):
                if ev.rc != 1 or "hostile" not in str(ev):
                    break
                t = run("item.py", "scrolls of teleport", "Read", timeout=60)
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
