"""Start this repo on a character (2026-11-04, the user: a first run for other players; logs stay on the player's PC). A game's
logs and records are gitignored, so a fresh clone has none: this makes them from templates/. If another game's records are here,
they first move to archive/NAME/ (gitignored too). Either way the numbers tuned to a character (the floor gate, the route limit)
drop to a new character's, and runs/no-base.txt makes the home routines wait for a base. What was learned stays: the facts,
lessons, skills and tools.

Run numbers carry on past the highest one in the facts (they're tagged by run, so reusing a number would mix them).

usage: python -I tools/newgame.py                 show what it would do
       python -I tools/newgame.py --yes           do it
Exit: 0 done (or shown), 1 refused.
"""
import csv
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
KNOWLEDGE = ROOT / "knowledge"
TEMPLATES = ROOT / "templates"
RECORDS = ("goals.md", "goals-done.md", "milestones.csv", "fights.csv", "travel.csv")  # a game's records in knowledge/
WORKING = ("captures", "jobs", "pages")  # folders in runs/ that belong to this PC, not to a game
START = {"max_danger": 3, "route_max": 5}  # the first game: danger 3-5 floors around Lv7-9, 7 at Lv12, 14 at Lv35
START_LEVEL = 1


def last_run():
    """The highest run number in the facts and in this PC's records."""
    last = 0
    facts = KNOWLEDGE / "facts.jsonl"
    if facts.exists():
        for line in facts.read_text(encoding="utf-8").splitlines():
            if line.strip():
                run = str(json.loads(line).get("run", ""))
                if run.isdigit():
                    last = max(last, int(run))
    metrics = RUNS / "metrics.csv"
    if metrics.exists():
        with metrics.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                if r["run"].isdigit():
                    last = max(last, int(r["run"]))
    return last


def last_game():
    """The archive name of the records here, or None when there are none (a fresh clone)."""
    if not (RUNS / "metrics.csv").exists() and not (KNOWLEDGE / "goals.md").exists():
        return None
    name = None
    p = RUNS / "runstats.csv"
    if p.exists():
        with p.open(encoding="utf-8", newline="") as fh:
            rows = [r for r in csv.DictReader(fh) if r.get("character")]
        if rows:
            name = re.sub(r"[^a-z0-9]+", "-", rows[-1]["character"].split("(")[0].strip().lower()).strip("-")
    return name or f"before-run-{last_run() + 1}"


def set_number(text, key, value):
    new, n = re.subn(rf'("{key}": )\d+,', rf"\g<1>{value},", text, count=1)
    if not n:
        sys.exit(f"tools/common.py: no {key} to set")
    return new


def main():
    apply = "--yes" in sys.argv[1:]
    name, next_run = last_game(), last_run() + 1
    if not TEMPLATES.is_dir():
        print("refused: templates/ is missing.")
        return 1
    archive = ROOT / "archive" / name if name else None
    if archive and archive.exists():
        print(f"refused: {archive.relative_to(ROOT)} already exists.")
        return 1
    if archive:
        print(f"this PC holds a game's records ({name}): they move to archive/{name}/")
    else:
        print("no records here yet (a fresh clone): nothing to set aside")
    print(f"makes blank records from templates/: runs/*.csv, and knowledge/ {', '.join(RECORDS)}. The next run is {next_run:02}.")
    print(f"resets: max_danger -> {START['max_danger']}, route_max -> {START['route_max']} (tools/common.py and elin-play's table)")
    print("keeps: facts.jsonl, lessons.md, the skills, the tools")
    print("home routines refuse until there's a base (runs/no-base.txt): tools/home.py holds the last game's coordinates")
    if not apply:
        print("nothing changed: add --yes to do it.")
        return 0

    if archive:
        (archive / "runs").mkdir(parents=True)
        if RUNS.is_dir():
            for f in sorted(RUNS.iterdir()):
                if f.name not in WORKING:
                    shutil.move(str(f), str(archive / "runs" / f.name))
        for f in RECORDS:
            if (KNOWLEDGE / f).exists():
                shutil.move(str(KNOWLEDGE / f), str(archive / f))
    for sub in WORKING:
        (RUNS / sub).mkdir(parents=True, exist_ok=True)
    for f in (TEMPLATES / "runs").iterdir():
        shutil.copyfile(f, RUNS / f.name)
    for f in (TEMPLATES / "knowledge").iterdir():
        shutil.copyfile(f, KNOWLEDGE / f.name)

    common = ROOT / "tools" / "common.py"
    text = common.read_bytes().decode("utf-8")
    for key, value in START.items():
        text = set_number(text, key, value)
    common.write_bytes(text.encode("utf-8"))
    skill = ROOT / ".claude" / "skills" / "elin-play" / "SKILL.md"
    text = skill.read_bytes().decode("utf-8")
    text, n = re.subn(r"\*\*\d+ at Lv\d+\*\*", f"**{START['max_danger']} at Lv{START_LEVEL}**", text, count=1)
    if not n:
        print("elin-play: no floor-gate number found to set: hygiene.py will flag the table")
    skill.write_bytes(text.encode("utf-8"))
    (RUNS / "no-base.txt").write_text(
        "This game has no base yet: tools/home.py still holds the last game's coordinates, so the home routines refuse.\n"
        "Once the boxes exist, put their cells in tools/home.py and delete this file.\n", encoding="utf-8", newline="\n")
    print(f"done. The next run is {next_run:02}. tools/common.py and elin-play's table changed: commit them.")
    if archive:
        print(f"Undo: move archive/{name}/ back, delete runs/no-base.txt, git checkout tools/common.py .claude/skills/elin-play/SKILL.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
