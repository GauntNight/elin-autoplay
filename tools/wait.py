"""Pass game time safely until a clock time: the bed's Pass Time when standing on a bed,
otherwise repeated Wait. Cancels (bridge `cancel`) at the target time or on any threat: a
hostile in view, HP below 80%, worse than plain Hungry, or a dialog/window opening.
Run 03 lesson: an unwatched Pass Time ran 21 game hours and a resident died meanwhile.

usage: python -I tools/wait.py HH:MM --user-ok   only with the user's yes for this wait
The user (runs 05, 11, 17): "Please don't wait... Waiting is the worst thing we can do in this
game as it costs hunger/time with no benefit." Run 17 waited 3.5 game hours for a shop to open;
so it refuses without --user-ok: do SP-free work, travel or sleep instead.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import stop  # noqa: E402


def clock(date):
    """'485-05-25 03:46' -> minutes since the epoch-ish (day*1440 + h*60 + m)."""
    d, t = date.split(" ")
    y, mo, dd = (int(x) for x in d.split("-"))
    h, m = (int(x) for x in t.split(":"))
    return ((y * 12 + mo) * 30 + dd) * 1440 + h * 60 + m


def main():
    if "--user-ok" not in sys.argv:
        print("refused: no waiting (the user, runs 05, 11, 17); --user-ok only with their yes for this wait")
        sys.exit(1)
    hh, mm = (int(x) for x in sys.argv[1].split(":"))
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    s = call("state")["data"]
    p = s["pc"]
    now = clock(p["date"])
    day_start = now - now % 1440
    target = day_start + hh * 60 + mm
    if target <= now:
        target += 1440
    acts = call("acts", dx=0, dz=0, mode="all")["data"]["acts"]
    pt = [a for a in acts if a["text"].startswith("Pass Time")]
    mode = "pass time" if pt else "wait"
    if pt:
        call("do", i=pt[0]["i"])
    why = "target time"
    decision = False  # a threat ended the wait: exit 3 (the tools' exit-code contract, common.stop)
    while True:
        if not pt:
            call("act", action="Wait")
        time.sleep(0.4 if pt else 0.15)
        s = call("state")["data"]
        p = s["pc"]
        if clock(p["date"]) >= target:
            break
        lay = (s.get("layers") or {}).get("top")
        if lay or s.get("drama"):
            why, decision = f"a window opened ({lay})", True
            break
        if any(c["hostile"] for c in s.get("nearby") or []):
            why, decision = "hostile in view", True
            break
        if p["hp"] * 100 < 80 * p["maxHp"] or p.get("hungerText") not in ("", "Normal", "Filled", "Hungry", None):
            why, decision = f"HP/hunger check ({p['hp']}/{p['maxHp']}, {p.get('hungerText')})", True
            break
        if pt and "PassTime" not in (p["ai"] or ""):
            why = f"pass time ended by itself ({p['ai']})"
            break
    if "PassTime" in (call("state")["data"]["pc"]["ai"] or ""):
        call("cancel")
        time.sleep(0.5)
    p = call("state")["data"]["pc"]
    now = (f"({mode}); now {p['date']}  HP {p['hp']}/{p['maxHp']} SP {p['sp']}  "
           f"hunger {p['hunger']} {p.get('hungerText') or ''}  ai {p['ai']}")
    if decision:
        stop(f"{why} {now}")
    print(f"done: {why} {now}")


if __name__ == "__main__":
    main()
