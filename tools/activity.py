"""Mark the start and end of a timed activity for the run tracker (the review of 2026-10-23: the
owner's measure is growth per real hour, and no log said what each activity earned). Each mark is
one row in runs/activity.csv: the real clock, the game date, the tag, the phase, exp, level, gold,
gold bars, the zone. stats.py pairs a start with its end and derives exp and orens per real hour
per tag; the loops call it themselves, so the numbers need no hand work at the close-out.

    from activity import mark
    mark("nefia", "start")        ...the loop...        mark("nefia", "end", note="3 floors")

Tags: nefia, jobs, home, travel, train, build, town, mine, farm, thief. A mark never raises (a log must
not stop play) and costs one bridge call.

usage: python -I tools/activity.py TAG start|end [NOTE]
"""
import csv
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "runs" / "activity.csv"
FIELDS = ["logged_at", "game_date", "tag", "phase", "exp", "lv", "gold", "gold_bars", "zone", "note"]


def mark(tag, phase, note=""):
    """Append one row; returns the row dict, or None when the bridge or the file failed."""
    try:
        from bridge import call
        s = call("state").get("data") or {}
        p = s.get("pc") or {}
        row = {
            "logged_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "game_date": p.get("date", ""),
            "tag": tag, "phase": phase,
            "exp": p.get("exp", ""), "lv": p.get("lv", ""),
            "gold": p.get("gold", ""), "gold_bars": p.get("goldBars", ""),
            "zone": (s.get("zone") or {}).get("name", ""),
            # run 35 (the user: "are groups better than solo at this point?"): every mark names the party size, so
            # stats and crewcheck.py can split each activity's rates by solo and crew
            # run 46: karma fell ~100 across three hours of loops and no record showed which one: every mark names it too
            "note": (f"{note} " if note else "") + f"[party {len(s.get('party') or [])}, karma {p.get('karma')}]",
        }
        new = not LOG.exists()
        with LOG.open("a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new:
                w.writeheader()
            w.writerow(row)
        return row
    except Exception as e:  # noqa: BLE001 - a log line must never stop play
        print(f"activity: not logged ({e})", file=sys.stderr)
        return None


def main():
    if len(sys.argv) < 3 or sys.argv[2] not in ("start", "end"):
        sys.exit(__doc__)
    row = mark(sys.argv[1], sys.argv[2], " ".join(sys.argv[3:]))
    if row:
        print(f"{row['tag']} {row['phase']}: {row['game_date']} exp {row['exp']} gold {row['gold']} at {row['logged_at']}")


if __name__ == "__main__":
    main()
