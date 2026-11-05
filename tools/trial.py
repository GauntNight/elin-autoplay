"""Trials: a series of new level 1 characters that put the rules through their paces while the player's own game stays safe
(the user, 2026-11-05: four 2-hour runs from level 1, "Make sure we keep Rolord"). A game's records live in runs/ and knowledge/,
and the tools read them there, so the kept game's records are parked in archive/NAME/ with a checksum of every file, and the trials
get blank ones. Its save is never loaded: new characters take the game's next free world_N. The trial's floor gate and route limit
go in runs/thresholds.json (gitignored, read by common.py), so no tracked file changes and the numbers leave with the records.

usage: python -I tools/trial.py park [--yes]          show or do the parking (a second park is refused)
       python -I tools/trial.py start RUN "CHARACTER" WORLD   start a trial's clock: minutes count from here
       python -I tools/trial.py mark "LABEL" [--note TEXT]    a milestone at the current minute, in runs/milestones.csv
       python -I tools/trial.py sample [--every 20] [--max 125]  log the state every N seconds until the window or the game ends;
                                                                 a level-up marks itself. Run it in the background
       python -I tools/trial.py table                 minutes to each level and the totals, per trial, against the baselines
       python -I tools/trial.py status                what is parked and which trial is running
       python -I tools/trial.py restore [--yes]       the trials' records to archive/trials-DATE/, the kept game's back, every
                                                      checksum verified (exit 1 and nothing more removed if one differs)
Exit: 0 done (or shown), 1 refused, 2 the bridge.
"""
import csv
import hashlib
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import newgame  # noqa: E402

ROOT = newgame.ROOT
RUNS = newgame.RUNS
KNOWLEDGE = newgame.KNOWLEDGE
ARCHIVE = ROOT / "archive"
PARKED = ARCHIVE / "PARKED.txt"  # the name of the parked game: a marker a session that died midway can find
PLAYER = ROOT / "player.md"
TRIAL = RUNS / "trial.json"
SAMPLES = RUNS / "trial_samples.csv"
SAMPLE_COLS = ["run", "minutes", "date", "lv", "exp", "exp_next", "exp_total", "hp", "max_hp", "sp", "hunger", "gold", "zone"]
START_NUMBERS = dict(newgame.START)
BASELINES = [  # minutes of play to each level: where the comparison starts
    ("Rolord (runs 03-08, Juere warrior)", {2: 250, 3: 610, 5: 740, 6: 1027, 7: 1332, 8: 1982, 9: 2277, 10: 2642}),
    ("Lefess (the 2026-11-04 test, Lich Pianist)", {}),  # level 1 at 60 minutes, one death at 30
]


def now():
    return datetime.now().astimezone()


def total_exp(lv, exp):
    """Character exp since level 1 (ExpToNext = 50 + 30 x level: fact #481, and Rolord's 1,809 at Lv10)."""
    return sum(50 + 30 * x for x in range(1, lv)) + exp


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def kept_files():
    """Every file that parking moves or copies, relative to the root."""
    out = [p for p in sorted(RUNS.rglob("*")) if p.is_file() and p.relative_to(RUNS).parts[0] not in newgame.WORKING]
    out += [KNOWLEDGE / f for f in newgame.RECORDS if (KNOWLEDGE / f).exists()]
    if PLAYER.exists():
        out.append(PLAYER)
    return out


def parked_name():
    return PARKED.read_text(encoding="utf-8").strip() if PARKED.exists() else None


