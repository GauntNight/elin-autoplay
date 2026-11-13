"""Play music in a town for Music skill exp and tips (run 46, G55's music lead).

The game (AI_PlayMusic, read 2026-11-12): holding an instrument, the right-click act on my own cell is "Play Music".
A song is ~26 turns (about 2 real seconds at x5). During it each listener in range may react: one who likes it gives
Music +50 skill exp (+10 in a user zone, such as home) and throws a tip; one who doesn't gives +10 and now and then a
rock. Interest falls as they listen, so a crowd tires. Music is a low skill (5 at the start of run 46), so its level-ups
come cheap, and each is 10-14 character exp.

usage: python -I tools/music.py [SONGS=200] [--instrument flute] [--min-sp 10] [--no-sleep] [--party-ok]
Refuses with the party along (run 46: karma 70 -> -45 over the Palmia stretches; allies answer thrown rocks and a kill
of a friendly townsperson is -5) unless --party-ok, and stops on any "Karma(-" line in the game log.
Holds the instrument, plays song after song; eats at the eat mark (farmday.eat_one) and sleeps at the SP floor (sleep.py,
the Rest ability without a bed). Stops (exit 3) on a hostile in view, HP under the loop floor, Hungry with no meal landed,
a sleep that didn't refill SP, a window it doesn't know, a song that wouldn't start, or runs/jobs/music.stop. Marks
itself "music" in runs/activity.csv. Exit 0 after SONGS songs.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from activity import mark  # noqa: E402
from common import THRESHOLDS, call, grab, pc, ready, run, setup, stop  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STOP = ROOT / "runs" / "jobs" / "music.stop"


def play():
    acts = (call("acts", dx=0, dz=0, mode="right").get("data") or {}).get("acts") or []
    hit = [a for a in acts if a["text"].startswith("Play Music")]
    if not hit:
        return False
    call("do", i=hit[0]["i"])
    time.sleep(0.5)
    for _ in range(240):
        if not str(pc().get("ai") or "").startswith("AI_PlayMusic"):
            return True
        time.sleep(0.25)
    return True


def main():
    setup()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    songs = int(args[0]) if args else 200
    inst = sys.argv[sys.argv.index("--instrument") + 1] if "--instrument" in sys.argv else "flute"
    min_sp = int(sys.argv[sys.argv.index("--min-sp") + 1]) if "--min-sp" in sys.argv else 10
    STOP.unlink(missing_ok=True)
    from common import data
    party = [c.get("name") for c in data("state").get("party") or [] if not c.get("pc")]
    if party and "--party-ok" not in sys.argv:
        # run 46: allies answer the listeners' thrown rocks, and a kill of a friendly townsperson is -5 karma
        stop(f"the party is along ({', '.join(party)}): play solo (send them home), or --party-ok")
    held = grab(inst)
    if not held:
        stop(f"no {inst} to hold")
    p0 = pc()
    mark("music", "start", note=f"{songs} songs, {held}")
    played, why = 0, ""
    try:
        for n in range(songs):
            if STOP.exists():
                why = "stop file"
                break
            # a hostile in view, HP, Hungry, a window: before each song (rocks from bored listeners are the risk)
            why = ready(hp=THRESHOLDS.get("loop_hp", 80), hunger=THRESHOLDS["hungry"], hostile_r=8)
            if why and "wait it out" in why:
                # run 46: ConDim (a thrown rock or a drink) ended the loop; elin-play's status rule is to stay put
                # until it clears: single turns, as ladder.condition_wait, at most 30
                for _ in range(30):
                    call("act", action="Wait")
                    time.sleep(0.4)
                    why = ready(hp=THRESHOLDS.get("loop_hp", 80), hunger=THRESHOLDS["hungry"], hostile_r=8)
                    if not why or "wait it out" not in why:
                        break
                if not why:
                    grab(inst)
            if why:
                break
            if pc().get("hunger", 0) >= THRESHOLDS["eat_at"]:
                # every loop eats on every branch (run 18 starved in a loop with food in the bag)
                from farmday import eat_one
                if not eat_one():
                    why = f"hunger {pc().get('hunger')} and no meal landed"
                    break
                grab(inst)
            if (pc().get("sp") or 0) <= min_sp:
                if "--no-sleep" in sys.argv:
                    why = f"SP at the floor {min_sp}"
                    break
                # SP comes back only from sleep: the Rest ability where I stand (sleep.py refuses at its hunger mark)
                out = run("sleep.py", timeout=600)
                print("  sleep: " + (str(out).strip().splitlines() or ["?"])[-1][:100], flush=True)
                from farmday import close_report
                close_report()
                if out.rc or (pc().get("sp") or 0) <= min_sp:
                    why = f"SP {pc().get('sp')} at the floor and the sleep didn't refill it (rc {out.rc})"
                    break
                grab(inst)
            if not play():
                why = "no Play Music act (the instrument not held?)"
                break
            played += 1
            # run 46: karma fell ~100 over the Palmia music stretches (70 -> -45 by 20:21) with the party along: a party
            # kill of a friendly listener who threw a rock is -5 (Chara.Die), NPC property in hand -1 (HoldCard). Any karma
            # loss in the log ends the loop, and the loop refuses to start with the party along (below)
            from common import data
            log = data("state").get("log") or []
            if any("Karma(-" in ln for ln in log[-12:]):
                why = "karma lost during the music: " + " / ".join(ln for ln in log[-12:] if "Karma" in ln or "kill" in ln)[:160]
                break
            if n % 20 == 19:
                p = pc()
                print(f"  {played} songs: exp {p0['exp']} -> {p['exp']}, gold {p0.get('gold')} -> {p.get('gold')}, SP {p['sp']}, HP {p['hp']}/{p['maxHp']}", flush=True)
    finally:
        p = pc()
        mark("music", "end", note=f"{played} songs")
        print(f"done: {played} songs; Lv{p['lv']} exp {p0['exp']} -> {p['exp']}; gold {p0.get('gold')} -> {p.get('gold')}; "
              f"SP {p0['sp']} -> {p['sp']}; {p['date']}", flush=True)
    if why:
        stop(why)
    return 0


if __name__ == "__main__":
    sys.exit(main())
