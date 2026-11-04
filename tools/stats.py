"""The run tracker's table: one row per run (and per event between runs, such as the 2026-10-19
review) with every number the user tracks across sessions (2026-10-20): minutes, game days,
level and exp, exp an hour, gold, damage, HP/PV/speed, deaths and near deaths, jobs, skills,
goals, game errors and errors an hour, tool changes, facts and the semantic index; and, since
the review of 2026-10-23 (the owner's measure is growth per play hour, and no CSV held a money
flow), income, bills, rent an hour, wealth, the plan's completion and the rates per activity.

Sources, each read as it stands (nothing here is typed twice):
  runs/metrics.csv     minutes, level, gold, deaths (its `actions` column, empty since run 03, was
                       dropped on 2026-10-23 and is not read)
  runs/power.csv       game dates, HP, PV, speed, melee a turn, exp, karma, gold (first and last row
                       of a run); since 2026-10-23 also logged_at (the real clock) and tag
  runs/errors.csv      game errors from run 12 on
  runs/runstats.csv    what only the run log says: the play model, jobs, skills learned, goals done,
                       near deaths, lowest HP, nefias, game errors before run 12 (one row a run,
                       written at close-out); since 2026-10-23 the typed money columns bills_paid,
                       income_gross, planned_items, planned_done, planned_partly, gold_bars_end,
                       platinum_end
  runs/activity.csv    the loops' start and end marks (tools/activity.py): real clock, game date,
                       tag, exp, lv, gold; absent until the first marked loop runs
  runs/index.csv       index size and speed (kb.py bench --log RUN)
  runs/bills.csv       the monthly tax bills (month, orens, run, source), one row as each one arrives
  runs/events.csv      events between runs and the commit ranges git can't place by subject; kind `review` and
                       `metrics` become their own rows (the tracker's "refactor" and "new metric" markers), kind
                       `tooling` (a tool change that changes no measure, run 31) is a record only: its commits
                       go with the next commit that names a run
  knowledge/facts.jsonl facts added per run
  knowledge/travel.csv legs; a blank `run` cell is filled here (below)
  git log              tool changes per run: commits are placed by "Run NN" in the subject, else by
                       an events.csv range, else with the next commit that names a run
  runs/toolchurn.csv   the same numbers for runs 01-40, frozen on 2026-11-04 when the history was squashed to one
                       commit for publishing; git log counts only what came after that root (the older commit
                       hashes in events.csv are a record now)

Derived money columns (2026-10-23). Every older column keeps its meaning and position; the
dashboard (tools/tracker/index.html) reads stats.csv by column name, so columns are only added.
  income             = runstats income_gross: jobs + chests + shipping + Treasure Hunt + salaries +
                       sales in orens, as the run log states them (gold bars and platinum apart)
  bills              = runstats bills_paid: the run's rent/tax payments in orens
  tax_accrual        what the bill clock charged for the run: bills_paid when typed, else
                       RENT_PER_DAY x game_days; tax_source says which ("bills_paid" or "70/day")
  net_gold           power.csv's last gold minus its first for the run (carried orens only)
  gold_bars_end, platinum_end   typed in runstats from the run log's end state (the next run's
                       start line reads the same save)
  wealth             metrics' gold at the end + BAR_ORENS x gold_bars_end + PLATINUM_ORENS x
                       platinum_end, when gold_bars_end is typed; wealth_source says
                       "bars+platinum" or "bars only" (platinum_end empty: counted as 0)
  orens_per_hour     income_gross / hours of play (gross: before bills and spending)
  rent_per_hour      tax_accrual / hours
  exp_per_game_day   exp_gained / game_days
  game_days_per_hour game_days / hours (the pace the bills arrive at)
  planned_items, planned_done, planned_partly   the previous summary's "Next session" items (the
                       Start item excluded) and how many the run did in full / in part
  planned_pct        100 x (planned_done + 0.5 x planned_partly) / planned_items

The run score (2026-10-26, tools/score.py holds the points and the reasons):
  bill               the monthly tax bill in force over the run's game days (runs/bills.csv, one row a
                     month from the run logs, averaged by day; a month with no row takes the nearest
                     month of the same game year, the earlier on a tie, else the last month before it)
  points             score.parts(): goals, milestones, nefias, exp, gold in days of rent, game days,
                     deaths; empty when the income or the bill is unknown
  points_per_hour, points_per_game_day
  goals_done, goal_steps   from run 26 on (REGISTER_FROM) counted from the register, not typed: the Done
                     table's rows in knowledge/goals.md whose Run is the run, and the milestones ticked
                     `- [x] Mn (DATE, run NN)` in goals.md and goals-done.md (the scoring rules, the user
                     2026-10-26); runstats' typed columns keep runs 03-25

Back-fill of the typed columns for runs 03-20 (2026-10-23): bills_paid, income_gross and
planned_* come from the history review in the session scratchpad (review-history.md sections 2
and 3, compiled from the run logs with file:line citations; its analyze.py holds the per-source
sums), gold_bars_end and platinum_end from the logs' start and end lines (10.md:70, 12.md:4,
12.md:158, 13.md:5, 14.md:5, 16.md:120 and 16.md:171, 18.md:4, 19.md:4, 20.md:4, 20.md:168;
run 20's 27 bars = 41 at the start - 15 for Samata + 1 found on a floor). A cell neither the
review nor a log gives stays empty.

Per-activity rates (runs/activity_rates.csv; printed under each run's row): an activity.csv row
belongs to the run whose power.csv logged_at window (first to last --log) holds its clock, else
to the latest run dated on or before it; a tag's start is paired with the next end of the same
tag in the same run, and the pairs are summed per run and tag: minutes, exp_gained (level-ups
included through exp_total), exp_per_hour, gold_delta (carried orens; a bill paid inside a
segment shows as a drop), orens_per_hour, game_days (fractional, from the game clock). A start
with no end (the loop died before its end mark) is counted and printed, not summed.

knowledge/travel.csv `run`: a leg belongs to the run whose runstats game_start..game_end holds
its start date; when two runs share that day, the later one (at a close-out every blank leg is
the current run's). The 2026-10-23 back-fill placed the ten boundary-day legs by the run logs'
quit and start times instead. stats.py fills only blank cells and leaves every other byte as
wgo.py wrote it.

usage: python -I tools/stats.py          write runs/stats.csv and runs/activity_rates.csv, print both
The dashboard (Elin Run Tracker) reads runs/stats.csv; elin-closeout says how to refresh it.
"""
import csv
import datetime as dt
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score import parts, total as points_total  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
TRAVEL = ROOT / "knowledge" / "travel.csv"
TOOL_PATHS = ("tools/", "mod/ElinBridge/", "mod/build.sh")
NEAR_DEATH = 0.25  # HP under a quarter of max (the user's "near deaths"; elin-play's rule zero)
BAR_ORENS = 175  # a gold bar at a shop (11.md:159-160)
PLATINUM_ORENS = 50  # a platinum coin, the review's working rate (a new skill costs 5 of them)
RENT_PER_DAY = 70  # orens of tax a game day at the current levy (~2,100 a 30-day month, runs 17-20)
REGISTER_FROM = 26  # goals and milestones counted from the register from this run on (the scoring rules)
ACTIVITY_COLS = ["run", "tag", "minutes", "exp_gained", "exp_per_hour", "gold_delta", "orens_per_hour", "game_days"]