def park(apply):
    if parked_name():
        print(f"refused: {parked_name()} is already parked in archive/ (trial.py restore brings it back).")
        return 1
    name = newgame.last_game()
    if not name:
        print("refused: no game's records here to park: a new player starts with elin-setup.")
        return 1
    dest = ARCHIVE / name
    if dest.exists():
        print(f"refused: {dest.relative_to(ROOT)} already exists.")
        return 1
    files = kept_files()
    print(f"{name}: {len(files)} files, {sum(p.stat().st_size for p in files) // 1024} KB to archive/{name}/, each with its checksum; the save is not touched")
    print(f"then blank records, runs/no-base.txt and runs/thresholds.json ({START_NUMBERS})")
    if not apply:
        print("nothing changed: add --yes to do it.")
        return 0
    manifest = [(p.relative_to(ROOT).as_posix(), sha(p)) for p in files]
    dest.mkdir(parents=True)
    (dest / "MANIFEST.sha256").write_text("".join(f"{h}  {r}\n" for r, h in manifest), encoding="utf-8", newline="\n")
    if PLAYER.exists():
        shutil.copyfile(PLAYER, dest / "player.md")
    PARKED.write_text(name + "\n", encoding="utf-8", newline="\n")  # first: a crash from here on still says what to restore
    newgame.set_aside(dest)
    newgame.make_blank()
    (RUNS / "thresholds.json").write_text(json.dumps(START_NUMBERS) + "\n", encoding="utf-8", newline="\n")
    newgame.mark_no_base()
    print(f"parked. Bring it back with: python -I tools/trial.py restore --yes (player.md: write the trial's now; {name}'s copy is in the archive)")
    return 0


