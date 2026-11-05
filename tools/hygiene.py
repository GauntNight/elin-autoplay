"""Drift check for the repo (the review of 2026-10-19 set the baseline; the review of 2026-10-23
added the enforcement, age and threshold checks). Run at every close-out: it prints what has
crept back since, so a full review is needed every 10-20 runs, not every one.

usage: python -I tools/hygiene.py        exit 0 when clean, 1 with findings (advisory at close-out)

Findings (exit 1; each a line a review had to fix by hand once):
  - a tool that spawns subprocesses itself instead of common.run (run() was copied 14 times)
  - a goto followed by a fixed sleep (walk() replies on arrival)
  - a skill or CLAUDE.md naming a tool that no longer exists
  - facts whose `where` isn't one place name, or whose subject has an alias
  - lessons.md's Live section over 35 entries; a skill over 350 lines; goals.md over 500 lines
  - HP-percent thresholds stated in a skill other than elin-play (one table, one place)
  - a new duplicate of a helper common.py already has
  - errors.csv (2026-10-23, R1): a row from before the latest run whose rule existed ("yes" or
    "partly") and whose prevented_now_by names no tool: ".py", "bridge", or a tool's bare name
    opening the text or a clause ("springday skips cats", "throw.hold ...") count as naming one;
    "(rule ...)" and "lessons: ..." don't. The row number is the file's line number.
  - lessons.md (R2): a Live lesson whose newest run tag ("(NN)", "(NN, MM)", a "Run NN" mention,
    or the "Run NN" heading above it) is 3+ runs older than the latest run in metrics.csv
  - THRESHOLDS (R6): common.THRESHOLDS against delve.MAX_DANGER, ladder.DEFAULT_MAX_DANGER (the
    gate or one less), hunt.DEFAULT_DANGER (2); farmday.py and minewalls.py use
    THRESHOLDS["hungry"] or state no other hunger literal; sleep.py uses THRESHOLDS["sleep_hunger"]
    or its number; elin-play's thresholds table states the same floor gate, Hungry, kamikaze
    distance and heal-to numbers (a regex per row; an unreadable row is a finding too)
  - the milestone lock (the run score's rules, the user 2026-10-26): a milestone in goals.md that
    knowledge/milestones.csv doesn't list (added or split without the user's yes), and one ticked
    since its approval without its run: `- [x] Mn (DATE, run NN)` (stats.py counts those)
Advisories (under "advisory:", the exit code untouched; the 2026-10-23 tools review, section 5):
  - a Live lesson holding a price or count (a number is a fact: kb.py add)
  - helper copies beyond the six above (top, pc, me, state, hold, put_away, walk_beside, threat,
    last, norm, has); a NoGoal poll loop (common.wait_idle); .splitlines()[-1] on a tool's output
    (common.last); a "stop" print in a file with no exit 3; a tool no skill and no other tool
    names; walk(hp=0) outside the home-only scripts; over 6 time.sleep calls in one script;
    run("close.py") right after run("box.py") (box.py closes itself)
"""
import csv
import importlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
RUNS = ROOT / "runs"
SKILLS = ROOT / ".claude" / "skills"
sys.path.insert(0, str(TOOLS))
from kb import SUBJECT_ALIASES, WHERE_ALIASES, all_facts, canon_where  # noqa: E402

COMMON_HELPERS = ("def run(", "def walk(", "def wait_idle(", "def cells(", "def pick(", "def matches(")
THIN_WRAPPERS = {"farmday.py", "shearwalk.py", "packcheck.py"}  # keep a signature-compatible run()
# the review of 2026-10-23: 29 more copies of these across 20 scripts (advisory until each is folded)
MORE_HELPERS = ("def top(", "def pc(", "def me(", "def state(", "def hold(", "def put_away(",
                "def walk_beside(", "def threat(", "def last(", "def norm(", "def has(")
