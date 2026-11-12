"""Run tool calls one after another and stop at the first that doesn't exit 0 (the review of 2026-11-11).

The rule (elin-play): never chain game-acting tools with `;`, and never run a later step after a refusal. It was
broken in runs 21, 28, 29, 42, 43 and 45: `act.py ... ; leave.py ; wgo.py ...` walked on after act.py had
exited 1. Each fix patched one tool. This is the chain itself: a step that refuses (1), fails on the bridge (2)
or stops for a decision (3) ends it, and the steps after it are named, not run.

usage: python -I tools/seq.py "TOOL ARGS" "TOOL ARGS" ...
  each argument is one call without the `python -I tools/` prefix, quoted as one string:
      python -I tools/seq.py "act.py 0 0 'Pick all'" "leave.py" "wgo.py 12 34"
  --dry   print the calls and run nothing
exit codes: 0 every step done; else the first failing step's own code (1 refused, 2 bridge, 3 stopped).
"""
import shlex
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent


def parse(step):
    parts = shlex.split(step)
    if not parts:
        return None, "an empty step"
    name = parts[0] if parts[0].endswith(".py") else parts[0] + ".py"
    if "/" in name or not (TOOLS / name).is_file():
        return None, f"'{parts[0]}' is not a tool in tools/"
    return [name, *parts[1:]], None


def main():
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    dry = "--dry" in sys.argv[1:]
    steps = [a for a in sys.argv[1:] if a != "--dry"]
    if not steps:
        print(__doc__)
        sys.exit(1)
    calls = []
    for step in steps:  # every step is checked before the first one runs
        argv, err = parse(step)
        if err:
            print(f"refused: {err}: {step!r}", file=sys.stderr)
            sys.exit(1)
        calls.append(argv)
    for n, argv in enumerate(calls, 1):
        shown = " ".join(argv)
        print(f"[{n}/{len(calls)}] {shown}", flush=True)
        if dry:
            continue
        rc = subprocess.run([sys.executable, "-I", "-X", "utf8", str(TOOLS / argv[0]), *argv[1:]]).returncode  # noqa: S603
        if rc:
            left = [" ".join(c) for c in calls[n:]]
            word = {1: "refused", 2: "failed on the bridge", 3: "stopped for a decision"}.get(rc, f"exited {rc}")
            print(f"stop: step {n} ({shown}) {word} (rc {rc})"
                  + (f"; not run: {' | '.join(left)}" if left else ""), flush=True)
            sys.exit(rc)
    print(f"done: {len(calls)} steps" + (" (dry)" if dry else ""))


if __name__ == "__main__":
    main()
