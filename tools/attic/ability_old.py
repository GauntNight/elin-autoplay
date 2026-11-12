"""Use an ability by name (Rest, Quick Craft, Pray, spells...), the way a right-click on
its button in the ability panel does. Opens the panel if it's closed. With --wait, waits
until the player's AI is idle again (resting, sleeping) and prints the result.

usage: python -I tools/ability.py NAME [--wait]
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402


def ability_buttons(name):
    bs = call("buttons", all=True)["data"]["buttons"]
    return [b for b in bs if b.get("card", "").lower() == name.lower() and "ButtonAbility" in b["name"]]


def main():
    name = sys.argv[1]
    wait = "--wait" in sys.argv
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    top = (call("state")["data"].get("layers") or {}).get("top")
    if top:
        sys.exit(f"a window or dialog is open ({top}): close it first")
    b = ability_buttons(name)
    if not b:
        call("act", action="MenuAbility")
        time.sleep(1.2)
        b = ability_buttons(name)
    if not b:  # the panel remembers its last tab (Atk/Def/...): show All and look again (run 04)
        tab = [x for x in call("buttons", all=True)["data"]["buttons"] if "ButtonTab" in x["name"] and x.get("text") == "All"]
        if tab:
            call("click", i=tab[0]["i"])
            time.sleep(0.6)
            b = ability_buttons(name)
    if not b:
        sys.exit(f"no ability named {name!r} in the panel")
    r = call("rclick", i=b[0]["i"])
    if not r.get("ok"):
        sys.exit(r.get("error"))
    print("used", name)
    if not wait:
        return
    for _ in range(120):
        time.sleep(3)
        s = call("state")["data"]
        p = s["pc"]
        busy = "ConSleep" in p["conditions"] or (p["ai"] or "").split(":")[0] not in ("NoGoal", "GoalEndTurn")
        if (s.get("layers") or {}).get("top") or not busy:
            break
    s = call("state")["data"]
    p = s["pc"]
    print(f"done: {p['date']}  HP {p['hp']}/{p['maxHp']}  SP {p['sp']}/{p['maxSp']}  hunger {p['hunger']}"
          f"  top {(s.get('layers') or {}).get('top')}")
    print("log:", " / ".join((s.get("log") or [])[-4:]))


if __name__ == "__main__":
    main()