# tools nothing need name: the shared module, the data and the record keepers, the user's rules
UNNAMED_OK = {"common.py", "home.py", "job.py", "kb.py", "stats.py", "hygiene.py", "stopjob.py", "activity.py",
              "summary_page.py", "elin_eye.py", "wait_ingame.py", "bridge.py"}
# scripts that walk only at home or in a town yard, where walk(hp=0) is fine (the fields have no foes
# when the home loops run; a nefia or a road walk keeps the 60% floor)
HOME_ONLY = {"farm.py", "farmday.py", "fish.py", "firstcraft.py", "paytax.py", "place.py", "ration.py",
             "reap.py", "unpack.py", "view.py"}
LESSON_AGE = 3  # runs: a Live lesson older than this is promoted, made a fact, superseded or dropped
MAX_SLEEPS = 6
LESSONS = ROOT / "knowledge" / "lessons.md"


def run_dates():
    """{run number: date} from metrics.csv."""
    with (RUNS / "metrics.csv").open(encoding="utf-8", newline="") as fh:
        return {int(r["run"]): r["date"] for r in csv.DictReader(fh) if r["run"].isdigit()}


TAG_ITEM = r"\d{2}|review \d{4}-\d{2}-\d{2}"  # "(18)", "(14, 17)", "(14, 17, review 2026-10-23)"


# The review of 2026-10-30: errors.csv had 24 domain spellings (skill names, "pack" and "elin-pack", "home" and
# "elin-home"), so "repeats in a skill's domain" (the skill verdicts) counted nothing. One fixed set, by the game
# area the error belongs to, whatever tool caused it.
DOMAINS = ("combat", "dungeon", "pack", "food", "travel", "home", "crew", "jobs", "gear", "thief", "time", "tools")


def errors_check(findings, latest, stems):
    """R1: a rule that existed and still has no tool behind it, one run later; R5: the domain is one of DOMAINS."""
    p = RUNS / "errors.csv"
    if not p.exists():
        return
    names = "|".join(sorted(map(re.escape, stems), key=len, reverse=True))
    named_re = re.compile(rf"(?:^|; |, )(?:{names})\b|\b(?:{names})(?:\.|'s)")
    with p.open(encoding="utf-8", newline="") as fh:
        for n, r in enumerate(csv.DictReader(fh), 2):
            if (r.get("domain") or "").strip() not in DOMAINS:
                findings.append(f"errors.csv row {n}: domain {r.get('domain')!r} is not one of {', '.join(DOMAINS)}")
            rule = (r.get("rule_existed") or "").strip().lower()
            if not rule.startswith(("yes", "partly")) or not (r.get("run") or "").isdigit():
                continue
            if int(r["run"]) >= latest:
                continue
            by = (r.get("prevented_now_by") or "").strip()
            if ".py" in by or "bridge" in by.lower() or named_re.search(by):
                continue
            findings.append(f"errors.csv row {n} (run {r['run']}): a rule existed and nothing enforces it yet: name the tool")


def live_entries(dates):
    """lessons.md's Live entries: (line, text, newest run or None). A '- ' line starts an entry,
    indented lines continue it; a 'Run NN' heading gives an untagged entry its run; a "review
    YYYY-MM-DD" tag counts as the latest run on or before that date, so it ages like one."""
    def run_of(item):
        if item.isdigit():
            return int(item)
        day = item.split()[-1]
        before = [run for run, d in dates.items() if d <= day]
        return max(before) if before else None

    text = LESSONS.read_text(encoding="utf-8")
    pre, live = text.split("## Live", 1)
    live = live.split("## Promoted", 1)[0]
    first = pre.count("\n") + 1
    entries, heading_run, cur = [], None, None
    for i, line in enumerate(live.splitlines(), first):
        if line.startswith("- "):
            cur = [i, line[2:].strip(), None]
            entries.append(cur)
        elif line.startswith("  ") and cur:
            cur[1] += " " + line.strip()
        else:
            cur = None
            if line.strip() and not line.startswith("#"):
                m = re.search(r"\b[Rr]un (\d{2})\b", line)
                heading_run = m.group(1) if m else None
        if cur and cur[2] is None:
            cur[2] = heading_run
    out = []
    for line, body, heading in entries:
        tags = [run_of(x) for grp in re.findall(rf"\(((?:{TAG_ITEM})(?:, (?:{TAG_ITEM}))*)\)", body)
                for x in grp.split(", ")]
        tags += [int(x) for x in re.findall(r"\b[Rr]un (\d{2})\b", body)]
        tags = [t for t in tags if t is not None]
        newest = max(tags) if tags else (int(heading) if heading else None)
        out.append((line, body, newest))
    return out


