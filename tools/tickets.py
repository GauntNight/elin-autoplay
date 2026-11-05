"""The first-time craft chain as one tool (run 42: every new recipe pays an old ticket, 117 orens anywhere, and trains Crafting and Carpentry from level 1;
done by hand it took 25 real minutes). From a home with a workbench: logs, stones by hand, vines and bones, then sawmill -> carpenter's table -> tinker's
table and every cheap recipe on them. Eats and sleeps itself. A recipe that fails is skipped and reported; nothing here stops for a missing material.

usage: python -I tools/tickets.py [--target N]     stop once N tickets are in the pack (default: all of the list)
Needs runs/earlybase.json (the bed) and the axe. Exit 0 done, 3 stopped (a hostile above my level, no food and too hungry to sleep).
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import data, last, pc, run, setup, state, stop, top, walk, walk_beside  # noqa: E402
from earlyday import clear_hostiles, clear_windows, named, tidy  # noqa: E402

BASE = Path(__file__).resolve().parent.parent / "runs" / "earlybase.json"
BED = json.loads(BASE.read_text(encoding="utf-8"))["bed"] if BASE.exists() else None
FOODS = ("boar on the bone", "stew", "soup", "blueberr", "crim", "on the bone", "bread", "ration", "jerk")
SPOTS = {"sawmill": (59, 48), "carpenter's table": (60, 49), "tinker's table": (61, 48)}
TARGET = int(sys.argv[sys.argv.index("--target") + 1]) if "--target" in sys.argv else 99


def stacks(word):
    return [i for i in data("inv")["items"] if word in i["name"] and not i.get("equipped") and "rotten" not in i["name"]]


def have(word):
    return sum(i.get("num") or 1 for i in stacks(word))


def tickets():
    return have("old ticket")


def eat_if_needed(limit=45):
    while pc()["hunger"] >= limit:
        for f in FOODS:
            s = stacks(f)
            if s:
                before = pc()["hunger"]
                run("item.py", s[0]["name"], "Eat", timeout=20)
                time.sleep(0.5)
                clear_windows()
                if pc()["hunger"] < before:
                    break
        else:
            return False
    return True


def sleep_if_low(need=9):
    """Sleep when SP is under need (and low enough for the bed to work); the Rest ability does when the bed won't."""
    p = pc()
    if p["sp"] >= need:
        return
    eat_if_needed()
    p = pc()
    if p["hunger"] >= 60:
        stop(f"hunger {p['hunger']} and SP {p['sp']}: no food to sleep on")
    walk(BED[0], BED[1], r=0, hp=1, timeout=8000)
    out = run("act.py", 0, 0, "Sleep", timeout=20)
    if out.rc:
        run("ability.py", "Rest", timeout=20)
    for _ in range(50):
        time.sleep(0.3)
        if top() or state().get("drama"):
            clear_windows()
        q = pc()
        if q["sp"] > p["sp"] + 5 and "ConSleep" not in str(q.get("conditions")):
            break
    clear_windows()


def crops():
    """Food first (run 43 ran dry mid-chain): a new map's crops are ripe and nearly free."""
    for obj, item, n in (("berry", "berry", 12), ("crim", "crim", 8)):
        run("gather.py", obj, item, n, 2, 45, "--food-run", timeout=120)
        clear_windows()
    call("act", action="EmptyHand")


def gather_all():
    """Materials for the whole list: about 16 logs, 12 stones, 14 vines, 3 bones, 6 branches."""
    crops()
    if not gather_needed():
        return
    for obj, item, n in (("vine bush", "vine", 14), ("tree", "log", 16)):
        sleep_if_low()
        out = run("gather.py", obj, item, n, 4, 45, "--food-run", timeout=240)
        clear_windows()
        if out.rc == 3 and "hostile" in out:
            clear_hostiles()
        call("act", action="EmptyHand")
    sleep_if_low()
    run("gather.py", "bone", "bone", 4, 4, 45, "--food-run", timeout=120)
    clear_windows()
    tried = set()
    while have("granite stone") < 12:
        sleep_if_low()
        hits = [h for h in call("find", name="a stone", r=60, n=200)["data"]["hits"]
                if h["kind"] == "obj" and not h.get("edge") and (h["x"], h["z"]) not in tried]
        if not hits:
            break
        h = hits[0]
        tried.add((h["x"], h["z"]))
        walk_beside(h["x"], h["z"])
        p = pc()
        run("harvest.py", h["x"] - p["x"], h["z"] - p["z"], 4, timeout=30)
        clear_windows()


