"""Read ONE scroll of return and wait for it to fire (run 20: the second read of a return during its
countdown cancelled it, "The air relaxes", and both scrolls were spent; runs 05 and 10 lost scrolls
the same way). The countdown took 19, 29 and 36 turns in run 20, so 16 waits are not enough.

Refuses (exit 1) while a return or evacuation is already counting down (state.pc.return, bridge
0.30.0; on an older mod the log's "tense up" without a "relaxes" only prints a note and waits),
on the world map, and without a scroll. An uncursed stack is read first; a cursed one only when
it is the only one.
Picks DESTINATION from the scroll's list (default Meadow), then passes turns while pc.return is
set: Wait when no hostile is adjacent (never on a stairway cell: Wait there takes the stairs),
fight.py on an adjacent one (when fight.py stops or refuses, one Wait passes the turn instead of
looping on the refusal). Never reads a second scroll. Stops (exit 3) under the HP floor, on a
window, when the countdown ends without a zone change, or after MAX turns.

usage: python -I tools/recall.py [DESTINATION=Meadow] [MAX_TURNS=60] [MIN_HP_PCT=50]
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BridgeError, overweight_stop, call, data, last, refuse, run, setup, state, stop, wait_until  # noqa: E402


def zone():
    return state().get("zone") or {}


def on_world(z):
    return z["region"] if "region" in z else "ntyris" in str(z.get("full") or "")


def pending(p):
    """The countdown from state.pc.return (bridge 0.30.0): its dict, None when none is running,
    or "unknown" on a mod that doesn't report it."""
    if "return" in p:
        return p["return"] or None
    return "unknown"


def main():
    setup()
    overweight_stop("a return")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    nums = [int(a) for a in args if re.fullmatch(r"\d+", a)]
    words = [a for a in args if not re.fullmatch(r"\d+", a)]
    dest = words[0] if words else "Meadow"
    max_turns = nums[0] if nums else 60
    min_hp = nums[1] if len(nums) > 1 else 50
    s = state()
    if on_world(s.get("zone") or {}):
        # run 45: the circuit's "go home: recall.py" met this refusal on the world map, and I walked 85,158 -> home instead:
        # about nine game days of rent for one day's scroll. Step into the local map under me (as wgo.meal_stop does), then read
        acts = call("acts", dx=0, dz=0, mode="all").get("data", {}).get("acts") or []
        enter = [a for a in acts if a["text"] == "Enter"]
        if not enter:
            refuse("a scroll of return can't be read on the world map, and this tile has no plain Enter (a town or nefia): walk off it first")
        call("do", i=enter[0]["i"])
        wait_until("zone", timeout=10000)
        wait_until("frames", n=30, timeout=3000)
        s = state()
        if on_world(s.get("zone") or {}):
            refuse("still on the world map after Enter: read it by hand from a local map")
        if any(c.get("hostile") for c in s.get("nearby") or []):
            refuse("a hostile on the local map I stepped into: fight or leave first")
        print(f"  stepped into {(s.get('zone') or {}).get('full')} to read the scroll")
    # run 23: after claiming Vernis it was the home zone, and the scroll's list had no Meadow: the scroll
    # was spent for nothing. The list holds the home zone (never the zone I stand in) and each visited
    # dungeon's deepest floor (SpatialManager.ListReturnLocations). Bridge 0.31.3 reports the home.
    z = s.get("zone") or {}
    if "home" in z and not s["pc"].get("return"):
        nefia_like = dest.lower() not in (z.get("home") or "").lower()
        if z.get("isHome") and not nefia_like:
            refuse(f"I'm in the home zone ({z.get('home')}): the return list never holds the zone I'm in")
        if dest.lower() in ("meadow",) and nefia_like:
            refuse(f"the home zone is {z.get('home')}, not {dest}: the return lists only the home; "
                   f"'Set as your Home' at {dest}'s hearth stone, or travel")
    ri = pending(s["pc"])
    log0 = s.get("log") or []
    if isinstance(ri, dict):
        # run 21: one already counting down is waited out here (never a second read), not refused
        print(f"{'an evacuation' if ri.get('evac') else 'a return'} is already counting down "
              f"({ri.get('turns')} turns left, to {ri.get('dest') or '?'}): waiting it out, not reading another")
    elif ri == "unknown" and any("tense up" in ln for ln in log0[-15:]) and not any("relaxes" in ln for ln in log0[-15:]):
        print("a return already seems to be counting down (the log): not reading another")
    else:
        names = [i["name"] for i in data("inv")["items"] if "scroll" in i["name"].lower() and "of return" in i["name"].lower()]
        if not names:
            refuse("no scroll of return in the pack")
        # an uncursed stack first (a cursed return goes somewhere else; the review of 2026-10-23)
        good = [n for n in names if not re.search(r"\b(cursed|doomed)\b", n.lower())]
        if not good:
            print(f"only a cursed stack ({names[0]}): reading it anyway, the destination may be random")
        out = run("item.py", (good or names)[0], "Read")
        if "Read -" not in out:
            refuse("couldn't read it: " + last(out)[-120:])
        wait_until("layer", timeout=4000)
        bs = data("buttons")["buttons"]
        hit = [b for b in bs if dest.lower() in (b.get("text") or "").lower()]
        if not hit:
            stop(f"no {dest!r} in the destination list: " + " | ".join((b.get("text") or "") for b in bs if b.get("text"))[:200])
        call("click", i=hit[0]["i"], expect=dest)
        wait_until("frames", n=5)
        if pending(state()["pc"]) is None:
            stop("no countdown after the pick: the list closed without one (is the scroll spent?): look.py")
    wait_out(zone().get("full"), max_turns, min_hp)


