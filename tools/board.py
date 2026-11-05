"""List a town's jobs from its nearest quest board in one step (Start Run 1: town jobs were a new character's best income: 247 orens and +1
influence in 3 real minutes). Walks next to the nearest ordinary board, opens it and prints each job with its reward, danger and time.
The board stays open, so a job is `bridge.py click N expect=NAME` from the list. All boards in a town show the same jobs.

usage: python -I tools/board.py [--close]
       python -I tools/board.py --take NAME [NAME ...]   accept these jobs in order, each by its name on the board (an instance job moves
                                                         me into it as its dialog ends, so it goes last); under Lv15 it refuses an instance
                                                         job below Lv4 or without the ally beside me at 70%+ (--weak-ok)
Exit 0 listed, 1 refused (no board known on this map), 2 the bridge.
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import act, pc, run, setup, walk_beside  # noqa: E402


INSTANCE = ("Monster hunting", "Monster extermination", "Troubled home")


def rows():
    return [x for x in call("buttons")["data"]["buttons"] if "item quest" in x.get("name", "")]


def take(name):
    """Open the board if needed and accept the first job with this name. True when accepted."""
    from common import run
    if not rows():
        hits = [h for h in call("find", name="quest board", r=4, n=4)["data"]["hits"]]
        if not hits:
            print(f"no board within 4 for {name}")
            return False
        act(hits[0]["x"], hits[0]["z"], "View Works")
        time.sleep(0.6)
    hit = [r for r in rows() if r["text"].startswith(name)]
    if not hit:
        print(f"no {name} on the board")
        return False
    call("click", i=hit[0]["i"], expect=name)
    time.sleep(0.5)
    run("talk.py", "3")
    yes = [b for b in call("buttons")["data"]["buttons"] if (b.get("text") or "").startswith("I accept")]
    if not yes:
        print(f"{name}: no accept button")
        return False
    call("click", i=yes[0]["i"])
    time.sleep(0.4)
    print(f"took {name}: " + run("talk.py", "4").strip()[-70:])
    return True


def main():
    setup()
    if "--take" in sys.argv:
        names = [a for a in sys.argv[sys.argv.index("--take") + 1:] if a != "--weak-ok"]
        # Start Runs 1, 3, 4: five of the twelve deaths were job arenas taken too weak or without the ally: nine or ten foes at once, whatever the Danger number says.
        # Under level 15 an instance job wants level 4 and the ally beside me at 70%+, unless --weak-ok.
        s = call("state")["data"]
        p, party = s["pc"], s.get("party") or []
        ally_ok = any(a.get("here") and a.get("dist", 99) <= 5 and a.get("hp", 0) * 10 >= a.get("maxHp", 1) * 7 for a in party)
        # Start Run 7: at Lv3 PV 16 (a stone breastplate, 208 orens at the camp) took a Danger 1 job, but HP 22 -> 4 three times, both scrolls read, the ally dead:
        # it paid 156 orens, 2 platinum and 40 exp and started that run's economy, so PV 15 stands in for the level only with 2 scrolls of teleport to spend.
        m = re.search(r"PV (-?\d+)", str(run("power.py", timeout=20)))
        scrolls = sum(i.get("num") or 1 for i in call("inv")["data"]["items"] if "scroll" in i["name"] and "of teleport" in i["name"])
        armored = bool(m) and int(m.group(1)) >= 15 and scrolls >= 2
        if p["lv"] < 15 and "--weak-ok" not in sys.argv and any(w in n for n in names for w in INSTANCE) and ((p["lv"] < 4 and not armored) or not ally_ok):
            print(f"refused: an instance job at Lv{p['lv']} with {'the ally ready' if ally_ok else 'no ally beside me at 70%+'}: level 4 (or PV 15 and 2 teleport scrolls) and the ally, or --weak-ok")
            return 1
        ok = [take(n) for n in names]
        return 0 if all(ok) else 1
    hits = [h for h in call("find", name="quest board", r=150, n=20)["data"]["hits"] if h.get("installed", True)]
    plain = [h for h in hits if "maniac" not in h["name"]] or hits
    if not plain:
        print("refused: no quest board known on this map")
        return 1
    b = plain[0]
    walk_beside(b["x"], b["z"])
    p = pc()
    call("acts", dx=b["x"] - p["x"], dz=b["z"] - p["z"], mode="all")
    act(b["x"], b["z"], "View Works")
    time.sleep(0.6)
    rows = [x for x in call("buttons")["data"]["buttons"] if "item quest" in x.get("name", "")]
    texts = call("texts")["data"]["texts"]
    infl = [x["text"] for x in call("buttons")["data"]["buttons"] if "Influence" in (x.get("tip") or x.get("text") or "")]
    print(f"at {b['name']} {b['x']},{b['z']}; {infl[:1]}")
    for r in rows:
        print(f"  {r['i']}: {r['text'][:110]}")
    print("  details: " + " | ".join(t for t in texts if any(w in t for w in ("orens", "Danger", "Days", "Hours", "Reward")))[:600])
    if "--close" in sys.argv:
        call("closetop")
    return 0


if __name__ == "__main__":
    sys.exit(main())
