"""Recipes at a station that still pay the first-time craft bonus (old tickets, 114 orens each
in Mysilia, plus skill exp), and whether I can make each from what I have now. With --craft,
crafts every one I can, once (stops below an SP floor). It takes whatever a slot accepts: the new-game test
lost its only skin to a bait (a Body Parts slot), so list first and use craft.py by name when materials are scarce.

usage: python -I tools/firstcraft.py STATION [--craft] [--min-sp N]
  STATION: a station's name as find.py sees it (workbench, carpenter's table, tinker's table,
           bonfire, sawmill ...) or "quick" for Quick Craft.
Needs bridge 0.11.0+ (recipe buttons carry firstTime).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import refuse, top, wait_idle, wait_until  # noqa: E402

VERBS = ("Craft", "Saw", "Cook", "Smelt", "Process", "Carve", "Sew", "Tinker", "Blend", "Cut")  # run 15: the stonecutter


def buttons(all_=False):
    return call("buttons", all=all_)["data"]["buttons"]


def open_station(name):
    if name == "quick":
        ab = [b for b in buttons(True) if b.get("card") == "Quick Craft"]
        if not ab:
            call("act", action="MenuAbility")
            wait_until("layer", timeout=3000)
            ab = [b for b in buttons(True) if b.get("card") == "Quick Craft"]
        if not ab:  # the review of 2026-10-23: an IndexError when the ability panel didn't open
            refuse("no Quick Craft button: the ability panel did not open (craft.py quick knows the hotbar's own Ability button)")
        call("rclick", i=ab[0]["i"])
    else:
        h = call("find", name=name, r=999, n=1)["data"]["hits"]
        if not h:
            sys.exit(f"no {name} on the map")
        h = h[0]
        if h["dist"] > 1:
            # walk to a free neighbour of the station (stations stand in rows, so the cell
            # past its end is often another station, and goto onto a blocked cell stops short)
            free = [(ox, oz) for ox, oz in ((-1, 0), (1, 0), (0, 1), (0, -1))
                    if not call("cell", dx=h["dx"] + ox, dz=h["dz"] + oz)["data"].get("blocked")]
            if not free:
                sys.exit(f"no free cell beside the {name}")
            ox, oz = min(free, key=lambda o: abs(h["dx"] + o[0]) + abs(h["dz"] + o[1]))
            from common import walk
            w = walk(h["x"] + ox, h["z"] + oz, r=0, hp=0, timeout=20000)
            near = call("find", name=name, r=3, n=1)["data"]["hits"]
            if not near:  # run 15: an open window refused the walk and this raised IndexError
                sys.exit(f"didn't reach the {name}: {w.get('why')} {w.get('error') or ''}")
            h = near[0]
        acts = call("acts", dx=h["dx"], dz=h["dz"], mode="all")["data"]["acts"]
        cr = [a for a in acts if a["text"].startswith(VERBS)]
        if not cr:
            sys.exit("no craft act: " + ", ".join(a["text"] for a in acts))
        call("do", i=cr[0]["i"])
    if top() != "LayerCraft":
        wait_until("layer", timeout=5000)  # the craft window opens
    if top() != "LayerCraft":
        # run 15: a converter (sawmill, stonecutter) opens a drag grid, not a recipe list; it was
        # left open and blocked the next station's walk
        opened = top()
        if opened:
            call("closetop")
        sys.exit(f"craft window did not open (top {opened}: a converter has no first-time recipes)")


def num(text):
    m = re.search(r"\d+", re.sub(r"<[^>]+>", "", text or ""))
    return int(m.group()) if m else 0


def check(rec_i):
    """Select a recipe; return (ingredient lines, can_make)."""
    call("click", i=rec_i)
    wait_until("frames", n=10, timeout=1500)  # the recipe card and its slots are rebuilt
    lines, ok = [], True
    for b in buttons():
        if not b.get("ing"):
            continue
        name, _, req = b["ing"].rpartition(" x")
        need, have = int(req) if req.isdigit() else 1, num(b["text"])
        if "(Extra)" in (b.get("text") or ""):  # optional slot (a rune): never blocks the craft
            lines.append(f"{name} {have}/{need} optional")
            continue
        lines.append(f"{name} {have}/{need}")
        if have < need:
            ok = False
    return lines, ok


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    station = args[0]
    craft = "--craft" in sys.argv
    min_sp = int(sys.argv[sys.argv.index("--min-sp") + 1]) if "--min-sp" in sys.argv else 8
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    open_station(station)
    done = set()
    for _ in range(60):
        recs = [b for b in buttons() if "drag text" in b["name"] and b.get("firstTime") and b["card"] not in done]
        if not recs:
            break
        r = recs[0]
        done.add(r["card"])
        lines, ok = check(r["i"])
        mark = "CAN MAKE" if ok else "missing"
        print(f"{r['card']:28} {mark:8} | " + "; ".join(lines))
        if craft and ok:
            if call("state")["data"]["pc"]["sp"] < min_sp:
                print("  stop: SP floor")
                craft = False
                continue
            main_btn = [b for b in buttons() if b["name"] == "ButtonMain" and b["text"] == "Craft"]
            if main_btn:
                call("click", i=main_btn[0]["i"])
                wait_until("frames", n=20, timeout=3000)  # the crafter task starts
                wait_idle(timeout=30000)  # a craft takes game turns: wait for the crafter AI to end
                log = call("state")["data"].get("log") or []
                print("  -> " + " / ".join(l for l in log[-4:] if "craft" in l.lower() or "ticket" in l.lower()))
                if top() != "LayerCraft":  # some crafts close the window: reopen for the rest
                    open_station(station)
    if not done:
        print("no first-time recipes left here")
    call("closetop")


if __name__ == "__main__":
    main()
