"""A long loop's registration, so it can be stopped (2026-10-19, after run 10's runaway loop).

register(NAME) writes runs/jobs/NAME.json (pid, start time, argv) and removes it on exit;
stop_requested(NAME) is true once runs/jobs/NAME.stop exists. The loop checks it between steps
and returns. tools/stopjob.py NAME writes the stop file and waits for that.
"""
import atexit
import json
import os
import sys
import time
from pathlib import Path

JOBS = Path(__file__).resolve().parent.parent / "runs" / "jobs"


def register(name):
    JOBS.mkdir(parents=True, exist_ok=True)
    (JOBS / f"{name}.stop").unlink(missing_ok=True)  # an old request must not stop a new run
    f = JOBS / f"{name}.json"
    f.write_text(json.dumps({"pid": os.getpid(), "started": time.time(), "argv": sys.argv}),
                 encoding="utf-8")
    atexit.register(lambda: f.unlink(missing_ok=True))


def stop_requested(name):
    return (JOBS / f"{name}.stop").exists()
