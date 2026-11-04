"""Perform the act at a cell whose text starts with TEXT (case-insensitive), never by index:
a creature standing on the cell puts its own acts (Talk, Attack...) first (run 03: `do 0`
meant to read a letter opened Kaberg's dialog instead).

usage: python -I tools/act.py DX DZ TEXT [mode]     e.g. act.py -1 0 Read
       python -I tools/act.py find NAME TEXT [mode]  the nearest thing/object NAME, e.g.
                                                     act.py find package Open
mode: all (default) | left | key | right
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    if a[0] == "find":
        hits = call("find", name=a[1], r=999, n=1)["data"]["hits"]
        if not hits:
            sys.exit(f"no {a[1]!r} on the explored map")
        dx, dz, text, rest = hits[0]["dx"], hits[0]["dz"], a[2], a[3:]
    else:
        dx, dz, text, rest = int(a[0]), int(a[1]), a[2], a[3:]
    mode = rest[0] if rest else "all"
    acts = call("acts", dx=dx, dz=dz, mode=mode)["data"]["acts"]
    if not text.strip():  # an empty TEXT matched everything and fired the first act (run 05: a shrine)
        sys.exit(f"acts at ({dx},{dz}): " + " | ".join(x["text"] for x in acts))
    hit = [x for x in acts if x["text"].lower().startswith(text.lower())]
    if not hit:
        sys.exit(f"no act starting {text!r} at ({dx},{dz}): " + " | ".join(x["text"] for x in acts))
    r = call("do", i=hit[0]["i"])
    print(r["data"]["did"] if r.get("ok") else r.get("error"))


if __name__ == "__main__":
    main()
