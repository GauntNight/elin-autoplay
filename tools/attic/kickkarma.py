"""Lower karma for the Thieves' Guild test (run 06, the user's decision): kick friendly
townsfolk. Card.Kick costs -1 karma when the target's hostility is Friend or above and it isn't my
faction, whatever my own karma is; it only pushes them (no damage). Rogues, punks and gangsters
are Neutral (bridge 0.17.0 `hostility`, run 07) and cost nothing, and rogues pick your pocket.
Only kicks Friend+ characters at or below MAX_LV, and stops if anything turns hostile.

usage: python -I tools/kickkarma.py [TARGET=-100] [MAX_LV=12] [MAX_KICKS=150]
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402


def progress():
    """'Accumulate Karma: N of -100' from the message log (the journal's own counter)."""
    for line in call("texts", all=True)["data"]["texts"]:
        m = re.search(r"Accumulate Karma: (-?\d+) of (-?\d+)", line)
        if m:
            return int(m.group(1))
    return None


def main():
    a = [int(x) for x in sys.argv[1:] if x.lstrip("-").isdigit()]
    target = a[0] if a else -100
    max_lv = a[1] if len(a) > 1 else 12
    max_kicks = a[2] if len(a) > 2 else 150
    kicks, karma_lines, skip = 0, 0, {}
    while kicks < max_kicks:
        s = call("state")["data"]
        if any(c["hostile"] for c in s.get("nearby") or []):
            print("stop: a hostile in view")
            break
        named = [c for c in s.get("nearby") or [] if not c["hostile"] and not c["party"]
                 and c.get("hostility") in ("Friend", "Ally")
                 and c["lv"] <= max_lv and skip.get(c["uid"], 0) < 3]
        if not named:
            print("no friendly townsfolk in view; walk somewhere busier")
            break
        c = min(named, key=lambda c: c["dist"])
        if c["dist"] > 1:
            from common import walk
            walk(s["pc"]["x"] + c["dx"], s["pc"]["z"] + c["dz"], r=0, hp=0, timeout=10000)
            continue
        acts = call("acts", dx=c["dx"], dz=c["dz"], mode="all")["data"]["acts"]
        kick = [x for x in acts if x["text"].startswith("Kick")]
        if not kick:
            skip[c["uid"]] = skip.get(c["uid"], 0) + 1
            continue
        before = progress()
        call("do", i=kick[0]["i"])
        time.sleep(0.8)
        kicks += 1
        # The journal's own counter decides (run 07: the log is oldest-first, so reading its
        # head for "Karma(-1)" saw nothing and skipped targets that did count).
        now = progress()
        if before is None or now is None or now >= before:
            skip[c["uid"]] = skip.get(c["uid"], 0) + 1  # no karma from this one
        else:
            karma_lines += before - now
        if kicks % 10 == 0:
            print(f"kicks {kicks}, karma -{karma_lines}, test at {now}")
        if now is not None and now <= target:
            break
    print(f"done: kicks {kicks}, karma -{karma_lines}, test at {progress()}")


if __name__ == "__main__":
    main()
