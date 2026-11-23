"""Count every home container by hand (G54 M0, the user 2026-11-08: "you may need to hand count the boxes and do a full
sweep to check inventory"): the bridge's stock op reports a ★Storage Chest as 96 slots whatever its wrenches (fact #1014),
but the open container window shows "USED / SIZE" (run 45: the yard chest 68,44 read 199 / 280). So this walks to each
installed container the stock op lists, opens it, reads that line, closes it, and writes one row per container with the
stock op's contents by kind.

usage: python -I tools/boxcount.py [--run NN] [--walk-all] [X,Z ...]
  Walks only the ★Storage Chests (the one kind whose window has the line); --walk-all opens every container (run 45's
  sweep: 72 opened, three locked: the practice chest, Fiama's quest chest, a boss chest at 65,40).
  writes runs/boxcount-NN.csv (x, z, name, used, size, by_stock_op, top contents) and prints the totals:
  containers, real slots, used, free; and the small ones (size 24 or less) with what they hold.
Every step runs farmday.home_guard first (run 41: a box walk with no stops ended in two deaths).
Exit 0 counted, 2 the bridge, 3 stopped (home_guard, a container that wouldn't open).
"""
import csv
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from close import close_all  # noqa: E402
from common import setup  # noqa: E402
import box  # noqa: E402
import farmday  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SIZE_RE = re.compile(r"^\s*(\d+) / (\d+)\s*$")  # the container window's count; "5/8" (no spaces) is something else


def window_size():
    texts = call("texts")["data"]
    texts = texts.get("texts") if isinstance(texts, dict) else texts
    hits = [SIZE_RE.match(str(t)) for t in texts or []]
    hits = [(int(m.group(1)), int(m.group(2))) for m in hits if m]
    return max(hits, key=lambda h: h[1]) if hits else None


def kinds(items):
    c = Counter()
    for it in items or []:
        n = re.sub(r"^(\d+|an?|the) ", "", it["name"])
        c[n] += 1
    return "; ".join(f"{k}" + (f" x{v}" if v > 1 else "") for k, v in c.most_common(6))


def main():
    if {"-h", "--help"} & set(sys.argv[1:]):  # run 58: --help read the boxes beside arrive.py (two bridge clients)
        print(__doc__)
        return
    setup()
    args = sys.argv[1:]
    run_no = args[args.index("--run") + 1] if "--run" in args else "xx"
    only = {tuple(map(int, a.split(","))) for a in args if re.fullmatch(r"\d+,\d+", a)}
    boxes = call("stock")["data"]["boxes"]
    if only:
        boxes = [b for b in boxes if (b["x"], b["z"]) in only]
    # run 45's first sweep opened all 72: only a ★Storage Chest's window shows "USED / SIZE" (43,51 92/160, 47,58 140/140,
    # 68,44 199/280); every other kind has no such line and its size is fixed by the kind (fact #1294), which the stock op
    # reads right. So only the Storage Chests are walked unless --walk-all; the rest take the op's slots and stack count.
    walk_all = "--walk-all" in args
    rows, failed = [], []
    for b in sorted(boxes, key=lambda b: (b["x"], b["z"])):
        size, src = None, "window"
        if walk_all or "Storage Chest" in b["name"]:
            farmday.home_guard("the box count")
            why = box.open_at(b["x"], b["z"])
            size = None if why else window_size()
            close_all(lambda *_: None)
            if why:
                failed.append((b["x"], b["z"], b["name"], why))
                print(f"  {b['x']},{b['z']} {b['name']}: won't open ({why})")
                continue
        if not size:
            if "Storage Chest" in b["name"]:
                failed.append((b["x"], b["z"], b["name"], "no 'N / M' line"))
                print(f"  {b['x']},{b['z']} {b['name']}: no size line")
                continue
            size, src = (b["count"], b["slots"]), "kind"
        used, cap = size
        rows.append({"x": b["x"], "z": b["z"], "name": b["name"], "used": used, "size": cap, "source": src,
                     "contents": kinds(b.get("items"))})
        print(f"  {b['x']},{b['z']} {b['name']}: {used} / {cap} ({src})" + (f" (stock op {b['slots']})" if cap != b["slots"] else ""))
    out = ROOT / "runs" / f"boxcount-{run_no}.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["x", "z", "name", "used", "size", "source", "contents"])
        w.writeheader()
        w.writerows(rows)
    size = sum(r["size"] for r in rows)
    used = sum(r["used"] for r in rows)
    print(f"{len(rows)} containers read ({len(failed)} not): {size} slots, {used} used, {size - used} free -> {out.name}")
    small = [r for r in rows if r["size"] <= 24]
    print(f"small (24 slots or less): {len(small)} containers, {sum(r['size'] for r in small)} slots, "
          f"{sum(r['used'] for r in small)} used")
    if failed:
        sys.exit(3)


if __name__ == "__main__":
    main()
