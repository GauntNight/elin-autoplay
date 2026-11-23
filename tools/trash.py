"""Garbage goes in the home trash can (G5), never the shipping chest (the user, run 08: shipping pays
0, the can pays Ecopo). Sweep the home map's garbage piles into the pack, then dump every junk stack
from the pack into the can (its drag grid: each stack dragged onto 'ing1' is destroyed for Ecopo).
Stops the sweep when a hostile comes into view. Skips anyone's property.

usage: python -I tools/trash.py [sweep R] [dump] [EXTRA_NAME ...]
       python -I tools/trash.py              sweep radius 80, then dump
       python -I tools/trash.py dump         only dump the pack's junk
       python -I tools/trash.py dump "leaf dish"   also dump stacks matching these names
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call, close as bridge_close  # noqa: E402
from common import pc, run, txlog, walk, walk_beside, wait_until  # noqa: E402
from farmday import home_guard  # noqa: E402

PICK = ("garbage", "rotten", "rubble", "empty bottle", "empty can")
DUMP = ("garbage", "rotten", "rubble", "empty bottle", "shit", "remnant of what once was")  # run 39: remnants; run 13: empty cans are scrap (scrap.py); run 30: a fresh "shit"; run 17:
# no vomit (a quest item in Return requests: one was dumped); dump one by its full name


def hostile_in_view():
    s = call("state")["data"]
    return [c["name"] for c in s.get("nearby") or [] if c.get("hostile")]


def sweep(r):
    done, n = set(), 0
    for _ in range(200):
        h = hostile_in_view()
        if h:
            print("sweep stopped: hostile in view:", ", ".join(h))
            return n
        hits = sorted((h for k in PICK for h in call("find", name=k, r=r, n=200)["data"]["hits"]
                       if h["kind"] == "thing" and not h["installed"] and (h["x"], h["z"]) not in done),
                      key=lambda h: h["dist"])
        if not hits:
            break
        h = hits[0]
        done.add((h["x"], h["z"]))
        if h["dist"] > 0:
            home_guard("the trash sweep")  # run 41
            walk(h["x"], h["z"], r=0, timeout=30000)  # at home; the sweep stops on a hostile itself
            p = pc()
            if (p["x"], p["z"]) != (h["x"], h["z"]):
                print(f"  can't reach {h['x']},{h['z']}")
                continue
        info = (call("cell", dx=0, dz=0).get("data") or {}).get("thingInfo") or []
        if any(t.get("npcProperty") for t in info):
            print(f"  skipped {h['x']},{h['z']}: someone's property")
            continue
        for _ in range(6):
            acts = call("acts", dx=0, dz=0, mode="all")["data"]["acts"]
            picks = [a for a in acts if a["text"].startswith("Pick") and any(k in a["text"].lower() for k in PICK)]
            if not picks:
                break
            call("do", i=picks[0]["i"])
            wait_until("frames", n=10, timeout=1500)
            n += 1
    print(f"swept {n} piles")
    return n


def ecopo_log():
    """The game's log ring, to count the ecopos the can pays (run 21: they land in the toolbelt's
    purse, which `inv` doesn't list, so the old count read 0 -> 0 on every dump)."""
    return list(call("state")["data"].get("log") or [])


def ecopos_paid(before, after):
    """Ecopos picked up in the lines `after` added to `before` (the ring drops its oldest lines:
    the new ones start after the longest tail of `before` that heads `after`)."""
    import re
    k = next((k for k in range(min(len(before), len(after)), 0, -1) if before[-k:] == after[:k]), 0)
    new = after[k:]
    n = 0
    for ln in new:
        if "ecopo" in ln.lower() and "pick up" in ln.lower():
            m = re.search(r"pick up (\d+) ecopos", ln)
            n += int(m.group(1)) if m else 1
    return n


