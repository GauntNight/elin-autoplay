"""Put every identified ☆ piece in the bags beside what I wear in that slot, before anything ships (run 40, the user: "how often
do you look at current equipment versus new?"). The answer was: by hand, by name, and not every batch: 14 pieces shipped on
the names alone that day, and the copper ring's Lightning weakness was last weighed in run 29. elin-pack has said "equip what beats
worn gear" since run 08; nothing made it happen.

It prints each piece's lines beside the worn one's and records the pieces it showed in runs/jobs/gearcheck.txt: shipstar.py ships
only recorded pieces. Deciding stays mine: this reads, it never equips. Armor numbers can't settle it alone: read the lines.

usage: python -I tools/gearcheck.py [SLOT ...]     SLOT: ring neck head body hand foot back waist weapon (default: all)
Exit 0 done (also with nothing to compare), 1 refused.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data, run, setup  # noqa: E402
from job import JOBS  # noqa: E402

RECORD = JOBS / "gearcheck.txt"
SLOTS = [("ring", r"\bring\b"), ("neck", r"\b(necklace|amulet|neck guard|pendant)\b"),
         ("head", r"\b(helm|hat|bucket|crown|cap|mask)\b"), ("body", r"\b(breastplate|robe|mail|armor|shirt|cuirass|dress)\b"),
         ("hand", r"\b(gloves|gauntlets)\b"), ("foot", r"\b(boots|shoes|sandals)\b"), ("back", r"\b(cloak|cape|mantle)\b"),
         ("waist", r"\b(girdle|belt)\b"), ("shield", r"\bshield\b"),
         ("weapon", r"\b(axe|sword|spear|scimitar|claymore|dagger|mace|staff|bow|crossbow|gun|shotgun|rifle|claw|halberd|scythe|mallet|club|whip|katana)\b")]
SKIP_LINE = re.compile(r"^(It is made|It is categorized|It uses|It can be equipped|Total |An? [a-z])")


def slot_of(name):
    n = re.sub(r"『.*?』|《.*?》", "", name).lower()
    return next((slot for slot, rx in SLOTS if re.search(rx, n)), None)


def lines_of(name):
    out = run("item.py", name, "info", timeout=60)
    return [ln.strip() for ln in str(out).splitlines() if ln.strip() and not SKIP_LINE.match(ln.strip())][:16]


def main():
    setup()
    want = set(sys.argv[1:])
    pack = data("stock").get("pack") or []
    worn = {}
    for i in pack:
        if i.get("equipped") and slot_of(i["name"]):
            worn.setdefault(slot_of(i["name"]), []).append(i["name"])
    shown = []
    # the pack's own grid too: a ring taken from a box and two ☆ guns rode there unread (PACK_KEEP keeps guns out of the bags)
    for i in pack:
        if not i.get("equipped") and i.get("items") is None and i["name"].startswith("☆") and (not want or slot_of(i["name"]) in want):
            print(f"\n== {slot_of(i['name'])}: {i['name']}")
            for ln in lines_of(i["name"]):
                print(f"   {ln}")
            shown.append(i["name"])
    for bag in pack:
        if bag.get("items") is None or "cooler" in bag["name"].lower() or "toolbelt" in bag["name"].lower():
            continue
        pieces = [s["name"] for s in bag["items"] if s["name"].startswith("☆") and (not want or slot_of(s["name"]) in want)]
        if not pieces:
            continue
        run("close.py", timeout=60)
        run("item.py", bag["name"], "Open", timeout=60)
        for name in pieces:
            slot = slot_of(name)
            print(f"\n== {slot}: {name}")
            for ln in lines_of(name):
                print(f"   {ln}")
            shown.append(name)
        run("close.py", timeout=60)
    print("\n-- worn --")
    for slot, names in worn.items():
        if want and slot not in want:
            continue
        for name in names:
            print(f"== {slot}: {name}")
            for ln in lines_of(name):
                print(f"   {ln}")
    done = set(RECORD.read_text(encoding="utf-8").splitlines()) if RECORD.exists() else set()
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text("\n".join(sorted(done | set(shown))) + "\n", encoding="utf-8")
    print(f"\n{len(shown)} pieces shown and recorded: shipstar.py may ship them")
    return 0


if __name__ == "__main__":
    sys.exit(main())
