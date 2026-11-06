"""Gather until the pack holds enough of an item: find the nearest object of a kind,
harvest it with the held tool (holding the axe first if nothing is held), pick up the
drops, repeat. Skips cells that offer no harvest (map edge, no path). Exit 0 at the target,
on low SP, or when nothing is left in range; exit 3 (stop) on common.ready's reasons before
each harvest (a hostile in view, a window, a task running, HP under 60%, Hungry, Overweight)
and on a full pack; exit 1 without the tool.

usage: python -I tools/gather.py OBJECT ITEM COUNT [min_sp] [radius] [--weak-ok] [--food-run]
  --food-run  gathering food while hungry: no hunger stop at all (the food is the fix)
  --weak-ok  (run 31) keep going past hostiles 10+ levels under me unless within 2 cells or an exploder
  e.g. python -I tools/gather.py weed leaf 14
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import grab, pack_full, ready, refuse, stop  # noqa: E402
from harvest import DONE, NO_ACT, harvest  # noqa: E402

# run 31 (the user's tip: fell a nefia's trees for G30's floors): every Lv1 putit in view stopped the felling.
# --weak-ok ignores a hostile 10+ levels under me unless it is within 2 cells or an exploder (threat.py's flag, the
# kamikaze ids: run 24's bomb rock was Lv14 and blew 145 -> 0); anything else in view still stops it
WEAK_OK = "--weak-ok" in sys.argv


def weak_check():
    import threat
    s = call("state")["data"]
    me = s["pc"].get("lv") or 0
    for c in sorted((c for c in s.get("nearby") or [] if c.get("hostile")), key=lambda c: c.get("dist", 99)):
        prof = threat.profile(c.get("id") or c.get("name")) or {"flags": []}
        exploder = "exploder" in prof["flags"] or "kamikaze" in (c.get("id") or "").replace("samurai_kamikaze", "") or c.get("id") == "hardgay"
        if exploder or c.get("dist", 99) <= 2 or (c.get("lv") or 0) > me - 10:
            return f"hostile in view: {c['name']} Lv{c.get('lv')} at {c.get('dist')}" + (" (an exploder)" if exploder else "")
    return None


# Objects whose harvest is a crop that must be ripe (see nearest()).
# run 33: the nut bushes (G14's ration nuts) too: an unripe crim or api is cut for a branch like a berry bush
CROPS = ("berry", "mushroom", "wheat", "potato", "imo", "cabbage", "carrot", "tomato", "corn", "rice", "crim", "api", "coffee")


def count(item):
    # Match the item id (leaf, grass, log...): names pluralize ("7 leaves").
    items = call("inv")["data"]["items"]
    # An exact item id wins: "grass" must not count "40 grass makeshift arrows" (run 03).
    by_id = [i for i in items if i["id"] == item]
    if by_id or item in KNOWN_IDS:
        return sum(i["num"] for i in by_id)
    want = item.lower()
    return sum(i["num"] for i in items if want in i["name"].lower() or want in singular(i["name"].lower()))


def singular(name):
    """'4 big leaves' -> '4 big leaf' (run 09: a stack of big leaves counted 0)."""
    def one(w):
        if w.endswith("ves"):
            return w[:-3] + "f"
        if w.endswith("ies"):
            return w[:-3] + "y"
        if w.endswith(("ses", "xes", "ches", "shes")):
            return w[:-2]
        return w[:-1] if w.endswith("s") and not w.endswith("ss") else w
    return " ".join(one(w) for w in name.split())


KNOWN_IDS = ("grass", "log", "plank", "stick", "branch", "vine", "leaf", "bone", "rock", "crim", "berry",
             "string", "bark", "resin", "mushroom")


def nearest(obj, r, skip, ripe_only=True, inside=None, outside=None):
    """Nearest matching object, one bridge call (`find`). Plants whose crop isn't ripe are
    skipped: harvesting them destroys the plant for a branch (run 03, berry bushes).
    ripe_only=False takes them too (clearing for soil wants them gone, run 10). inside and
    outside are (x0, z0, x1, z1) boxes: keep only hits inside the first, none inside the second."""
    rep = call("find", name=obj, r=r, n=500)
    if not rep.get("ok"):
        return None
    within = lambda h, b: b[0] <= h["x"] <= b[2] and b[1] <= h["z"] <= b[3]  # noqa: E731
    for h in rep["data"]["hits"]:
        if h["kind"] != "obj" or (h["x"], h["z"]) in skip:
            continue
        if (inside and not within(h, inside)) or (outside and within(h, outside)):
            continue
        # Ripeness matters only for fruiting crops (an unripe berry bush is destroyed for a
        # branch); trees give logs and weeds give grass at any stage.
        if ripe_only and h.get("ripe") is False and any(c in h["name"].lower() for c in CROPS):
            continue
        # Objects on the map's border can't be reached (their only act is "Enter"); checking
        # first saves the walk (run 03: three game hours lost walking to edge trees).
        if h.get("edge"):  # bridge 0.11.0 flags border objects in `find`
            skip.add((h["x"], h["z"]))
            continue
        return (h["dist"], h["dx"], h["dz"], h["x"], h["z"])
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]  # the new-game test: --weak-ok in radius's place crashed int()
    obj, item, target = args[0], args[1], int(args[2])
    min_sp = int(args[3]) if len(args) > 3 else 4
    r = int(args[4]) if len(args) > 4 else 12
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # Hold the right tool: an axe for trees, a pickaxe for stone and rock (run 03: holding the
    # pickaxe, "An oak tree is too difficult to harvest" x30 in an endless loop).
    o = obj.lower()
    want = "woodcutter" if "tree" in o else ("pickaxe" if any(w in o for w in ("stone", "rock", "ore")) else None)
    held = call("state")["data"]["pc"]["held"] or ""
    # A hand job (flowers, weeds, berries) with a throwable or weapon held turns "Harvest" into
    # "Throw" (run 04: the Putit on the hotbar became the held item). Empty the hands first.
    if not want and held and not any(w in held.lower() for w in ("axe", "pickaxe", "sickle", "hoe", "shovel")):
        from unpack import put_away_held  # the inventory's own "Put away", not common.put_away (the hotbar deselect)
        put_away_held()
        held = call("state")["data"]["pc"]["held"] or ""
        if held:
            refuse(f"could not put away the held {held}")
    if want and want not in held.lower():
        # common.grab: a whole word ("woodcutter's axe"), never a cursed stack (the review of 2026-10-23)
        got = grab(want, what="tool")
        if not got:
            refuse(f"no {want} in the pack")
        print(f"holding the {got}", flush=True)
    skip = set()
    have = count(item)
    print(f"{item}: {have}/{target}", flush=True)

    def report():
        p = call("state")["data"]["pc"]
        print(f"stopped with {item} {have}/{target}; SP {p['sp']}/{p['maxSp']}; {p['date']}", flush=True)
    tries = 0
    while have < target and tries < 3 * target + 10:
        tries += 1
        # run 17: on a wild field a kamikaze yeek walked up during a harvest and blew (-30 HP);
        # nothing here looked for hostiles. common.ready: a hostile in view (threat order belongs
        # to delve/fight), a window, a task still running, HP, Hungry, Overweight
        # Start Run 1: gathering weeds is how a new character fixes hunger, so its food run goes on whatever the hunger: stopping it starves her
        why = ready(idle=True, hostiles=not WEAK_OK, hunger=None if "--food-run" in sys.argv else 70)
        if not why and WEAK_OK:
            why = weak_check()
        if why:
            report()
            stop(why)
        if pack_full():  # run 12 (errors row 5): a pick-up into a full pack vanished
            report()
            stop("the pack is full: store or drop something first")
        n = nearest(obj, r, skip)
        if not n:
            print(f"no {obj} left within {r}")
            break
        _, dx, dz, ax, az = n
        res = harvest(dx, dz, min_sp)
        if res == NO_ACT:
            skip.add((ax, az))
            continue
        if res != DONE:
            break
        log = call("state")["data"].get("log") or []
        if any("too difficult to harvest" in l for l in log[-3:]):
            report()
            stop(f"the held tool can't harvest {obj} (too difficult): another tool, or another object")
        before, have = have, count(item)
        if have <= before:
            # It gave something else (a young tree gives branches): don't pick it again
            # (run 03: an endless loop on young oaks).
            skip.add((ax, az))
        print(f"  {item}: {have}/{target}", flush=True)
    report()


if __name__ == "__main__":
    main()
