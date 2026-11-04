"""Use an item that opens a picker grid (identify, enchant, blend, uncurse...) on a target item, and
put the target back on if it was worn: the game's picker takes a worn item off (run 07: the club came
off in a blend and I fought a drone bare-handed; the breastplate came off in an enchant).

usage: python -I tools/picker.py ITEM ACTION TARGET
  e.g. python -I tools/picker.py "scroll of identify" Read "Paper Decorative Ring"
       python -I tools/picker.py "acidproof liquid" Blend "Rigid Hand Axe"
       python -I tools/picker.py "rod of identify" Zap "stone bejeweled amulet"   (a rod is held, then zapped)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call, close  # noqa: E402

TOOLS = Path(__file__).resolve().parent


from common import last, matches, wait_until  # noqa: E402
from common import run as tool  # noqa: E402


def worn(target):
    """True / False for the target's worn state, None when it is neither in the pack nor worn
    (in process: `inv`; the review of 2026-10-23 found the bridge.py subprocess back here)."""
    items = call("inv")["data"]["items"]
    hits = matches(target, items, key="name")
    if not hits:
        return None
    return any(i.get("equipped") for i in hits)


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    item, action, target = sys.argv[1:4]
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    was_worn = worn(target)
    if was_worn is None:
        sys.exit(f"no {target!r} in the pack or worn")
    # run 40: three plain scrolls of enchant weapon read on an axe at +3 only "resisted" and were used up. The code (ActEffect): the
    # cap is 2, great 4, +1 when blessed. A piece at its cap is refused before the read
    if "enchant" in item.lower() and "--force" not in sys.argv:
        cap = (4 if "great" in item.lower() else 2) + (1 if "blessed" in item.lower() else 0)
        stock = call("stock", r=0)["data"].get("pack") or []
        names = [i["name"] for i in stock] + [s["name"] for i in stock for s in i.get("items") or []]
        now = [n for n in names if target.lower() in n.lower()]
        m = re.search(r" \+(\d+)", now[0]) if now else None
        if m and int(m.group(1)) >= cap:
            sys.exit(f"refused: {now[0]} is at +{m.group(1)}: {item} caps at +{cap}; it would resist and be used up (--force)")
    log0 = call("state")["data"].get("log") or []
    if action.lower() == "zap":
        print(last(tool("item.py", item, "Grab")))
        acts = call("acts", dx=0, dz=0, mode="right")["data"]["acts"]
        zap = [a for a in acts if a["text"].startswith("Zap")]
        if not zap:
            sys.exit("no Zap act with the rod held")
        call("do", i=zap[0]["i"])
    else:
        print(last(tool("item.py", item, action)))
    wait_until("layer", timeout=4000)  # the picker grid opens
    btns = call("buttons", all=True)["data"]["buttons"]
    slot = next((b["i"] for b in btns if b["name"].startswith("ing1")), None)
    hits = matches(target, [b for b in btns if "inventory" in b["name"] and b.get("card")])
    src = hits[0]["i"] if hits else None
    if slot is None or src is None:
        tool("close.py")
        sys.exit(f"picker not open or {target!r} not listed (slot {slot}, item {src})")
    r = call("drag", i=src, j=slot)
    print("dragged:", (r.get("data") or {}).get("dragged"), r.get("error") or "")
    wait_until("frames", n=30, timeout=3000)  # the effect lands and the log line is written
    tool("close.py")
    if action.lower() == "zap":
        tool("hotbar.py", "--deselect")
    log = call("state")["data"].get("log") or []
    print("log:", " / ".join(log[-3:]))
    if was_worn and not worn(target):
        # the target may have been renamed by identification: equip by the new name if it changed
        # run 22: log[-4:] still held the last scroll's "is identified as ☆The Tough Light Cloak", so
        # an enchanted Mass Hand Axe was "re-equipped" as the cloak and two nefias went by without it:
        # only the lines this action wrote count
        new = log[len(log0):] if log[:len(log0)] == log0 else [l for l in log if l not in log0]
        name = target
        for l in new:
            m = re.search(r"is identified as (.+?)\.$", l)
            if m:
                name = m.group(1)
        print("re-equip:", last(tool("item.py", name, "Equip")))
        again = worn(name)
        print("worn again:", again)
        if not again:
            sys.exit(f"!! {name!r} is off: equip it by hand (item.py NAME Equip) before going on")


if __name__ == "__main__":
    main()
