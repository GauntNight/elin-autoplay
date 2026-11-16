"""The end of the user's play window (run 22: run 21 quit two hours before the five the user had asked
for). When the user gives a duration or an end time, write it here at once; `bridge.py quit` refuses
before it unless --early-ok.

usage: python -I tools/session_end.py 5h | 90m | 03:00   set the end (a clock time rolls to tomorrow)
       python -I tools/session_end.py                     print it and the minutes left
       python -I tools/session_end.py --clear             the window is over or the user ended it
Kept in runs/jobs/session_end.txt (gitignored with the running loops' files).

closeout_refusal(argv) is the close-out's own gate (run 50: play stopped at 14:24 of a window to 15:54 when the near
nefias ran out, and the paperwork ran while the game sat idle until the user said quit): summary_page.py asks it, and it
refuses while more than CLOSEOUT_MIN minutes are left unless the user's word is on record (`bridge.py quit --early-ok
'user: ...'` logs it in runs/early_quits.csv) or given as --early-ok 'user: "their words"'.
"""
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

FILE = Path(__file__).resolve().parent.parent / "runs" / "jobs" / "session_end.txt"
EARLY = Path(__file__).resolve().parent.parent / "runs" / "early_quits.csv"  # bridge.py quit's log of early quits
CLOSEOUT_MIN = 30  # the paperwork runs beside the last half hour of play (run 42), never instead of play (run 50)


def now():
    """Aware local time: run 36's window crossed the end of daylight saving (the clock goes back an hour), and the naive
    "06:17" it had stored moved the end an hour later; an aware time is one instant whatever the clock does."""
    return datetime.now().astimezone()


def ends_at():
    """The window's end while it is still ahead, else None (a past end is no longer a reason)."""
    try:
        end = datetime.fromisoformat(FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    if end.tzinfo is None:  # a file from before run 36: read as local time
        end = end.astimezone()
    end = end.astimezone()
    return end if end > now() else None


def user_ended(end):
    """True when bridge.py quit logged the user's word ('user: ...') against this window's end."""
    try:
        lines = EARLY.read_text(encoding="utf-8").splitlines()[1:]
    except OSError:
        return False
    key = f"{end:%Y-%m-%d %H:%M}"
    for line in lines:
        parts = line.split(",", 2)
        if len(parts) == 3 and parts[1] == key and parts[2].strip().strip('"').startswith("user:"):
            return True
    return False


def closeout_refusal(argv):
    """Why the close-out may not start yet, or None: no window, its last CLOSEOUT_MIN minutes, or the user's word."""
    end = ends_at()
    if not end:
        return None
    left = int((end - now()).total_seconds()) // 60
    if left <= CLOSEOUT_MIN or user_ended(end):
        return None
    if "--early-ok" in argv:
        i = argv.index("--early-ok")
        if i + 1 < len(argv) and argv[i + 1].startswith("user:"):
            return None
    return (f"refused: the play window runs until {end:%H:%M} ({left} minutes left); the close-out starts in its last "
            f"{CLOSEOUT_MIN} minutes or on the user's word (--early-ok 'user: QUOTE'). Out of near nefias: Fast Travel to a "
            "region not circuited lately, a fame sale, or the dummy (elin-train); never the paperwork instead of play (run 50)")


def parse(arg, t):
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([hm])", arg)
    if m:
        n = float(m.group(1))
        return t + (timedelta(hours=n) if m.group(2) == "h" else timedelta(minutes=n))
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", arg)
    if m:
        end = t.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
        return end if end > t else end + timedelta(days=1)
    sys.exit(f"not a duration or a clock time: {arg!r} (5h, 90m, 03:00)")


def main():
    args = sys.argv[1:]
    if "--clear" in args:
        FILE.unlink(missing_ok=True)
        print("cleared")
        return
    if args:
        end = parse(args[0], now())
        FILE.parent.mkdir(parents=True, exist_ok=True)
        FILE.write_text(end.isoformat(timespec="minutes"), encoding="utf-8")
    end = ends_at()
    if end:
        print(f"the play window ends {end:%Y-%m-%d %H:%M %Z} ({int((end - now()).total_seconds()) // 60} minutes left)")
    else:
        print("no play window set")


if __name__ == "__main__":
    main()
