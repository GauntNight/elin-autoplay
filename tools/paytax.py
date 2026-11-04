"""Pay the oldest tax bill at home (G1's tax chest). The chest opens a drag grid (run 08: its old
"Deliver" menu entry is gone): take the bill from the mail post, stand beside the chest, Use it,
drag the bill onto the 'ing1' slot, close. Refuses when the gold doesn't cover the bill.

usage: python -I tools/paytax.py
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call, close as bridge_close  # noqa: E402

TOOLS = Path(__file__).resolve().parent
MAIL_POST, CHEST = "61,50", (62, 49)


from common import last, run  # noqa: E402


def amount(name):
    m = re.search(r"Of ([\d,]+) Orens", name)
    return int(m.group(1).replace(",", "")) if m else 0


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    held = [i["name"] for i in call("inv")["data"]["items"] if "Tax Bill" in i["name"]]
    bag = None
    if not held:
        # run 17: February's bill lay placed on the ground by the home board, and once grabbed it
        # went to the toolbelt and then the backpack, where neither `inv` nor the mail post sees
        # it. Look in the carried bags (the drag needs that bag's window open), then the ground.
        for b in ("backpack", "loot bag", "spoils bag"):
            if "Tax Bill" in run("bag.py", b):
                bag, held = b, [next(x.strip() for x in run("bag.py", b).split(":", 1)[-1].split(",") if "Tax Bill" in x)]
                break
            run("close.py")
    if not held:
        g = [h for h in call("find", name="Tax Bill", r=99, n=1)["data"]["hits"] if h["kind"] == "thing"]
        if g:
            from common import walk_beside
            walk_beside(g[0]["x"], g[0]["z"])
            p = call("state")["data"]["pc"]
            print(run("act.py", str(g[0]["x"] - p["x"]), str(g[0]["z"] - p["z"]), "Grab (", "right").strip()[-60:])
            return main()
    if not held:
        out = run("box.py", MAIL_POST)
        bills = re.findall(r"★Tax Bill Of [\d,]+ Orens", out)
        if not bills:
            print("no tax bill in the mail post, the bags or on the ground")
            return
        oldest = bills[-1]  # the post lists the newest first
        print(last(run("box.py", MAIL_POST, "--take", "Of " + oldest.split("Of ")[1])))
        held = [oldest]
    gold = call("state")["data"]["pc"]["gold"]
    if gold < amount(held[0]):
        sys.exit(f"not enough gold: {gold} for {held[0]} (the bill stays in the pack)")
    from common import walk, wait_until
    walk(CHEST[0], CHEST[1] - 1, r=0, hp=0, timeout=20000)
    if bag:
        run("bag.py", bag)  # its window stays open beside the chest's grid, so the drag sees the bill
    print(run("act.py", "find", "tax chest", "Use"))
    wait_until("layer", timeout=4000)  # the chest's drag grid opens
    btns = call("buttons", all=True)["data"]["buttons"]
    slot = next((b["i"] for b in btns if b["name"].startswith("ing1")), None)
    bill = next((b["i"] for b in btns if "inventory grid" in b["name"] and "Tax Bill" in (b.get("card") or "")), None)
    if slot is None or bill is None:
        run("close.py")
        sys.exit(f"tax chest grid not open or bill not listed (slot {slot}, bill {bill})")
    r = call("drag", i=bill, j=slot)
    time.sleep(1)
    run("close.py")
    after = call("state")["data"]["pc"]["gold"]
    print(f"paid {(r.get('data') or {}).get('dragged')}: gold {gold} -> {after}")


if __name__ == "__main__":
    main()