def lessons_checks(findings, advisories, dates):
    latest = max(dates, default=0)  # no logs yet: a new game (docs/new-game.md)
    rel = LESSONS.relative_to(ROOT).as_posix()
    for line, body, newest in live_entries(dates):
        short = body[:60] + ("..." if len(body) > 60 else "")
        if newest is None:
            advisories.append(f"{rel}:{line}: a Live lesson with no run tag: add (NN) ({short})")
        elif newest <= latest - LESSON_AGE:
            findings.append(f"{rel}:{line}: a Live lesson from run {newest:02} is {LESSON_AGE}+ runs old: "
                            f"promote, make it a fact, supersede or drop ({short})")
        untagged = re.sub(rf"\((?:{TAG_ITEM})(?:, (?:{TAG_ITEM}))*\)", "", body)
        m = re.search(r"\d[\d,]* orens|x\d|\+\d", untagged)
        if m:
            advisories.append(f"{rel}:{line}: a number is a fact: kb.py add ('{m.group(0)}' in: {short})")


def milestones_check(findings, goals):
    """The scoring rules in goals.md: every milestone is one the user approved, and a tick names its run."""
    with (ROOT / "knowledge" / "milestones.csv").open(encoding="utf-8", newline="") as fh:
        lock = {(r["goal"], r["milestone"]): r for r in csv.DictReader(fh)}
    goal = None
    for i, line in enumerate(goals.splitlines(), 1):
        m = re.match(r"### (G\d+)\.", line)
        if m:
            goal = m.group(1)
        m = re.match(r"- \[(.)\] (M\d+)\b", line)
        if not (m and goal):
            continue
        row = lock.get((goal, m.group(2)))
        if row is None:
            findings.append(f"knowledge/goals.md:{i}: {goal} {m.group(2)} isn't in knowledge/milestones.csv: "
                            "a milestone is added or split only with the user's yes")
        elif m.group(1) == "x" and row["state_at_approval"] != "done" and not re.match(r"- \[x\] M\d+ \([^)]*\brun \d+\)", line):
            findings.append(f"knowledge/goals.md:{i}: {goal} {m.group(2)} ticked without its run: write (DATE, run NN)")


