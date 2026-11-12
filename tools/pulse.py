"""Watch the game itself while a loop runs: exit when nothing has happened for too long (the review of 2026-11-11).

A loop's log can go quiet for two reasons: a long step, or a hang. Run 45's circuit sat 15 real minutes on Ancient
Ruin B3 with the turn counter still, and run 42's delve held 17 minutes on one soil block; both were found by a
look, late. About half of runs 42, 44 and 45 was outside any marked loop. This asks the bridge for the state every
few seconds (a second client is fine since bridge 0.23.0; `state` changes nothing) and ends, so the session is
called back, when:
  - the player's turn counter and the game clock haven't moved for --idle seconds (default 300): exit 3;
  - the bridge hasn't answered for --dead seconds (default 90): exit 2 (the game is gone or frozen);
  - --max seconds have passed (default 1790, never over 3600): exit 0, "still moving": re-arm it.
Run it in the background beside every unattended loop. It never acts in the game.

usage: python -I tools/pulse.py [--idle 300] [--dead 90] [--max 1790] [--every 10]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bridge  # noqa: E402

CAP = 3600


def read():
    """(turn, date, zone, top window, ai) or None when the bridge doesn't answer."""
    try:
        r = bridge.call("state")
    except OSError:
        bridge.close()
        return None
    if not r.get("ok"):
        return None
    s = r["data"]
    p = s.get("pc") or {}
    return (p.get("turn"), p.get("date") or s.get("date"), (s.get("zone") or {}).get("name"),
            (s.get("layers") or {}).get("top"), p.get("ai"), s.get("inGame", True))


def main():
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--idle", type=int, default=300)
    ap.add_argument("--dead", type=int, default=90)
    ap.add_argument("--max", type=int, default=1790)
    ap.add_argument("--every", type=int, default=10)
    a = ap.parse_args()
    t0 = time.time()
    deadline = t0 + min(a.max, CAP)
    last_key, moved_at, answered_at, seen = None, t0, t0, None
    while time.time() < deadline:
        now = time.time()
        cur = read()
        bridge.close()  # one short connection a poll: never hold the socket between polls
        if cur is None:
            if now - answered_at >= a.dead:
                print(f"stop: the bridge hasn't answered for {int(now - answered_at)}s: the game is closed, frozen or "
                      "loading; bridge.py ping, then Player.log")
                sys.exit(2)
        else:
            answered_at, seen = now, cur
            key = cur[:2]
            if key != last_key:
                last_key, moved_at = key, now
            elif now - moved_at >= a.idle:
                turn, date, zone, top, ai, in_game = cur
                where = "not in a game" if not in_game else f"{zone}, {date}, turn {turn}"
                print(f"stop: nothing has moved for {int(now - moved_at)}s ({where}; window: {top or 'none'}; "
                      f"task: {ai or 'none'}): look.py, then decide; a loop that is still running is stuck")
                sys.exit(3)
        time.sleep(max(1, a.every))
    if seen:
        print(f"still moving after {int(time.time() - t0)}s ({seen[2]}, {seen[1]}, turn {seen[0]}): re-arm")
    else:
        print(f"no answer yet after {int(time.time() - t0)}s: re-arm or bridge.py ping")
    sys.exit(0)


if __name__ == "__main__":
    main()
