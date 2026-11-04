"""Mining practice on my own stone walls (run 18): a stone wall is 1 stone and 0 SP at the wall
workshop, mining it back with the pickaxe ("Mine (Easy)", ~0.5 SP) drops the stone again, and each
mine trains Mining (1.60 -> 1.75 for 4 walls at Mining 1.6). Mining is G11's key: the home's iron
big rock (reqLv 66) opens at 56 (iron pickaxe) + 1.5 x Mining, so Mining 7; every level is also
10-14 character exp (G10). (wallmine.py is the other one: it mines a dungeon's walls for ore.)

Each round: craft the stones in the pack into stone walls at the wall workshop, place them on a
strip outside the Workshop, mine them with the hardest pickaxe, pick the stones up.

usage: python -I tools/minewalls.py [ROUNDS=5] [min_sp=15] [--plank]
Stops (exit 3) at the SP floor, HP under THRESHOLDS["loop_hp"], Hungry (70+) or Starving, a
hostile in view, a window, or when no stone is left (common.ready: run 18's starvation found this
loop with an HP floor of 0 and no hunger test).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from activity import mark  # noqa: E402
from common import THRESHOLDS, call, cells, data, grab, ready, run, setup, stop, wait_idle, wait_until, walk  # noqa: E402
import home  # noqa: E402

STRIP = [(47, 53), (48, 53), (49, 53), (50, 53), (47, 52), (48, 52), (49, 52), (50, 52)]
WORKSHOP_STAND = (48, 59)  # beside the wall workshop (48,60)
STONE = re.compile(r"^(?:(\d+) )?(?:an? )?(\w+) stones?$")
PLANK = re.compile(r"^(?:(\d+) )?(?:an? )?(\w+) planks?$")
# run 18: a mined stone wall sometimes drops a pebble instead (29 rounds turned 6 stones into 17
# pebbles); a plank wall gave its plank back 3 of 3 times. --plank uses planks.
KIND = "plank" if "--plank" in sys.argv else "stone"


def stones():
    """The material stacks in the pack: plain stones (not cut stones, not pebbles), or planks."""
    out = []
    for i in call("inv")["data"]["items"]:
        m = (PLANK if KIND == "plank" else STONE).match(i["name"])
        if m and "cut" not in i["name"]:
            out.append((i["name"], int(m.group(1) or 1)))
    return out


def clear_strip():
    """Mine every wall standing on the strip and pick up every stone lying there; returns the
    number mined. Run at the start of each round too, so a round cut short (the morning shipping
    report) leaves no wall or stone behind (run 18)."""
    info = cells(STRIP)
    walls = [c for c in STRIP if (info.get(c) or {}).get("block")]
    mined = 0
    if walls:
        grab("iron pickaxe")
        for x, z in walls:
            walk(x, z - 1, r=0, timeout=20000)
            p = data("state")["pc"]
            acts = [a for a in call("acts", dx=x - p["x"], dz=z - p["z"], mode="right")["data"]["acts"]
                    if a["text"].startswith("Mine")]
            if acts:
                call("do", i=acts[0]["i"])
                wait_idle(20000)
                mined += 1
        run("hotbar.py", "--deselect")
    info = cells(STRIP)
    for x, z in [c for c in STRIP if (info.get(c) or {}).get("things")]:
        walk(x, z - 1, r=0, timeout=20000)
        p = data("state")["pc"]
        for _ in range(3):
            acts = [a for a in call("acts", dx=x - p["x"], dz=z - p["z"], mode="all")["data"]["acts"]
                    if a["text"].startswith("Pick")]
            if not acts:
                break
            call("do", i=acts[0]["i"])
            wait_until("frames", n=10, timeout=2000)
    return mined


def gate(min_sp):
    """Why the round must not start, or None: one ready() in place of the three checks the review
    of 2026-10-23 found here (hunger 70 / Starving / HP 60, threat(60), SP). The morning shipping
    report is read and closed first."""
    why = ready(hp=THRESHOLDS["loop_hp"], hunger=THRESHOLDS["hungry"], sp=min_sp)
    if why and "LayerShippingResult" in why:
        print(" / ".join(run("read.py").strip().splitlines())[:300])
        run("close.py")
        why = ready(hp=THRESHOLDS["loop_hp"], hunger=THRESHOLDS["hungry"], sp=min_sp)
    return why


def main(argv):
    setup()
    nums = [int(a) for a in argv if a.isdigit()]
    rounds = nums[0] if nums else 5
    min_sp = nums[1] if len(nums) > 1 else 15
    mark("mine", "start", note=f"{rounds} rounds of {KIND} walls")
    try:
        for r in range(rounds):
            why = gate(min_sp)
            if why:
                stop(why)
            clear_strip()
            # walls crafted by a round that was cut short go up first (run 18: 8 plank walls were left
            # in hand after the morning report, and the next round found no planks and stopped)
            walls = sum(int(m.group(1) or 1) for i in call("inv")["data"]["items"]
                        if (m := re.match(rf"^(?:(\d+) )?(?:an? )?{KIND} walls?$", i["name"])))
            have = [] if walls else stones()
            n = min(walls or sum(c for _, c in have), len(STRIP))
            if not n:
                stop(f"no {KIND}s in the pack")
            if not walls:
                walk(*WORKSHOP_STAND, r=0, timeout=40000)
            made = min(walls, n)
            for name, count in have:
                k = min(count, n - made)
                if k <= 0:
                    break
                out = run("craft.py", "0", "1", f"{KIND} wall", str(k), "--use", name, "--allow-default", timeout=300)
                made += k if "crafted" in out.lower() else 0
            run("close.py")
            targets = STRIP[:made]
            run("place.py", f"{KIND} wall", *[f"{x},{z}" for x, z in targets], timeout=900)
            mined = clear_strip()
            p = data("state")["pc"]
            print(f"round {r + 1}: {made} walls, {mined} mined; SP {p['sp']}, Lv{p['lv']} {p['exp']}/{p['expNext']}")
    finally:
        mark("mine", "end")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