def thresholds_check(findings):
    """R6: the tools' constants and elin-play's table against common.THRESHOLDS."""
    try:
        from common import THRESHOLDS as T
    except Exception as e:  # noqa: BLE001
        findings.append(f"common.py: THRESHOLDS can't be imported ({type(e).__name__}: {e})")
        return

    def attr(mod, name):
        try:
            m = importlib.import_module(mod)
        except BaseException as e:  # noqa: BLE001 - a module that exits or raises on import is a finding
            findings.append(f"{mod}.py: import failed in hygiene ({type(e).__name__}: {e}); THRESHOLDS can't be checked against it")
            return None
        if not hasattr(m, name):
            findings.append(f"{mod}.py: no {name} (the 2026-10-23 review asks for it); THRESHOLDS can't be checked against it")
            return None
        return getattr(m, name)

    v = attr("delve", "MAX_DANGER")
    if v is not None and v != T["max_danger"]:
        findings.append(f"delve.py: MAX_DANGER {v} != THRESHOLDS max_danger {T['max_danger']}")
    v = attr("ladder", "DEFAULT_MAX_DANGER")
    gate = (T["max_danger"], T["max_danger"] - T["unattended_minus"])
    if v is not None and v not in gate:
        findings.append(f"ladder.py: DEFAULT_MAX_DANGER {v} not in {gate} (THRESHOLDS max_danger, unattended_minus)")
    v = attr("hunt", "DEFAULT_DANGER")
    if v is not None and v != 2:
        findings.append(f"hunt.py: DEFAULT_DANGER {v} != 2 (elin-play's hunt row)")
    known = {T["hungry"], T["eat_at"], T["sleep_hunger"]}
    for name in ("farmday.py", "minewalls.py"):
        p = TOOLS / name
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8")
        if 'THRESHOLDS["hungry"]' in s:
            continue
        for m in re.finditer(r"hunger\"?\]?\s*>=\s*(\d+)", s):
            if int(m.group(1)) not in known:
                line = s[:m.start()].count("\n") + 1
                findings.append(f"{name}:{line}: a hunger literal {m.group(1)}; THRESHOLDS hungry is {T['hungry']} (use it)")
    p = TOOLS / "sleep.py"
    if p.exists():
        s = p.read_text(encoding="utf-8")
        if 'THRESHOLDS["sleep_hunger"]' not in s:
            for m in re.finditer(r"hunger\"?\]?\s*>=\s*(\d+)", s):
                if int(m.group(1)) != T["sleep_hunger"]:
                    line = s[:m.start()].count("\n") + 1
                    findings.append(f"sleep.py:{line}: a hunger literal {m.group(1)}; THRESHOLDS sleep_hunger is {T['sleep_hunger']}")
    skill = SKILLS / "elin-play" / "SKILL.md"
    if not skill.exists():
        findings.append("elin-play/SKILL.md is missing: the thresholds table can't be checked")
        return
    rel = skill.relative_to(ROOT).as_posix()
    lines = skill.read_text(encoding="utf-8").splitlines()
    table = [(i, ln) for i, ln in enumerate(lines, 1) if ln.startswith("|")]

    def row_number(what, label_re, patterns, want):
        for i, ln in table:
            if not re.search(label_re, ln, re.I):
                continue
            for pat in patterns:
                ms = re.findall(pat, ln)
                if ms:
                    if int(ms[-1]) != want:
                        findings.append(f"{rel}:{i}: the thresholds table says {what} {ms[-1]}, THRESHOLDS say {want}")
                    return
            findings.append(f"{rel}:{i}: the thresholds table's {what} number can't be read (THRESHOLDS say {want})")
            return
        findings.append(f"{rel}: no thresholds-table row for {what} (THRESHOLDS say {want})")

    from common import TRACKED_THRESHOLDS as TT  # the table states the tracked numbers: a trial's runs/thresholds.json is that game's
    row_number("the floor gate", r"floor gate|MAX_DANGER",
               [r"\*\*(\d+) at Lv", r"MAX_DANGER`?\D{0,16}?(\d+)", r"gate\D{0,20}?(\d+)"], TT["max_danger"])
    row_number("Hungry", r"^\| Status", [r"Hungry \((\d+)\+?\)", r"Hungry\D{0,8}?(\d+)"], T["hungry"])
    row_number("the kamikaze distance", r"Suicide attackers|kamikaze",
               [r"from \*{0,2}(\d+)\+ cells", r"(\d+)\+? cells"], T["kamikaze_dist"])
    row_number("heal-to", r"Leave the floor|heal to", [r"heal to (\d+)%"], T["heal_to"])


