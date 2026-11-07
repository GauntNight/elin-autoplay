"""Have a mage identify everything in the pack and bags in one step (run 43: done by hand on each pass of Tinker's Camp since run 08: a talk, three clicks, a Bye). Reads the price from the dialog and stops over MAX. Godly pieces aren't covered: the mage's artifact service does those, one at a time, and only when the slot can beat what's worn (elin-pack 3).

usage: python -I tools/identifyall.py [NAME=Aliyun] [MAX=1500]   stand near NAME (at Tinker's Camp: bridge.py walkto 60 55)
Exit 0 done (or nothing to identify), 1 refused (not in view, no such service), 3 a dialog that didn't read as expected.
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, data, last, refuse, run, setup, state, stop  # noqa: E402


def click(text):
    for b in data("buttons")["buttons"]:
        if text in (b.get("text") or ""):
            r = call("click", i=b["i"], expect=text)
            time.sleep(0.3)
            return bool(r.get("ok"))
    return False


def bye():
    click("Bye")
    run("talk.py", timeout=60)


def main():
    setup()
    args = sys.argv[1:]
    name = args[0] if args else "Aliyun"
    most = int(args[1]) if len(args) > 1 else 1500
    out = run("talkto.py", name, timeout=120)
    if out.rc:
        refuse(f"talkto {name}: {str(out)[-120:]}")
    gold0 = state()["pc"].get("gold")
    if not click("Identify all"):
        bye()
        refuse(f"{name} offers no 'Identify all of my stuff'")
    said = str(run("talk.py", timeout=60))
    m = re.search(r"For ([\d,]+) Orens", said, re.I)
    if not m:
        # nothing unidentified, or a line I haven't seen: either way no money moved
        print(f"{name}: no price offered: {last(said)[:120]}")
        bye()
        return 0
    price = int(m.group(1).replace(",", ""))
    if price > most:
        click("No.")
        run("talk.py", timeout=60)
        bye()
        print(f"{name}: {price} is over {most}: declined")
        return 0
    if not click("Yes."):
        stop("no Yes in the dialog")
    run("talk.py", timeout=60)
    bye()
    print(f"{name}: identified for {price}, gold {gold0} -> {state()['pc'].get('gold')}; next: gearcheck.py, then shipstar.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
