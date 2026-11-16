"""Open a container, move named items into it (or out of it with --take), close it. With no
items, list what it holds. One process and one bridge connection: calling item.py from a
script that holds the bridge blocks it (the bridge serves one client at a time; run 04).

usage: python -I tools/box.py WHERE [--take] [ITEM ...]
  WHERE  X,Z of the container, or its name ("shipping chest", "shared sturdy box")
  ITEM   part of the item's name, e.g. "granite stone" "7 burnable" (one stack per ITEM)
  e.g.   python -I tools/box.py "shipping chest" "straw shirt" "empty bottle"
         python -I tools/box.py 53,53 --take "granite pickaxe"
Storage rule (Props.ListThingStack): at home a station draws ingredients from the pack and
every installed container on the map, at any distance, but one stack per recipe slot. So
keep each crafting material in a single stack, in one box.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from close import close_all  # noqa: E402
from common import _key, act, contents, pc, stack_hits, top, txlog, wait_idle, wait_until  # noqa: E402
from unpack import stand_beside  # noqa: E402


def qty(card):
    m = re.match(r"(\d+) ", card or "")
    return int(m.group(1)) if m else 1


def worn(b):
    """An equipped item's slot (WidgetEquip, the accessory list) is a ButtonGrid too: never move
    it (run 06: "Mica Necklace" moved the worn mica necklace into a shelf)."""
    return b.get("checked") or "WidgetEquip" in (b.get("path") or "") or "List ETC" in (b.get("path") or "")


def side_slots(name, take):
    """The stacks `name` means on the side they move from (pack, or the box with --take), by the
    shared matcher: an exact name first, so "a seed of tomato" no longer takes "a seed of tomato
    +6" (run 15: box.py's own word-start match took the first slot it found). Two different
    names at the winning level are refused."""
    cands = [b for b in call("buttons", all=True)["data"]["buttons"]
             if b.get("card") and "ButtonGrid inventory" in b["name"]
             and bool(b.get("mine")) != take and not worn(b)]
    hits, ambiguous = stack_hits(name, cands)
    if ambiguous:
        raise ValueError("fits " + " / ".join(sorted({b["card"] for b in hits})) + ": give the full name")
    return hits


def side_qty(card, take):
    """How many of exactly this stack's item are on the moving side (counted by the chosen
    stack's own name: once it has moved, `name` may fit other stacks, run 15)."""
    return sum(qty(b["card"]) for b in call("buttons", all=True)["data"]["buttons"]
               if b.get("card") and _key(b["card"]) == _key(card) and "ButtonGrid inventory" in b["name"]
               and bool(b.get("mine")) != take and not worn(b))


def magic_pages():
    """The ★Storage Chest's category tabs and page buttons ("Tool (20)", "2"): a paged magic chest shows one
    category page at a time, so a take sees only the visible page (run 28's lesson; run 30 found 130 items there)."""
    return [b for b in call("buttons", all=True)["data"]["buttons"] if b.get("name") == "ButtonUIMagicChestPage(Clone)"]


def find_in_pages(name):
    """Click through the magic chest's category tabs (and each one's pages) until `name` is on the page."""
    for tab in [b["text"] for b in magic_pages() if "(" in (b.get("text") or "")]:
        hit = [b for b in magic_pages() if b.get("text") == tab]
        if not hit:
            continue
        call("click", i=hit[0]["i"], expect=tab)
        wait_until("frames", n=8, timeout=1000)
        pages = sorted({b["text"] for b in magic_pages() if (b.get("text") or "").isdigit()}, key=int) or ["1"]
        for pg in pages:
            if pg != "1":
                hp = [b for b in magic_pages() if b.get("text") == pg]
                if not hp:
                    continue
                call("click", i=hp[0]["i"], expect=pg)
                wait_until("frames", n=8, timeout=1000)
            slots = side_slots(name, True)
            if slots:
                return slots
    return []


def transfer(name, take):
    try:
        slots = side_slots(name, take)
        if take and not slots and magic_pages():
            slots = find_in_pages(name)
    except ValueError as e:
        return f"!! refused: {e}"
    if not slots:
        return f"none {'in the box' if take else 'in the pack'}"
    before = side_qty(slots[0]["card"], take)
    acts = [a for a in call("invacts", i=slots[0]["i"])["data"]["acts"] if a["text"] == "Transfer"]
    if not acts:
        return "no Transfer offered"
    call("invdo", i=acts[0]["i"])
    wait_until("frames", n=8, timeout=1000)
    if side_qty(slots[0]["card"], take) == before:
        return "!! did not move: the box or the pack is probably full"
    if take:
        # run 31: 34 oak logs taken out left me Overweight (phase 3: "Your backpack is squashing you!", 216 -> 186 HP)
        # while the sawmill ran; burden phase 3+ costs HP (elin-play's status row), so such a take goes straight back
        phase = pc().get("burdenPhase") or 0
        if phase >= 3:
            back = side_slots(name, False)
            put = [a for a in call("invacts", i=back[0]["i"])["data"]["acts"] if a["text"] == "Transfer"] if back else []
            if put:
                call("invdo", i=put[0]["i"])
                wait_until("frames", n=8, timeout=1000)
            return f"!! put back: {slots[0]['card']} left me at burden phase {phase} (3+ costs HP): take part of it (Split)"
    return f"moved {slots[0]['card']}"


