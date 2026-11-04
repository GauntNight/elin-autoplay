"""Shear every furry creature in view (run 10): any creature whose race has fur can be sheared
once per visit (Card.CanBeSheared: c_fur >= 0; wild ones reset to tier 1 when the zone resets).
Rabbits and squirrels give cashmere (the snow putit's material), sheep, goats, pigs, cows, horses
and dogs wool, beetles silk, spiders spider silk, bears and dodos hide (races.json fur column).
Shearing costs 1 SP and gives +1 affinity; a creature in combat gives half (AI_Shear.GetFur).

Holds the shears, walks to each target with the game's own Shear act, waits for it to finish,
puts the shears away. Skips hostiles (they fight back) and anything without a Shear act.
Before each target common.ready decides (the review of 2026-10-23: a hostile arriving mid-loop
was still approached): a hostile in view, a window, a task running, HP under 60%, Hungry or
Overweight puts the shears away and stops (exit 3).

usage: python -I tools/shear.py [radius=12]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import ready, run, stop, wait_idle  # noqa: E402


def item(*args):
    run("item.py", *args)
    run("close.py")


def fibers():
    return {i["name"] for i in call("inv")["data"]["items"] if "fiber" in i["name"] or "palulu" in i["name"]}


def main():
    r = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    s = call("state")["data"]
    hostile = {c["name"] for c in s.get("nearby") or [] if c.get("hostile")}
    item("shears", "Grab")
    done, tried = 0, set()
    while True:
        why = ready()
        if why:
            item("shears", "Put away")
            print(f"sheared {done}; fiber now: {', '.join(sorted(fibers())) or 'none'}")
            stop(why)
        hits = [h for h in call("find", name="", r=r, n=200)["data"]["hits"]
                if h["kind"] == "chara" and (h["x"], h["z"]) not in tried and h["name"] not in hostile
                and "snow putit" not in h["name"]]  # the home putit grows long fur as livestock (run 10)
        target = None
        for h in sorted(hits, key=lambda h: h["dist"]):
            p = call("state")["data"]["pc"]
            acts = call("acts", dx=h["x"] - p["x"], dz=h["z"] - p["z"], mode="right")["data"]["acts"]
            sh = [a for a in acts if a["text"].startswith("Shear")]
            tried.add((h["x"], h["z"]))
            if sh:
                target = (h, sh[0])
                break
        if not target:
            break
        h, a = target
        before = fibers()
        call("do", i=a["i"])
        wait_idle(25000)  # the Shear task walks there and shears; the reply comes the frame it ends
        log =[l for l in call("state")["data"].get("log") or [] if "shear" in l.lower()]
        print(f"{h['name']}: {log[-1] if log else 'no shear message'}")
        done += 1
    item("shears", "Put away")
    print(f"sheared {done}; fiber now: {', '.join(sorted(fibers())) or 'none'}")


if __name__ == "__main__":
    main()
