"""Invest in a shopkeeper's shop (G26, the Merchants Guild: run 29) when the price is low enough.

Each direct investment (talk, "I want to invest", Yes) raises the shop one level and pays Merchants Guild
contribution 5 + the shop's new count (run 29: Fleaun's level 1 shop cost 143 and paid 6; Raydorre's level 10
asked 4,819 for ~16). The price climbs with the shop's level (CalcMoney.Invest: max(c x 700, c² x 80 + 200),
less CHA/2 + Investing), so low-level shops are the cheap points. This reads the level and the price and says
Yes only at or under MAX orens, then Bye; one dialog at a time (elin-play's hard rule).

usage: python -I tools/invest.py NAME [MAX=600] [TIMES=1]
Exit 0 invested (or priced over MAX: the price is printed), 1 refused (not in view, no Invest choice), 3 a
dialog that didn't read as expected.
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import last, refuse, run, setup, state, stop  # noqa: E402


def choices():
    bs = call("buttons")["data"]["buttons"]
    return [b for b in bs if (b.get("text") or "").strip()]


def drama_text():
    d = state().get("drama") or {}
    return " ".join(str(v) for v in (d.values() if isinstance(d, dict) else [d]))


def click(text):
    b = next((b for b in choices() if (b.get("text") or "").startswith(text)), None)
    if not b:
        return False
    call("click", i=b["i"], expect=text)
    run("talk.py")
    time.sleep(0.3)
    return True


def contribution():
    texts = call("texts").get("data") or []
    texts = texts if isinstance(texts, list) else texts.get("texts") or []
    for i, t in enumerate(texts):
        if "Merchants Guild" in str(t) and i > 0 and "Contribution" in str(texts[i - 1]):
            return str(texts[i - 1])
    return "?"


def bye():
    if not click("Bye"):
        run("close.py")


def main():
    setup()
    a = sys.argv[1:]
    if not a:
        refuse("usage: invest.py NAME [MAX=600] [TIMES=1]")
    name, cap = a[0], int(a[1]) if len(a) > 1 else 600
    times = int(a[2]) if len(a) > 2 else 1
    out = run("talkto.py", name)
    if out.rc != 0 or "I want to invest" not in str(out):
        if out.rc == 0:
            bye()
        refuse(f"{name}: no 'I want to invest' ({last(str(out))[:120] or 'no dialog'})")
    level = re.search(r"Shop Level: (\d+)", str(out))
    print(f"{name}: shop level {level.group(1) if level else '?'}")
    done = 0
    while done < times:
        if not click("I want to invest"):
            stop("the Invest choice is gone")
        text = str(run("talk.py"))
        m = re.search(r"cost you ([\d,]+) orens", text) or re.search(r"cost you ([\d,]+) orens", drama_text())
        if not m:
            bye()
            stop(f"no price read: {text[-160:]}")
        price = int(m.group(1).replace(",", ""))
        if price > cap:
            click("No")
            print(f"  {price:,} orens is over the cap {cap:,}: declined")
            break
        g0 = state()["pc"].get("gold")
        click("Yes")
        g1 = state()["pc"].get("gold")
        done += 1
        print(f"  invested {price:,} (gold {g0} -> {g1})")
    after = str(run("talk.py"))
    lv = re.search(r"Shop Level: (\d+)", after)
    bye()
    time.sleep(0.5)  # the HUD's guild tracker is hidden under the dialog: read it after Bye
    print(f"{name}: {done} investment(s); shop level now {lv.group(1) if lv else '?'}; Merchants {contribution()}")


if __name__ == "__main__":
    main()
