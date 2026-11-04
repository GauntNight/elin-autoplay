"""Make and plant a farm plot (G3, run 05), through the game's own acts.

A field needs bare ground first: the shovel's "Dig" strips the grass floor (TaskDig), then the
hoe's "Plow" turns soil into floor "field" (TaskPlow; the hoe refuses grass, objects and water).
On a field a ripe crop waits for you, rain waters it and no weeds grow (GrowSystem). Each step
costs about 1 SP. A seed is planted by holding it and right-clicking a cell ("Plant"); it
sprouts at the next 06:00 on a cell with no object. Keep the home's soil cost under its limit
first (home board Fertility >= 3 per imo): see clear.py.

usage: python -I tools/farm.py till X,Z [X,Z ...]          dig (shovel) then plow (hoe) each cell
       python -I tools/farm.py plant SEED X,Z [X,Z ...]    plant one SEED on each field cell
       python -I tools/farm.py status X,Z [X,Z ...]        floor, plant and stage of each cell
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call, close  # noqa: E402

TOOLS = Path(__file__).resolve().parent


from common import grab, matches, pc, ready, run, state, stop, wait_until, walk  # noqa: E402
from common import cells as read_cells  # noqa: E402


def take(name):
    """Hold a pack item through common.grab: its matcher folds "seeds of X" and "a seed of X" into
    one name (run 10: planting stopped one seed short each time when only the singular was left),
    matches whole words and skips cursed stacks. The hotbar selection is emptied first (a selected
    slot outranks a Grab). Returns True when the item is in hand."""
    if matches(name, [pc().get("held") or ""]):
        return True
    run("hotbar.py", "--deselect")
    return bool(grab(name, what="seed or tool"))


def cell(x, z):
    p = pc()
    return call("cell", dx=x - p["x"], dz=z - p["z"])["data"]


def act_at(x, z, text):
    """Do the right-click act starting with `text` on absolute cell x,z; walk beside it if the
    act isn't offered from here. Waits until I'm idle again, looking for a window or a hostile
    between the bridge's idle waits (each returns the moment the task ends, or after a second).
    Returns the act's text (with " (interrupted)") or None."""
    for attempt in range(2):
        p = pc()
        acts = call("acts", dx=x - p["x"], dz=z - p["z"], mode="right")["data"]["acts"]
        hit = [a for a in acts if a["text"].lower().startswith(text.lower())]
        if hit:
            call("do", i=hit[0]["i"])
            for _ in range(40):
                w = wait_until("idle", timeout=1000)
                s = state()
                if (s.get("layers") or {}).get("top") or any(c["hostile"] for c in s.get("nearby") or []):
                    return hit[0]["text"] + " (interrupted)"
                if w.get("done"):
                    break
            return hit[0]["text"]
        if attempt == 0:
            walk(x - 1 if x > p["x"] else x + 1, z, r=0, hp=0, timeout=15000)  # at home
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    mode = a[0]
    if mode == "plant":
        seed, cells = a[1], a[2:]
    else:
        seed, cells = None, a[1:]
    cells = [tuple(int(v) for v in c.split(",")) for c in cells]
    info = read_cells(cells)  # one call for every listed cell (was a state + cell pair per cell)
    if mode == "status":
        for x, z in cells:
            c = info.get((x, z)) or {}
            print(f"{x},{z}: {c.get('floor')}  obj {c.get('obj')}  stage {c.get('growStage')}  ripe {c.get('ripe')}")
        return
    why = ready(hp=None, hunger=None)  # a window, busy, a bad condition, a hostile in view (at home)
    if why:
        stop(why)

    def done(x, z, text):
        if "(interrupted)" in text:  # a window opened or a hostile came into view: a decision
            print(f"{x},{z}: {text}")
            stop(text)
        return text

    if mode == "till":
        todo = [(x, z) for x, z in cells if (info.get((x, z)) or {}).get("floor") != "field"]
        dig = [(x, z) for x, z in todo if "grass" in ((info.get((x, z)) or {}).get("floor") or "")]
        if dig and take("shovel"):
            for x, z in dig:
                print(f"{x},{z}: {done(x, z, act_at(x, z, 'Dig') or 'no Dig act')} -> {cell(x, z).get('floor')}")
        if todo and take("hoe"):
            for x, z in todo:
                print(f"{x},{z}: {done(x, z, act_at(x, z, 'Plow') or 'no Plow act')} -> {cell(x, z).get('floor')}")
    elif mode == "plant":
        if not take(seed):
            sys.exit(f"couldn't hold {seed!r}")
        for x, z in cells:
            c = info.get((x, z)) or {}
            if c.get("floor") != "field" or c.get("obj"):
                print(f"{x},{z}: skipped (floor {c.get('floor')}, obj {c.get('obj')})")
                continue
            print(f"{x},{z}: {done(x, z, act_at(x, z, 'Plant') or 'no Plant act')} -> obj {cell(x, z).get('obj')}")
            if not take(seed):
                print("no seeds left to hold")
                break
    p = pc()
    print(f"SP {p['sp']}/{p['maxSp']}  {p['date']}")


if __name__ == "__main__":
    main()
