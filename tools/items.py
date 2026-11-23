"""What the player carries, by what each thing is rather than what it is called (the review of 2026-11-11).

50 of the 241 recorded errors were a name that matched the wrong thing or a bag nobody looked in: a starvation
death beside "roasted" food that the word "roasts" missed (run 18), 22 meals in the Cooler Box that matched no
word (run 41), evacuation scrolls "not found" in the spoils bag three times (runs 40, 41, 44), my own fireproof
blanket sold as a stolen one (run 44), a carried antibody dropped as excess (run 44). Every tool that sorted
items had its own word list and its own idea of which bags to open.

The bridge's `items` op (0.40.0) lists every carried thing at any depth with its category, trait, reference
element (which scroll, rod, potion or book), the creature a food is made of, blessed state, charges, lock, weight,
rot, stolen flag, what can be done with it, and its container chain. Unidentified things read id "unidentified"
and carry no ref or bless (honest play). This module is the one reader of it:

    inventory()                 every carried thing (dicts), read once per call; kind() is on each as "kind"
    kind(it)                    "meal", "ration", "prepared", "raw", "milk", "scroll:SpEvac", "rod:SpTeleport",
                                "potion:SpHealCritical", "book:SpHero", "blanket", "lockpick", "container", ...
    find(kind=, id=, ref=, pred=, usable=True, items=None)
                                the matching things; usable drops cursed, rotten, 0-charge, unidentified and
                                anything inside a locked container
    count(...)                  find()'s total: charges for rods and charged tools, else the stack sizes
    meals(hunger, items=None)   what may be eaten now, best first (the rules are in the function)
    container_of(it, items)     the container an item sits in, or None for the pack itself
    where(it, items)            "pack", or "a loot bag > a pouch"
    reach(it, items)            open the containers so its slot is on screen (item.py / bag.py take `uid:N`)
    use(it, verb, items)        reach() then `item.py uid:N VERB`; returns the tool's output with .rc
    to_pack(it, items)          move it out of its bag into the pack's own grid (shops and boxes show only that)
    protected(it, items)        why a tool that drops, ships, sells or stores must leave this alone, or None
                                (kit=False for a tool that enforces the stock caps on the kit itself)

usage: python -I tools/items.py            a summary by kind
       python -I tools/items.py KIND       the things of one kind ("meal", "scroll:SpEvac", "rod", "container")
       python -I tools/items.py --meals    what eat.py would eat now, in order
       python -I tools/items.py --protected  what the drop/ship/sell tools must leave alone, and why
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data, run  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "knowledge" / "game"
CARRY = ROOT / "runs" / "carry.txt"

# trait class -> the kind's prefix; the reference element completes it ("scroll:SpEvac")
REF_KINDS = {"TraitScrollRandom": "scroll", "TraitScroll": "scroll", "TraitRodRandom": "rod", "TraitRod": "rod",
             "TraitPotionRandom": "potion", "TraitPotion": "potion", "TraitSpellbookRandom": "book",
             "TraitSpellbook": "book"}
TRAIT_KINDS = {"TraitFoodTravel": "ration", "TraitBlanketFireproof": "blanket", "TraitLockpick": "lockpick",
               "TraitScrollMapTreasure": "map", "TraitAncientbook": "ancientbook", "TraitCurrency": "currency",
               "TraitCurrencyMedal": "medal", "TraitLightSource": "light", "TraitToolBelt": "toolbelt"}
RAW_CATS = ("fruit", "vegi", "mushroom", "nuts", "grain")       # eaten raw when nothing better is carried
NEVER_RAW = ("meat", "egg", "fish")                             # corpses, a cat's egg (karma), raw carp (foods.md)
GEAR_CATS = ("torso", "head", "back", "waist", "arm", "foot", "finger", "ring", "neck", "amulet", "shield", "sword",
             "dagger", "blunt", "staff", "axe", "polearm", "scythe", "martial", "bow", "crossbow", "gun", "cane",
             "throw", "toolbelt", "lightsource")
RATION_RESERVE = 5  # run 44: travel rations kept back for Fast Travel fares; the rest are food

# The kit by kind: what leaves the pack only by my own hand (elin-pack). A tool that drops, ships, sells or stores
# asks protected() first. Kept here, keyed by what a thing is; packcheck's word lists stay until they are folded in.
KIT_KINDS = ("scroll:SpEvac", "scroll:SpReturn", "scroll:SpTeleport", "scroll:SpTeleportShort", "rod:SpTeleport",
             "rod:SpTeleportShort", "rod:SpHealCritical", "rod:SpHealHeavy", "rod:SpHealLight",
             "potion:SpHealCritical", "potion:SpHealHeavy", "potion:SpHealLight", "potion:SpHOT",
             "ration", "blanket", "lockpick", "light", "toolbelt")

_tables = {}


def _table(name):
    if name not in _tables:
        p = GAME / f"{name}.json"
        _tables[name] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    return _tables[name]


def _flesh(ref_card):
    """'human' or 'cat' when a food's creature is one (insanity; karma -5: foods.md, run 05, run 44), else None.
    An unknown creature id counts as human: never eaten by a loop."""
    if not ref_card:
        return None
    if "charas" not in _tables:
        _tables["charas"] = {c["id"]: c.get("race") for c in _table("charas")}
        _tables["races"] = {r["id"]: r.get("tag") or [] for r in _table("races")}
    if ref_card not in _tables["charas"]:
        things = {t["id"] for t in _table("things")}
        return None if ref_card in things else "human"  # an ingredient (sesame), not a creature
    tags = _tables["races"].get(_tables["charas"][ref_card]) or []
    return "human" if "human" in tags else "cat" if "cat" in tags else None


def kind(it):
    trait, cat = it.get("trait") or "", it.get("cat") or ""
    if trait in REF_KINDS:
        return REF_KINDS[trait] + (":" + it["ref"] if it.get("ref") else "")
    if trait in TRAIT_KINDS:
        return TRAIT_KINDS[trait]
    if it.get("container"):
        return "container"
    if cat.startswith("meal"):
        return "meal"
    if cat == "preserved":
        return "prepared"
    if cat == "milk":
        return "milk"
    if cat in RAW_CATS or cat in NEVER_RAW:
        return "raw"
    if cat in GEAR_CATS:
        return "gear"
    return cat or None


def inventory():
    its = data("items")["items"]
    for it in its:
        it["kind"] = kind(it)
    return its


def _by_uid(items):
    return {i["uid"]: i for i in items}


def container_of(it, items):
    return _by_uid(items).get(it.get("parent")) if it.get("parent") else None


def where(it, items):
    by = _by_uid(items)
    return " > ".join(by[u]["name"] for u in it.get("path") or [] if u in by) or "pack"


def usable(it):
    """False for what can't be used as it is: unidentified, cursed or doomed, rotten, a charged thing at 0."""
    if not it.get("identified", True) or (it.get("bless") or 0) < 0 or it.get("rotten"):
        return False
    k = it.get("kind") or kind(it) or ""
    if (k.startswith("rod") or k in ("blanket", "lockpick")) and not it.get("charges"):
        return False
    return True