def rows(name):
    p = RUNS / name
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def game_day(date):
    """486-08-11 -> days since year 0; Elin's calendar has 12 months of 30 days."""
    y, m, d = (int(v) for v in date.split()[0].split("-"))
    return (y * 12 + m - 1) * 30 + d


def game_days_between(a, b):
    """Game days from a to b, fractional when the dates carry a clock ("487-06-09 14:42")."""
    def hours(d):
        parts = d.split()
        h = game_day(parts[0]) * 24
        if len(parts) > 1 and ":" in parts[1]:
            hh, mm = parts[1].split(":")[:2]
            h += int(hh) + int(mm) / 60
        return h
    return (hours(b) - hours(a)) / 24


def monthly_bill(start, end, bills):
    """The monthly bill in force over a run's game days, averaged by day; bills is {(year, month): orens}."""
    if not (bills and start and end):
        return None
    a, b = game_day(start), game_day(end)

    def bill(d):
        y, m = divmod((d - 1) // 30, 12)
        same = [(abs(mm - (m + 1)), mm) for (yy, mm) in bills if yy == y]
        if same:
            return bills[(y, min(same)[1])]
        before = [k for k in bills if k < (y, m + 1)]
        return bills[max(before)] if before else None
    vals = [v for v in (bill(d) for d in range(a, max(a + 1, b))) if v is not None]
    return sum(vals) / len(vals) if vals else None


def register_counts():
    """{run: goals done} from goals.md's Done table and {run: milestones ticked} from both goal files."""
    goals = (ROOT / "knowledge" / "goals.md").read_text(encoding="utf-8")
    done_file = (ROOT / "knowledge" / "goals-done.md").read_text(encoding="utf-8")
    done = defaultdict(int)
    for m in re.finditer(r"^\| G\d+[^|]*\|[^|]*\|[^|]*\|\s*(\d+)\s*\|\s*$", goals, re.M):
        done[int(m.group(1))] += 1
    steps = defaultdict(int)
    for m in re.finditer(r"^- \[x\] M\d+ \([^)]*\brun (\d+)\)", goals + "\n" + done_file, re.M):
        steps[int(m.group(1))] += 1
    return done, steps


def exp_total(lv, exp):
    """Character exp from level 1: ExpToNext is 50 + 30 x level (Lv13 440, Lv15 500 as read)."""
    return sum(50 + 30 * k for k in range(1, lv)) + exp


MARKED = ("review", "metrics")  # event kinds that get their own stats row and a marker on the tracker's charts


def git_buckets(events):
    """{point: counts of tool changes}: the frozen history (runs/toolchurn.csv) plus the commits since the root. The
    root is left out: as the only commit of a squashed history its numstat is the whole repo, not a change."""
    roots = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8").stdout.split()
    since = ["HEAD", *("^" + r for r in roots)]
    out = subprocess.run(["git", "log", "--reverse", "--format=@@%h|%s", "--numstat", *since], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8").stdout
    added = subprocess.run(["git", "log", "--diff-filter=A", "--format=@@%h", "--name-only", *since], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8").stdout
    new_files, cur = defaultdict(set), None
    for line in added.splitlines():
        if line.startswith("@@"):
            cur = line[2:]
        elif line.strip():
            new_files[cur].add(line.strip())
    commits = []
    for block in out.split("@@")[1:]:
        head, *files = block.strip("\n").split("\n")
        h, subj = head.split("|", 1)
        stat = []
        for f in files:
            parts = f.split("\t")
            if len(parts) == 3:
                stat.append((parts[2], int(parts[0]) if parts[0].isdigit() else 0,
                             int(parts[1]) if parts[1].isdigit() else 0))
        m = re.search(r"\bRun (\d{2})\b", subj)
        commits.append({"h": h, "run": m.group(1) if m else None, "stat": stat})
    order = [c["h"] for c in commits]
    for ev in events:  # commit ranges events.csv names win over subjects
        if ev.get("kind") not in MARKED and ev.get("kind") != "run":
            continue  # run 31: a `tooling` event's commits go with the next commit that names a run (no row of their own)
        if ev.get("first_commit") and ev["first_commit"] in order:
            i, j = order.index(ev["first_commit"]), order.index(ev["last_commit"])
            for c in commits[i:j + 1]:
                c["run"] = ev["id"]
    nxt = None
    for c in reversed(commits):  # the rest go with the next commit that names a run
        if c["run"] is None:
            c["run"] = nxt
        nxt = c["run"]
    b = defaultdict(lambda: {"commits": 0, "files": set(), "new": set(), "lines": 0, "skills": set()})
    for c in commits:
        x = b[c["run"]]
        x["commits"] += 1
        for path, a, d in c["stat"]:
            if path.startswith(TOOL_PATHS) and not path.endswith((".md", ".txt")):
                x["files"].add(path)
                x["lines"] += a + d
                if path in new_files[c["h"]]:
                    x["new"].add(path)
            if path.startswith(".claude/skills/"):
                x["skills"].add(path.split("/")[2])
    counts = defaultdict(lambda: {"commits": 0, "files": 0, "new": 0, "lines": 0, "skills": 0})
    for r in rows("toolchurn.csv"):
        c = counts[r["point"]]
        c["commits"] += int(r["commits"])
        c["files"] += int(r["files"])
        c["new"] += int(r["files_new"])
        c["lines"] += int(r["lines"])
        c["skills"] += int(r["skills"])
    for point, x in b.items():
        c = counts[point]
        c["commits"] += x["commits"]
        c["files"] += len(x["files"])
        c["new"] += len(x["new"])
        c["lines"] += x["lines"]
        c["skills"] += len(x["skills"])
    return counts


def fill_travel_runs(hand):
    """Give each knowledge/travel.csv leg with no `run` cell the run whose game range holds its
    start date (two on a shared day: the later). Text-level, so wgo.py's bytes stay; returns the
    number of legs filled."""
    if not TRAVEL.exists():
        return 0
    lines = TRAVEL.read_bytes().splitlines(keepends=True)
    if not lines or not lines[0].rstrip(b"\r\n").endswith(b",run"):
        return 0
    n_cols = len(lines[0].rstrip(b"\r\n").split(b","))
    ranges = [(r["run"], game_day(r["game_start"]), game_day(r["game_end"]))
              for r in hand.values() if r.get("game_start") and r.get("game_end")]
    filled = 0
    for i, line in enumerate(lines[1:], 1):
        body = line.rstrip(b"\r\n")
        end = line[len(body):]
        cells = next(csv.reader([body.decode("utf-8")]))
        if len(cells) >= n_cols and cells[n_cols - 1]:
            continue
        try:
            d = game_day(cells[0])
        except (ValueError, IndexError):
            continue
        hits = sorted(run for run, a, b in ranges if a <= d <= b)
        if not hits:
            continue
        if len(cells) >= n_cols and body.endswith(b","):  # an empty run cell
            body = body[:-1]
        lines[i] = body + b"," + hits[-1].encode() + end
        filled += 1
    if filled:
        TRAVEL.write_bytes(b"".join(lines))
    return filled


def activity_rates(power, metrics):
    """Pair activity.csv's starts and ends per run and tag -> ([row dicts], {run: unpaired starts})."""
    marks = [r for r in rows("activity.csv") if r.get("logged_at") and r.get("tag")]
    if not marks:
        return [], {}
    windows = {}
    for run, prs in power.items():
        ts = sorted(r["logged_at"] for r in prs if r.get("logged_at"))
        if ts:
            windows[run] = (ts[0], ts[-1])
    by_date = sorted((m["date"], run) for run, m in metrics.items())

    def run_of(ts):
        for run, (a, b) in windows.items():
            if a <= ts <= b:
                return run
        before = [run for d, run in by_date if d <= ts[:10]]
        return before[-1] if before else ""

    def clock(ts):
        return dt.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

    pending, agg, unpaired = {}, defaultdict(lambda: defaultdict(float)), defaultdict(int)
    for r in sorted(marks, key=lambda r: r["logged_at"]):
        key = (run_of(r["logged_at"]), r["tag"])
        if r.get("phase") == "start":
            if key in pending:
                unpaired[key[0]] += 1
            pending[key] = r
            continue
        if r.get("phase") != "end" or key not in pending:
            continue
        s, a = pending.pop(key), agg[key]
        a["minutes"] += (clock(r["logged_at"]) - clock(s["logged_at"])).total_seconds() / 60
        if all(num(x.get(k)) is not None for x in (s, r) for k in ("lv", "exp")):
            a["exp"] += (exp_total(int(num(r["lv"])), int(num(r["exp"])))
                         - exp_total(int(num(s["lv"])), int(num(s["exp"]))))
        if num(s.get("gold")) is not None and num(r.get("gold")) is not None:
            a["gold"] += num(r["gold"]) - num(s["gold"])
        if s.get("game_date") and r.get("game_date"):
            a["days"] += game_days_between(s["game_date"], r["game_date"])
    for key in pending:
        unpaired[key[0]] += 1
    out = []
    for (run, tag), a in sorted(agg.items()):
        hours = a["minutes"] / 60
        out.append({"run": run, "tag": tag, "minutes": round(a["minutes"]),
                    "exp_gained": int(a["exp"]), "exp_per_hour": round(a["exp"] / hours) if hours else "",
                    "gold_delta": int(a["gold"]), "orens_per_hour": round(a["gold"] / hours) if hours else "",
                    "game_days": round(a["days"], 1)})
    return out, unpaired


def main():
    if not (RUNS / "metrics.csv").exists():  # logs are gitignored: a fresh clone has none
        print("no records yet on this PC: a new player starts with the elin-setup skill (tools/newgame.py --yes)")
        return
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    metrics = {r["run"]: r for r in rows("metrics.csv")}
    hand = {r["run"]: r for r in rows("runstats.csv")}
    events = rows("events.csv")
    power = defaultdict(list)
    for r in rows("power.csv"):
        power[r["run"]].append(r)
    errs = defaultdict(int)
    for r in rows("errors.csv"):
        errs[r["run"]] += 1
    index = {r["run"]: r for r in rows("index.csv")}
    reg_done, reg_steps = register_counts()
    bill_table = {tuple(int(v) for v in r["month"].split("-")): num(r["orens"]) for r in rows("bills.csv")}
    facts_by_run = defaultdict(int)
    for line in (ROOT / "knowledge" / "facts.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            facts_by_run[json.loads(line)["run"]] += 1
    git = git_buckets(events)
    rates, unpaired = activity_rates(power, metrics)
    by_run_tag = defaultdict(list)
    for r in rates:
        by_run_tag[r["run"]].append(r)

    points = sorted(metrics)
    for ev in events:  # an event between runs sits after the run its `after` names (R1 after 12)
        if ev["kind"] in MARKED:
            points.insert(points.index(ev["after"]) + 1 if ev["after"] in points else len(points), ev["id"])
    out, facts_total, goals_total, skills_total, prev_exp = [], 0, 0, 0, None
    for p in points:
        ev = next((e for e in events if e["id"] == p and e["kind"] in MARKED), None)
        g = git.get(p, {"commits": 0, "files": 0, "new": 0, "lines": 0, "skills": 0})
        row = {"point": p, "label": ev["label"] if ev else f"Run {p}", "kind": ev["kind"] if ev else "run",
               "date": ev["date"] if ev else metrics[p]["date"],
               "model": ev["model"] if ev else (hand.get(p, {}).get("play_model") or ""),
               "system": "", "tool_commits": g["commits"], "tool_files": g["files"],
               "tool_files_new": g["new"], "tool_lines": g["lines"], "skills_touched": g["skills"]}
        if ev:
            out.append(row)
            continue
        m, h, pw = metrics[p], hand.get(p, {}), power.get(p, [])
        row["system"] = "v2 refactored" if int(p) >= 13 else "v1"
        minutes = num(m["minutes"])
        hours = minutes / 60 if minutes else None
        start = h.get("game_start") or (pw[0]["game_date"] if pw else "")
        end = h.get("game_end") or (pw[-1]["game_date"] if pw else "")
        last = pw[-1] if pw else {}
        lv = int(m["char_level"]) if m["char_level"] else None
        # exp: the end of the run against its start (runstats' lv_start/exp_start, else the run before's
        # end); a run whose either end wasn't read gets no exp gained rather than a guess
        exp_end = num(h.get("exp_end")) if h.get("exp_end") else num(last.get("exp"))
        total = exp_total(lv, int(exp_end)) if lv and exp_end is not None else None
        if h.get("lv_start") and h.get("exp_start"):
            prev_exp = exp_total(int(h["lv_start"]), int(h["exp_start"]))
        gained = total - prev_exp if total is not None and prev_exp is not None else None
        prev_exp = total
        e = errs[p] if int(p) >= 12 else num(h.get("errors"))
        facts_total += facts_by_run.get(p, 0)
        if int(p) >= REGISTER_FROM:
            goals_done, goal_steps = reg_done.get(int(p), 0), reg_steps.get(int(p), 0)
        else:
            goals_done, goal_steps = h.get("goals_done", ""), h.get("goal_steps", "")
        goals_total += int(num(goals_done) or 0)
        learned = [num(h.get(k)) for k in ("skills_new", "spells_new", "feats_new")]
        learned = int(sum(x for x in learned if x is not None)) if any(x is not None for x in learned) else None
        skills_total += learned or 0
        low, low_max = num(h.get("lowest_hp")), num(h.get("lowest_hp_max"))
        days = game_day(end) - game_day(start) if start and end else None
        # the money flows (2026-10-23): typed in runstats at close-out, derived here
        bills, income = num(h.get("bills_paid")), num(h.get("income_gross"))
        if bills is not None:
            accrual, tax_source = bills, "bills_paid"
        elif days is not None:
            accrual, tax_source = RENT_PER_DAY * days, f"{RENT_PER_DAY}/day"
        else:
            accrual, tax_source = None, ""
        golds = [num(r.get("gold")) for r in pw if num(r.get("gold")) is not None]
        net_gold = golds[-1] - golds[0] if len(golds) >= 2 else None
        bars, plat, gold_end = num(h.get("gold_bars_end")), num(h.get("platinum_end")), num(m["gold"])
        wealth = (gold_end + BAR_ORENS * bars + PLATINUM_ORENS * (plat or 0)
                  if bars is not None and gold_end is not None else None)
        items, done, partly = num(h.get("planned_items")), num(h.get("planned_done")), num(h.get("planned_partly"))
        planned_pct = round(100 * (done + 0.5 * (partly or 0)) / items) if items and done is not None else None
        row.update({
            "character": h.get("character", ""),
            "minutes": int(minutes) if minutes else "",
            "game_start": start, "game_end": end,
            "game_days": days if days is not None else "",
            "level": lv or "", "exp_total": total if total is not None else "",
            "exp_gained": gained if gained is not None else "",
            "exp_per_hour": round(gained / hours) if gained is not None and hours else "",
            "gold": m["gold"], "deaths": m["deaths"],
            "near_deaths": h.get("near_deaths", ""),
            "lowest_hp_pct": round(100 * low / low_max) if low is not None and low_max else "",
            "jobs": h.get("jobs", ""), "jobs_failed": h.get("jobs_failed", ""),
            "skills_learned": learned if learned is not None else "",
            "skills_learned_total": skills_total if h else "",
            "goals_done": goals_done, "goals_done_total": goals_total if h else "",
            "goal_steps": goal_steps,
            "nefias": h.get("nefias", ""),
            "errors": int(e) if e is not None else "",
            "errors_per_hour": round(e / hours, 2) if e is not None and hours else "",
            "max_hp": last.get("max_hp", ""), "pv": last.get("pv", ""),
            "speed": last.get("speed") or h.get("speed_end", ""),
            "melee_per_turn": last.get("melee_per_turn", ""),
            # my own at the run's end (power.csv my_melee; before run 37's close only a card taken with no ally along
            # has it, so a run that ended with one is blank rather than carrying an earlier row's weapon set)
            "my_melee": last.get("my_melee", ""),
            "karma": last.get("karma") or h.get("karma_end", ""),
            "facts_added": facts_by_run.get(p, 0), "facts_total": facts_total,
            "index_entries": index.get(p, {}).get("index_entries", ""),
            "query_ms": (round(num(index[p]["query_embed_ms"]) + num(index[p]["query_search_ms"]), 1)
                         if p in index and index[p].get("query_embed_ms") else ""),
            # the money columns, appended so the dashboard's older columns keep their place
            "income": int(income) if income is not None else "",
            "bills": int(bills) if bills is not None else "",
            "tax_accrual": int(accrual) if accrual is not None else "", "tax_source": tax_source,
            "net_gold": int(net_gold) if net_gold is not None else "",
            "gold_bars_end": int(bars) if bars is not None else "",
            "platinum_end": int(plat) if plat is not None else "",
            "wealth": int(wealth) if wealth is not None else "",
            "wealth_source": ("bars+platinum" if plat is not None else "bars only") if wealth is not None else "",
            "orens_per_hour": round(income / hours) if income is not None and hours else "",
            "rent_per_hour": round(accrual / hours) if accrual is not None and hours else "",
            "exp_per_game_day": round(gained / days, 1) if gained is not None and days else "",
            "game_days_per_hour": round(days / hours, 1) if days is not None and hours else "",
            "planned_items": int(items) if items is not None else "",
            "planned_done": int(done) if done is not None else "",
            "planned_partly": int(partly) if partly is not None else "",
            "planned_pct": planned_pct if planned_pct is not None else "",
        })
        bill = monthly_bill(start, end, bill_table)
        row["bill"] = round(bill) if bill else ""
        pts = parts(row)
        score = points_total(pts) if pts["gold"] is not None else None
        row.update({
            "points": round(score) if score is not None else "",
            "points_per_hour": round(score / hours) if score is not None and hours else "",
            "points_per_game_day": round(score / days, 1) if score is not None and days else "",
        })
        out.append(row)
    cols = list(dict.fromkeys(k for r in out for k in r))
    with (RUNS / "stats.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    with (RUNS / "activity_rates.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=ACTIVITY_COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(rates)
    show = ["point", "model", "minutes", "game_days", "level", "exp_gained", "exp_per_hour", "gold", "deaths",
            "near_deaths", "jobs", "skills_learned", "goals_done", "errors", "errors_per_hour", "tool_files",
            "max_hp", "pv", "speed", "melee_per_turn", "my_melee", "facts_total", "index_entries", "query_ms",
            "income", "bills", "orens_per_hour", "rent_per_hour", "wealth", "planned_pct", "points",
            "points_per_hour"]
    print("  ".join(c[:9].rjust(9) for c in show))
    for r in out:
        print("  ".join(str(r.get(c, ""))[:9].rjust(9) for c in show))
        for a in by_run_tag.get(r["point"], []):  # the per-activity rates under the run's row
            print(f"      {a['tag']:7} {a['minutes']:5} min  exp {a['exp_gained']:+6} ({a['exp_per_hour']}/h)"
                  f"  orens {a['gold_delta']:+7} ({a['orens_per_hour']}/h)  {a['game_days']} game days")
        if unpaired.get(r["point"]):
            print(f"      ({unpaired[r['point']]} activity start(s) with no end mark: not summed)")
    filled = fill_travel_runs(hand)
    print(f"wrote {(RUNS / 'stats.csv').relative_to(ROOT)} ({len(out)} rows, {len(cols)} columns), "
          f"{(RUNS / 'activity_rates.csv').relative_to(ROOT)} ({len(rates)} rows)"
          + (f"; filled `run` on {filled} travel.csv legs" if filled else ""))


if __name__ == "__main__":
    main()
