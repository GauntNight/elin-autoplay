"""Wait until Elin is running with a game loaded (after a launch with autoload), then print
the bridge version and a compact look. Exits 1 on timeout.

usage: python -I tools/wait_ingame.py [timeout_seconds]

Launch with autoload (the bridge loads the save once the title screen settles):
  printf world_4 > mod/dist/ElinBridge/autoload.txt
  explorer.exe steam://rungameid/2135150
  python -I tools/wait_ingame.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call, close  # noqa: E402


def main():
    limit = float(sys.argv[1]) if len(sys.argv) > 1 else 240
    t0 = time.time()
    while time.time() - t0 < limit:
        try:
            s = call("state")
            if s.get("ok") and s["data"].get("inGame") and not (s["data"].get("layers") or {}).get("top"):
                v = call("ping")["data"]["version"]
                print(f"in game after {time.time() - t0:.0f}s, bridge {v}")
                from common import run
                print(run("look.py", "3"))
                return
        except OSError:
            close()
        time.sleep(2)
    sys.exit(f"not in game after {limit:.0f}s")


if __name__ == "__main__":
    main()
