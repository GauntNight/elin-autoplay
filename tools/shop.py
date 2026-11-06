"""List a shopkeeper's wares with their prices (run 21, G21 the towns tour: the stock was listed by
hand six times in one evening; every shop on the tour gets recorded).

usage: python -I tools/shop.py NAME [--record "WHERE" --run N] [--keep-open]
Talks to NAME (talkto.py), picks "Show me your wares", prints each stack with its "Buy" price, and
with --record adds the stock to the graph (kb.py add NAME "stock (DATE)" ...). The window is
closed at the end unless --keep-open (to buy with bridge invacts/invdo, elin-play's Buy row).
It also flags what the goals look for: alarm clocks, wall lamps and electronics (G18: always
steel), monster balls (G20), one-handed weapons (G19), skill books.
Exit 0 listed, 1 refused (no such shopkeeper or no wares), 2 bridge, 3 stopped (a window, busy).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import data, last, refuse, run, state, stop, wait_until  # noqa: E402

# run 21 (the user asked whether crystals beat steel: crystal is hardness 22): steel gear breaks into
# steel ore with the iron hammer (G18), obsidian (60) beats iron (56); gem materials make no ingots
WANTED = re.compile(r"alarm clock|wall lamp|pendant light|electronic|monitor|computer|monster ball|"
                    r"specialized book|scroll of return|travel ration|steel|obsidian", re.I)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    argv = sys.argv[1:]
    opt = {k: argv[argv.index(k) + 1] for k in ("--record", "--run") if k in argv and argv.index(k) + 1 < len(argv)}
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] not in opt)]
    if not args:
        refuse("usage: shop.py NAME [--record WHERE --run N] [--keep-open]")
    name = args[0]
    where = opt.get("--record")
    out = run("talkto.py", name, "1")
    if out.rc != 0:
        stop(f"talkto: {out[-200:]}") if out.rc == 3 else refuse(f"talkto: {out[-200:]}")
    bs = data("buttons").get("buttons") or []
    # run 40: a platinum merchant's choice reads "I want to trade platinum coins"
    wares = [b for b in bs if any(w in (b.get("text") or "") for w in ("Show me your wares", "trade platinum coins", "trade small medals"))]  # run 42: Miral
    if not wares:
        texts = " | ".join((b.get("text") or "")[:30] for b in bs if b.get("text"))
        # run 21: Odysammy's dialog was left open here and every walk after it was refused
        bye = [b for b in bs if (b.get("text") or "").startswith("Bye")]
        if bye:
            call("click", i=bye[0]["i"], expect="Bye")
        run("talk.py")
        refuse(f"{name} has no wares (asleep, or not a shop): " + texts)
    call("click", i=wares[0]["i"], expect=wares[0]["text"][:20])
    run("talk.py")
    wait_until("frames", n=30, timeout=3000)
    if (state().get("layers") or {}).get("top") != "LayerInventory":
        stop("the wares window didn't open")
    stock = []
    for b in data("buttons", all=True).get("buttons") or []:
        if not b.get("card") or b.get("mine") or "inventory grid" not in (b.get("name") or ""):
            continue
        acts = data("invacts", i=b["i"]).get("acts") or []
        buy = next((a["text"] for a in acts if a["text"].startswith("Buy 1")), "")
        # run 42: Nino's wagons and Miral's medal goods printed "?": gold bars and medals are prices too
        price = re.search(r"\(([\d,]+) (orens|small medals?|gold bars?|platinum coins?|ecopos?)\)", buy)
        stock.append((b["card"], ((price.group(1) + ("" if price.group(2) == "orens" else " " + price.group(2).split()[0])) if price else "?")))
    date = state()["pc"].get("date", "")
    print(f"{name}'s wares ({date}): {len(stock)} stacks")
    for card, price in stock:
        flag = "  <== goal" if WANTED.search(card) else ""
        print(f"  {price:>10}  {card}{flag}")
    if where:
        text = ", ".join(f"{c} {p}" for c, p in stock) or "nothing"
        r = run("kb.py", "add", name, f"stock ({date.split()[0]})", text, "--run", opt.get("--run", ""), "--where", where)
        print("  " + (last(r)[:160] or "(not recorded)"))
    if "--keep-open" not in sys.argv:
        run("close.py")


if __name__ == "__main__":
    main()
