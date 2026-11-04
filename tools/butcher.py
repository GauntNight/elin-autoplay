"""Butcher every corpse in the pack and the Cooler Box with the butcher's tool (run 13, G6).

The tool is a converter used from the pack (TraitCrafter MixType.Butcher): Use opens a drag grid;
a corpse dragged onto its ing1 slot becomes one random body part (fang, heart, grotesque offal,
skin or bone, 20% each), which lands in the pack. The grid lists the Cooler Box's corpses too, and
they drag straight in. Bag 2 needs 4 skins, the sleeping bag 2; hearts and offal feed board jobs.

usage: python -I tools/butcher.py [--dry] [NAME ...]   (NAME: only corpses matching these words)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, matches, ready, refuse, run, setup, stop, top, wait_idle  # noqa: E402

PARTS = ("skin", "fang", "heart", "offal", "bone")


def grid():
    bs = call("buttons", all=True)["data"]["buttons"]
    ing = [b for b in bs if b["name"].startswith("ing1")]
    corpses = [b for b in bs if "ButtonGrid inventory" in b["name"] and "corpse" in (b.get("card") or "")]
    return (ing[0]["i"] if ing else None), corpses


def open_tool():
    if top() != "LayerDragGrid":
        out = run("item.py", "butcher's tool", "Use")
        if out.rc != 0:
            refuse("no butcher's tool to use: " + out.strip()[-120:])
        call("wait", until="layer", timeout=5000)
    if top() != "LayerDragGrid":
        refuse(f"the butcher's tool grid did not open (top {top()})")


def parts():
    """{part: count} over every inventory slot the bridge lists (the toolbelt included: picked-up
    skins stack onto the toolbelt's skins, and `inv` doesn't list the toolbelt; run 13)."""
    import re
    out = {}
    for b in call("buttons", all=True)["data"]["buttons"]:
        card = (b.get("card") or "").lower()
        if "ButtonGrid inventory" not in b["name"] or "corpse" in card:
            continue
        for p in PARTS:
            if re.search(r"\b" + p + r"s?\b", card):
                m = re.match(r"(\d+) ", card)
                out[p] = out.get(p, 0) + (int(m.group(1)) if m else 1)
    return out


def main():
    setup()
    want = [a.lower() for a in sys.argv[1:] if not a.startswith("--")]
    # the shared check before the first act: a window other than the tool's own grid, busy, a bad
    # condition, a hostile in view (the user, run 15: never butcher in combat)
    why = ready(hp=None, hunger=None, burden=None, world_ok=True, allow=("LayerInventory", "LayerDragGrid"))
    if why:
        stop(why)
    open_tool()
    done = []
    stopped = None
    for _ in range(30):
        ing, corpses = grid()
        # whole words: "putit" fits "corpse of 『Putit』", not a putit-something else
        corpses = [c for c in corpses if not want or any(matches(w, [c]) for w in want)]
        if not corpses:
            break
        # the user, run 15: "butchering should be done after combat or when we're safe... trying to
        # butcher while in combat is high risk and we keep getting stuck": a hostile in view ends it
        foes = [x["name"] for x in call("state")["data"].get("nearby") or [] if x.get("hostile")]
        if foes:
            stopped = "hostile in view (" + ", ".join(foes[:3]) + "): butcher later, when safe"
            break
        c = corpses[0]
        if "--dry" in sys.argv:
            print("corpses: " + ", ".join(b["card"] for b in corpses))
            break
        if ing is None:
            refuse("no ing1 slot in the grid")
        before = parts()  # run 13: the log is a fixed-size ring, so counting its lines read old news
        r = call("drag", i=c["i"], j=ing)
        if not r.get("ok"):
            refuse(f"drag of {c['card']} failed: {r.get('error')}")
        wait_idle(timeout=30000)
        after = parts()
        got = [f"{after[k] - before.get(k, 0)} {k}" for k in after if after[k] > before.get(k, 0)]
        print(f"  {c['card']} -> " + (", ".join(got) or "nothing new counted"))
        done.append(c["card"])
        open_tool()  # the grid stays open after a butcher; reopen if it closed
    run("close.py")
    print(f"butchered {len(done)}" if done else "no corpses")
    if stopped:
        stop(stopped)


if __name__ == "__main__":
    main()