def wanted(card, extra):
    """Junk by its kind (DUMP, a substring), or an EXTRA name given in full. Run 16: the extras
    were substrings too, so "seeds of wheat +1" also dumped "2 seeds of wheat +12" (the best wheat
    seeds, G14). An extra now has to be the card's whole name, its count prefix optional."""
    import re
    raw = (card or "").strip()
    c = raw.lower()
    # run 29: "A Rotten Raw Food Small Shield (Godly)", an unidentified Godly shield made of the material
    # "rotten raw food", matched "rotten" and the can destroyed it. Gear (armour values or weapon dice),
    # artifacts and unidentified things (a capitalized name) never go in, whatever their name holds
    if ("☆" in raw or "★" in raw or re.search(r"\[-?\d+, -?\d+\]", raw) or re.search(r"\(\d+d\d+", raw)
            or re.match(r"^(an? |\d+ )?[A-Z]", re.sub(r"^(A |An )", lambda m: m.group(1).lower(), raw))):
        return False
    if any(k in c for k in DUMP):
        return True
    # run 58: "a potion of salt water" is in packcheck's JUNK and not in DUMP, so packcheck routed it here at every sort and this
    # list left it: one arrival after another with 1 out of place. What packcheck routes to the can goes in the can
    try:
        import packcheck
        if packcheck.route(raw)[0] == "trash":
            return True
    except Exception:  # noqa: BLE001 - the lists below still decide
        pass
    # run 54: packcheck routed a paper scrap from the mail here by the game's junk category, and this name list didn't
    # take it, so leave.py refused home on it: the same table decides both (elin-play: a kind from the game's table)
    try:
        from packcheck import _junk_kind
        if _junk_kind(raw):
            return True
    except Exception:  # noqa: BLE001 - the name list above still works
        pass
    bare = re.sub(r"^(an? |\d+ )", "", c)
    for e in extra:
        e = e.lower().strip()
        if c == e or bare == re.sub(r"^(an? |\d+ )", "", e):
            return True
    return False


def from_bags(extra):
    """Run 44: the sweep's garbage went into the pack and purge's unclutter tucked it into the pouch, where the dump
    (the pack grid only) never saw it: 214 garbages and 33 cans, weight 108, Overweight at home and HP 276 -> 119 on
    the arrival walks. Junk in a carried bag comes out into the pack first, as many stacks as there are free cards."""
    from common import data, run
    for bag in data("stock").get("pack") or []:
        if bag.get("items") is None or "cooler" in bag["name"].lower():
            continue
        junk = [x["name"] for x in bag["items"] if wanted(x["name"], extra)]
        free = 35 - sum(1 for i in data("stock").get("pack") or [] if not i.get("equipped"))
        if junk and free > 1:
            out = run("bag.py", bag["name"], "--take", *junk[:free - 1])
            run("close.py")
            print(f"  out of {bag['name']}: {', '.join(junk[:free - 1])} (rc {out.rc})")


def dump(extra):
    from_bags(extra)
    hits = call("find", name="trash can", r=999, n=1)["data"]["hits"]
    if not hits:
        sys.exit("no trash can on this map")
    can = hits[0]
    if can["dist"] > 1:
        walk_beside(can["x"], can["z"], r=0, timeout=30000)  # at home; it tries each free neighbour
    p = pc()
    dx, dz = can["x"] - p["x"], can["z"] - p["z"]
    acts = call("acts", dx=dx, dz=dz, mode="all")["data"]["acts"]
    use = [a for a in acts if a["text"].startswith("Use (a trash can")]
    if not use:
        sys.exit(f"no Use act on the trash can from {p['x']},{p['z']}")
    before = ecopo_log()
    call("do", i=use[0]["i"])
    wait_until("layer", timeout=4000)  # the recycler grid opens
    dumped = []
    for _ in range(30):
        btns = call("buttons", all=True)["data"]["buttons"]
        slot = next((b["i"] for b in btns if b["name"].startswith("ing1")), None)
        if slot is None:
            break
        src = next((b for b in btns if "inventory grid" in b["name"] and "UIInventory" in b.get("path", "")
                    and wanted(b.get("card"), extra)), None)
        if src is None:
            break
        r = call("drag", i=src["i"], j=slot)
        if not r.get("ok"):
            # run 21: bridge 0.30.0 refused every drop and this loop printed 30 dumps of nothing
            print(f"!! drag refused: {r.get('error')}; stopping", file=sys.stderr)
            break
        dumped.append(src.get("card"))
        txlog("dumped", src.get("card"), "pack", "the trash can")  # run 49: the run's item ledger
        wait_until("frames", n=10, timeout=1500)  # the grid rebuilds after each drop
    # run 11: close.py reported the recycle window closed but it stayed open; the next bag.py
    # Shift+click sent the Cooler Box food (19 mushrooms, soybeans, a heart) into the recycler.
    # closetop, then check the top layer.
    for _ in range(4):
        if (call("state")["data"].get("layers") or {}).get("top") != "LayerDragGrid":
            break
        call("closetop")
        wait_until("frames", n=8, timeout=1000)
    run("close.py")
    print("dumped:", "; ".join(dumped) if dumped else "nothing")
    print(f"ecopos paid: {ecopos_paid(before, ecopo_log())} (from the log)")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    only_dump = bool(a) and a[0] == "dump"
    r = 80
    if a and a[0] == "sweep":
        r = int(a[1]) if len(a) > 1 and a[1].isdigit() else 80
        a = a[2:] if len(a) > 1 and a[1].isdigit() else a[1:]
    elif only_dump:
        a = a[1:]
    if not only_dump:
        sweep(r)
    dump(a)


if __name__ == "__main__":
    main()
