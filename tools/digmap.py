"""Dig up treasure maps (G44, the user 2026-11-04; run 41): the dig is on the world map itself. Each carried map's spot is in
bridge `places` (TraitScrollMapTreasure.GetDest); a shovel in hand on that tile offers "Dig (Easy)" (TaskDig), and "You dig up
the treasure" leaves an unguarded mystic treasure chest on the tile, unlocked. The first one (run 41, Lv21): 1,753 orens, 2 gold
bars, 2 medals, two pieces, about 2 real minutes with the walk.

usage: python -I tools/digmap.py --list                 every carried map's spot, nearest first
       python -I tools/digmap.py --plan [X,Z]             a greedy tour of them from here or X,Z, with each leg's worst ambush level
       python -I tools/digmap.py [N=1] [--max-dist D=70] [--danger-ok N]   the nearest N maps: walk, dig, pick the chest, list it
Between legs it eats (entering the tile's field map) and sleeps on the world map when wgo.py stops for it. Each dig is a row in
runs/digs.csv: real seconds, game hours, map level, walk length, orens, bars, medals and the rest of the chest.
The chests ride home closed; their money counts as carried (elin-pack), so arrive.py's chest step empties them.
Exit 0 done, 1 refused (not on the world map, no shovel, no map in reach), 3 stopped (wgo.py's stop, a hostile, a window).
"""
import csv
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import THRESHOLDS, call, data, last, pc, refuse, run, setup, state, stop, top, wait_idle, wait_until  # noqa: E402

LOG = Path(__file__).resolve().parent.parent / "runs" / "digs.csv"
FIELDS = ["logged_at", "game_date", "seconds", "game_hours", "lv", "walked", "orens", "bars", "medals", "other"]


def maps():
    d = data("places", r=3)
    return d["me"], d.get("treasure") or []


def world_ok():
    return bool((state().get("zone") or {}).get("region"))


def game_hours(date):
    """Hours since year 0 from 'YYY-MM-DD HH:MM' (a game month is 30 days, a year 12 months)."""
    m = re.match(r"(\d+)-(\d+)-(\d+) (\d+):(\d+)", date)
    y, mo, da, h, mi = (int(x) for x in m.groups())
    return ((y * 12 + mo) * 30 + da) * 24 + h + mi / 60


def date_now():
    return pc().get("date") or ""


def nefia_here():
    """The nefia (or any 'Danger Lv.' place) on this world-map tile, else None."""
    for p in (call("places", r=0).get("data") or {}).get("places") or []:
        if p.get("dist") == 0 and "Danger Lv." in (p.get("name") or ""):
            return p.get("name")
    return None


def off_nefia():
    """Run 50: a meal stop and the unload each 'entered this tile' on a nefia's tile, which is the nefia itself: once the
    conquered Mystical Cave (2B), once Tangled Cave's danger-14 B1 beside an electric cloud and a kamikaze samurai Lv13 at
    3 cells. Step one tile aside first, so Enter opens a field map."""
    name = nefia_here()
    for way in ("e", "w", "n", "s"):
        if not name:
            return
        print(f"  {name} is on this tile: one step {way} before entering", flush=True)
        call("move", dir=way)
        wait_until("frames", n=30, timeout=3000)
        name = nefia_here()
    if name:
        stop(f"every tile beside me holds {name}: no field map to enter here")


def enter_and_eat():
    """A local map for a meal: Enter on this tile, eat, leave. Exit 3 of eat.py passes up."""
    off_nefia()
    out = run("act.py", "0", "0", "Enter")
    if world_ok():
        out = run("act.py", "0", "0", "Enter")  # lessons run 38: the first Enter is sometimes ignored
    if world_ok():
        stop(f"couldn't enter this tile to eat: {last(out)}")
    out = run("eat.py", "--until", "40")
    print("  " + last(out))
    if out.rc:
        # a weak foe on the meal's map cancels the meal (run 41: a danger 10 field): kill what's in view, then eat
        for c in state().get("nearby") or []:
            if c.get("hostile") and (c.get("lv") or 99) <= pc()["lv"]:
                print("  " + last(run("fight.py", c.get("id") or c["name"])))
        out = run("eat.py", "--until", "40")
        print("  " + last(out))
    if out.rc:
        stop(f"meal: {last(out)}")
    out = run("leave.py", "--force")
    if not world_ok():
        stop(f"couldn't leave the meal's map: {last(out)}")


def upkeep():
    """Eat and sleep before a leg, the way a nefia's door gets it (elin-play: sleep on the overworld)."""
    p = pc()
    if p.get("hunger", 0) >= THRESHOLDS["eat_at"]:  # run 44: 55 here, 45 everywhere else
        enter_and_eat()
        p = pc()
    if (p.get("sleepPhase") or 0) >= 1:
        if p.get("hunger", 0) >= 50:
            enter_and_eat()
        print("  " + last(run("sleep.py")))


