"""Hand out flyers for the Merchants Guild trial (run 17) by throwing them at townsfolk.

What the game does (Chara.GiveGift, ActThrow ThrowType.Flyer, QuestTaskFlyer): a thrown flyer is
a gift. The NPC refuses it when rnd(20) != 0 and its CHA > rnd(my CHA + Negotiation x 3 + 10):
the flyer is destroyed. Otherwise it keeps the flyer and the trial counts it (30 needed, any town
but the guild's own map). Handed over with the adjacent "Gift" act since run 17 (a thrown one
hit a bystander). **Throwing a flyer at someone who already holds one is a hostile act**
(DoHostileAction), so nobody is ever thrown at twice: every uid thrown at is kept in
runs/jobs/flyers.json, accepted or not. Each throw also gives Throwing +50 exp (ActThrow).

usage: python -I tools/flyer.py [GIFTS=10]
Stops when the flyers run out, nobody new is in range, a window opens or a hostile shows up.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import grab, ready, refuse, stop, wait_until, walk, walk_beside  # noqa: E402

# The refusal roll is target CHA > rnd(my CHA + Negotiation x 3 + 10): Lv20-40 shopkeepers and
# guards almost always refuse; children, citizens and tourists (Lv1-5) mostly take it. "Shrugs at
# you" is printed both ways (refusal, and a gift of no value): the trial count in the journal is
# the only truth (run 17: 2 of 30 after 9 throws at anyone).
MAX_LV = 8
DONE = Path(__file__).resolve().parent.parent / "runs" / "jobs" / "flyers.json"


def load():
    try:
        return json.loads(DONE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def new_lines(log0, log1):
    """The log is a fixed-size ring: the new lines are what follows the longest tail of log0
    that starts log1."""
    for k in range(len(log0)):
        tail = log0[k:]
        if log1[:len(tail)] == tail:
            return log1[len(tail):]
    return log1[-4:]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = [x for x in sys.argv[1:] if x.isdigit()]
    throws = int(a[0]) if a else 10
    rng = int(a[1]) if len(a) > 1 else 5
    done = load()
    seen = set()
    for k in range(1, throws + 1):
        s = call("state")["data"]
        # the shared check (the review of 2026-10-23): a window, busy, a bad condition, the world
        # map, a hostile in view; HP and hunger are the player's business in town
        why = ready(s, hp=None, hunger=None, burden=None)
        if why:
            stop(why)
        near = s.get("nearby") or []
        zone = (s.get("zone") or {}).get("full", "")
        if "guild_merchant" in zone:
            refuse("flyers given on the guild's own map don't count")
        # named townsfolk only: "a puppy", "a cat" are animals (a puppy shrugged, run 17)
        cands = [c for c in near if not c.get("party") and not c.get("hostile") and str(c["uid"]) not in done
                 and c.get("hostility") in ("Neutral", "Friend") and c["dist"] >= 1
                 and not c["name"].startswith(("a ", "an ")) and c.get("lv", 99) <= MAX_LV]
        if not cands:
            # roam: walk to the nearest waypoint not yet visited (a 12-cell grid over the town)
            b = [int(v) for v in ((s.get("zone") or {}).get("bounds") or "0,0,0,0").split(",")]
            p = s["pc"]
            pts = [(x, z) for x in range(b[0] + 6, b[2] - 3, 12) for z in range(b[1] + 6, b[3] - 3, 12)
                   if f"{x},{z}" not in seen]
            if not pts:
                print("nobody new in view and every waypoint visited")
                return
            x, z = min(pts, key=lambda q: abs(q[0] - p["x"]) + abs(q[1] - p["z"]))
            seen.add(f"{x},{z}")
            walk(x, z, r=2, timeout=30000, weak_ok=True)
            continue
        t = min(cands, key=lambda c: c["dist"])
        # run 17: a thrown flyer can hit someone else in the line of fire (a tourist twice), and a
        # second flyer to a holder is a hostile act (Lv40 guards): hand it over instead. The
        # right-click "Gift" on an adjacent NPC gives one (ActPlan: GiveGift(SplitHeld(1))).
        if t["dist"] > 1:
            p = s["pc"]
            walk_beside(p["x"] + t["dx"], p["z"] + t["dz"], timeout=20000, weak_ok=True)
            s = call("state")["data"]
            t = next((c for c in s.get("nearby") or [] if c["uid"] == t["uid"]), None)
            if not t or t["dist"] > 1:
                continue
        if not grab("flyer"):  # was throw.hold, a bool over common.grab (the 2026-10-23 cleanup)
            print("no flyers left")
            return
        acts = call("acts", dx=t["dx"], dz=t["dz"], mode="right")["data"]["acts"]
        th = [x for x in acts if x["text"].startswith("Gift")]
        if not th:
            done[str(t["uid"])] = "no gift act: " + " | ".join(x["text"] for x in acts)
            continue
        log0 = list(s.get("log") or [])
        call("do", i=th[0]["i"])
        wait_until("layer", timeout=2000)  # the "Give ...?" confirmation, when the game asks
        if (call("state")["data"].get("layers") or {}).get("top"):  # the "Give ...?" confirmation
            yes = [b for b in call("buttons")["data"]["buttons"] if (b.get("text") or "").strip().startswith("Yes")]
            if yes:
                call("click", i=yes[0]["i"])
                wait_until("frames", n=10, timeout=1500)
        log1 = list(call("state")["data"].get("log") or [])
        new = new_lines(log0, log1)
        refused = False  # unknowable from the log (see MAX_LV): never throw at this uid again
        done[str(t["uid"])] = " / ".join(new)[-140:]
        DONE.parent.mkdir(parents=True, exist_ok=True)
        DONE.write_text(json.dumps(done, ensure_ascii=False, indent=0), encoding="utf-8")
        print(f"{k:2} {t['name']} ({t['id']}) d{t['dist']}: Lv{t.get('lv')} | {' / '.join(new)[-110:]}")
    print("throw limit reached")


if __name__ == "__main__":
    main()
