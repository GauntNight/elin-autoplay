"""The end of the user's play window (run 22: run 21 quit two hours before the five the user had asked
for). When the user gives a duration or an end time, write it here at once; `bridge.py quit` refuses
before it unless --early-ok.

usage: python -I tools/session_end.py 5h | 90m | 03:00   set the end (a clock time rolls to tomorrow)
       python -I tools/session_end.py                     print it and the minutes left
       python -I tools/session_end.py --clear             the window is over or the user ended it
Kept in runs/jobs/session_end.txt (gitignored with the running loops' files).
"""
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

FILE = Path(__file__).resolve().parent.parent / "runs" / "jobs" / "session_end.txt"


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