def gather_needed():
    return have(" log") < 6 or have("vine") < 4


def built(station):
    return bool([x for x in call("find", name=station, r=30, n=1)["data"]["hits"] if x.get("installed", True)])


def material(word, n):
    """The --use word for a stack with at least n of this kind: '5 cedar logs' -> 'cedar'; '9 granite stones' -> '9 granite' (a box's single stone would win otherwise)."""
    for s in stacks(word):
        if (s.get("num") or 1) >= n:
            m = re.match(r"(?:(\d+) |an? )?(\w+)", s["name"])
            return f"{m.group(1)} {m.group(2)}" if m.group(1) and word == "stone" else m.group(2)
    return None


def near(station):
    h = [x for x in call("find", name=station, r=30, n=1)["data"]["hits"] if x.get("installed", True)]
    if not h:
        return None
    walk_beside(h[0]["x"], h[0]["z"])
    p = pc()
    return h[0]["x"] - p["x"], h[0]["z"] - p["z"]


def craft(station, name, use=None, n=1):
    """One recipe by name. True when a new item came of it."""
    sleep_if_low()
    clear_hostiles()
    pos = near(station) if station != "quick" else None
    if station != "quick" and pos is None:
        print(f"  {name}: no {station}")
        return False
    call("act", action="EmptyHand")
    time.sleep(0.1)
    args = ["quick", name] if station == "quick" else [pos[0], pos[1], name]
    args += [n, "--force"] + (["--use", use] if use else [])
    before = tickets()
    out = run("craft.py", *args, timeout=40)
    clear_windows()
    acts = call("acts", dx=0, dz=0, mode="all")["data"]["acts"]
    put = [a for a in acts if a["text"].startswith("Put away")]
    if put:
        call("do", i=put[0]["i"])
        time.sleep(0.1)
    ok = "You crafted" in out or "crafted" in last(out)
    print(f"  {name}: {'ok' if ok else last(out)[-70:]}  tickets {tickets()} (+{tickets() - before})  SP {pc()['sp']}", flush=True)
    tidy()
    return ok


def saw(word, min_n=1):
    pos = near("sawmill")
    if pos is None:
        return
    for s in stacks(word):
        if (s.get("num") or 1) >= min_n:
            sleep_if_low(6)
            run("convert.py", pos[0], pos[1], "Saw", s["name"], timeout=40)
            clear_windows()
            return


def place(item, spot):
    x, z = spot
    out = run("place.py", item, f"{x},{z}", f"{x + 1},{z}", f"{x},{z + 1}", f"{x + 1},{z + 1}", timeout=30)
    clear_windows()
    print(f"  placed {item}: {'placed' in out}", flush=True)
    return "placed" in out


def strings(n):
    for _ in range(n):
        if have("vine") < 2:
            return
        craft("workbench", "String")


def stones_by_hand(n):
    tried = set()
    while have("granite stone") < n:
        sleep_if_low()
        hits = [h for h in call("find", name="a stone", r=60, n=200)["data"]["hits"]
                if h["kind"] == "obj" and not h.get("edge") and (h["x"], h["z"]) not in tried]
        if not hits:
            return
        h = hits[0]
        tried.add((h["x"], h["z"]))
        walk_beside(h["x"], h["z"])
        p = pc()
        run("harvest.py", h["x"] - p["x"], h["z"] - p["z"], 4, timeout=30)
        clear_windows()


