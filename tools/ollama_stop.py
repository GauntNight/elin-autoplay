"""End the repo-local Ollama server (the user's rule, 2026-11-03: "make sure the Ollama server and things go off when
we exit"; KB #155). The close-out's last step, after kb.py embed and bench, which need the server.

Ollama has no shutdown call, so this ends one process, found by what it does and never by name: whatever listens on
127.0.0.1:11435, only after checking it is ollama.exe from the user's install, running `serve`, and not also
listening on 11434, the user's own Ollama. `taskkill /PID N /T /F` takes its runner with it, which holds the GPU memory.
Then it checks that the port has closed and no runner is left. Never Elin, never the user's Ollama, nothing else.

usage: python -I tools/ollama_stop.py [--check]
  --check  say what would be ended and end nothing
exit codes: 0 stopped, or nothing to stop; 1 refused (the listener isn't what it should be); 2 still running afterwards.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from offcheck import descendants, listeners, processes  # noqa: E402

PORT = 11435
USERS_OLLAMA_PORT = 11434


def refuse_reason(pid, procs):
    """None if PID is the repo-local server, else why not."""
    p = next((x for x in procs if x["ProcessId"] == pid), None)
    if p is None:
        return f"PID {pid} isn't in the process list"
    expected = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Ollama" / "ollama.exe"
    if str(p["ExecutablePath"] or "").lower() != str(expected).lower():
        return f"PID {pid} is {p['ExecutablePath']!r}, not the installed ollama.exe"
    if "serve" not in (p["CommandLine"] or "").split():
        return f"PID {pid} runs {p['CommandLine']!r}, not `ollama serve`"
    if pid in listeners(USERS_OLLAMA_PORT):
        return f"PID {pid} also listens on {USERS_OLLAMA_PORT}, the user's own Ollama"
    return None


def main():
    check_only = "--check" in sys.argv[1:]
    pids = listeners(PORT)
    if not pids:
        print(f"nothing listens on {PORT}: nothing to stop")
        return 0
    if len(pids) != 1:
        print(f"refused: {len(pids)} processes listen on {PORT}: {pids}")
        return 1
    pid = pids[0]
    procs = processes()
    why = refuse_reason(pid, procs)
    if why:
        print(f"refused: {why}")
        return 1
    below = [p["ProcessId"] for p in descendants(pid, procs)]
    if check_only:
        print(f"would end PID {pid} and the {len(below)} below it {below}")
        return 0

    r = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True, timeout=60)
    print((r.stdout + r.stderr).strip())
    t0 = time.time()
    while time.time() - t0 < 30:
        time.sleep(1)
        alive = {p["ProcessId"] for p in processes()}
        if not listeners(PORT) and not alive & ({pid} | set(below)):
            print(f"stopped: nothing listens on {PORT}, no runner left ({time.time() - t0:.0f} s)")
            return 0
    print(f"still running after 30 s: listeners {listeners(PORT)}; check with tools/offcheck.py")
    return 2


if __name__ == "__main__":
    sys.exit(main())