def walk_to(tx, tz, danger_ok):
    args = [str(tx), str(tz), "--weak-ok", "--ambush"]
    if danger_ok:
        args += ["--danger-ok", str(danger_ok)]
    for _ in range(12):
        try:
            me = data("places", r=1)["me"]
        except Exception as e:  # run 44: an ambush landed just after wgo's arrival, and 'places' raised on the field map
            if "not on the world map" not in str(e):
                raise
            import wgo
            outcome = wgo.handle_ambush()
            print(f"  an ambush on arrival: {outcome}", flush=True)
            if outcome != "cleared":
                stop(f"an ambush on the way to {tx},{tz}: {outcome}")
            continue
        if me == f"{tx},{tz}":
            return True
        upkeep()
        out = run("wgo.py", *args, timeout=600)
        print("  " + last(out))
        if out.rc == 1:
            print(f"  refused: {last(out)}")
            return False
        if out.rc == 0:
            continue
        text = last(out).lower()
        if "hungry" in text or "hunger" in text or "sleep" in text:
            continue
        stop(f"the walk to {tx},{tz} stopped: {last(out)}")
    stop(f"12 legs and not at {tx},{tz}")


def shovel_in_pack():
    """Deselecting puts a held tool back in the bag it came from (run 41): take it out again before each dig. Returns the
    shovel's name: run 47's pine shovel was refused because "iron shovel" was written in here twice."""
    for i in data("inv")["items"]:
        if "shovel" in i["name"].lower():
            return i["name"]
    for i in data("stock")["pack"]:
        hit = [x["name"] for x in i.get("items") or [] if "shovel" in x["name"].lower()]
        if hit:
            out = run("bag.py", i["name"], "--take", hit[0])
            run("close.py")
            if out.rc:
                refuse(f"no shovel: {last(out)}")
            return hit[0]
    refuse("no shovel in the pack or a carried bag")


def dig_here():
    name = shovel_in_pack()
    # run 57: a seasonal drama ("Winter...winter is coming!") opened on arrival and the grab read "no usable slot"
    # (invacts is ignored under a LayerDrama): step through any dialog first
    if (state().get("layers") or {}).get("top") == "LayerDrama":
        run("talk.py", "20")
    out = run("item.py", name, "Grab")
    if out.rc:
        refuse(f"no shovel in hand: {last(out)}")
    out = run("act.py", "0", "0", "Dig", "right")
    if out.rc:
        stop(f"no Dig here: {last(out)}")
    wait_idle(30000)
    log = " ".join(str(x) for x in state().get("log") or [])
    run("hotbar.py", "--deselect")
    print("  " + ("treasure!" if "treasure" in log.lower() else "no treasure in the log"))
    out = run("act.py", "0", "0", "Pick")
    if out.rc:
        stop(f"no chest to pick here: {last(out)}")


def read_chest():
    """The newest chest's contents from the stock op, without opening it (an opened chest takes later quick moves, and bag.py
    takes the first chest of that name: run 41's row for the second chest carried the first's list)."""
    chests = [i for i in data("stock")["pack"] if "mystic treasure chest" in i["name"].lower()]
    newest = max(chests, key=lambda i: i.get("uid") or 0)
    return ", ".join(x["name"] for x in newest.get("items") or [])


def amount(text, word):
    m = re.search(r"([\d,]+) " + word, text)
    if m:
        return int(m.group(1).replace(",", ""))
    return 1 if re.search(r"\ba\s+" + word.rstrip("s"), text) or "★Small Medal," in text and word.startswith("Small") else 0


def plan(mx, mz, ms, start=None):
    """A greedy tour of the carried maps: each next stop the nearest, with each leg's worst ambush level by wgo's own measure
    (the straight line, the best tile within a step of each point). Terrain is read once, for every tile in reach."""
    from wgo import TERRAIN_LETTERS
    cells = {}
    r = max(m["dist"] for m in ms) + 12
    for want in TERRAIN_LETTERS:
        for h in (call("terrain", r=r, want=want, n=60000).get("data") or {}).get("hits") or []:
            cells[(mx + h["dx"], mz + h["dz"])] = h

    def worst(ax, az, bx, bz):
        n = max(abs(bx - ax), abs(bz - az)) or 1
        w = 0
        for i in range(1, n + 1):
            px, pz = ax + round((bx - ax) * i / n), az + round((bz - az) * i / n)
            near = [max(0, h["danger"] - 5) for ox in (-1, 0, 1) for oz in (-1, 0, 1)
                    if (h := cells.get((px + ox, pz + oz))) and not h["blocked"]]
            if near and min(near) > w:
                w = min(near)
        return w

    left = [(mx + m["dx"], mz + m["dz"], m["lv"], m["blessed"]) for m in ms]
    at = start or (mx, mz)
    total = 0
    while left:
        left.sort(key=lambda t: max(abs(t[0] - at[0]), abs(t[1] - at[1])))
        t = left.pop(0)
        d = max(abs(t[0] - at[0]), abs(t[1] - at[1]))
        total += d
        print(f"  {at[0]},{at[1]} -> {t[0]},{t[1]}  d{d}  worst ambush {worst(at[0], at[1], t[0], t[1])}  map Lv{t[2]} {t[3]}")
        at = (t[0], t[1])
    print(f"{len(ms)} maps, {total} tiles, about {total * 2.5 / 24:.0f} game days")