def restore(apply):
    name = parked_name()
    if not name:
        print("refused: nothing is parked.")
        return 1
    src = ARCHIVE / name
    lines = [ln.split("  ", 1) for ln in (src / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines() if ln.strip()]
    dest = ARCHIVE / f"trials-{now():%Y-%m-%d}"
    n = 2
    while dest.exists():
        dest = ARCHIVE / f"trials-{now():%Y-%m-%d}-{n}"
        n += 1
    print(f"the trials' records -> {dest.relative_to(ROOT)}/; {name}'s {len(lines)} files back in place")
    if not apply:
        print("nothing changed: add --yes to do it.")
        return 0
    # the trials' records out first, under the same rule newgame uses
    dest.mkdir(parents=True)
    newgame.set_aside(dest)
    if PLAYER.exists():
        shutil.copyfile(PLAYER, dest / "player.md")
    # the kept game's records back: runs/* and the knowledge records, then player.md
    for f in sorted((src / "runs").iterdir()):
        shutil.move(str(f), str(RUNS / f.name))
    for f in newgame.RECORDS:
        if (src / f).exists():
            shutil.move(str(src / f), str(KNOWLEDGE / f))
    if (src / "player.md").exists():
        shutil.copyfile(src / "player.md", PLAYER)
    bad = [r for h, r in lines if not (ROOT / r).exists() or sha(ROOT / r) != h]
    if bad:
        print(f"CHECK FAILED on {len(bad)} files, first: {bad[:5]}. archive/{name}/ and PARKED.txt are left in place.")
        return 1
    print(f"verified: all {len(lines)} checksums match.")
    (src / "MANIFEST.sha256").replace(dest / f"{name}.MANIFEST.sha256")
    (src / "player.md").unlink(missing_ok=True)
    shutil.rmtree(src / "runs", ignore_errors=True)  # empty by now
    src.rmdir()
    PARKED.unlink()
    return 0


def current():
    try:
        return json.loads(TRIAL.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def minutes(t=None):
    t = t or current()
    return round((now() - datetime.fromisoformat(t["start"])).total_seconds() / 60, 1) if t else None


def start(args):
    if not parked_name():
        print("refused: nothing is parked: trial.py park first, so a trial's records can't mix with a kept game's.")
        return 1
    if len(args) < 3:
        print('usage: trial.py start RUN "CHARACTER" WORLD')
        return 1
    TRIAL.write_text(json.dumps({"run": args[0], "character": args[1], "world": args[2], "start": now().isoformat()}) + "\n",
                     encoding="utf-8", newline="\n")
    print(f"trial {args[0]}: {args[1]} in {args[2]}, the clock runs from {now():%H:%M:%S}")
    return 0


def mark(label, note=""):
    t = current()
    if not t:
        print("refused: no trial running.")
        return 1
    m = minutes(t)
    with (RUNS / "milestones.csv").open("a", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerow([t["run"], label, m, "", "", "", note])
    print(f"{t['run']} +{m} min: {label}")
    return 0


def sample(every, cap):
    from bridge import call  # noqa: E402 (only this command needs the game)
    t = current()
    if not t:
        print("refused: no trial running.")
        return 1
    new = not SAMPLES.exists()
    with SAMPLES.open("a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(SAMPLE_COLS)
        last_lv, dead_since = None, None
        end = time.time() + cap * 60
        while time.time() < end:
            try:
                s = call("state")["data"]
                p = s["pc"]
                dead_since = None
            except SystemExit:  # bridge.py exits 2 when the game isn't answering
                dead_since = dead_since or time.time()
                if time.time() - dead_since > 180:
                    print("the bridge has been silent for 3 minutes: the game is closed")
                    return 0
                time.sleep(every)
                continue
            except Exception as e:  # noqa: BLE001 (a sampler must never die on a loading screen)
                print(f"skip: {type(e).__name__}: {e}"[:160])
                time.sleep(every)
                continue
            lv, exp = p.get("lv"), p.get("exp") or 0
            if lv is not None:
                w.writerow([t["run"], minutes(t), p.get("date"), lv, exp, p.get("expNext"), total_exp(lv, exp), p.get("hp"), p.get("maxHp"),
                            p.get("sp"), p.get("hunger"), p.get("gold"), str((s.get("zone") or {}).get("name", ""))])
                fh.flush()
                if last_lv is not None and lv > last_lv:
                    mark(f"level {lv}")
                last_lv = lv
            time.sleep(every)
    print(f"the sample window of {cap} minutes is over")
    return 0


def table():
    rows = []
    if SAMPLES.exists():
        with SAMPLES.open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
    runs = sorted({r["run"] for r in rows})
    for label, levels in BASELINES:
        print(f"{label}: " + (", ".join(f"Lv{k} {v}" for k, v in levels.items()) or "never above Lv1 in its hour"))
    for run in runs:
        rr = []
        for r in (r for r in rows if r["run"] == run):
            if rr and int(r["exp_total"]) < int(rr[-1]["exp_total"]):  # a sampler still running when the next character started
                break
            rr.append(r)
        first = {}
        for r in rr:
            first.setdefault(int(r["lv"]), float(r["minutes"]))
        end, m = rr[-1], float(rr[-1]["minutes"])
        rate = int(end["exp_total"]) / m * 60 if m else 0
        low = min((int(r["hp"]) * 100 // max(int(r["max_hp"]), 1)) for r in rr if r["hp"] and r["max_hp"])
        print(f"run {run}: " + ", ".join(f"Lv{k} {v:.0f}" for k, v in sorted(first.items()) if k > 1)
              + f" | end +{m:.0f} min Lv{end['lv']}, exp {end['exp_total']} ({rate:.0f} an hour), {end['gold']} orens, lowest HP {low}%")
    return 0


def status():
    print("parked: " + (parked_name() or "nothing"))
    t = current()
    print(f"trial: {t['run']} {t['character']} ({t['world']}), +{minutes(t)} min" if t else "trial: none running")
    return 0


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    cmd = a[0] if a else "status"
    apply = "--yes" in a

    def opt(name, default):
        return type(default)(a[a.index(name) + 1]) if name in a else default
    if cmd == "park":
        return park(apply)
    if cmd == "restore":
        return restore(apply)
    if cmd == "start":
        return start(a[1:])
    if cmd == "mark":
        return mark(a[1], opt("--note", "")) if len(a) > 1 else 1
    if cmd == "sample":
        return sample(opt("--every", 20), opt("--max", 125))
    if cmd == "table":
        return table()
    if cmd == "status":
        return status()
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
