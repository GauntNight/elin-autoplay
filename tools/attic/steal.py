"""Take every item stack out of NPC containers, one stack at a time (run 06: the Thieves' Guild
test counts karma lost after accepting it; each stack taken from an NPC's container is -1 karma,
InvOwner.Transaction). Used in Derphy, which has no guards, on the user's decision.

usage: python -I tools/steal.py NAME [MAX_STACKS] [R]
  NAME        container name, e.g. "big crate", "stone chest" (nearest first)
  MAX_STACKS  stop after this many stacks taken (default 20)
Stops when the pack is full or a hostile is in view. Prints the karma lines it saw.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from box import transfer  # noqa: E402
from close import close_all  # noqa: E402
from unpack import act, contents, me, top, walk_beside  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    name = a[0]
    max_n = int(a[1]) if len(a) > 1 else 20
    r = int(a[2]) if len(a) > 2 else 60
    taken, karma, done = 0, 0, set()
    while taken < max_n:
        hits = [h for h in call("find", name=name, r=r, n=40)["data"]["hits"]
                if h.get("installed") and (h["x"], h["z"]) not in done]
        if not hits:
            print("no more containers")
            break
        h = min(hits, key=lambda h: h["dist"])
        done.add((h["x"], h["z"]))
        close_all(lambda *_: None)
        if not walk_beside(h["x"], h["z"]):
            continue
        time.sleep(0.5)
        if not act(h["x"], h["z"], "Open"):
            continue
        time.sleep(1.0)
        if top() != "LayerInventory":
            continue
        items = contents()
        print(f"{h['name']} {h['x']},{h['z']}: {len(items)} stacks")
        for it in items:
            if taken >= max_n:
                break
            nm = it.split(" ", 1)[1] if it.split(" ", 1)[0].isdigit() else it
            nm = nm.removeprefix("a ").removeprefix("an ")
            out = transfer(nm, True)
            if out.startswith("moved"):
                taken += 1
            elif "full" in out:
                print("pack full")
                close_all(lambda *_: None)
                print(f"taken {taken}")
                return
        close_all(lambda *_: None)
        log = call("state")["data"]["log"]
        karma += sum(1 for line in log[:30] if "Karma(-" in line)
    print(f"taken {taken} stacks")


if __name__ == "__main__":
    main()