def is_exploder(c):
    """delve.py's test: threat.py's exploder flag, 'kamikaze' in the id or name, or a hot guy (run 39: wait_out)."""
    import threat
    prof = threat.profile(c.get("id") or c.get("name") or "") or {"flags": []}
    nm = (c.get("name") or "").lower()
    return "exploder" in prof["flags"] or "kamikaze" in (c.get("id") or "").replace("samurai_kamikaze", "") or "kamikaze" in nm or "hot guy" in nm


def wait_out(start, max_turns=60, min_hp=50):
    """Pass turns until the zone changes (the countdown fired): fight an adjacent foe, never Wait on a stairway,
    never read a second scroll. Shared with evac.py (run 33). Returns on arrival; stop() otherwise."""
    for t in range(1, max_turns + 1):
        s = state()
        if (s.get("zone") or {}).get("full") != start:
            print(f"arrived: {s['zone'].get('full')} after {t - 1} turns")
            return
        p = s["pc"]
        ri = pending(p)
        if ri is None:
            stop("the countdown ended but the zone didn't change (aborted, failed because the destination "
                 "is this map, or Squashed): look.py, and don't read another before checking")
        if p["hp"] * 100 < min_hp * p["maxHp"]:
            stop(f"HP {p['hp']}/{p['maxHp']} under {min_hp}% while waiting for the return")
        if (s.get("layers") or {}).get("top"):
            stop(f"a window is open ({s['layers']['top']}): answer it, the countdown goes on")
        # run 39 (Capricious Grassland B5): a fast named Kamikaze yeek showed up 2 cells off on a night floor. Here an
        # adjacent exploder got fight.py, which refuses exploders, and then a Wait beside it. An exploder within 4
        # cells is a teleport scroll now (the countdown is mine, not the map's: if it stops, the check above says so)
        boom = [c for c in s.get("nearby") or [] if c.get("hostile") and c.get("dist", 9) <= 4 and is_exploder(c)]
        if boom:
            tp = [i["name"] for i in data("inv")["items"] if re.search(r"scrolls? of teleport\b", i["name"].lower())
                  and "short" not in i["name"].lower() and not re.search(r"\b(cursed|doomed)\b", i["name"].lower())]
            if not tp:
                stop(f"{boom[0]['name']} (an exploder) at {boom[0].get('dist')} and no scroll of teleport in the pack: "
                     "zap a rod of teleport")
            out = run("item.py", tp[0], "Read")
            print(f"  exploder {boom[0]['name']} at {boom[0].get('dist')}: read {tp[0]} "
                  f"({'ok' if 'Read -' in out else last(out)[:60]})")
            continue
        adj = [c for c in s.get("nearby") or [] if c.get("hostile") and c.get("dist", 9) <= 1]
        if adj:
            name = adj[0]["name"].split(" ", 1)[-1] if adj[0]["name"].startswith(("a ", "an ")) else adj[0]["name"]
            out = run("fight.py", name, str(min_hp), timeout=300)
            if out.rc == 0:
                continue  # the fight passed turns
            # a refusal (above my level, an avoid kind) or a stop: a Wait passes the turn anyway
            # (the review of 2026-10-23: the loop used to repeat the refusal without a turn passing)
            print(f"  fight.py rc {out.rc}: {last(out)[:100]}; passing the turn with Wait")
        here = data("cell", dx=0, dz=0)
        if any("stair" in str(th).lower() for th in here.get("things") or []):
            # never Wait on a stairway (it takes the stairs): step to a free neighbour first
            for dx, dz in ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                c = data("cell", dx=dx, dz=dz)
                if not c.get("blocked") and not c.get("things") and not c.get("water"):
                    call("step", dx=dx, dz=dz)
                    break
            continue
        turn0 = p.get("turn")
        call("act", action="Wait")
        # run 21: Waits sent back to back were swallowed while the last one was still running (60
        # loop turns passed 11 game turns): wait for the game's turn counter to move before the next
        for _ in range(20):
            try:
                wait_until("frames", n=5, timeout=1000)
                s2 = state()
            except BridgeError as e:
                # run 58: the countdown fired and the home map's load held the main thread past 2 s: a traceback and exit 2
                # for a return that had worked. The load isn't a hang: wait it out and read the zone again
                if "main thread" not in str(e):
                    raise
                time.sleep(3)
                s2 = state()
            if (s2.get("zone") or {}).get("full") != start or s2["pc"].get("turn") != turn0:
                break
        if isinstance(ri, dict) and t % 5 == 0:
            print(f"  turn {t}: {ri.get('turns')} left")
    stop(f"no arrival after {max_turns} turns (the countdown can run to ~36): wait more, never read again")


if __name__ == "__main__":
    main()
