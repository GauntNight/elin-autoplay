"""Move a box that holds things (G12, run 18): a filled container can't be grabbed ("You can't put
that in your backpack!"), so empty it into a carried bag with the game's Shift+click (with the box
and the bag open, a box stack goes into the bag), grab the empty box, place it, open it there and
Shift+click the same stacks back. The box keeps its own name, sharing and priority settings.

usage: python -I tools/boxshift.py FX,FZ TX,TZ [--bag "loot bag"]
       python -I tools/boxshift.py FX,FZ TX,TZ --contents   only the contents, into the box already
              at TX,TZ, in trips that never pass Heavy Burden (run 18: a parts box of scrap and cans
              in one bag left me Squashed, 125 -> 101 HP); the emptied box stays where it was
The bag must have room for the box's stacks (the loot bag holds 35); stops (exit 3) if a stack
won't move, leaving everything where it is now (box, bag or pack) and saying so.
After a move, update tools/home.py and the elin-home table.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from close import close_all  # noqa: E402
from common import act, call, open_inventory, run, setup, stop, top, wait_until  # noqa: E402
from unpack import stand_beside  # noqa: E402


def grid(bs):
    return [b for b in bs if b.get("card") and "ButtonGrid inventory" in b["name"]]


def open_bag(bag):
    bs = open_inventory()
    mine = [b for b in bs if b.get("in") == "pack" and bag.lower() in (b.get("card") or "").lower()]
    if not mine:
        stop(f"no {bag!r} in the pack")
    # Shift+click goes to whichever other window is open: close every other carried container
    # (run 18: with the Cooler Box open, 2 mahogany planks went into it; bag.py learned the same in run 10)
    card = mine[0]["card"]
    done = set()
    while True:  # one at a time, listing again after each: a closed window renumbers the buttons
        bs = call("buttons", all=True)["data"]["buttons"]
        others = [b for b in bs if b.get("in") == "pack" and b.get("card") and b["card"] != card
                  and b["card"] not in done
                  and any(k in b["card"].lower() for k in ("box", "backpack", "bag", "trunk", "pouch", "purse"))]
        if not others:
            break
        done.add(others[0]["card"])
        other = {a["text"]: a["i"] for a in (call("invacts", i=others[0]["i"]).get("data") or {}).get("acts", [])}
        if "Close" in other:
            call("invdo", i=other["Close"])
            wait_until("frames", n=10, timeout=1500)
    for _ in range(3):  # run 18: right after a move the bag's slots weren't listed yet
        bs = call("buttons", all=True)["data"]["buttons"]
        mine = [b for b in bs if b.get("in") == "pack" and b.get("card") == card]
        acts = {a["text"]: a["i"] for a in (call("invacts", i=mine[0]["i"]).get("data") or {}).get("acts", [])}
        if "Open" in acts:
            call("invdo", i=acts["Open"])
            wait_until("frames", n=15, timeout=2000)
        if any(b.get("in") == mine[0]["card"] for b in call("buttons", all=True)["data"]["buttons"]):
            break
        wait_until("frames", n=30, timeout=2000)
    return mine[0]["card"]


def open_box(x, z):
    r = stand_beside(x, z)
    if not r:
        stop(f"can't reach the box at {x},{z}")
    opened = act(x, z, "Open")
    if not opened:
        stop(f"can't open the box at {x},{z}")
    if top() != "LayerInventory":
        wait_until("layer", timeout=4000)  # the container window opens
    return opened


HEAVY = ("Overweight", "Very Overweight", "Squashed")  # phase 3+: HP loss each turn (look.py)


def burden():
    """The burden label: pc.burdenText at phase 1+ (bridge 0.30.0), else the HUD's label (an
    older mod). "" when unburdened."""
    p = call("state")["data"].get("pc") or {}
    if p.get("burdenPhase") is not None:
        return (p.get("burdenText") or "").strip().rstrip("!") if p["burdenPhase"] >= 1 else ""
    hud = call("texts", all=True)["data"]["texts"]
    return next((t.strip().rstrip("!") for t in hud if t.strip().rstrip("!") in
                 ("Burden", "Heavy Burden") + HEAVY), "")


def heavy():
    """Phase 3+ (Overweight, Squashed): pc.burdenPhase, else the HUD label."""
    p = call("state")["data"].get("pc") or {}
    if p.get("burdenPhase") is not None:
        return p["burdenPhase"] >= 3
    return burden() in HEAVY


def shift_all(cards, src_of, dst_name, what, light=False):
    """Shift+click each stack whose container passes src_of, until none is left; returns the
    cards moved (a name twice for two stacks of it). `cards` is a Counter of names to move
    (None: everything)."""
    moved = []
    for _ in range(80):
        bs = call("buttons", all=True)["data"]["buttons"]
        src = [b for b in grid(bs) if src_of(b.get("in"))]
        left = [b for b in src if cards is None or moved.count(b["card"]) < cards.get(b["card"], 0)]
        if not left:
            # run 18: a grid mid-rebuild once listed none of a shelf's last 4 stacks; look again
            wait_until("frames", n=30, timeout=2000)
            bs = call("buttons", all=True)["data"]["buttons"]
            src = [b for b in grid(bs) if src_of(b.get("in"))]
            left = [b for b in src if cards is None or moved.count(b["card"]) < cards.get(b["card"], 0)]
        if not left:
            return moved
        b = left[0]
        n0 = sum(1 for a in src if a["card"] == b["card"])
        r = call("shiftclick", i=b["i"])
        wait_until("frames", n=10, timeout=1500)
        after = call("buttons", all=True)["data"]["buttons"]
        # judged by one stack of that name leaving the source: a box may hold several stacks with
        # one name ("a scrap" of two materials, run 18), and an empty target box has no slots to
        # name it by
        gone = sum(1 for a in grid(after) if src_of(a.get("in")) and a["card"] == b["card"]) < n0
        if not (r.get("ok") and r["data"].get("changed")) or not gone:
            stop(f"{what}: {b['card']} did not move into {dst_name} ({r.get('error') or r.get('data')});"
                 f" moved so far: {moved}")
        moved.append(b["card"])
        if light and heavy():  # put that one back and end the trip
            bs = call("buttons", all=True)["data"]["buttons"]
            back = [a for a in grid(bs) if a["card"] == b["card"] and not src_of(a.get("in"))
                    and a.get("in") not in ("pack",)]
            if back:
                call("shiftclick", i=back[0]["i"])
                wait_until("frames", n=10, timeout=1500)
            moved.pop()
            return moved
    stop(f"{what}: still stacks left after 80 moves")


def contents_only(fx, fz, tx, tz, bag):
    """Carry the stacks of the box at (fx, fz) into the box at (tx, tz), trip by trip."""
    total = []
    for trip in range(12):
        close_all(lambda *_: None)
        open_box(fx, fz)
        bagname = open_bag(bag)
        bs = call("buttons", all=True)["data"]["buttons"]
        boxname = next((b.get("in") for b in grid(bs) if b.get("in") not in ("pack", bagname)
                        and not b.get("mine")), None)
        if not boxname:
            print(f"the box at {fx},{fz} is empty: {len(total)} stacks moved in {trip} trips")
            close_all(lambda *_: None)
            return total
        moved = shift_all(None, lambda c: c == boxname, bagname, f"{fx},{fz} -> {bagname}", light=True)
        if not moved:
            stop(f"not one stack fits under Heavy Burden: {burden()}")
        close_all(lambda *_: None)
        open_box(tx, tz)
        open_bag(bag)
        back = shift_all(Counter(moved), lambda c: c == bagname, "the box", f"{bagname} -> {tx},{tz}")
        print(f"trip {trip + 1}: {len(back)} stacks: {', '.join(back)}")
        total += back
    stop("still stacks left after 12 trips")


def main(argv):
    setup()
    args = [a for a in argv if not a.startswith("--")]
    bag = argv[argv.index("--bag") + 1] if "--bag" in argv else "loot bag"
    if "--bag" in argv:
        args.remove(bag)
    (fx, fz), (tx, tz) = (tuple(int(v) for v in a.split(",")) for a in args[:2])
    if "--contents" in argv:
        contents_only(fx, fz, tx, tz, bag)
        return 0
    close_all(lambda *_: None)
    opened = open_box(fx, fz)
    bagname = open_bag(bag)
    bs = call("buttons", all=True)["data"]["buttons"]
    boxname = next((b.get("in") for b in grid(bs) if b.get("in") not in ("pack", bagname) and not b.get("mine")), None)
    moved = []
    if boxname:
        moved = shift_all(None, lambda c: c == boxname, bagname, f"{fx},{fz} -> {bagname}", light=True)
        bs = call("buttons", all=True)["data"]["buttons"]
        if any(b.get("in") == boxname for b in grid(bs)):
            # too heavy for one bag-load (run 18): put it all back and say so
            shift_all(Counter(moved), lambda c: c == bagname, boxname, f"{bagname} -> {fx},{fz}")
            close_all(lambda *_: None)
            stop(f"{fx},{fz} is too heavy to carry in one load ({len(moved)} stacks fit before {burden()}):"
                 " place an empty box at the target and use --contents")
    print(f"{opened}: {len(moved)} stacks into {bagname}: {', '.join(moved) or 'it was empty'}")
    close_all(lambda *_: None)
    out = run("move.py", f"{fx},{fz}", f"{tx},{tz}", timeout=600)
    print(out.strip())
    if out.rc != 0:
        stop(f"the box did not move; its {len(moved)} stacks are in {bagname}")
    if moved:
        open_box(tx, tz)
        open_bag(bag)
        back = shift_all(Counter(moved), lambda c: c == bagname, "the box", f"{bagname} -> {tx},{tz}")
        print(f"back into the box at {tx},{tz}: {len(back)} of {len(moved)} stacks")
        close_all(lambda *_: None)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
