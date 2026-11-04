"""Break scrap junk in the pack into scrap with the hammer (run 13).

A held hammer offers "Disassemble" on an installed thing (TaskHarvest, HarvestType.Disassemble): the
thing turns into its first ingredient, ~91% of the time for a single item. Empty cans, toasters,
junk tools, pots, research and mining equipment, light stands, flotsam and the platinum lucky cat
are all ['scrap'] in things.json; the gold lucky cat gives a gold ingot. It works when the thing's
material hardness + 1 is at most the hammer's hardness + 1.5 x Crafting (the copper hammer: 34).

For each such stack in the pack: place one on a clear cell beside me, hold the hammer, Disassemble,
pick up what it left (TrySmoothPick often drops it straight into the pack). Stops at the first
refusal and says why. Run 13: a research equipment gave nothing (the miss), an empty can 1 scrap.

usage: python -I tools/scrap.py [--dry] [NAME ...]
  NAME  break these pack items too, by name (e.g. "strange silver coin": a gacha coin, ['scrap'],
        silver 27; not broken by default because the coins are currency)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, cells, grab, hammer_scrap, matches, pack_full, pc, ready, refuse, setup, stop, wait_idle  # noqa: E402
from place import place_at  # noqa: E402


def pack_junk(extra=()):
    rows = [r for r in call("inv")["data"]["items"] if not r.get("equipped")]
    named = {r["name"] for e in extra for r in matches(e, rows, key="name")}  # whole words
    return [r["name"] for r in rows if hammer_scrap(r["name"], r.get("id")) or r["name"] in named]


def clear_cell():
    p = pc()
    near = [(p["x"] + dx, p["z"] + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1) if dx or dz]
    for (x, z), c in cells(near).items():  # cells() is {(x, z): info}
        if not c.get("blocked") and not c.get("things") and not c.get("obj") and not c.get("edge") \
                and not c.get("water") and not c.get("door") and not c.get("wall") \
                and c.get("floor") != "field":  # never on a crop cell
            return x, z
    return None


def one(name):
    spot = clear_cell()
    if not spot:
        stop("no clear cell beside me: stand somewhere open")
    x, z = spot
    r = place_at(re.sub(r"^\d+ ", "", name), x, z)  # the whole stack goes down
    if r != "placed":
        refuse(f"could not place {name} at {x},{z}: {r}")
    if not grab("hammer", what="tool"):
        refuse("no hammer to hold (the copper hammer rides in the kit)")
    p = pc()
    acts = call("acts", dx=x - p["x"], dz=z - p["z"], mode="right")["data"]["acts"]
    dis = [a for a in acts if a["text"].startswith("Disassemble")]
    if not dis:
        refuse(f"no Disassemble at {x},{z}: " + ", ".join(a["text"] for a in acts)
               + " (too hard for this hammer? the log says 'too hard')")
    call("do", i=dis[0]["i"])
    wait_idle(timeout=60000)
    left = cells([(x, z)])[(x, z)].get("things") or []
    got = []
    for _ in range(4):
        if pack_full():  # errors.csv row 5: a pick-up into a full pack vanishes
            print("  the pack is full: not picking up")
            break
        p = pc()
        acts = call("acts", dx=x - p["x"], dz=z - p["z"], mode="all")["data"]["acts"]
        picks = [a for a in acts if a["text"].startswith("Pick")]
        if not picks:
            break
        got.append(picks[0]["text"][len("Pick ("):].rstrip(")"))
        call("do", i=picks[0]["i"])
        wait_idle(timeout=10000)
    print(f"  {name} at {x},{z}: {dis[0]['text']} -> " + (", ".join(got) if got else
          "nothing (the ~9% miss)" if not left else "left on the cell: " + ", ".join(left)))


def main():
    setup()
    todo = pack_junk([a for a in sys.argv[1:] if not a.startswith("--")])
    if not todo:
        print("no scrap junk in the pack")
        return
    print("scrap junk: " + ", ".join(todo))
    if "--dry" in sys.argv:
        return
    why = ready(hp=None, hunger=None, burden=None)  # a window, busy, a bad condition, a hostile in view
    if why:
        stop(why)
    for name in todo:
        one(name)  # run 13: Place puts down the whole stack, and Disassemble breaks it all (2 cans -> 2 scraps)


if __name__ == "__main__":
    main()
