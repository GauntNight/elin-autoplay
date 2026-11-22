"""The keep rules for home storage, by kind (G70 Smart Storage M2, run 57): one table that the clear-out (clearout.py) and
the home routine read, instead of word lists in each tool.

**The user (2026-11-21): the keep rule is "sell unless used"**, and to the audit's calls (knowledge/storage-audit.md): "Approve
the list mostly. But sell the cards and figures. They just increase tourist value - unless they have another purpose?" (they
have none: the game tags them 'tourism', no recipe takes one).

verdict(item) reads a bridge `stock` op row (name, id, uid, num) and the game's own category (things.json; never a word in the
name for the kind, elin-play's rule since runs 47-50; names only split a kind's states: learned, deciphered, spam, cursed) and
returns (CALL, why), CALL one of:
  keep      stays where it is (the kit, currency, materials, food, maps, undecoded books, medals)
  caps      stock.py's caps decide (spellbooks, rods, scrolls, potions): unchanged by G70
  sell      to a shopkeeper (sell.py; ☆ gear may ship instead, after gearcheck.py)
  trash     the trash can: none yet (run 57: it refused learned recipes, which Samata buys; garbage is trash.py's)
  read      read it here (unlearned recipes: readrecipes.py; skill books)
  identify  unidentified: Aliyun first, then its kind decides (never sold unread: the user's rule)
  gear      sell, but only after gearcheck.py has read it against the worn piece (the user, run 40)

usage: python -I tools/keep.py            the verdict for every stack in the home's containers, counted by call and theme
       python -I tools/keep.py --list CALL every stack with that call, with its place
Exit 0.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "knowledge" / "game"
_T = {}

# Categories (things.json 'category') by call. A category not named here is "keep" (the safe default: nothing sells by
# accident); the audit's themes, approved by the user 2026-11-21, decide each line.
SELL_CATS = {"card", "figure",                       # the user: "sell the cards and figures"
             "booze", "junk", "souvenir",            # nothing uses them
             "deco", "mount", "light", "table", "window", "_furniture", "util", "mech",  # furniture not placed
             "dna"}                                  # genes: the crew is out of feat points (gene.py plan)
GEAR_ROOTS = {"armor", "weapon"}                     # gearcheck first
CAP_CATS = {"spellbook", "rod", "scroll", "potion"}  # stock.py
KEEP_CATS = {"currency", "map", "seed", "ore", "stone", "wood", "textile", "bodyparts", "_resource", "flora",
             "lightsource", "_tool", "container", "_item", "_block", "ext"}  # ext: scraps for the Blacksmith (craftrun)
FOOD_ROOTS = {"food"}
# Ammo: the bow's iron arrows stay; every other ammo sells (the audit: 15 kinds, 12,147 rounds)
AMMO_KEEP = {"arrow"}  # the id of iron/plain arrows; makeshift and other kinds sell
# Drinks: potions are the caps' business; plain drinks (tea, liquid, milk) sell
DRINK_KEEP_IDS = set()


def _table(name):
    if name not in _T:
        _T[name] = json.loads((GAME / f"{name}.json").read_text(encoding="utf-8"))
    return _T[name]


def _things():
    if "things_by_id" not in _T:
        _T["things_by_id"] = {t["id"]: t for t in _table("things")}
    return _T["things_by_id"]


def _root(cat):
    cats = {c["id"]: c for c in _table("categories")}
    seen = set()
    while cat in cats and cats[cat].get("_parent") and cat not in seen:
        seen.add(cat)
        cat = cats[cat]["_parent"]
    return cat


def category(it):
    row = _things().get(it.get("id") or "")
    cat = (row or {}).get("category") or ""
    return cat, _root(cat) if cat else ""


def verdict(it):
    name, tid = it.get("name") or "", it.get("id") or ""
    cat, root = category(it)
    if tid == "unidentified" or re.search(r"\((Good|Great|Miracle|Godly|Excellent|Special)\)$", name):
        return "identify", "unidentified: Aliyun first"
    # run 57: the clear-out sold ★Cassette Tape No.109 (furniture/mech) for 3 orens: a ★ thing is unique or a quest's,
    # and the keep list names quest items (★). The statue of Creator (core_user) never sold at the chest either (run 42)
    if name.lstrip().startswith("★") or tid == "core_user":
        return "keep", "★ (unique or a quest's) or the statue of Creator"
    if name.startswith("cursed ") or " cursed " in name:
        return "keep", "cursed: never sold or worn unread (uncurse first)"
    if tid == "rp_random":
        # run 57: the trash can refused them ("this move isn't valid") and Samata paid 36-40 a stack; the chest pays 0 (run 42)
        return ("sell", "a learned recipe's copy (a shop pays, the chest doesn't)") if "(Learned" in name else ("read", "an unlearned recipe")
    if tid == "letter" and "[spam]" in name:
        return "sell", "spam mail (the trash can takes garbage only)"
    if tid == "book_ancient":
        if "deciphered" in name:
            return "sell", "a deciphered copy (decode.py has used it)"
        return "keep", "undecoded: G63's decodes"
    if cat == "ancientbook":
        return "sell", "a naughty book (no decode)"
    if cat == "skillbook":
        return "read", "a skill book"
    if cat in CAP_CATS or cat.startswith("potion"):
        return "caps", "stock.py's caps"
    if cat == "ammo":
        # the material is a state of the kind, not the kind: 'arrow' covers iron, grass, mica and wooden arrows
        if tid in AMMO_KEEP and name.split(" ", 1)[-1].startswith("iron "):
            return "keep", "the bow's iron arrows"
        # run 57: ☆The Dreadbane Crossbow (undead bane [*****+]) rides for the crypt and Azrasizzle: its iron quarrels stay
        if tid == "quarrel" and name.split(" ", 1)[-1].startswith("iron "):
            return "keep", "the undead-bane crossbow's iron quarrels"
        return "sell", "ammo the bow doesn't use"
    if root in GEAR_ROOTS:
        return "gear", f"{cat}: gearcheck.py first"
    if cat in SELL_CATS:
        return "sell", f"{cat}: no use (G70)"
    if root == "book" or cat == "_book":
        return "sell", "a book: read once, no use"
    if cat == "milk":
        return "keep", "milk: cooking"
    if root == "drink":
        if cat == "_drink" and "potion" not in name:
            return "sell", "a plain drink"
        return "caps", "a potion: stock.py's caps"
    if root in FOOD_ROOTS:
        return "keep", "food: meals and cookdishes (the surplus is a count, not a kind)"
    if cat in KEEP_CATS or root in ("resource", "currency"):
        return "keep", f"{cat or root}: used (one working stack a kind)"
    return "keep", f"no rule for {cat or tid} (kept until one is written)"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from common import data, setup
    setup()
    want = sys.argv[sys.argv.index("--list") + 1] if "--list" in sys.argv else None
    s = data("stock")
    calls, themes = Counter(), Counter()
    for box in s["boxes"]:
        if not box.get("installed"):
            continue
        for it in box.get("items") or []:
            c, why = verdict(it)
            calls[c] += 1
            themes[(c, category(it)[0])] += 1
            if want == c:
                print(f"  {box['x']},{box['z']} {box['name']}: {it['name']} [{it.get('id')}] - {why}")
    print("calls: " + ", ".join(f"{k} {v}" for k, v in calls.most_common()))
    if not want:
        for (c, cat), n in themes.most_common(40):
            print(f"  {c:8} {cat:14} {n}")


if __name__ == "__main__":
    main()
