"""Travel rations from home (G14; runs 15 and 16 did it by hand): grind grain at the millstone,
then make rations at the ration maker, both two-slot converters (TraitCrafter, numIng 2).

  millstone (the Kitchen):     2 bundles of wheat -> a sack of flour     (recipe 1)
                         2 bundles of rice plant -> a bag of rice  (recipe 2)
  ration maker (the Kitchen):  flour + a nut (api nut, crim, coffee bean) -> a travel ration  (22)
                         rice + a mushroom -> a travel ration                         (23)

Each converter opens a drag grid ("Grind"); a stack dragged onto ing1 and again onto ing2 fills
both slots when it holds 2 or more (TraitCrafter.IsCraftIngredient: `card == c && card.Num < 2`
is the only refusal), and the craft starts once every slot is filled (InvOwnerCraft.TryStartCraft).
The grain, flour, rice and nuts come from the harvest box first; what's left goes back.

usage: python -I tools/ration.py [--dry]
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, ready, refuse, run, setup, stop, top, wait_idle, walk  # noqa: E402
from home import BOX_STR, HARVEST_BOX, STATIONS  # noqa: E402
from packcheck import has_word, split_listing  # noqa: E402

MILL, MAKER = STATIONS["millstone"], STATIONS["ration maker"]
STAND = (59, 43)  # beside both (run 16; again since G56 M2, run 48: the millstone 58,44 and the maker 60,42)
GRAIN = ("bundle of wheat", "bundles of wheat", "bundle of rice plant", "bundles of rice plant",
         "sack of flour", "sacks of flour", "bag of rice", "bags of rice")
NUTS = ("api nut", "crim", "coffee bean")


def is_(card, *words):
    """A whole-word match with plurals (packcheck.has_word): "crim" no longer fits "crimson" (the
    review of 2026-10-23); "of wheat" still matches as a phrase."""
    return has_word(card, words)


def plain_mushroom(card):
    """Only the plain mushroom stacks (white and red ones are harmful foods, foods.md)."""
    c = card.lower()
    return bool(re.search(r"\bmushrooms?\b", c)) and not is_(c, "seed", "white", "red", "rare", "rotten")


def grid():
    bs = call("buttons", all=True)["data"]["buttons"]
    slots = {b["name"].split()[0]: b for b in bs if re.match(r"ing\d\b", b["name"])}
    pack = [b for b in bs if "ButtonGrid inventory" in b["name"] and b.get("card")]
    return slots, pack


def count(card):
    m = re.match(r"(\d+) ", card or "")
    return int(m.group(1)) if m else 1


def open_station(xy):
    if top():
        run("close.py")
    p = call("state")["data"]["pc"]
    acts = call("acts", dx=xy[0] - p["x"], dz=xy[1] - p["z"], mode="all")["data"]["acts"]
    hit = [a for a in acts if a["text"].startswith("Grind")]
    if not hit:
        refuse(f"no Grind act at {xy}: " + " | ".join(a["text"] for a in acts))
    call("do", i=hit[0]["i"])
    call("wait", until="layer", timeout=5000)
    if top() != "LayerDragGrid":
        refuse(f"the converter at {xy} did not open (top {top()})")


def convert(xy, first, second, label):
    """One craft: a stack matching `first` onto ing1, one matching `second` onto ing2."""
    open_station(xy)
    slots, pack = grid()
    a = [b for b in pack if first(b["card"])]
    if not a or "ing1" not in slots:
        run("close.py")
        return False
    if not call("drag", i=a[0]["i"], j=slots["ing1"]["i"]).get("ok"):
        run("close.py")  # run 21: a refused drag (bridge 0.30.0's guard) went unnoticed
        return False
    slots, pack = grid()  # the listing changed: list again before the second drag
    b = [x for x in pack if second(x["card"]) and (x["card"] != a[0]["card"] or count(x["card"]) >= 2)]
    if not b or "ing2" not in slots:
        run("close.py")
        return False
    before = {x["card"] for x in pack}
    if not call("drag", i=b[0]["i"], j=slots["ing2"]["i"]).get("ok"):
        run("close.py")
        return False
    wait_idle(timeout=30000)
    log = call("state")["data"].get("log") or []
    got = [ln for ln in log[-3:] if ln.startswith("You pick up")]
    print(f"  {label}: {a[0]['card']} + {b[0]['card']} -> {got[-1][12:] if got else '?'}")
    run("close.py")
    return True


def rations():
    import re as _re
    n = 0
    for b in call("buttons", all=True)["data"]["buttons"]:
        m = _re.match(r"(\d+ |an? )travel rations?$", (b.get("card") or "").strip())
        if m and "ButtonGrid inventory" in b["name"]:
            n += int(m.group(1)) if m.group(1)[0].isdigit() else 1
    return n


def pack_cards():
    return [i["name"] for i in call("inv")["data"]["items"]]


def main():
    setup()
    dry = "--dry" in sys.argv
    if "startSite" not in ((call("state")["data"].get("zone") or {}).get("full") or ""):
        refuse("not at home")
    why = ready(hp=None, hunger=None)  # a window, busy, a bad condition, a hostile in view
    if why:
        stop(why)
    # 1. the inputs from the harvest box
    names = split_listing(run("box.py", BOX_STR(HARVEST_BOX)))
    want = [n for n in names if is_(n, *GRAIN, *NUTS) or plain_mushroom(n)]
    if dry:
        print("harvest box: " + (", ".join(want) or "no grain, nuts or mushrooms"))
        print("pack: " + ", ".join(c for c in pack_cards() if is_(c, *GRAIN, *NUTS) or plain_mushroom(c)))
        return
    if want:
        print(run("box.py", BOX_STR(HARVEST_BOX), "--take", *want))
    r = walk(*STAND, r=0, hp=0)
    if r.get("why") not in ("arrived", None) and not r.get("done"):
        stop(f"couldn't reach the millstone: {r.get('why')}")
    made, start = 0, rations()
    # 2. grind: 2 wheat -> flour, 2 rice plants -> rice
    for kind, out in (("wheat", "flour"), ("rice plant", "rice")):
        for _ in range(20):
            if sum(count(c) for c in pack_cards() if is_(c, "of " + kind)) < 2:
                break
            if not convert(MILL, lambda c, k=kind: is_(c, "of " + k), lambda c, k=kind: is_(c, "of " + k), out):
                break
    # 3. rations: flour + nut, rice + mushroom
    for first, second in ((lambda c: is_(c, "of flour"), lambda c: is_(c, *NUTS)),
                          (lambda c: is_(c, "of rice") and not is_(c, "rice plant"), plain_mushroom)):
        for _ in range(20):
            if not convert(MAKER, first, second, "ration"):
                break
            made += 1
    # 4. what's left goes back (grain is never shipped: G14)
    back = [c for c in pack_cards() if is_(c, *GRAIN, *NUTS) or plain_mushroom(c)]
    if back:
        print(run("box.py", BOX_STR(HARVEST_BOX), *back))
    total = rations()
    # run 16: one convert() turns the whole stack (3 flour + 3 nuts -> 3 rations), so count rations
    print(f"rations made: {total - start} ({made} converter runs); travel rations carried: {total}")


if __name__ == "__main__":
    main()