def tinker():
    """The tinker's table and its tools (run 43: a table recipe isn't always known at the start: a desk counts as Table, fact to check; the first chair and a table or desk, 2 bones)."""
    t0 = time.time()
    if not built("tinker's table"):
        if have(" log") < 6:
            sleep_if_low()
            run("gather.py", "tree", "log", 8, 3, 45, "--food-run", timeout=180)
            clear_windows()
            call("act", action="EmptyHand")
        if have("bone") < 3:
            run("gather.py", "bone", "bone", 4, 2, 45, "--food-run", timeout=120)
            clear_windows()
        if not (have("a table") or have("desk")):
            if have("plank") < 4:
                saw(" log", 2)
            m = material("plank", 4)
            if m:
                craft("carpenter's table", "Desk", m)
        if not have("chair"):
            m = material("log", 2)
            if m:
                craft("carpenter's table", "Round chair", m)
        craft("workbench", "Tinker's table")
        place("tinker's table", SPOTS["tinker's table"])
    if not built("tinker's table"):
        print("no tinker's table: " + ", ".join(i["name"][:18] for i in data("inv")["items"] if any(w in i["name"] for w in ("chair", "table", "desk", "bone"))))
        return
    stones_by_hand(9)
    if have("vine") < 8:
        run("gather.py", "vine bush", "vine", 8, 2, 45, "--food-run", timeout=120)
        clear_windows()
    if have("stick") < 6:
        saw("branch", 1)
    if have("nail") < 1 and have("bone"):
        craft("tinker's table", "Nail")
    strings(4)
    for n, cost in (("Pickaxe", 2), ("Shovel", 2), ("Woodcutter's axe", 1), ("Hammer", 2), ("Sickle", 2)):
        st, sk, sg = material("stone", cost), material("stick", 1), material("string", 1)
        if st and sk and sg:
            craft("tinker's table", n, f"{st},{sk},{sg}")
    st, sk = material("stone", 1), material("stick", 1)
    if st and sk and have("nail"):
        craft("tinker's table", "Hoe", f"{st},{sk},bone")
    print(f"tinker done: {tickets()} tickets, SP {pc()['sp']}, hunger {pc()['hunger']}, {time.time() - t0:.0f}s")


def main():
    setup()
    t0 = time.time()
    if "--tinker" in sys.argv:
        tinker()
        return 0
    gather_all()
    print(f"gathered: logs {have(' log')}, stones {have('granite stone')}, vines {have('vine')}, bones {have('bone')}, branches {have('branch')}; SP {pc()['sp']}  {time.time() - t0:.0f}s", flush=True)
    logs = lambda n=2: material("log", n)  # noqa: E731
    if not built("sawmill"):
        craft("workbench", "Sawmill", f"{logs(3)},{material('stone', 3)}")
        place("sawmill", SPOTS["sawmill"])
    if not have("plank"):
        saw(" log", 3)  # planks
    if not have("stick"):
        saw("branch", 2)  # sticks
    if not built("carpenter's table"):
        craft("workbench", "Carpenter's table", f"{material('plank', 4)},{material('stone', 2)}")
        place("carpenter's table", SPOTS["carpenter's table"])
    strings(5)
    saw("branch", 2)
    craft("carpenter's table", "Wooden weapon", f"{logs(2)},{material('string', 1)},{material('stick', 2)}")
    for n, u in (("Round chair", logs(2)), ("Scrap", logs(1))):
        craft("carpenter's table", n, u)
    craft("carpenter's table", "Table", f"{logs(2)},{material('branch', 2)}" if material("branch", 2) else logs(2))
    saw(" log", 2)
    craft("carpenter's table", "Desk", material("plank", 4))
    craft("carpenter's table", "Boomerang", f"{material('plank', 4)},{material('string', 2)}")
    if have("bone") < 3:
        run("gather.py", "bone", "bone", 4, 2, 45, "--food-run", timeout=120)
        clear_windows()
    if not built("tinker's table") and have("bone") >= 2 and have("round chair") and have("a table"):
        craft("workbench", "Tinker's table")
        place("tinker's table", SPOTS["tinker's table"])
    if near("tinker's table"):
        craft("tinker's table", "Nail")
        strings(5)
        for n, cost in (("Pickaxe", 2), ("Shovel", 2), ("Woodcutter's axe", 1), ("Hammer", 2), ("Sickle", 2)):
            if tickets() >= TARGET:
                break
            st, sk, sg = material("stone", cost), material("stick", 1), material("string", 1)
            if st and sk and sg:
                craft("tinker's table", n, f"{st},{sk},{sg}")
        st, sk = material("stone", 1), material("stick", 1)
        if st and sk and have("nail"):
            craft("tinker's table", "Hoe", f"{st},{sk}", 1)
    for n in ("Fishing rod", "Wall torch"):
        craft("workbench", n)
    print(f"done: {tickets()} tickets, SP {pc()['sp']}, hunger {pc()['hunger']}, {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
