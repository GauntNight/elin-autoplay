"""Sell the stolen goods at a black market (run 33: done by hand at Minwer and Siyun with a scratch loop).
steal.py appends every stolen item's name to runs/stolen.txt; this opens the fence's wares (shop.py
--keep-open), sells each listed stack with its "Sell N" act, closes the shop (the Thieves Guild books the
contribution when the window closes: elin-play) and prints the guild line from the journal. Only Derphy
(Siyun), Port Kapul (Minwer) and my own land buy stolen goods below rank 4 (G27's notes).

usage: python -I tools/fence.py SHOPKEEPER [--dry]
Exit 0, 1 refused (nothing listed, the shopkeeper not in view), 3 stopped (a window).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, data, last, refuse, run, stop  # noqa: E402

STOLEN = Path(__file__).resolve().parent.parent / "runs" / "stolen.txt"


def listed():
    return [ln.strip() for ln in STOLEN.read_text(encoding="utf-8").splitlines() if ln.strip()] if STOLEN.exists() else []


def base(name):
    """'2 tapestries' and 'a tapestry' share a base: the count and article dropped, a trailing s tolerated."""
    w = name.lower().split()
    if w and (w[0].isdigit() or w[0] in ("a", "an")):
        w = w[1:]
    return " ".join(w).rstrip("s")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        refuse("usage: fence.py SHOPKEEPER")
    names = listed()
    if not names:
        refuse("runs/stolen.txt lists nothing: steal.py records what it takes")
    if "--dry" in sys.argv:
        print("\n".join(names))
        return
    # run 43: purge's unclutter and a full grid put thefts in the bags, and the shop's list shows only the pack: 15 of 27 "not sold"
    wanted = {base(n) for n in names}
    for bag in data("stock", r=0)["pack"]:
        hits = [x["name"] for x in bag.get("items") or [] if base(x["name"]) in wanted]
        if hits:
            run("bag.py", bag["name"], "--take", *hits[:8])
            run("close.py")
    out = run("shop.py", args[0], "--keep-open", timeout=300)
    if out.rc != 0:
        refuse(f"shop.py: {last(out) or out.rc}")
    sold, left = [], []
    gold0 = data("state")["pc"].get("gold")
    for name in names:
        bs = call("buttons", all=True)["data"]["buttons"]
        hit = [b for b in bs if "inventory grid" in (b.get("name") or "") and b.get("mine") is not False
               and base(b.get("card") or "") == base(name)]
        if not hit:
            left.append(name)
            continue
        acts = call("invacts", i=hit[0]["i"]).get("data", {}).get("acts", [])
        sells = [a for a in acts if a["text"].startswith("Sell")]
        if not sells:
            left.append(name)
            continue
        a = sells[-1]  # "Sell N" for the whole stack
        call("invdo", i=a["i"])
        sold.append(f"{name} ({a['text']})")
    run("close.py")
    run("talk.py")
    STOLEN.write_text("\n".join(left) + ("\n" if left else ""), encoding="utf-8")
    # run 43: 14 "sold" with the gold, the guild total and the pack unchanged: a sale counts only when the purse moved
    if sold and data("state")["pc"].get("gold") == gold0:
        STOLEN.write_text("\n".join(left + [s.split(" (Sell")[0] for s in sold]) + "\n", encoding="utf-8")
        stop(f"{len(sold)} Sell acts and the gold didn't move: the shopkeeper asleep or out of money? Nothing sold")
    print(f"sold {len(sold)}: " + "; ".join(sold))
    if left:
        print(f"not sold (not in the pack grid? bagged?): {', '.join(left)}")
    if sold:
        print([ln for ln in run("journal.py", "guilds").splitlines() if "Thieves" in ln][-1:] or "")


if __name__ == "__main__":
    main()