def open_at(x, z):
    """Walk beside the container at x,z and open its window. None when it's open, else why not
    (run 19: dishes.py opens the Dishes box this way to read and set its share lock)."""
    close_all(lambda *_: None)
    if top() is not None:
        return f"a window is still open ({top()}): close it first"
    if not stand_beside(x, z):
        return f"can't reach the container at {x},{z}"
    # Run 06: a stale position (still walking from an earlier goto) opened the shipping chest one
    # cell away, and a rod and a spellbook were shipped. walkto replies on arrival (the review of
    # 2026-10-23 dropped the 10 x 0.4 s stand-still poll); one short idle wait covers a task still
    # ending, then check that the act names the container on that cell.
    wait_idle(timeout=3000)
    p1 = pc()
    cell = call("cell", dx=x - p1["x"], dz=z - p1["z"])["data"]
    here = [str(t.get("name") if isinstance(t, dict) else t).lower() for t in cell.get("things") or []]
    here.append(str(cell.get("obj") or "").lower())
    opened = act(x, z, "Open")
    if not opened:
        return f"can't open the container at {x},{z}"
    m = re.search(r"\((.*)\)", opened)
    if m and not any(m.group(1).lower() in h for h in here):
        close_all(lambda *_: None)
        return f"opened {opened!r}, not the container at {x},{z} ({here}): stopped"
    if top() != "LayerInventory":
        wait_until("layer", timeout=4000)  # the container window opens
    if top() != "LayerInventory":
        return f"no container window (top {top()})"
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = [a for a in sys.argv[1:] if a not in ("--take", "--unidentified-ok")]
    take = "--take" in sys.argv
    where, items = args[0], args[1:]
    # run 21: 13 unidentified pieces shipped for 197 orens (a Godly shield brought 5; identified ☆
    # gear ships for 30-200+): an item still showing its quality class is identified first
    if "shipping" in where.lower() and not take and "--unidentified-ok" not in sys.argv:
        unknown = [it for it in items if re.search(r"\((Good|Great|Miracle|Godly|Excellent|Special)\)", it)]
        if unknown:
            sys.exit("refused: unidentified gear ships for almost nothing (fact #791): identify first, "
                     "or --unidentified-ok: " + " | ".join(unknown))
        # run 48: empty cans, a book pile, sacks and washing tubs went into the shipping chest by name, against the
        # user's run-08 rule (trash.py's docstring: shipping pays 0, the can pays Ecopo). The game's own category decides
        import items as carried
        inv = carried.inventory()
        # run 49: a ☆ junk piece (☆The Scrubber, a boss-chest regular) is no garbage: the trash can's grid doesn't take
        # it (trash.py dumped nothing), and packcheck has shipped it since run 30
        junk = [it for it in items for c in inv
                if c.get("kind", "").startswith("junk") and not c["name"].startswith("☆")
                and (str(c.get("uid")) == it[4:] if it.startswith("uid:") else it.lower() in c["name"].lower())]
        if junk:
            sys.exit("refused: garbage goes in the trash can, never the shipping chest (the user, run 08): "
                     "python -I tools/trash.py dump " + " ".join(f'"{j}"' for j in sorted(set(junk))))
    if re.fullmatch(r"\d+,\d+", where):
        x, z = map(int, where.split(","))
    else:
        h = call("find", name=where, r=999, n=1)["data"]["hits"]
        if not h:
            sys.exit(f"no {where!r} on the map")
        x, z = h[0]["x"], h[0]["z"]
    if not take:
        # run 46: `box.py "shipping chest" uid:N` printed "none in the pack" for six things in the bags and exited 0,
        # so seq.py ran on; a uid in a bag is brought into the pack's own grid first (items.to_pack)
        for it in items:
            if it.startswith("uid:"):
                import items as carried
                inv = carried.inventory()
                hit = [c for c in inv if str(c.get("uid")) == it[4:]]
                if hit and carried.container_of(hit[0], inv) is not None:
                    ok, why = carried.to_pack(hit[0], inv)
                    if not ok:
                        sys.exit(f"{it}: could not bring it out of {carried.where(hit[0], inv)}: {why}")
    why = open_at(x, z)
    if why:
        sys.exit(why)
    if not items:
        print(f"{x},{z}: " + (", ".join(contents()) or "empty"))
    failed = 0
    for it in items:
        res = transfer(it, take)
        print(f"{it}: {res}")
        if res.startswith("moved"):  # run 49: the run's item ledger (common.txlog)
            box = f"{where} ({x},{z})" if where != f"{x},{z}" else where
            txlog("took" if take else "boxed", res[6:], box if take else "pack", "pack" if take else box)
        failed += not res.startswith("moved")
    close_all(lambda *_: None)
    if failed:
        # run 46: a run of "none in the pack" lines exited 0 and a seq.py chain went on as if they had moved
        sys.exit(f"{failed} of {len(items)} not moved")


if __name__ == "__main__":
    main()
