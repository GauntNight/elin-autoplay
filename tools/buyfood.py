"""Turn gold into food at an open or named shop in one step (Start Run 3: five inn visits of hand-reading tooltips in two hours): sell every old ticket, read each food's nutrition from
its tooltip, and buy by food per oren until the budget is gone. Meals earlyday.py doesn't know yet go in runs/foods.txt, one word a line, for it to eat.

usage: python -I tools/buyfood.py [--keep N] [--shop ROLE_ID]   stand by the shopkeeper (default merchant_inn); N orens are kept
Exit 0 done, 1 refused (no shopkeeper near).
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import data, run, setup  # noqa: E402

FOODS = Path(__file__).resolve().parent.parent / "runs" / "foods.txt"


def gold():
    return call("state")["data"]["pc"].get("gold") or 0


def grid():
    return [b for b in call("buttons")["data"]["buttons"] if "grid" in b.get("name", "") and b.get("card")]


def nutrition(b):
    call("hover", i=b["i"])
    time.sleep(0.08)
    for t in call("tip")["data"].get("texts") or []:
        m = re.match(r"Nutrition (\d+)", t)
        if m:
            return int(m.group(1))
    return 0


def price(b):
    acts = call("invacts", i=b["i"])["data"]["acts"]
    for a in acts:
        m = re.match(r"Buy 1\s+\(([\d,]+) orens?\)", a["text"])
        if m:
            return int(m.group(1).replace(",", "")), a["i"]
    return None, None


def main():
    setup()
    a = sys.argv[1:]
    keep = int(a[a.index("--keep") + 1]) if "--keep" in a else 0
    role = a[a.index("--shop") + 1] if "--shop" in a else "merchant_inn"
    who = [c for c in call("state")["data"].get("nearby") or [] if c.get("id") == role]
    if not who:
        print(f"refused: no {role} in view")
        return 1
    out = run("shop.py", who[0]["name"], "--keep-open", timeout=40)
    if "wares" not in out:
        print("refused: " + out[-100:])
        return 1
    for i in data("inv")["items"]:
        if "old ticket" in i["name"]:
            for _ in range(i.get("num") or 1):
                name = [x["name"] for x in data("inv")["items"] if "old ticket" in x["name"]]
                if name:
                    run("item.py", name[0], "Sell", timeout=15)
    print(f"gold after tickets: {gold()}")
    offers = []
    for b in grid():
        n = nutrition(b)
        card = b["card"]
        if not n or "rotten" in card or "bundle of" in card:  # Start Run 7: a raw crop tops the list at 2 food an oren, 8 a bundle by hand, but the loops' meals() leave "plant" uneaten: the money sat in the pack
            continue
        p, _ = price(b)
        if p:
            offers.append((n / p, n, p, card))
    offers.sort(reverse=True)
    words = set(FOODS.read_text(encoding="utf-8").split("\n")) if FOODS.exists() else set()
    bought = 0
    for ratio, n, p, card in offers:
        if ratio < 0.55:  # a stew at 119 for 63: not while bread exists
            continue
        base = re.sub(r"^(\d+|an?) ", "", card)
        while gold() - p >= keep:
            hit = [b for b in grid() if re.sub(r"^(\d+|an?) ", "", b["card"]) == base]
            if not hit:
                break
            q, k = price(hit[0])
            if q is None or gold() - q < keep:
                break
            before = gold()
            call("invdo", i=k)
            time.sleep(0.1)
            if gold() >= before:  # Start Run 3: a full pack refuses silently and this loop spun: stop, say so
                print(f"a purchase of {base} changed nothing: the pack is probably full ({len([i for i in data('inv')['items'] if not i.get('equipped')])} cards)")
                run("close.py", timeout=10)
                return 0
            bought += n
        words.add("on the bone" if "on the bone" in base else base.split()[-1].rstrip("s"))
    FOODS.write_text("\n".join(sorted(w for w in words if w)) + "\n", encoding="utf-8", newline="\n")
    run("close.py", timeout=10)
    print(f"bought {bought} food; {gold()} orens left; best: {[(round(r, 2), c[:22]) for r, _, _, c in offers[:4]]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
