"""Sell fame to an informer (runs 32-42: done by hand each time; the near nefia refill scales with fame, so a sale pulls it back under the gate, and half the tax bill is fame x 2).
Talks to NAME, sells until the offer falls under MIN or TIMES sales are done, says Bye. One dialog at a time.

usage: python -I tools/famesale.py NAME [TIMES=3] [MIN=140]    e.g. famesale.py Gizon, famesale.py Ishbear (stand near them: whereis.py any NAME)
Exit 0 done, 1 refused (not in view, no sale offered), 3 a dialog that didn't read as expected.
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, data, run, setup, state, stop, refuse  # noqa: E402


def click(text):
    for b in data("buttons")["buttons"]:
        if text in (b.get("text") or ""):
            r = call("click", i=b["i"], expect=text)
            time.sleep(0.3)
            return bool(r.get("ok"))
    return False


def main():
    setup()
    args = sys.argv[1:]
    if not args:
        refuse(__doc__.splitlines()[3])
    name = args[0]
    times = int(args[1]) if len(args) > 1 else 3
    least = int(args[2]) if len(args) > 2 else 140
    out = run("talkto.py", name, timeout=120)
    if out.rc:
        refuse(f"talkto {name}: {str(out)[-120:]}")
    gold0 = state()["pc"].get("gold")
    sold = []
    for _ in range(times):
        if not click("sell my fame"):
            if not sold:
                click("Bye")
                run("talk.py")
                refuse(f"{name} offers no fame sale")
            break
        said = str(run("talk.py", timeout=60))
        m = re.search(r"for ([\d,]+) orens", said)
        if not m:
            stop(f"no price in the dialog: {said[:160]}")
        price = int(m.group(1).replace(",", ""))
        if price < least:
            click("No.")
            run("talk.py", timeout=60)
            print(f"  {price} is under {least}: declined")
            break
        if not click("Yes."):
            stop("no Yes in the dialog")
        run("talk.py", timeout=60)
        sold.append(price)
    click("Bye")
    run("talk.py", timeout=60)
    print(f"{name}: sold {sold}, gold {gold0} -> {state()['pc'].get('gold')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
