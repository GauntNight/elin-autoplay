"""Mine a block in a lawful town without a witness (run 23, G18: Aquli Teola's steel crystal pillars).

Mining and digging are hostile acts (TaskMine/TaskDig.IsHostileAct): in a zone with law each one
done costs Karma -1, and on every progress tick each human in a strict circle of 4 (dx*dx + dz*dz
< 16: the bridge's Distance 3 or less) with line of sight to me rolls 1 in 10 to call the nearest
guard, who attacks (Point.TryWitnessCrime; Aquli Teola's cyber guards are Lv40). So:
  1. walk beside the block; refuse (exit 3) if anyone who could witness is within START, or a cell
     in line of sight within START + 1 is unseen (dark: a person could stand there);
  2. turn on the bridge's sneak guard (0.31.2): at the start of each of my turns, before the task's
     roll, a possible witness within R cancels the task (a watchful player's cancel; the game's
     rules are untouched). R = 3 is the game's own set (run 23: a guard posted at Distance 4 by
     Aquli Teola's east gate pillar);
  3. hold the pickaxe and mine; the game's "Really commit a crime?" is answered "Yes." (never the
     "don't ask again": the prompt stays) with the guard already on, then the drop is picked up
     (run 23: harvest.py stopped on that dialog, the tool turned the guard off, and the click that
     followed mined the first pillar unguarded);
  4. report the karma change, the guard's stops and what came into the pack.

usage: python -I tools/sneakmine.py X,Z [X,Z ...] [--r 3] [--start R] [--tool pickaxe]
       python -I tools/sneakmine.py X,Z --disassemble "mountain of ores"   (the hammer's Disassemble of
       town property, run 23 at Vernis: TaskHarvest.TryGetAct takes the cell's things from the last
       one back, so the named thing must be the last one that can be disassembled; the tool checks
       the act's own start line names it and cancels otherwise)
--wait N: when not alone beside the target, pass up to N single turns (Wait) for the witnesses to
walk off, re-checking each turn; stops on a hostile in view or HP under 80% (run 23: Aquli Teola's
west gate guard keeps post one cell from its pillar).
Exit codes: 0 done, 1 refused, 2 bridge, 3 stopped (a witness, the guard cancelled, a hostile).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import act, call, cells, data, grab, ready, refuse, setup, state, stop, wait_idle, walk_beside  # noqa: E402

CRIME = "Really commit a crime?"


def opt(name, default):
    a = sys.argv
    return a[a.index(name) + 1] if name in a else default


def witnesses(r):
    w = data("witness", r=r)
    who = [f"{c['name']} d{c['dist']}" + (" (guard)" if c.get("guard") else "")
           for c in w["creatures"] if c.get("witness")]
    return who, w["blindCells"], w["zoneLaw"]


def mine(x, z, thing=None):
    """Start the Mine (or Disassemble) act on (x, z), answer the crime prompt, check the task names
    the intended target, wait until it ends."""
    p = state()["pc"]
    acts = call("acts", dx=x - p["x"], dz=z - p["z"], mode="right")["data"]["acts"]
    if thing:
        hit = [a for a in acts if a["text"].startswith("Disassemble")]
    else:
        hit = [a for a in acts if a["act"] == "TaskMine" or a["text"].startswith("Mine")]
    if not hit:
        stop(f"no {'Disassemble' if thing else 'Mine'} act at {x},{z}: " + ", ".join(a["text"] for a in acts))
    call("do", i=hit[0]["i"])
    print(f"  {hit[0]['text']}")
    for _ in range(20):
        time.sleep(0.5)
        if (state().get("layers") or {}).get("top") != "Dialog":
            break
        texts = data("texts")["texts"]
        if CRIME not in texts:
            stop("a dialog opened: " + " | ".join(texts))
        bs = data("buttons")["buttons"]
        yes = [b for b in bs if b["text"].split("|")[-1].strip() == "Yes."]  # "a | Yes.": key, caption
        if not yes:
            stop("the crime prompt has no 'Yes.' button")
        call("click", i=yes[0]["i"], expect="Yes.")
    if thing:
        time.sleep(0.3)
        log = " ".join((state().get("log") or [])[-4:])
        if "disassemble" in log.lower() and thing not in log:
            call("cancel")
            stop(f"the Disassemble started on something else: {log}")
    w = wait_idle(timeout=90000)
    return w.get("why")


def main():
    setup()
    r, tool = int(opt("--r", 3)), opt("--tool", "pickaxe")
    start = int(opt("--start", r))
    skip = {"--r", "--start", "--tool", "--disassemble", "--wait"}
    patience = int(opt("--wait", 0))
    thing = opt("--disassemble", None)
    if thing and "--tool" not in sys.argv:
        tool = "iron hammer"
    targets, args = [], sys.argv[1:]
    for i, a in enumerate(args):
        if a in skip or (i and args[i - 1] in skip):
            continue
        x, _, z = a.partition(",")
        targets.append((int(x), int(z)))
    if not targets:
        refuse("no target cells (X,Z)")
    if r < 3 or start < r:
        refuse(f"--r {r} --start {start}: the game's witness set is Distance 3 or less; neither may be under it")
    why = ready(hp=80)
    if why:
        refuse(why)
    karma0 = state()["pc"].get("karma")
    for x, z in targets:
        c = cells([(x, z)]).get((x, z)) or {}
        if thing:
            if not any(thing in t for t in c.get("things") or []):
                print(f"{x},{z}: no {thing} there ({c.get('things')}): skipped")
                continue
            print(f"{x},{z}: {', '.join(c['things'])}")
        elif not c.get("block"):
            print(f"{x},{z}: no block there ({c.get('floor')}): skipped")
            continue
        else:
            print(f"{x},{z}: {c['block']} of {c.get('blockMat')} (hardness {c.get('blockHard')}, {c.get('blockReq')})")
        w = walk_beside(x, z)
        if w.get("why") != "arrived":
            stop(f"the walk beside {x},{z} ended: {w.get('why')} {w.get('hostile') or ''}")
        who, _, law = witnesses(start)
        _, blind, _ = witnesses(start + 1)
        waited = 0
        while (who or blind) and waited < patience:
            why = ready(hp=80)
            if why:
                stop(f"while waiting for the witnesses to leave: {why}")
            call("act", action="Wait")
            wait_idle(timeout=5000)
            waited += 1
            who, _, law = witnesses(start)
            _, blind, _ = witnesses(start + 1)
        if waited:
            print(f"  waited {waited} turns: {', '.join(who) or 'alone'}")
        if who or blind:
            stop(f"not alone at {x},{z}: {', '.join(who) or 'nobody seen'} within {start}; "
                 f"{blind} unseen cells in sight within {start + 1}")
        if not grab(tool, what="tool"):
            refuse(f"no {tool} to hold")
        try:
            call("sneak", r=r)
            outcome = mine(x, z, thing)
            sn = data("sneak")
        finally:
            call("sneak", r=0)
        after = cells([(x, z)]).get((x, z)) or {}
        p = state()["pc"]
        print(f"  {outcome}; block now {after.get('block')}; karma {karma0} -> {p.get('karma')}; guard stops {sn['stops']}")
        if sn["stops"]:
            stop(f"the sneak guard cancelled the mining at {x},{z}: {sn['lastStop']}")
        if after.get("block") if not thing else any(thing in t for t in after.get("things") or []):
            stop(f"{x},{z} not done ({outcome})")
        # only what belongs to nobody: the trolley under Vernis's ore pile is town property (theft)
        for t in after.get("thingInfo") or []:
            if not t.get("npcProperty") and act(x, z, f"Pick ({t['name']}"):
                print(f"  picked up {t['name']}")
    print(f"done: karma {karma0} -> {state()['pc'].get('karma')}")


if __name__ == "__main__":
    main()
