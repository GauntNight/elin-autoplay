"""Decode every ancient book in the pack for the Mages Guild (run 33, G34).

The code (TraitAncientbook, TraitBaseSpellbook): decoding a book as the PC pays the Mages Guild 5 + 2 x its tier (the
title's place in the list below) once; a deciphered copy refuses ("already decoded") and stacks. A read is
GetActDuration ticks (16 at Literacy 25), each a check: it fails when rnd(LER x (100 + Literacy x 10)/100 x 30) <
10 + 15 x tier. A failure spends a charge and either drains half the max mana, confuses, or (even at home) summons
1-3 read-fail monsters of the zone's danger. So: the highest tier first while charges last, never confused (the check
fails 3 in 4), and a stop on any hostile in view.

--fetch (run 40: my notes said three books waited; the boxes held ~40): take the undecoded books from the home's boxes,
as many as the free cards allow and no two of one name (item.py refuses a name that fits two), the fullest box first;
decode them, ship the deciphered copies so the cards come free again, and repeat until no box holds one. Never a
cursed book.

usage: python -I tools/decode.py [--dry] [--fetch]
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, data, ready, run, setup, stop, wait_idle  # noqa: E402

TIERS = ["Voynich Manuscript", "Dhol Chants", "Ponape Scripture", "Revelations of Glaaki", "G'harne Fragments",
         "Liber Damnatus", "Book of Dzyan", "Book of Eibon", "Grand Grimoire", "Celaeno Fragments", "Necronomicon",
         "The R'lyeh Text", "Eltdown Shards", "The Golden Bough", "Apocalypse"]
BOOK = re.compile(r'^an? (?:blessed )?ancient book titled "(.+)" \((\d+) Charges?\)$')


def books():
    """[(tier, name)] of the undecoded ancient books in the pack (bags included), highest tier first."""
    out = []
    for i in call("inv")["data"]["items"]:
        m = BOOK.match(i["name"])
        if m and "cursed" not in i["name"].lower():
            out.append((TIERS.index(m.group(1)) if m.group(1) in TIERS else 0, i["name"]))
    return sorted(out, reverse=True)


def deciphered(title):
    """How many deciphered copies of a title the pack holds (they stack: 'N deciphered ancient books titled ...')."""
    n = 0
    for i in call("inv")["data"]["items"]:
        if "deciphered" in i["name"] and f'"{title}"' in i["name"]:
            m = re.match(r"(\d+) ", i["name"])
            n += int(m.group(1)) if m else 1
    return n


def boxed():
    """{where: [(tier, name)]} the undecoded books lying directly in the home's boxes (bridge `stock`, never a cursed one)."""
    from stock import inventory
    out = {}
    for it in inventory()[1]:
        m = BOOK.match(it["name"])
        if m and it["where"] != "pack" and not it["bag"]:
            out.setdefault(it["where"], []).append((TIERS.index(m.group(1)) if m.group(1) in TIERS else 0, it["name"]))
    return out


def fetch():
    """Take one batch into the pack: the box with the most books, no two of one name. Returns how many it took."""
    from stock import free_cards
    rows = boxed()
    if not rows:
        return 0
    room = free_cards(data("stock")) - 1  # one card stays free: a stack changing windows needs it
    if room <= 0:
        stop("no free card to carry a book: bag a stack, then run again")
    where = max(rows, key=lambda w: len(rows[w]))
    names = list(dict.fromkeys(name for _, name in sorted(rows[where], reverse=True)))[:room]
    r = run("box.py", where, "--take", *names)
    print(r, flush=True)
    if r.rc != 0:
        stop(f"box.py {where} --take refused (rc {r.rc})")
    return len(names)


def ship_deciphered():
    """The decoded copies have no further use: they go to the shipping chest, so their cards come free."""
    names = [i["name"] for i in call("inv")["data"]["items"] if "deciphered ancient book" in i["name"]]
    for name in names:
        r = run("box.py", "shipping chest", name)
        print(r, flush=True)
        if r.rc != 0:
            # run 53: the chest takes 40 stacks a morning (fact #1001) and was full after a big unload, so the fetch stopped
            # after one book; a deciphered copy waits on the library route (64,46, the big Storage Chest, has room) instead
            import home
            for x, z in [home.LIBRARY[2]] + [b for b in home.LIBRARY if b != home.LIBRARY[2]]:
                r2 = run("box.py", f"{x},{z}", name)
                if r2.rc == 0:
                    print(f"  shipping chest full: {name} -> {x},{z} (ship it another morning)", flush=True)
                    break
            else:
                stop(f"box.py shipping chest refused (rc {r.rc}) and no library box took it: is everything full?")


def main(argv):
    from job import register  # run 58: bridge.call refuses a second acting client while this runs
    register("decode")
    setup()
    if "--fetch" in argv and "--dry" not in argv:
        total = 0
        while True:
            total += decode_pack()
            ship_deciphered()
            if not fetch():
                break
        print(f"fetch done: +{total} Mages Guild contribution; no undecoded book left in a box")
        return 0
    todo = books()
    for tier, name in todo:
        print(f"  tier {tier} (+{5 + 2 * tier}): {name}")
    if "--dry" in argv or not todo:
        print(f"{len(todo)} undecoded books in the pack")
        if "--fetch" in argv:
            for where, rows in boxed().items():
                print(f"  {where}: {len(rows)} books worth +{sum(5 + 2 * t for t, _ in rows)}")
        return 0
    print(f"done: +{decode_pack()} Mages Guild contribution")
    return 0


def decode_pack():
    """Decode every undecoded book in the pack; returns the contribution gained."""
    gained = tries = 0
    while True:
        todo = books()
        if not todo:
            break
        why = ready(hp=60, hunger=70)
        if why:
            stop(f"{why} (decoded +{gained} so far)")
        # run 33: a failure drains half the max mana; below that the overflow comes out of HP (199 -> 109 at MP 7)
        p = data("state")["pc"]
        if p["mp"] < p["maxMp"] // 2 + 5:
            stop(f"MP {p['mp']}/{p['maxMp']}: a failed read drains {p['maxMp'] // 2} and the overflow hurts; sleep or "
                 f"rest first (decoded +{gained} so far)")
        tier, name = todo[0]  # common.ready stops on ConConfuse (the check fails 3 in 4 while confused)
        title = BOOK.match(name).group(1)
        before = deciphered(title)
        tries += 1
        run("item.py", name, "Read")
        wait_idle(timeout=120000)
        log = " / ".join((data("state").get("log") or [])[-3:])
        if deciphered(title) > before:  # a failure renames the book too (one charge less), so count the decoded
            gained += 5 + 2 * tier
            print(f"decoded {title}: +{5 + 2 * tier} (total +{gained})", flush=True)
        else:
            print(f"failed {title}: {log}", flush=True)
    print(f"batch: +{gained} from {tries} reads", flush=True)
    return gained


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
