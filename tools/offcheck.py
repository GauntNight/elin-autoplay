"""What a session has left running (2026-11-03, KB #155; the user: "make sure the Ollama server and things go off
when we exit"). Read-only: it looks at the process list and the port, and ends nothing. Run it at session start
and as the close-out's last step.

It lists Elin, the repo-local Ollama on 127.0.0.1:11435 and its runners, the bash that launched it, the loops
registered in runs/jobs/, tools/watchlog.py followers, and any tail/grep/sed/cut running from Git's usr\\bin (those
may belong to another project's session, so they are listed and never assumed to be ours). A parent that is
gone marks a monitor as orphaned. The user's own Ollama on 11434 isn't this repo's and is only named.

usage: python -I tools/offcheck.py
exit codes: 0 nothing left, 2 the process list couldn't be read, 3 something is still running (listed).
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GIT_USR = "c:\\program files\\git\\usr\\bin\\"
MONITOR = {"tail.exe", "grep.exe", "sed.exe", "cut.exe"}


def powershell(script):
    """Run one read-only PowerShell query and return its JSON as a list (empty when it prints nothing)."""
    out = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                         capture_output=True, text=True, timeout=120).stdout.strip()
    if not out:
        return []
    data = json.loads(out)
    return data if isinstance(data, list) else [data]


def processes():
    return powershell("Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,"
                      "ExecutablePath,CommandLine | ConvertTo-Json -Compress")


def listeners(port):
    """The PIDs listening on a TCP port."""
    rows = powershell(f"Get-NetTCPConnection -LocalPort {int(port)} -State Listen -ErrorAction SilentlyContinue | "
                      "Select-Object OwningProcess | ConvertTo-Json -Compress")
    return sorted({int(r["OwningProcess"]) for r in rows})


def descendants(pid, procs):
    """Every live process below PID."""
    found, frontier = [], {pid}
    while frontier:
        kids = [p for p in procs if p["ParentProcessId"] in frontier and p not in found]
        found += kids
        frontier = {p["ProcessId"] for p in kids}
    return found


def registered_jobs(procs):
    """Loops registered in runs/jobs/ whose PID is still alive."""
    alive = {p["ProcessId"] for p in procs}
    jobs = []
    for f in sorted((REPO / "runs" / "jobs").glob("*.json")):
        try:
            job = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if job.get("pid") in alive:
            jobs.append((f.stem, job["pid"]))
    return jobs


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        procs = processes()
        ours = listeners(11435)
        theirs = listeners(11434)
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        print(f"couldn't read the process list: {e}")
        return 2

    alive = {p["ProcessId"] for p in procs}
    left = []

    for p in procs:
        if (p["Name"] or "").lower() == "elin.exe":
            left.append(f"Elin is running (PID {p['ProcessId']}): python -I tools/bridge.py quit")

    for pid in ours:
        kids = descendants(pid, procs)
        left.append(f"repo-local Ollama listens on 11435 (PID {pid}, {len(kids)} below it): python -I tools/ollama_stop.py")
    for p in procs:
        cmd = (p["CommandLine"] or "").replace("\\", "/")
        if "ollama_serve.sh" in cmd:
            left.append(f"ollama_serve.sh is still running (PID {p['ProcessId']}): it exits with the server")
        if "tools/watchlog.py" in cmd:
            left.append(f"a log follower is running (PID {p['ProcessId']}): it ends at its deadline, or TaskStop it")

    for name, pid in registered_jobs(procs):
        left.append(f"loop {name} is running (PID {pid}): python -I tools/stopjob.py {name}")

    monitors = [p for p in procs if (p["Name"] or "").lower() in MONITOR
                and (p["ExecutablePath"] or "").lower().startswith(GIT_USR)]
    orphans = [p for p in monitors if p["ParentProcessId"] not in alive]
    for p in monitors:
        tag = "ORPHANED monitor" if p in orphans else "monitor"
        left.append(f"{tag} PID {p['ProcessId']}: {(p['CommandLine'] or p['Name'])[:110]}")

    tail_grep = sum(1 for p in orphans if p["Name"].lower() in ("tail.exe", "grep.exe"))
    print(f"orphaned tail/grep monitors: {tail_grep}")
    if theirs:
        print(f"(the user's own Ollama on 11434 is running, PID {', '.join(map(str, theirs))}: not this repo's)")
    if not left:
        print("nothing left running")
        return 0
    print(f"{len(left)} still running:")
    for line in left:
        print(f"  {line}")
    return 3


if __name__ == "__main__":
    sys.exit(main())