def find(kind=None, id=None, ref=None, pred=None, usable_only=True, items=None):  # noqa: A002
    """The carried things that match. kind: exact ("scroll:SpEvac") or a prefix before the colon ("rod")."""
    out = []
    for it in items if items is not None else inventory():
        k = it.get("kind") or ""
        if kind is not None and k != kind and k.split(":")[0] != kind:
            continue
        if id is not None and it.get("id") != id:
            continue
        if ref is not None and it.get("ref") != ref:
            continue
        if usable_only and not usable(it):
            continue
        if pred is not None and not pred(it):
            continue
        out.append(it)
    return out


def count(*a, **kw):
    """find()'s total: the charges of rods and charged tools, the stack sizes of everything else."""
    n = 0
    for it in find(*a, **kw):
        k = it.get("kind") or ""
        n += (it.get("charges") or 0) if k.startswith("rod") or k in ("blanket", "lockpick") else (it.get("num") or 1)
    return n


def meals(hunger=0, items=None):
    """What a loop may eat now, best first. The rules, each from a recorded error:
      - only what the game offers Eat on (milk: Drink), in a food category: gear made of a food material has a
        gear category and never shows (run 34, the user: "Raw Food Weapons/Armor are not things to eat");
      - never rotten, cursed or unidentified; never raw meat, eggs or fish (corpses; a cat's egg, karma -5; raw
        carp); never a meal made of a human or a cat (run 44: a Public performer's meat, insanity);
      - a travel ration only at hunger 80+ or above the Fast Travel reserve (runs 28, 29, 44);
      - anywhere carried, at any depth (runs 30, 32, 39: food in the loot bag was never looked at), except
        inside a locked container;
      - cooked meals first, then prepared food, then raw fruit and vegetables, then milk, then rations; within a
        group the Cooler Box first (it is where food keeps), then the pack, then the bags."""
    items = items if items is not None else inventory()
    by = _by_uid(items)
    rations = sum(i.get("num") or 1 for i in items if i.get("kind") == "ration")
    order = {"meal": 0, "prepared": 1, "raw": 2, "milk": 3, "ration": 4}
    out = []
    for it in items:
        k = it.get("kind")
        if k not in order or it.get("equipped") or not usable(it):
            continue
        can = it.get("can") or []
        if "eat" not in can and not (k == "milk" and "drink" in can):
            continue
        if k == "raw" and (it.get("cat") or "") in NEVER_RAW:
            continue
        if _flesh(it.get("refCard")):
            continue
        if k == "ration" and hunger < 80 and rations <= RATION_RESERVE:
            continue
        chain = [by.get(u) or {} for u in it.get("path") or []]
        if any(c.get("locked") for c in chain):
            continue
        place = 0 if any(c.get("trait") == "TraitCoolerBox" for c in chain) else 1 if not chain else 2
        out.append((order[k], place, len(chain), it))
    return [it for *_, it in sorted(out, key=lambda t: t[:3])]


