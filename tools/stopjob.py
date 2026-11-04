"""Stop a loop Claude started in this session (2026-10-19: the user's rule, this repo only).

1. Ask: write runs/jobs/NAME.stop and wait for the loop to return at its next check
   (springday.py checks between steps; a farm round takes up to ~20 real minutes).
2. Only if it is still running after --wait seconds: end the one process the loop registered
   in runs/jobs/NAME.json, after checking it is still that process (python, its command line
   runs tools/NAME.py, created just before it registered, so the PID wasn't reused):
   taskkill /PID N /T /F (with its children: wait.py, sleep.py).
Never by name or pattern, never Elin (quit through the bridge), never Ollama or anything else.

usage: python -I tools/stopjob.py NAME [--wait SECONDS=600] [--no-kill]
--no-kill asks and checks, and says what step 2 would end without ending it.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from job import JOBS  # noqa: E402


def proc(pid):
    """Name, command line and creation time (unix seconds) of a live PID, or None."""
    ps = (f"Get-CimInstance Win32_Process -Filter 'ProcessId={int(pid)}' | Select-Object Name,"
          "CommandLine,@{n='Created';e={([DateTimeOffset]$_.CreationDate).ToUnixTimeSeconds()}}"
          " | ConvertTo-Json")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                         capture_output=True, text=True, timeout=60).stdout.strip()
    return json.loads(out) if out else None


def check(name, job):
    """None if the registered PID is still the loop that registered it, else why not."""
    p = proc(job["pid"])
    if not p:
        return "gone"
    cmd = (p.get("CommandLine") or "").replace("\\", "/")
    if not (p.get("Name") or "").lower().startswith("python"):
        return f"PID {job['pid']} is {p.get('Name')}, not python"
    if f"tools/{name}.py" not in cmd:
        return f"PID {job['pid']} runs {cmd[:120]!r}, not tools/{name}.py"
    if not -5 <= job["started"] - p["Created"] <= 120:
        return f"PID {job['pid']} was created {job['started'] - p['Created']:.0f} s from its registration"
    return None


def main():
    a = sys.argv[1:]
    wait = 600
    if "--wait" in a:
        k = a.index("--wait")
        wait = int(a[k + 1])
        a = a[:k] + a[k + 2:]
    no_kill = "--no-kill" in a
    a = [x for x in a if x != "--no-kill"]
    if len(a) != 1 or not re.fullmatch(r"[a-z0-9_-]+", a[0]):
        sys.exit(__doc__)
    name = a[0]
    f = JOBS / f"{name}.json"
    if not f.exists():
        sys.exit(f"no registered job {name} (runs/jobs/{name}.json)")
    job = json.loads(f.read_text(encoding="utf-8"))
    if check(name, job) == "gone":
        f.unlink(missing_ok=True)
        sys.exit(f"{name}: PID {job['pid']} has already ended (stale registration removed)")

    (JOBS / f"{name}.stop").write_text("", encoding="utf-8")
    print(f"{name}: asked to stop (PID {job['pid']}); waiting up to {wait} s")
    t0 = time.time()
    while time.time() - t0 < wait:
        time.sleep(5)
        if not f.exists() or check(name, job) == "gone":
            (JOBS / f"{name}.stop").unlink(missing_ok=True)
            print(f"{name}: stopped by request after {time.time() - t0:.0f} s")
            return

    why = check(name, job)
    if why == "gone":
        print(f"{name}: ended")
    elif why:
        sys.exit(f"{name}: refusing to end it: {why}")
    elif no_kill:
        print(f"{name}: still running; step 2 would end PID {job['pid']} (--no-kill: left running)")
        return
    else:
        r = subprocess.run(["taskkill", "/PID", str(job["pid"]), "/T", "/F"],
                           capture_output=True, text=True, timeout=60)
        print(f"{name}: did not stop in {wait} s; taskkill: {(r.stdout + r.stderr).strip()}")
    f.unlink(missing_ok=True)
    (JOBS / f"{name}.stop").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
