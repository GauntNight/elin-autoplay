"""Nearest explored cells whose object (tree, plant, rock), thing (item, furniture, board)
or visible creature matches a name. One bridge call (`find` op, bridge 0.9.0+); older
bridges fall back to a cell-by-cell scan of objects only (slow beyond radius 15).

usage: python -I tools/find.py NAME [radius] [count]
       python -I tools/find.py --all [radius]      (a census of every object/thing kind)
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402


def search(name, r, n):
    rep = call("find", name=name, r=r, n=n)
    if not rep.get("ok"):
        sys.exit(rep.get("error"))
    return rep["data"]["hits"], rep["data"]["count"]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    name = sys.argv[1].lower()
    r = int(sys.argv[2]) if len(sys.argv) > 2 else (999 if name != "--all" else 12)
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    if name == "--all":
        hits, _ = search("", r, 100000)
        kinds = collections.Counter(f"{h['kind']:5} {h['name']}" for h in hits)
        for k, c in kinds.most_common():
            print(f"{c:3} {k}")
        return
    hits, count = search(name, r, n)
    for h in hits:
        tag = " inst" if h.get("installed") else ""
        print(f"({h['dx']:+d},{h['dz']:+d}) d{h['dist']} {h['kind']} {h['name']}{tag}")
    if not hits:
        print("none within", r)
    elif count > len(hits):
        print(f"... {count - len(hits)} more")


if __name__ == "__main__":
    main()
