"""Walk up to a visible creature by name and open its Talk act (the game allows
talking from two cells away), then step through the dialog like talk.py.

usage: python -I tools/talkto.py NAME [max_steps]
The name is matched as a whole word (common.pick); two different creatures fitting it is a
refusal (exit 1), so "guard" with two guards in view asks for the full name. Stops (exit 3) when
a dialog or window is already open, the player is mid-task, or a hostile is in view.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call, close  # noqa: E402
from common import pick, ready, refuse, run, stop, wait_until, walk  # noqa: E402


def find(name):
    s = call("state")["data"]
    near = s.get("nearby") or []
    c = pick(name, near, what="creature", quiet=True, key="name")
    if c is None and any(pick(name, [x], quiet=True, key="name") for x in near):
        names = sorted({x["name"] for x in near if pick(name, [x], quiet=True, key="name")})
        refuse(f"{name!r} fits {len(names)} creatures in view: " + " | ".join(names) + " (give the full name)")
    return s, c


def main():
    name = sys.argv[1]
    steps = sys.argv[2] if len(sys.argv) > 2 else "30"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for _ in range(12):
        s, c = find(name)
        if c is None:
            sys.exit(f"{name} is not in view")
        # a dialog or window already open swallows the Talk (run 17's bandit demand); the
        # world map has no Talk act; a hostile in view is a decision first
        why = ready(s, hp=None, hunger=None, idle=True, world_ok=True, burden=None, allow=("LayerInventory",))
        if why:
            stop(why)
        pc = s["pc"]
        if c["dist"] <= 2:
            acts = call("acts", dx=c["dx"], dz=c["dz"], mode="all")["data"]["acts"]
            talk = [a for a in acts if a["text"].startswith("Talk")]
            if talk:
                call("do", i=talk[0]["i"])
                wait_until("layer", timeout=3000)  # the dialog opens
                print(run("talk.py", steps))
                return
        # Walk to the cell next to them, on our side (walkto: no fixed sleep, run 12 review).
        tx = c["dx"] - (1 if c["dx"] > 0 else -1 if c["dx"] < 0 else 0)
        tz = c["dz"] - (1 if c["dz"] > 0 else -1 if c["dz"] < 0 else 0)
        walk(pc["x"] + tx, pc["z"] + tz, r=0, timeout=10000)  # the HP floor stays (a town, a road camp)
    sys.exit(f"could not get next to {name}")


if __name__ == "__main__":
    main()