def main():
    if not (RUNS / "metrics.csv").exists():  # logs are gitignored: a fresh clone has none
        print("no records yet on this PC: a new player starts with the elin-setup skill (tools/newgame.py --yes)")
        return
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    findings, advisories = [], []
    tools = {p.name: p for p in TOOLS.glob("*.py")}
    existing = set(tools)
    stems = {p.stem for p in tools.values()}
    sources = {n: p.read_text(encoding="utf-8") for n, p in tools.items()}
    dates = run_dates()
    latest = max(dates, default=0)  # no logs yet: a new game (docs/new-game.md)

    for name in sorted(tools):
        p, s = tools[name], sources[name]
        # run 37's close: a heredoc had turned r"\b" into a backspace in item.py (run 30) and farmday.py (run 34), so the
        # shield guard and the gear-word filter never matched: a control character in a tool's source is a finding
        for i, ln in enumerate(s.splitlines(), 1):
            bad = sorted({f"0x{ord(ch):02x}" for ch in ln if ord(ch) < 32 and ch not in "\t\r"})
            if bad:
                findings.append(f"{name}:{i}: control character {', '.join(bad)} (a backslash lost in a heredoc?)")
        if name in ("common.py", "hygiene.py", "stopjob.py", "summary_page.py", "kb.py", "elin_eye.py",
                    "stats.py", "offcheck.py", "ollama_stop.py", "publishcheck.py", "newgame.py"):
            continue  # stopjob's and ollama_stop's taskkill are the user's rules; the others never talk to the game (stats.py and publishcheck: git log; offcheck: the process list)
        if "subprocess.run(" in s:
            findings.append(f"{name}: spawns a subprocess itself; use common.run")
        for m in re.finditer(r'call\("goto"[^\n]*\n(?:[^\n]*\n){0,2}[^\n]*time\.sleep\(', s):
            line = s[:m.start()].count("\n") + 1
            findings.append(f"{name}:{line}: a goto followed by a fixed sleep; use common.walk")
        for h in COMMON_HELPERS:
            wrapper = (name in THIN_WRAPPERS and h == "def run(") or (h == "def walk(" and "common_walk(" in s)
            if h in s and not wrapper:  # a thin wrapper over common's helper is fine
                findings.append(f"{name}: defines {h.rstrip('(')}() again; import it from common")
        if name == "bridge.py":
            continue  # norm() and call() live there
        # the advisories of the 2026-10-23 tools review
        for h in MORE_HELPERS:
            if h in s:
                advisories.append(f"{name}: defines {h[4:].rstrip('(')}() again; common.py has it")
        src_lines = s.splitlines()
        for m in re.finditer(r'startswith\(\(?"NoGoal"', s):
            at = s[:m.start()].count("\n")
            before = src_lines[max(0, at - 12):at + 1]
            around = src_lines[max(0, at - 12):at + 8]
            if any(re.match(r"\s*(while|for)\b", ln) for ln in before) and any("time.sleep(" in ln for ln in around):
                advisories.append(f"{name}:{at + 1}: a NoGoal poll loop; use common.wait_idle")
        for m in re.finditer(r"\.splitlines\(\)\[-1\]", s):
            advisories.append(f"{name}:{s[:m.start()].count(chr(10)) + 1}: .splitlines()[-1] on an output; use common.last")
        if re.search(r"""print\(f?["'](?:stop|stopping|stopped)[: ]""", s) and "sys.exit(3)" not in s \
                and not re.search(r"(?<!def )\bstop\(", s):
            advisories.append(f"{name}: prints a stop with no exit 3 (sys.exit(3) or common.stop)")
        if name not in UNNAMED_OK:
            stem = p.stem
            in_tools = any(f"{stem}.py" in t or re.search(rf"^(?:from {stem} import|import {stem}\b)", t, re.M)
                           for n, t in sources.items() if n != name)
            in_docs = any(f"{stem}.py" in d.read_text(encoding="utf-8")
                          for d in list(SKILLS.glob("*/SKILL.md")) + [ROOT / "CLAUDE.md", ROOT / "knowledge" / "tool-notes.md"]
                          if d.exists())
            if not in_tools and not in_docs:
                advisories.append(f"{name}: no skill and no other tool names it (retire it to tools/attic or document it)")
        if name not in HOME_ONLY:
            for m in re.finditer(r"walk(?:_beside)?\([^\n]*\bhp=0\b", s):
                advisories.append(f"{name}:{s[:m.start()].count(chr(10)) + 1}: a walk with hp=0 outside the home-only scripts")
        n_sleep = s.count("time.sleep(")
        if n_sleep > MAX_SLEEPS:
            advisories.append(f"{name}: {n_sleep} time.sleep calls (over {MAX_SLEEPS}: the bridge's wait op replies when done)")
        for m in re.finditer(r'run\("box\.py"[^\n]*\n(?:[^\n]*\n){0,2}[^\n]*run\("close\.py"', s):
            advisories.append(f"{name}:{s[:m.start()].count(chr(10)) + 1}: run(\"close.py\") right after box.py, which closes itself")

    # the review of 2026-10-30: the tool index is generated from the docstrings (tools/README.md) and the tool notes moved
    # out of elin-play into knowledge/tool-notes.md: both are checked for dead tool names; the index for staleness
    try:
        import toolindex
        cur = (TOOLS / "README.md").read_text(encoding="utf-8") if (TOOLS / "README.md").exists() else ""
        if cur != toolindex.render():
            advisories.append("tools/README.md is out of date: python -I tools/toolindex.py")
        for ln in toolindex.render().splitlines():
            if ln.endswith("(no docstring)"):
                advisories.append(f"{ln.split('`')[1]}: no module docstring (tools/README.md shows it blank)")
    except Exception as e:  # noqa: BLE001
        advisories.append(f"toolindex: {e}")
    docs = list(SKILLS.glob("*/SKILL.md")) + [ROOT / "CLAUDE.md", ROOT / "knowledge" / "tool-notes.md"]
    for p in docs:
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8")
        for m in re.finditer(r"\b([a-z_]+\.py)\b", s):
            name = m.group(1)
            around = s[max(0, m.start() - 160):m.end() + 160].lower()
            if name in existing or name == "tools.py" or re.search(r"retired|deleted|was removed|gone", around):
                continue
            findings.append(f"{p.relative_to(ROOT)}: names {name}, which doesn't exist in tools/")
        n = s.count("\n")
        if p.name == "SKILL.md" and n > 350:
            findings.append(f"{p.relative_to(ROOT)}: {n} lines (over 350: move history to the run logs)")
        if p.parent.name != "elin-play" and p.name == "SKILL.md":
            for m in re.finditer(r"\b(?:at|under|below|over|above)\s+\d{2}% HP\b", s):  # a rule, not a past number
                findings.append(f"{p.relative_to(ROOT)}: states an HP threshold ({m.group(0)}); elin-play's table is the one place")

    lessons = LESSONS.read_text(encoding="utf-8")
    live = lessons.split("## Live", 1)[-1].split("## Promoted", 1)[0]
    n_live = len(re.findall(r"^- ", live, re.M))
    if n_live > 35:
        findings.append(f"knowledge/lessons.md: {n_live} live lessons (over 35: promote or supersede)")
    goals = (ROOT / "knowledge" / "goals.md").read_text(encoding="utf-8")
    if goals.count("\n") > 500:
        findings.append(f"knowledge/goals.md: {goals.count(chr(10))} lines (over 500: archive done goals, trim logs)")

    bad_where, aliased = 0, 0
    for f in all_facts():
        w = f.get("where")
        if w and canon_where(w) != w and w.strip().lower() in WHERE_ALIASES:
            bad_where += 1
        if (f.get("s") or "").strip().lower() in SUBJECT_ALIASES:
            aliased += 1
    if bad_where:
        findings.append(f"knowledge/facts.jsonl: {bad_where} facts with a non-canonical `where` (kb.py add canonicalises; old ones are read through the alias)")
    if aliased:
        findings.append(f"knowledge/facts.jsonl: {aliased} facts whose subject is an alias (fine to leave; new facts should use the canonical name)")

    errors_check(findings, latest, stems)
    lessons_checks(findings, advisories, dates)
    thresholds_check(findings)
    milestones_check(findings, goals)

    if findings:
        print(f"hygiene: {len(findings)} findings (latest run {latest:02})")
        for f in findings:
            print("  - " + f)
    else:
        print("hygiene: clean")
    if advisories:
        print(f"advisory: {len(advisories)}")
        for a in advisories:
            print("  - " + a)
    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
