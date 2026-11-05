"""Use an ability by its name from the ability window (Start Run 1): Rest, Pray. Opens the window, right-clicks the button with that
name in the same step as listing it, and closes the window, so nothing else can shift the list in between.

Rest at SP under about 20% falls asleep where you stand, with no bed (fact #1197); above that it only meditates and heals.
Pray once a day trains Faith (a new character's cheap skill: 100 raw exp, code: research of 2026-11-04).

usage: python -I tools/ability.py NAME        e.g. python -I tools/ability.py Rest
Exit 0 used, 1 refused (no such ability), 2 the bridge.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402


def use(name):
    """Right-click the ability called name. True when the bridge took the click."""
    def listed():
        return [b for b in call("buttons")["data"]["buttons"] if "ButtonAbility" in b.get("name", "") and b.get("card") == name]
    hits = listed()
    if not hits:
        call("act", action="MenuAbility")
        for _ in range(10):
            time.sleep(0.2)
            hits = listed()
            if hits:
                break
    if not hits:
        # run 15, Start Run 5: at times the injected Menu keys do nothing (all four at once, after a death); the hotbar's own "Ability" button opens the list
        for b in call("buttons", all=True)["data"]["buttons"]:
            if b.get("hot") == "HotItemLayer":
                tip = (call("hover", i=b["i"]).get("data") or {}).get("texts") or [""]
                if tip[0] == "Ability":
                    call("buttons", all=True)
                    call("click", i=b["i"])
                    for _ in range(10):
                        time.sleep(0.2)
                        hits = listed()
                        if hits:
                            break
                    break
    if not hits:
        return False
    rep = call("rclick", i=hits[0]["i"])
    if any("ButtonAbility" in b.get("name", "") for b in call("buttons")["data"]["buttons"]):
        call("act", action="MenuAbility")  # the window toggles shut
    return bool(rep.get("ok"))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    name = sys.argv[1]
    if not use(name):
        print(f"refused: no ability called {name!r} in the window")
        return 1
    print(f"used {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
