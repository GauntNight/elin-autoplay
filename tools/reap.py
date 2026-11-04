"""Reap seeds or cut crops on listed field cells (run 10), with the right tool held.

Reap: the sickle's "Reap seeds" (TaskHarvest): 1-3 seeds (mean 1.83), the plant is removed, no
food. Mushrooms can be reaped at any stage, pasture from stage 1, other crops only when ripe
(GrowSystem.CanReapSeed). Cut: the iron axe's harvest act: a mushroom gives one mushroom at any
stage (GrowSystemKinoko), pasture 1+rnd(stage) pasture (cut it at stage 3), and a seed comes back
~12% of the time on a field (TryPopSeed). Both lose items when the home's soil is over its limit.

usage: python -I tools/reap.py reap X,Z [X,Z ...] [--tool "bronze war sickle"]
       python -I tools/reap.py cut X,Z [X,Z ...]
Prints what each cell gave (from the pack's change) and the SP spent.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call, close  # noqa: E402
from common import grab, matches, pack_full, pc, ready, refuse, stop, wait_idle, wait_until, walk  # noqa: E402

SICKLE = "bronze war sickle"  # run 32: the iron sickle was lost in run 26 (the Warded Cave); a war sickle reaps too
TOOL = {"reap": SICKLE, "cut": "woodcutter's axe"}  # run 21: "sickle" also fit a ☆war sickle in the tool box


def take_tool(name):
    """The tool in hand through common.grab (whole-word name, cursed stacks skipped); a hotbar
    selection is emptied first (run 05: a selected slot outranks a Grab)."""
    if matches(name, [pc().get("held") or ""]):
        return
    from hotbar import deselect
    deselect()
    if not grab(name, what="tool"):
        refuse(f"no {name!r} in the pack to hold")


def pack():
    out = {}
    for i in call("inv")["data"]["items"]:
        m = re.match(r"(?:an? |(\d+) )?(.*)", i["name"])
        n = int(m.group(1)) if m.group(1) else 1
        k = singular(m.group(2))
        out[k] = out.get(k, 0) + n
    return out


def grab_drops(x, z):
    """Harvests land on the cell or a neighbour (Map.TrySmoothPick), and the home's silver bells
    "clean the ground" (run 10: four cut pastures vanished): pick up every loose (not installed)
    thing within one cell of the target at once. Planted seeds are installed and stay."""
    for _ in range(8):
        hits = [h for h in call("find", name="", r=30, n=500)["data"]["hits"]
                if h["kind"] == "thing" and not h.get("installed")
                and abs(h["x"] - x) <= 1 and abs(h["z"] - z) <= 1]
        if not hits:
            return
        if pack_full():  # errors.csv row 5: a pick-up into a full pack vanishes
            print(f"  the pack is full: {len(hits)} drops left on the ground by {x},{z}")
            return
        h = hits[0]
        walk(h["x"], h["z"], r=0, hp=0, timeout=10000)  # at home
        acts = call("acts", dx=0, dz=0, mode="right")["data"]["acts"]
        g = [a for a in acts if a["text"].startswith("Grab (") and h["name"] in a["text"]]  # not a planted seed
        if not g:
            return
        call("do", i=g[0]["i"])
        wait_until("frames", n=10, timeout=1500)


def singular(name):
    """'3 seeds of mushroom' and 'a seed of mushroom' count as one key."""
    return re.sub(r"^seeds\b", "seed", re.sub(r"rooms\b", "room", name))


def main():
    args = sys.argv[1:]
    if "--tool" in args:  # run 32: the iron sickle was lost in run 26; a war sickle is a farming tool too
        i = args.index("--tool")
        TOOL[args[0]] = args[i + 1]
        del args[i:i + 2]
    mode, cells = args[0], [tuple(map(int, c.split(","))) for c in args[1:]]
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    wait_idle(timeout=3000)  # run 21: springday's walk here still read AI_Goto:Success and the cut was refused as busy
    why = ready(hp=None, hunger=None)  # a window, busy, a bad condition, a hostile in view (at home)
    if why:
        stop(why)
    take_tool(TOOL[mode])
    sp0 = call("state")["data"]["pc"]["sp"]
    total = {}
    for x, z in cells:
        # grab_drops' "Grab" puts a pick-up in hand, replacing the tool (run 10: every reap after
        # the first found no Reap act): hold the tool again before each cell
        take_tool(TOOL[mode])
        before = pack()
        p = call("state")["data"]["pc"]
        if max(abs(x - p["x"]), abs(z - p["z"])) > 1:
            # acts on a far cell come back empty: stand next to it first (south side: row z-1)
            walk(x, z - 1, r=0, hp=0, timeout=15000)
            p = call("state")["data"]["pc"]
        acts = call("acts", dx=x - p["x"], dz=z - p["z"], mode="right")["data"]["acts"]
        want = [a for a in acts if (a["text"].startswith("Reap") if mode == "reap"
                                    else a["act"] == "TaskHarvest" and not a["text"].startswith("Reap"))]
        if not want:
            print(f"{x},{z}: no {mode} act ({', '.join(a['text'] for a in acts) or 'none'})")
            continue
        call("do", i=want[0]["i"])
        wait_idle(timeout=30000)  # the harvest task ends on its own (was a 30 x 1 s poll)
        grab_drops(x, z)
        after = pack()
        got = {k: after[k] - before.get(k, 0) for k in after if after[k] > before.get(k, 0)}
        for k, v in got.items():
            total[k] = total.get(k, 0) + v
        print(f"{x},{z}: {', '.join(f'{v} {k}' for k, v in got.items()) or 'nothing'}")
    take_tool(TOOL[mode])  # puts the last grabbed drop back in the pack
    close()
    sp = call("state")["data"]["pc"]["sp"]
    print(f"total: {', '.join(f'{v} {k}' for k, v in total.items()) or 'nothing'}; SP {sp0} -> {sp}")


if __name__ == "__main__":
    main()
