"""Spend a feat point by name (run 41: every level gives one, and clicking through the sheet by hand costs real minutes in a Lv1 run).
Opens the sheet through the exp bar (fact #223), clicks the feat, answers Yes, closes.

usage: python -I tools/feat.py                 list what's on offer
       python -I tools/feat.py NAME [NAME ...]  buy the first one on offer, per point, in that order
Exit 0 done (or listed), 1 refused (no point or none of them on offer), 2 the bridge.
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402


def sheet():
    if not any("Feat Purchase" in b.get("name", "") for b in call("buttons")["data"]["buttons"]):
        hit = [b for b in call("buttons", all=True)["data"]["buttons"] if "WidgetExp" in (b.get("path") or "")]
        if not hit:
            return []
        call("click", i=hit[0]["i"])
        time.sleep(0.6)
    return [b for b in call("buttons")["data"]["buttons"] if "Feat Purchase" in b.get("name", "")]


def points():
    bs = call("buttons")["data"]["buttons"]
    m = [re.search(r"Acquire Feat \((\d+)\)", b.get("text") or "") for b in bs]
    return next((int(x.group(1)) for x in m if x), 0)


def close():
    for _ in range(3):
        if (call("state")["data"].get("layers") or {}).get("top") is None:
            return
        call("closetop")
        time.sleep(0.2)


def main():
    feats = sheet()
    names = sys.argv[1:]
    if not names:
        print(f"{points()} point(s): " + " | ".join(b["text"].split(" | ")[0] for b in feats))
        close()
        return 0
    bought = 0
    for want in names:
        while points():
            feats = sheet()
            hit = [b for b in feats if b["text"].split(" | ")[0].lower() == want.lower()]
            if not hit:
                break
            call("click", i=hit[0]["i"], expect=hit[0]["text"].split(" | ")[0])
            time.sleep(0.4)
            yes = [b for b in call("buttons")["data"]["buttons"] if (b.get("text") or "").endswith("Yes.")]
            if not yes:
                print(f"no Yes for {want}")
                break
            call("click", i=yes[0]["i"])
            time.sleep(0.5)
            print(f"bought {want}")
            bought += 1
            break
    close()
    if not bought:
        print("refused: no point, or none of those on offer")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