def reach(it, items=None):
    """Open what has to be open for the item's slot to be on screen. An item in the pack needs nothing; one in a
    carried bag needs that bag open; one deeper is taken up a level at a time (bag.py --take), so it ends in the
    bag that sits in the pack. Returns (True, "") or (False, why)."""
    items = items if items is not None else inventory()
    path = list(it.get("path") or [])
    while len(path) > 1:  # bring the inner container out into the pack
        out = run("bag.py", f"uid:{path[0]}", "--take", f"uid:{path[1]}", timeout=120)
        if out.rc:
            return False, f"couldn't take the container out of {where(it, items)}: {(out.splitlines() or [''])[-1][:100]}"
        path = path[1:]
    if path:
        out = run("bag.py", f"uid:{path[0]}", timeout=120)
        if out.rc:
            return False, f"couldn't open {where(it, items)}: {(out.splitlines() or [''])[-1][:100]}"
    return True, ""


def to_pack(it, items=None):
    """Move a thing out of its bag into the pack's own grid (a shop's sell list and a box's quick move show only
    that grid). Returns (True, "") or (False, why); a thing already there is True."""
    items = items if items is not None else inventory()
    if not it.get("path"):
        return True, ""
    ok, why = reach(it, items)
    if not ok:
        return False, why
    top = (it.get("path") or [None])[-1]
    out = run("bag.py", f"uid:{top}", "--take", f"uid:{it['uid']}", timeout=120)
    run("close.py", timeout=30)
    return (out.rc == 0), ("" if out.rc == 0 else (out.splitlines() or [""])[-1][:120])


def use(it, verb, items=None, *flags):
    ok, why = reach(it, items)
    if not ok:
        out = type(run("close.py", timeout=30))(why)
        out.rc = 1
        return out
    return run("item.py", f"uid:{it['uid']}", verb, *flags, timeout=120)


