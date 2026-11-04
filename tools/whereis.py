"""Ask a town guard "Where is..." and let the game walk me there (AI_Goto), then wait until
I've arrived. Picks the guard's entry by text, never by index.

usage: python -I tools/whereis.py GUARD|any TARGET
  e.g. python -I tools/whereis.py Elfeus "furniture shopkeeper"
       python -I tools/whereis.py Elfeus "tax chest"
Refuses (exit 1) standing in deep water (pc.inWater, bridge 0.30.0), without a guard or an entry;
stops (exit 3) when the sweep or the guard's walk heads into deep water (run 19's drowning).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import cells, pc, refuse, run, stop, wait_until, walk  # noqa: E402


def button(text):
    for b in call("buttons")["data"]["buttons"]:
        if text.lower() in b["text"].lower():
            return b["i"]
    return None


def main():
    guard, target = sys.argv[1], sys.argv[2]
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    s = call("state")["data"]
    p = s["pc"]
    # bridge 0.30.0: standing in deep water is pc.inWater (pathWater said "(here)" before, and
    # every walk stopped on it); step out by hand first
    if p.get("inWater"):
        refuse("standing in deep water: step out first (run 19: suffocation)")
    # run 17: at night no guard was in view, so whereis.py failed and I swept Willow for the
    # target by hand instead (the user: "if you ask the guard the 'quest' stuff is always at the
    # top level"). GUARD "any": walk the town's waypoints until any guard is in view, then ask it.
    if guard.lower() == "any":
        b = [int(v) for v in ((s.get("zone") or {}).get("bounds") or "0,0,0,0").split(",")]
        pts = sorted(((x, z) for z in range(b[1] + 5, b[3] - 2, 8) for x in range(b[0] + 5, b[2] - 2, 8)),
                     key=lambda q: abs(q[0] - p["x"]) + abs(q[1] - p["z"]))
        # run 19 (death by drowning, Port Kapul): the sweep walked waypoints in the harbour and the
        # game's pathing swam; Kapul's guards are "guard_port", so none matched and it kept going.
        # Skip waypoints on water; bridge 0.28 walkto stops before deep water (why "water").
        dry = cells(pts)
        pts = [q for q in pts if not (dry.get(q) or {}).get("water") and not (dry.get(q) or {}).get("blocked")]
        for x, z in [(p["x"], p["z"])] + pts:
            if (x, z) != (p["x"], p["z"]):
                w = walk(x, z, r=2, timeout=30000, weak_ok=True)
                if w.get("why") in ("water", "hp"):
                    stop(f"the sweep stopped: {w.get('why')} {w.get('water') or ''} (HP {w.get('hp')}/{w.get('maxHp')})")
            g = [c for c in call("state")["data"].get("nearby") or [] if str(c.get("id") or "").startswith("guard")]
            if g:
                guard = g[0]["name"]
                break
        else:
            refuse("no guard found on this map")
    run("talkto.py", guard)
    # A quest's target that isn't on the "Where is" list (guards never are) has its own line in a
    # guard's main menu: "Do you know Havin the guard? (Small errand)" (the user's tip, run 15: a
    # night's sweep of Mysilia missed him; one guard walked me there).
    b = button("Do you know " + target)
    if b is None:
        b = button("Where is...")
        if b is None:
            refuse("the guard's dialog has no 'Where is...' (is it a guard? is the dialog open?)")
        call("click", i=b)
        time.sleep(1.0)
        b = button(target)
    if b is None:
        opts = [x["text"] for x in call("buttons")["data"]["buttons"] if x["text"].startswith("Where is")]
        bye = button("No.")
        if bye is not None:
            call("click", i=bye)
        refuse(f"no entry for {target!r}; the guard knows: " + " | ".join(opts))
    call("click", i=b)
    time.sleep(1.0)
    # Close the guard's reply the way talk.py does (a raw key press cancelled the walk). The walk
    # starts only once the dialog is fully closed: if it returns to the guard's menu, say Bye
    # (run 03, Olvina: a guard who is also a job client loops back to the menu).
    run("talk.py")
    for _ in range(3):
        if not call("state")["data"].get("drama"):
            break
        bye = button("Bye.")
        if bye is None:
            break
        call("click", i=bye)
        time.sleep(1.0)
    # the guard's walk (AI_Goto): the bridge's wait returns the frame it ends; between waits the
    # path is checked for deep water (run 19). Up to 10 x 15 s, as the old 150 x 1 s poll.
    wait_until("moved", timeout=5000)  # the walk starts (or it is a one-cell answer)
    for _ in range(10):
        p = pc()
        if p.get("pathWater") or p.get("inWater"):  # the walk heads into deep water: cancel it
            call("cancel")
            stop(f"the walk to {target} crosses deep water at {p.get('pathWater') or 'here'} (suffocation)")
        w = wait_until("idle", timeout=15000)
        if w.get("done"):
            break
    p = pc()
    print(f"arrived near {target} at {p['x']},{p['z']} ({p['date']})")


if __name__ == "__main__":
    main()
