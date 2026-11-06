"""Open a locked chest in the pack (run 42: treasure-map chests can come locked, "a cool mystic treasure chest" at lock 21; a locked chest lists as empty, and digmap.py and
chests.py --field took that for empty: one was dropped on a field with its contents inside). The game's Open starts a timed task, and the next command cancels it ("You give up
opening"), so each try waits for the task to end. A failed try costs no charge and no item without a lockpick; it can be tried again.

usage: python -I tools/unlock.py [NAME] [TRIES=8]    NAME: part of the chest's name (default: the first locked chest in the pack)
Exit 0 opened (or none locked), 1 refused (no such chest), 3 stopped (still locked after TRIES, a hostile, a window).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data, ready, refuse, run, setup, stop, wait_idle  # noqa: E402


def locked():
    return [i for i in data("inv")["items"] if "chest" in i["name"].lower() and "wrench" not in i["name"].lower() and i.get("lockLv")]


def main():
    setup()
    args = sys.argv[1:]
    nums = [int(a) for a in args if re.fullmatch(r"\d+", a)]
    words = [a for a in args if not re.fullmatch(r"\d+", a)]
    tries = nums[0] if nums else 8
    todo = locked()
    if words:
        todo = [i for i in todo if words[0].lower() in i["name"].lower()]
    if not todo:
        print("no locked chest in the pack")
        return 0
    name = todo[0]["name"]
    print(f"{name}: lock {todo[0]['lockLv']}")
    for n in range(1, tries + 1):
        why = ready(hunger=None, hp=50)
        if why:
            stop(f"not picking: {why}")
        out = run("item.py", name, "Open", timeout=60)
        if out.rc:
            refuse(f"item.py Open: {out}")
        wait_idle(timeout=60000)
        left = [i for i in locked() if i["name"] == name]
        print(f"  try {n}: lock {left[0]['lockLv'] if left else 0}")
        if not left:
            run("close.py", timeout=30)
            print(f"opened on try {n}")
            return 0
    stop(f"{name} still locked after {tries} tries")


if __name__ == "__main__":
    sys.exit(main())
