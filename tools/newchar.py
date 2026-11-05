"""Make a new character from the title screen and start the game (Start Run 1: the steps of elin-setup section 4 as one tool, each picked by name).

usage: python -I tools/newchar.py RACE CLASS [--name NAME]    e.g. Yerles Warrior
       python -I tools/newchar.py random random               a real random pick from the two lists
Leaves the game creating the world, about 80 seconds, on the Novice Adventurer law and no oaths: never Permadeath. A new game is always a new
local save (Game.Create takes the first free world_N and never touches another). Prints the world it took.
Exit 0 started, 1 refused (not at the title, no such race or class), 2 the bridge.
"""
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402

SAVE = Path.home() / "AppData" / "LocalLow" / "Lafrontier" / "Elin" / "Save"


def buttons():
    return call("buttons")["data"]["buttons"]


def click_text(text, starts=False):
    for b in buttons():
        t = b.get("text") or ""
        if (t.startswith(text) if starts else text in t):
            call("click", i=b["i"])
            time.sleep(0.6)
            return True
    return False


def pick_from_list(list_index, want):
    """Open the list button at this index of the maker and click the entry named want (or a random one)."""
    lists = [b for b in buttons() if b.get("name", "").startswith("ButtonSimple icon list") and b.get("tip") == "List"]
    call("click", i=(lists[list_index]["i"] if len(lists) > list_index else (10 if list_index == 2 else 11)))
    for _ in range(20):
        time.sleep(0.2)
        if (call("state")["data"].get("layers") or {}).get("top") == "LayerList":
            break
    rows = [b for b in buttons() if "ButtonGeneral" in b.get("name", "") and " | " in (b.get("text") or "")]
    names = [b["text"].split(" | ")[-1] for b in rows]
    if not rows:
        print("refused: the list didn't open")
        sys.exit(1)
    if want.lower() == "random":
        hit = random.choice(rows)
    else:
        found = [b for b in rows if b["text"].split(" | ")[-1].lower() == want.lower()]
        if not found:
            print(f"refused: no {want!r} in {names}")
            sys.exit(1)
        hit = found[0]
    call("click", i=hit["i"])
    time.sleep(0.6)
    return hit["text"].split(" | ")[-1]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        return 1
    before = {p.name for p in SAVE.glob("world_*")}
    for _ in range(40):  # the news pop-up comes first; one Cancel only: a second closes the title menu itself (Start Run 1)
        tops = [b.get("text") or "" for b in buttons()]
        if any("Create an adventurer" in t for t in tops) or (call("state")["data"].get("layers") or {}).get("top") == "LayerEditBio":
            break
        if (call("state")["data"].get("layers") or {}).get("top") == "LayerHelp":
            call("act", action="Cancel")
        time.sleep(1)
    if (call("state")["data"].get("layers") or {}).get("top") != "LayerEditBio" and not click_text("Create an adventurer"):
        print("refused: not at the title screen")
        return 1
    race = pick_from_list(4, args[0])  # the maker has six List buttons: the last two are race and class
    job = pick_from_list(5, args[1])
    bs = [b for b in buttons() if b.get("name", "").startswith("ButtonEmbark")]
    if not bs:
        print("refused: no Create button")
        return 1
    call("click", i=bs[0]["i"])
    time.sleep(1.2)
    bs = [b for b in buttons() if b.get("name", "").startswith("ButtonEmbark")]
    law = [b.get("text", "") for b in buttons() if b.get("toggle") or b.get("on") or b.get("checked") or "[x]" in (b.get("text") or "")]
    if not any("Novice" in t for t in law) or any("Permadeath" in t for t in law):
        print(f"refused: the law screen reads {law}")
        return 1
    call("click", i=bs[0]["i"])
    for _ in range(20):
        time.sleep(0.5)
        new = {p.name for p in SAVE.glob("world_*")} - before
        if new:
            break
    print(f"started: {race} {job} in {sorted(new)[0] if new else '?'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