def carry_list():
    """runs/carry.txt: the errand items (one per line; '#' comments). A line is a kind ("potion:SpCureCorruption"),
    an id ("id:lockpick"), a uid ("uid:123456") or, as before, words that must all be in the name."""
    out = []
    if CARRY.exists():
        out = [ln.strip() for ln in CARRY.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    # run 50: what a ladder gather job is collecting (runs/jobs/gather.txt 'OBJECT ITEM TARGET') is carried on purpose;
    # purge dropped the 22-24 tufts of grass on four floors in a row (runs/tx/items.log), and the job cut them again each floor
    jobs = CARRY.parent / "jobs" / "gather.txt"
    if jobs.exists():
        for ln in jobs.read_text(encoding="utf-8").splitlines():
            parts = ln.split()
            if len(parts) >= 3 and not ln.lstrip().startswith("#"):
                out.append(" ".join(parts[1:-1]))
    return out


RANGED_CATS = ("bow", "crossbow", "gun", "sling")
_DICE = re.compile(r"\((\d+)d(\d+)([+-]\d+)?")


def best_ranged(items):
    """The carried ranged weapon with the highest average damage (dice and bonus from its name), or None."""
    def avg(i):
        m = _DICE.search(i.get("name") or "")
        return int(m.group(1)) * (int(m.group(2)) + 1) / 2 + int(m.group(3) or 0) if m else 0
    cands = [i for i in items if (i.get("cat") or "") in RANGED_CATS and i.get("identified", True)]
    return max(cands, key=avg) if cands else None


def protected(it, items=None, carry=None, kit=True):
    """Why a tool that drops, ships, sells or stores must leave this thing alone, or None. One gate for purge,
    packcheck, trash, fence, shipstar and stock (the review of 2026-11-11: each had its own word list, and the
    gaps were a worn torch bagged, the woodcutter's axe dropped, my own blanket fenced, the antibody purged)."""
    k = it.get("kind") or kind(it) or ""
    if it.get("equipped"):
        return "worn"
    if not it.get("identified", True):
        return "unidentified (identify first: Aliyun, a scroll, the spell)"
    if kit and k in KIT_KINDS and usable(it):  # kit=False: a tool that enforces the stock caps on the kit itself
        return f"kit ({k})"
    # run 57: a sell loop over keep.py's "gear" sold ☆The Luminescent Long Bow (2d12+14, the wish's bow and the one in use)
    # to Moyer for 366 orens: the ranged weapon was neither worn nor on the carry list. The best carried ranged weapon by its
    # average damage is kit, whatever tool asks
    if kit and (it.get("cat") or "") in RANGED_CATS:
        best = best_ranged(items if items is not None else inventory())
        if best and best.get("uid") == it.get("uid"):
            return "kit (the ranged weapon in use: the best carried)"
    # the user, run 58: "All tools (Shovel, Axe, etc) should be palced in the 'hot bar' area ... so they are never lost/removed
    # again": a carried tool is kit whatever tool asks (the game's category _tool, the lockpick's id), one of each kind on the hotbar
    if kit and (it.get("cat") == "_tool" or it.get("id") == "lockpick") and (it.get("bless") or 0) >= 0:
        return "kit (a tool: the hotbar, run 58)"
    # run 58: a sale list held ★Putit In Amber (the thrown opener), unprotected since it left the kit kinds: ★ things stay
    if kit and it["name"].startswith("\u2605") and (it.get("cat") or "") in GEAR_CATS + ("ranged", "weapon"):
        return "kit (a \u2605 piece)"
    if it.get("container") and (it.get("count") or it.get("locked")):
        return "a container that isn't empty" + (" (locked: unread)" if it.get("locked") else "")
    name = (it.get("name") or "").lower()
    for line in carry if carry is not None else carry_list():
        low = line.lower()
        hit = (low == k.lower() or low == f"id:{it.get('id')}".lower() or low == f"uid:{it.get('uid')}"
               or (":" not in low and all(w in name for w in low.split())))
        if hit:
            return f"on the carry list ({line})"
    return None


def main():
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    its = inventory()
    args = sys.argv[1:]
    if "--meals" in args:
        hunger = (data("state").get("pc") or {}).get("hunger", 0)
        ms = meals(hunger, its)
        print(f"hunger {hunger}: {len(ms)} things to eat, in order")
        for it in ms:
            print(f"  {it['name']}  [{it['kind']}, {where(it, its)}]")
        return
    if "--protected" in args:
        for it in its:
            why = protected(it, its)
            if why:
                print(f"  {it['name']}  [{where(it, its)}]: {why}")
        return
    if args:
        hits = find(args[0], usable_only=False, items=its)
        for it in hits:
            flags = [w for w, on in (("cursed", (it.get("bless") or 0) < 0), ("blessed", (it.get("bless") or 0) > 0),
                                     ("rotten", it.get("rotten")), ("stolen", it.get("stolen")),
                                     ("unidentified", not it.get("identified", True)), ("locked", it.get("locked"))) if on]
            print(f"  {it['name']}  [{it['kind']}, {where(it, its)}" + (", " + ", ".join(flags) if flags else "") + "]")
        print(f"{len(hits)} stacks, {count(args[0], items=its)} usable (charges for rods)")
        return
    kinds = {}
    for it in its:
        kinds.setdefault(it["kind"] or "?", []).append(it)
    for k in sorted(kinds):
        print(f"  {k}: {len(kinds[k])} stacks, {sum(i.get('num') or 1 for i in kinds[k])} things")
    print(f"{len(its)} stacks carried, {sum(1 for i in its if i.get('container'))} containers")


if __name__ == "__main__":
    main()
