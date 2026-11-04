"""Play an instrument song after song for a music quest ("Baby!": score N music points at a
party), and stop safely. Run 05: the party's Concert Hall has its instruments installed on the
map (a harpsichord there); the game's Play Music act walks to it and plays one song.

How the game scores it (AI_PlayMusic, QuestMusic): each song starts at 40 points; a listener
within 4 cells reacts at most once a song (+5 to +10; at a low-level party even boos add). Each
beat after the third risks a mistake, about 1 in (4 + song level); a mistake ends the song
with score/2 - 20, and half the mistakes raise the song's level. A clean song pays score x 1.1
and moves on to the next, harder part. So early songs stumble and the song gets better with
practice. The party ends after 180 game minutes and moves you back to town.

usage: python -I tools/perform.py [INSTRUMENT] [min_sp] [max_songs] [min_hp_pct] [--past]
  --past      keep playing past the target until the party ends (run 06)
  INSTRUMENT  name of an instrument on the map next to me, or none for the held one
  min_sp      stop when SP falls to this (default 6)
  max_songs   stop after this many songs (default 30)
  min_hp_pct  stop when HP falls below this percentage (default 70): bored listeners throw
              rocks, about 5 HP each from out of sight (run 05); heal and run it again
Stops at the target score, at the SP or HP floor, on a hostile in view, a window opening, or
a zone change (the party's time limit). At the time limit the game pauses (LayerPause, which
only a real key closes): `bridge.py closetop` ends it and the game moves you back to town.
Exit 0 at the target, the song limit, the SP floor or the party's end; 3 stopped for a decision
(a hostile, HP under the floor, a window); 1 refused (no instrument, no Play Music act).
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import ready, wait_until  # noqa: E402


def score():
    texts = call("texts", all=True)["data"]["texts"]
    for t in texts:
        m = re.search(r"Music Score: (-?\d+) of (\d+)", t)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None, None


def start(name):
    if name:
        hit = call("find", name=name, r=2, n=1)["data"]["hits"]
        if not hit:
            sys.exit(f"no {name!r} within 2 cells")
        dx, dz = hit[0]["dx"], hit[0]["dz"]
    else:
        dx, dz = 0, 0
    acts = call("acts", dx=dx, dz=dz, mode="all")["data"]["acts"]
    play = [a for a in acts if a["text"].startswith("Play Music")]
    if not play:
        sys.exit("no Play Music act: " + ", ".join(a["text"] for a in acts))
    call("do", i=play[0]["i"])


def song_gate(s, min_hp_pct, idle=False):
    """Why to stop, or None: common.ready (a hostile, HP under the floor, a window, a bad
    condition; busy only before the first song). The review of 2026-10-23 removed a duplicate HP
    test here; the hostile message below is this tool's own, so it isn't common.threat."""
    foes = [c["name"] for c in s.get("nearby") or [] if c.get("hostile")]
    if foes:
        # run 11: a furious guest (Samamer, Lv8 apprentice mage) paralyzed me and took 75 -> 8 HP
        # in two songs with lightning arrows and elemental scar. Don't play on: teleport away from
        # a caster, or leave the hall; killing a guest who was a Friend costs Karma -5
        return "a hostile in view (" + ", ".join(foes) + "): stop playing; teleport off a caster"
    return ready(s, hp=min_hp_pct, hunger=None, idle=idle, burden=None)


def main():
    past = "--past" in sys.argv  # run 06: keep playing to the party's end (Music exp, tips)
    a = [x for x in sys.argv[1:] if x != "--past"]
    name = a[0] if a and a[0].lower() != "none" else None
    min_sp = int(a[1]) if len(a) > 1 else 6
    max_songs = int(a[2]) if len(a) > 2 else 30
    min_hp = int(a[3]) if len(a) > 3 else 70
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    s = call("state")["data"]
    zone0 = s["zone"]["full"]
    sc, dest = score()
    print(f"start: score {sc}/{dest}  SP {s['pc']['sp']}  {s['pc']['date']}")
    why = "song limit"
    decision = False
    t = song_gate(s, min_hp, idle=True)  # before the first act: a window, busy, a hostile, HP
    if t:
        print("stopped:", t)
        sys.exit(3)
    for n in range(1, max_songs + 1):
        if s["pc"]["sp"] <= min_sp:
            why = f"SP {s['pc']['sp']} at the floor"
            break
        start(name)
        wait_until("frames", n=15, timeout=2000)  # the song starts
        seen = set(s.get("log") or [])
        notes = []
        t0 = time.time()
        while time.time() - t0 < 120:
            time.sleep(0.5)
            s = call("state")["data"]
            for line in s.get("log") or []:
                if line not in seen:
                    seen.add(line)
                    if not line.startswith("*") and "♪" not in line:
                        notes.append(line)
            if s["zone"]["full"] != zone0 or song_gate(s, min_hp):
                break
            if "PlayMusic" not in (s["pc"]["ai"] or ""):
                break
        # The song's result (Evaluate) lands a moment after the AI goes idle: read the score
        # only once it has settled (run 05: +0 read at once, then +80 on the next start).
        before = sc
        time.sleep(1.5)
        sc, dest = score()
        gain = (sc - before) if sc is not None and before is not None else None
        g = f"{gain:+d}" if gain is not None else "?"
        print(f"song {n}: {s['pc']['date']}  score {sc}/{dest} ({g})  SP {s['pc']['sp']}  "
              f"listeners {len(s.get('nearby') or [])}  | " + " / ".join(notes[-4:]))
        if s["zone"]["full"] != zone0:
            why = f"zone changed to {s['zone']['full']} (the party ended)"
            break
        t = song_gate(s, min_hp)
        if t:
            why, decision = t, True
            break
        if sc is not None and dest and sc >= dest and not past:
            why = "target reached"
            break
    print("stopped:", why)
    if decision:
        sys.exit(3)


if __name__ == "__main__":
    main()