def main():
    setup()
    args = sys.argv[1:]
    if not world_ok():
        refuse("not on the world map")
    me, ms = maps()
    mx, mz = (int(x) for x in me.split(","))
    if "--plan" in args:
        i = args.index("--plan")
        start = tuple(int(x) for x in args[i + 1].split(",")) if i + 1 < len(args) and "," in args[i + 1] else None
        plan(mx, mz, ms, start)
        return
    if "--list" in args:
        for m in sorted(ms, key=lambda t: t["dist"]):
            print(f"  ({m['dx']:+d},{m['dz']:+d}) d{m['dist']} -> {mx + m['dx']},{mz + m['dz']}  {m['name']} Lv{m['lv']} {m['blessed']}")
        print(f"{len(ms)} maps carried, from {me}")
        return
    pos = [a for a in args if a.isdigit() and args[args.index(a) - 1] not in ("--max-dist", "--danger-ok")]
    n = int(pos[0]) if pos else 1
    max_dist = int(args[args.index("--max-dist") + 1]) if "--max-dist" in args else 70
    danger_ok = int(args[args.index("--danger-ok") + 1]) if "--danger-ok" in args else 0
    done = 0
    skip = set()  # spots whose route wgo.py refused (run 41: most of the far maps lie past level 20+ fields)
    while done < n:
        me, ms = maps()
        mx, mz = (int(x) for x in me.split(","))
        near = sorted((m for m in ms if m["dist"] <= max_dist and (mx + m["dx"], mz + m["dz"]) not in skip), key=lambda t: t["dist"])
        if not near:
            if done:
                print(f"{done} dug; no other carried map within {max_dist} on an allowed route")
                return
            refuse(f"no carried map within {max_dist} on an allowed route")
        m = near[0]
        tx, tz = mx + m["dx"], mz + m["dz"]
        print(f"map Lv{m['lv']} at {tx},{tz}, {m['dist']} tiles from {me}")
        t0, h0 = time.time(), game_hours(date_now())
        if not walk_to(tx, tz, danger_ok):
            skip.add((tx, tz))
            continue
        dig_here()
        listing = read_chest()
        row = {"logged_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "game_date": date_now(),
               "seconds": round(time.time() - t0), "game_hours": round(game_hours(date_now()) - h0, 1),
               "lv": m["lv"], "walked": m["dist"], "orens": amount(listing, "orens"),
               "bars": amount(listing, "gold bars"), "medals": amount(listing, "Small Medals"), "other": listing}
        new = not LOG.exists()
        with LOG.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, FIELDS)
            if new:
                w.writeheader()
            w.writerow(row)
        print(f"  {row['seconds']} s, {row['game_hours']} game hours: {listing}")
        done += 1
        unload()


FRUITLESS = False  # an unload that found nothing to empty ends the tries for this tour (run 44)


def unload():
    """Run 44: 20 maps in one tour, and a closed chest weighs 15 (Burden 2 at five): at burden phase 2 step into the
    tile's field map, empty the chests there with chests.py --field (they stay behind), and come back up. Run 41 did
    this by hand."""
    global FRUITLESS
    p = data("state")["pc"]
    if (p.get("burdenPhase") or 0) < 2 or FRUITLESS:
        return
    # run 44: the weight was medals, bars and food, the one chest locked and the next nested inside it: chests.py found
    # nothing six times, and each try stepped into the tile's field map (danger 36 by Specwing: a shiva and a penguin)
    pack = data("stock").get("pack") or []
    if not any("treasure chest" in (x.get("name") or "").lower() for i in pack for x in [i] + (i.get("items") or [])):
        return
    if nefia_here():  # run 50: the unload's Enter on a nefia's tile went into Tangled Cave's B1 (danger 14)
        off_nefia()
    acts = call("acts", dx=0, dz=0, mode="all").get("data", {}).get("acts") or []
    enter = [a for a in acts if a["text"] == "Enter"]
    if not enter:
        print("  burden phase 2 and no field map here: the chests ride on")
        return
    call("do", i=enter[0]["i"])
    wait_until("zone", timeout=10000)
    out = run("chests.py", "--field", timeout=900)
    print(f"  unload at burden phase {p.get('burdenPhase')}: chests.py --field rc {out.rc}: {last(out)[:100]}", flush=True)
    if "no chest left" in str(out) or "locked chest" in str(out):
        FRUITLESS = True  # nothing it can empty: no more field-map trips for it this tour
    lv = run("leave.py", "--force", timeout=300)
    if lv.rc != 0:
        stop(f"leave.py rc {lv.rc} after the unload: {last(lv)[:100]}")


if __name__ == "__main__":
    main()
