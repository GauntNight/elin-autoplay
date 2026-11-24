"""Follow a log with a stop condition: the only way to watch a log here (2026-11-03, KB #155).

`tail -f LOG | grep ...` never ends by itself: on 2026-11-02, 141 such pipelines from this repo's sessions
were still running days later, holding about 1.4 GB and blocking the Git for Windows upgrade. This is one
python process with its own deadline, so it ends whoever kills its parent, and it isn't in Git's usr\\bin.

Run it as the command of the Monitor tool, or in the background with Bash. Each printed line is an event.
A monitor's timeout must be longer than --max, so this exits first; re-arm it for a longer watch.

usage: python -I tools/watchlog.py LOG [--match RE] [--until RE] [--max SECONDS=1790] [--idle SECONDS=900] [--from-start]
  --match RE     print only the lines that match (default: every line)
  --until RE     print the first line that matches and exit 0
  --max SECONDS  exit 3 after this long (never over 3600)
  --idle SECONDS say so once when the log hasn't grown for this long: silence isn't success
  --from-start   read what the log already holds (default: only what is added from now on, but a log under two minutes old is
                 read from its start: run 55 watched two jobs that had ended before the watcher began)
exit codes: 0 --until matched, 1 refused (bad arguments), 3 the deadline passed: re-arm if it is still needed.
"""
import argparse
import re
import sys
import time
from pathlib import Path

CAP = 3600  # seconds: no watch outlives this, whatever it is asked for
POLL = 1.0


def young(log, secs=120):
    """Run 55: a short job ended before its watcher began. st_ctime is the file's creation on Windows."""
    try:
        return time.time() - log.stat().st_ctime < secs
    except OSError:
        return False


def follow(log, match, until, deadline, idle, start_at_end):
    """Print the lines that match. Returns the exit code."""
    pos = None if start_at_end else 0
    partial = b""
    quiet_since = time.time()
    told_quiet = False
    while time.time() < deadline:
        size = log.stat().st_size if log.exists() else None
        if size is not None:
            if pos is None:
                pos = size
            elif size < pos:  # truncated or replaced: start over
                pos, partial = 0, b""
            if size > pos:
                with log.open("rb") as f:
                    f.seek(pos)
                    chunk = f.read()
                pos += len(chunk)
                quiet_since, told_quiet = time.time(), False
                lines = (partial + chunk).split(b"\n")
                partial = lines.pop()
                for raw in lines:
                    line = raw.decode("utf-8", "replace").rstrip("\r")
                    if until and until.search(line):
                        print(line, flush=True)
                        return 0
                    if match is None or match.search(line):
                        print(line, flush=True)
        if pos is None:  # the log doesn't exist yet: everything it gets is new
            pos = 0
        if idle and not told_quiet and time.time() - quiet_since >= idle:
            print(f"watchlog: {log.name} has been quiet for {idle} s", flush=True)
            told_quiet = True
        time.sleep(POLL)
    print(f"watchlog: deadline reached, {log.name} no longer watched", flush=True)
    return 3


def main():
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("log")
    p.add_argument("--match")
    p.add_argument("--until")
    p.add_argument("--max", type=int, default=1790)
    p.add_argument("--idle", type=int, default=900)
    p.add_argument("--from-start", action="store_true")
    a = p.parse_args()
    try:
        match = re.compile(a.match) if a.match else None
        until = re.compile(a.until) if a.until else None
    except re.error as e:
        print(f"bad pattern: {e}")
        return 1
    if a.max <= 0:
        print("--max must be above 0")
        return 1
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    return follow(Path(a.log), match, until, time.time() + min(a.max, CAP), a.idle, not (a.from_start or young(Path(a.log))))


if __name__ == "__main__":
    sys.exit(main())
