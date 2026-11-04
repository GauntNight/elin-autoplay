"""A board harvest job ("Harvest season", "Farm worker wanted", "Harvest for me"), run 19: the loop
that runs 17-19 did by hand. Inside the instance (Zone_instance_harvest, 180 game minutes):

  1. scan the fields round the ★Farmer's Shipping Chest for ripe crops (bridge cells)
  2. harvest the heaviest size words first, then the nearest (legendary, heavier than an elephant,
     monstrous, bigger than a man, very huge, huge, rather big, handy), with harvest.py --weak-ok
  3. deliver ("Use" the chest, its Deliver All button) every LOAD harvests, at Burden, and at the end
  4. stop: the instance ended (back in town), SP at the floor, nothing ripe, or a real threat

The user's rules (run 19): don't chase mobs in a harvest job, range attack or ignore. So weak
hostiles (3+ levels below me) are ignored and nothing is fought from here: a stronger one stops
the loop for a decision. Run 18: deliver every ~35s (92s carried was Squashed).

usage: python -I tools/harvestjob.py [min_sp=5] [load=4] [radius=20] [--ends HH:MM]
Progress is the quest tracker's "Deliver Crops: X of Ys" line.
--ends: the instance's end (the accept time + 180 game minutes). Within 20 minutes of it no new
harvest starts and what is carried is delivered (run 19: 64.0s of 71.3s when time ran out; the
job was taken at 05:31 in the dark and a bat chase took ~25 of the 180 minutes). Take a harvest
job only in full daylight, 06:00 to ~14:00, and start it standing by the chest.
Exit: 0 done (target met or nothing left), 1 refused (not in a harvest instance), 2 bridge,
3 stopped for a decision (a threat, SP, a window).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from activity import mark  # noqa: E402
from common import cells, data, last, refuse, run, setup, state, stop, wait_until, walk_beside  # noqa: E402

SIZES = ("legendary", "heavier than an elephant", "monstrous", "bigger than a man", "very huge",
         "huge", "rather big", "handy")
HEAVY = ("Burden", "Heavy Burden", "Overweight", "Very Overweight", "Squashed")
# The user's rule (run 19): weak hostiles (3+ levels below me) are ignored in a harvest job. The
# flag goes to harvest.py on its command line (--weak-ok), since it runs as a subprocess.
WEAK_OK = True


def rank(obj):
    o = obj.lower()
    return next((i for i, w in enumerate(SIZES) if w in o), len(SIZES))


def progress():
    for t in data("texts", all=True)["texts"]:
        m = re.search(r"Deliver Crops: ([\d.]+)s of ([\d.]+)s", t)
        if m:
            return float(m.group(1)), float(m.group(2))
    return None


def burdened():
    """Burden phase 1+ (any label): pc.burdenPhase (bridge 0.30.0), else the HUD's label."""
    p = data("state")["pc"]
    if p.get("burdenPhase") is not None:
        return p["burdenPhase"] >= 1
    return any(t.strip().rstrip("!") in HEAVY for t in data("texts", all=True)["texts"])


def in_job():
    return data("state")["zone"]["full"].startswith("Zone_instance_harvest")


def chest():
    h = data("find", name="Farmer's Shipping Chest", r=999, n=1)["hits"]
    return (h[0]["x"], h[0]["z"]) if h else None


def deliver(cx, cz):
    w = walk_beside(cx, cz, weak_ok=True)
    if not w.get("done"):
        return f"the walk to the chest ended: {w.get('why')}"
    p = data("state")["pc"]
    acts = [a for a in data("acts", dx=cx - p["x"], dz=cz - p["z"], mode="all")["acts"] if a["text"].startswith("Use")]
    if not acts:
        return "the chest offers no Use"
    data("do", i=acts[0]["i"])
    wait_until("layer", timeout=4000)  # the chest's window opens
    btn = [b for b in data("buttons")["buttons"] if "Deliver All" in (b.get("tip") or "") or "Deliver All" in b.get("text", "")]
    if not btn:
        run("close.py")
        return "no Deliver All button"
    data("click", i=btn[0]["i"])
    wait_until("frames", n=15, timeout=2000)
    run("close.py")
    return None


def ripe_cells(cx, cz, r):
    pts = [(x, z) for x in range(cx - r, cx + r + 1) for z in range(cz - r, cz + r + 1)]
    c = cells(pts)
    out = [(p, c[p]["obj"]) for p in pts if c.get(p) and c[p].get("ripe") and c[p].get("obj")]
    return sorted(out, key=lambda q: (rank(q[1]), abs(q[0][0] - cx) + abs(q[0][1] - cz)))


def minutes_left(ends):
    """Game minutes until HH:MM today (or tomorrow, past midnight), None without --ends."""
    if not ends:
        return None
    now = data("state")["pc"]["date"].split()[-1]
    h, m = map(int, now.split(":"))
    eh, em = map(int, ends.split(":"))
    return ((eh * 60 + em) - (h * 60 + m)) % (24 * 60)


def main(argv):
    setup()
    ends = argv[argv.index("--ends") + 1] if "--ends" in argv else None
    argv = [a for a in argv if a not in ("--ends", ends)]
    nums = [int(a) for a in argv if a.isdigit()]
    min_sp, load, radius = (nums + [5, 4, 20][len(nums):])[:3]
    if not in_job():
        refuse("not in a harvest job's instance (Zone_instance_harvest)")
    c = chest()
    if not c:
        refuse("no Farmer's Shipping Chest on this map")
    mark("jobs", "start", note="harvest job")
    try:
        return job(c, min_sp, load, radius, ends)
    finally:
        note = "back in town"
        try:
            if in_job():
                note = f"delivered {progress()}"
        except Exception:  # noqa: BLE001 - the mark must not hide the real exit
            pass
        mark("jobs", "end", note=note)


def job(c, min_sp, load, radius, ends):
    carried, tried = 0, set()
    while True:
        if not in_job():
            print("the job's time is up: back in town (look.py, then the client)")
            return 0
        s = state()
        p = s["pc"]
        foes = [x for x in s.get("nearby") or [] if x.get("hostile") and (x.get("lv") or 99) > p["lv"] - 3]
        if foes:
            stop(f"{foes[0]['name']} Lv{foes[0]['lv']} in view (range attack or leave it: no chasing)")
        if p["sp"] <= min_sp:
            if carried:
                deliver(*c)
            stop(f"SP {p['sp']} at the floor {min_sp}")
        left = minutes_left(ends)
        if left is not None and left < 20:
            if carried:
                deliver(*c)
            print(f"{left} game minutes left: no new harvest; delivered {progress()}")
            return 0
        todo = [q for q in ripe_cells(*c, radius) if q[0] not in tried]
        if not todo:
            if carried:
                deliver(*c)
            print(f"nothing ripe left within {radius} of the chest; delivered {progress()}")
            return 0
        (x, z), obj = todo[0]
        tried.add((x, z))
        out = run("harvest.py", str(x - p["x"]), str(z - p["z"]), str(min_sp), *(["--weak-ok"] if WEAK_OK else []), timeout=600)
        print(out.strip().splitlines()[0] if out.strip() else f"harvest {obj}: no output")
        if out.rc == 0:
            carried += 1
            tried.discard((x, z))  # a fruit plant can ripen again (the scan skips it until then)
        if carried >= load or burdened():
            why = deliver(*c)
            if why:
                stop(f"delivery failed: {why}")
            carried = 0
            print(f"  delivered: {progress()}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
