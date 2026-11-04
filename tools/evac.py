"""Read ONE scroll of evacuation (none in the pack: cast the Evacuation spell, run 34) and wait it out (run 33: done by hand six times with an inline Wait loop).
An evacuation goes straight out of a conquered nefia and, in play, to the world map from an unconquered
one too (Vernis Mine B6, Silent Grassland B1-B5); elin-play's older note (B1's entrance stairway) is
handled: if a floor is still under me afterwards, say so (stairs.py up). The countdown runs 10-19 turns;
recall.wait_out passes them (fights an adjacent foe, never Waits on a stairway, never reads a second
scroll: a second read cancels the first and spends both, runs 05, 10, 20).

usage: python -I tools/evac.py [MAX_TURNS=60] [MIN_HP_PCT=50]
Exit 0 on a zone change, 1 refused (on the world map, no scroll, a hostile in view: elin-play's rule is
no foe in view when reading), 3 stopped (HP, a window, no arrival).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, data, last, refuse, run, state, stop, wait_until  # noqa: E402
from recall import on_world, pending, wait_out  # noqa: E402


EVAC_MP = 20  # run 34: the Evacuation spell's cost at Lv31 (69 -> 49 MP)


def spell_stock(alias):
    """The casts in stock of one of my spells (bridge `power`), 0 when unknown."""
    try:
        return {x["spell"]: x["stock"] for x in data("power")["party"][0].get("spells") or []}.get(alias, 0)
    except Exception:  # noqa: BLE001 - an unknown stock is no stock
        return 0


def main():
    nums = [int(a) for a in sys.argv[1:] if re.fullmatch(r"\d+", a)]
    max_turns = nums[0] if nums else 60
    min_hp = nums[1] if len(nums) > 1 else 50
    s = state()
    z = s.get("zone") or {}
    if on_world(z):
        refuse("on the world map already")
    ri = pending(s["pc"])
    if isinstance(ri, dict):
        print(f"{'an evacuation' if ri.get('evac') else 'a return'} is already counting down ({ri.get('turns')} turns): waiting it out")
    else:
        if any(c.get("hostile") for c in s.get("nearby") or []):
            refuse("a hostile is in view: elin-play reads evacuation only with no foe in view (fight or step away first)")
        names = [i["name"] for i in data("inv")["items"] if re.search(r"scrolls? of evacuation", i["name"].lower())]
        if not names:
            # run 34: the conquests' exits spent the last scroll while the Evacuation spell held 31 casts (read from
            # books on 489-12-01); the bridge's cast op (cure.py's path) casts it with no hotbar button
            stock = spell_stock("SpEvac")
            if not stock:
                refuse("no scroll of evacuation in the pack and no Evacuation casts (the bags don't count: take one out)")
            # the first test (Ominous Forest B1, 490-02-25): "You fail to cast" once, then the countdown; 20 MP a cast.
            # A failed cast spends the turn and the MP only, so try again while MP lasts and no foe is in view
            for attempt in range(1, 4):
                if state()["pc"].get("mp", 0) < EVAC_MP:
                    stop(f"MP under {EVAC_MP} for an Evacuation cast after {attempt - 1} failed: teleport or the stairs")
                # Unnamed Ruin B2: the retry right after a failed cast was refused "busy: GoalEndTurn"
                wait_until("idle", timeout=5000)
                r = call("cast", spell="SpEvac")
                if not r.get("ok") and "busy" in (r.get("error") or ""):
                    wait_until("frames", n=30, timeout=3000)
                    r = call("cast", spell="SpEvac")
                if not r.get("ok") or not (r.get("data") or {}).get("cast"):
                    refuse(f"no scroll of evacuation, and the Evacuation cast was refused: {r.get('error') or r.get('data')}")
                print(f"cast Evacuation (stock {stock}, attempt {attempt})")
                wait_until("frames", n=10, timeout=2000)
                s2 = state()
                if pending(s2["pc"]) is not None:
                    break
                if any(c.get("hostile") for c in s2.get("nearby") or []):
                    stop("the Evacuation cast failed and a hostile is in view: fight or teleport, then try again")
        else:
            good = [n for n in names if not re.search(r"\b(cursed|doomed)\b", n.lower())]
            out = run("item.py", (good or names)[0], "Read")
            if "Read -" not in out:
                refuse("couldn't read it: " + last(out)[-120:])
        wait_until("frames", n=10, timeout=2000)
        if pending(state()["pc"]) is None:
            stop("no countdown after the read or cast (a cast can fail): look.py, and don't read another before checking")
    wait_out(z.get("full"), max_turns, min_hp)
    z2 = (state().get("zone") or {}).get("full") or ""
    if not on_world(state().get("zone") or {}):
        print(f"landed on {z2}: take the stairs up (stairs.py up)")


if __name__ == "__main__":
    main()
