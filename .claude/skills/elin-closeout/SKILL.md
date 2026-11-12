---
name: elin-closeout
description: Closing an Elin session (runs 03-05, the user's requests) - quit through the bridge, the run log, metrics and milestone rows, facts, lessons and skills, goals, the summary file with Mermaid diagrams of the knowledge graph and the open goal chains, the rendered summary page (tools/summary_page.py, published as an Artifact and checked in Chrome), the next-run memory, and the local commit. Use whenever a session ends or the user says to close up for the day.
---

# Closing a session

The user's standing asks: every session ends with a short summary they can read (run 03), the
knowledge graph drawn in it (run 03), and the diagrams rendered as a page (2026-10-17: "it looks
fantastic"). Nothing is pushed. Work through the steps in order; the first two need the game.

## 1. While the game still runs

- `python -I tools/power.py --log RUN`: the end-of-run power card in `runs/power.csv` (since run 14
  it also logs speed, exp, karma and gold for the run tracker; since the 2026-10-23 review the real
  clock and a `--tag`: run it at each milestone too, `--tag nefia|jobs|home|travel|train|town`).
- Check `runs/activity.csv` has a start and an end for every loop the run used (ladder, trainday,
  springday, minewalls, harvestjob mark their own; `activity.py TAG end` closes one left open).
- Note the date, level, exp, gold and where the character is saved (`look.py`).
- `python -I tools/bridge.py quit`: the only way to quit (it saves first). Never kill the process.

## 2. Record the run

- **Run log** `runs/YYYY-MM-DD-NN.md`: goal, notable events, deaths and causes, game errors
  (outcomes the game can't undo), what worked and what failed, open questions. **Every "What
  failed" bullet becomes an errors.csv row**, and a real-time loss over 15 minutes (a walk to an
  expired nefia, a hang) is a row with domain `time` and the minutes as its cost (the review of
  2026-10-23: run 19's 652-oren identify and run 20's two wasted walks were in the log only).
- **`runs/metrics.csv`**: date, run, minutes, level, gold, deaths, furthest goal, notes.
- **`runs/milestones.csv`**: one row per milestone with minutes since the session started (check
  they rise), game errors, tool fixes, skills in use.
- **`runs/runstats.csv`** (the run tracker, the user 2026-10-20): one row with what only the run log
  says. That is the play model (from this session's transcript: the model the harness reports,
  not a guess), the character, the game dates, the level and exp at the start, jobs done and
  failed, new skills, spells and feats, goals done, goal milestones reached, near deaths (HP under
  25% of max), the lowest HP and its max, nefias conquered, the karma at the end, and a short
  note; since the 2026-10-23 review also **`bills_paid`** (the run's rent payments), **`income_gross`**
  (jobs + chests + shipping + Treasure Hunt + salaries + sales), **`planned_items`/`planned_done`**
  (the last summary's Next list against this run), **`gold_bars_end`** and **`platinum_end`**: all
  from the log's own numbers, typed, never guessed (blank when unknown). A change to the system
  between runs (a review or refactor: kind `review`, the chart's "refactor" line; a change to how a charted
  measure is counted, so its line can jump for that reason alone: kind `metrics` (the run score, R3; the table lists it, the
  charts leave it out: the user, 2026-11-11, "it makes it hard to read"); a
  new model) gets a row in `runs/events.csv` with its commit range and model, so the chart marks it. A tool or log that
  changes no charted measure (fights.csv, R4) is kind `tooling`: a record only, no marker, its commits go with the next commit
  that names a run (the user, 2026-10-29: "I didn't change the metrics then").
- **Goals and milestones from run 26 on are counted from the register** (stats.py: the Done table's Run
  and the `- [x] Mn (DATE, run NN)` ticks), so tick them in that form; runstats' goals_done and
  goal_steps stay for the runs before. A new or split milestone needs the user's yes and its row in
  `knowledge/milestones.csv` (hygiene.py).
- **`runs/bills.csv`** (the run score, 2026-10-26): one row per tax bill the run saw arrive (month,
  orens, run, source line). The score counts gold in days of rent, so a missing month is priced from
  the nearest one; paytax.py and springday print the amount.

## 3. Distill

- Observations (prices, places, foods, fights, outcomes, recipe trees) go in the graph:
  `kb.py add SUBJECT PREDICATE "OBJECT" --run NN [--where PLACE] [--note TEXT]`. Read the run log
  once more for any that were only written there (run 05 missed the kitten egg and Earthy Ruin).
- One-off mistakes and insights: one line each in `knowledge/lessons.md`'s **Live** section, with
  the run; a lesson a tool now enforces or a skill states moves to **Promoted** (one line) in the
  same session, and a reversed one to **Superseded** as an old -> new pair. New foods in
  `knowledge/foods.md`. A fact that corrects an older one: `kb.py add ... --supersedes N`.
- **`runs/errors.csv`**: one row per game error (run, game date, what, cost, skill domain, whether
  a rule existed, whether it's a repeat, what prevents it now). The review of runs 03-12 found
  milestones.csv can't judge a skill (no run without it, one-off milestones); the repeat column
  can: a skill is failing when an error repeats in its domain. **The rules of the 2026-10-23
  review** (12 of 43 errors since run 12 broke a rule already written; `hygiene.py` checks them):
  - a row with `rule_existed` yes or partly ends the same session with `prevented_now_by` naming a
    **tool or bridge op** (a refusal or a precondition), not a lesson or a skill line;
  - a Live lesson carries its run and is promoted, made a fact, superseded or dropped once it is
    3 runs old; a lesson that states a price, a count or a formula is a fact (`kb.py add`), never Live;
  - the skill verdict ("What this skill changed") is three lines of numbers: the measure, the
    baseline, the latest (repeats in its domain from errors.csv; exp and orens per hour from stats.csv);
  - the thresholds live in `common.THRESHOLDS`; a tool's own number is a drift, not a rule.
- A procedure seen in two or more runs becomes a skill or updates the one that covers it, with a
  "What this skill changed" block of three lines: the measure, the baseline, the latest (repeats
  in its domain from errors.csv). Check every skill for rules the run made stale (run 05: Kaberg
  in dungeons after "dungeons solo"; a box listed under two uses).
- Goals: elin-goals' end-of-session step in `knowledge/goals.md`.
- **Walk the next plan's recipe trees** with `kb.py make` down to the stations and their own
  inputs. Run 05's first diagram stopped one level short and missed bolts (blacksmith's table),
  the spinner's 5 needles and the smelter.

## 4. The summary file: `runs/<run>-summary.md`

`tools/summary_page.py` reads this file, so keep its shape (copy the last summary):
- `# Run NN summary: CHARACTER, level A to B (DATE, ...)`, then one paragraph (the page's lede).
- A results table `| | Start of run NN | End of run NN |` (the page puts it under "Results").
- The "Compared with the runs before" table carries, since the 2026-10-23 review, three rate rows
  from stats.csv: exp per hour, gross orens per hour, rent per hour (and the per-activity table from
  runs/activity_rates.csv when the loops wrote marks); since 2026-10-26 **points per hour first**
  (`score.py` prints the run's points by component: the lede says what earned and what cost them).
- `## Goals` with a `| Goal | Set by | Status |` table. Status starts `**done DATE**: ...`,
  `open: ...`, or `**MILESTONE**: ...` (the bold phrase becomes the pill).
- `## What was achieved in the game` (bullets), `## The knowledge graph now` (the `kb.py stats`
  numbers, the graph diagram, an "Across runs" table with `---:` number columns),
  `## The open goal chains` (one diagram per goal chain), `## Skills and tools: new and updated`
  (table), `## Next session` (numbered, in priority order: the start routine, then **at most
  three goal items plus upkeep**; every stale item from the last plan is marked do, park or drop;
  goals.md's Next lines say the same).

Mermaid rules (each one cost a re-render on 2026-10-17):
- `flowchart TB` for anything over four steps deep: an `RL` chain six deep shrank to tiny text.
- Two labelled edges into one node overlap their labels; put the number in the node instead.
- Colors by `classDef NAME fill:#...,stroke:#...,color:#1f2937` (readable on both themes), and
  the page's legend from comment lines: `%% legend: done=done; todo=binding: none in hand` and
  `%% note: Dotted lines: derived or indexed from`.

## 5. Index, render, check

0. `python -I tools/hygiene.py`: the drift check from the 2026-10-19 review (a tool spawning its own
   subprocesses or copying a helper, a goto followed by a sleep, a skill naming a tool that's gone,
   a threshold outside elin-play's table, lessons' Live over 35, goals.md over 500 lines, facts with
   the old place names; since 2026-10-23 the errors.csv rule-existed rows without a tool, Live
   lessons 3 runs old, THRESHOLDS against the tools and elin-play's table, and advisories). Fix what
   it lists in this session, or say in the run log why not, **and paste its last line into the run
   log** (no run log 13-20 showed it had run).
1. `python -I tools/kb.py embed`, then `kb.py stats`; put the numbers into the summary, and embed
   again (editing the notes moves the count by a few; it settles on the second pass).
2. `python -I tools/summary_page.py runs/<run>-summary.md` writes `runs/pages/<run>-summary.html`
   (gitignored: the md is the source).
   **No Artifact tool (another LLM, or a player who'd rather keep it local):** use **elin-summary** for steps 2-4 and the tracker in step 6.
3. Publish it with the Artifact tool: a new artifact per run (`icon` "map", a one-sentence
   `description`); a later fix republishes the same file path, or passes the run's `url`.
4. Look at it in Chrome (`tabs_context_mcp` with createIfEmpty, `navigate`, then scroll and
   screenshot through every diagram in one `browser_batch`). Fix what doesn't read in the md,
   rebuild, republish. Close the tab. No browser connected: say the page wasn't checked.
5. Add the link to `runs/pages/links.csv` (gitignored: `found_in,url`, with the run as `found_in`). **A claude.ai
   link never goes in a tracked file** (2026-11-04: the repo is public; `tools/publishcheck.py` refuses one).
6. **The run tracker**: `python -I tools/kb.py bench --log RUN` (the index's size and query speed
   to `runs/index.csv`), then `python -I tools/stats.py` (joins every log into `runs/stats.csv`;
   check the new row against the run log). Refresh the dashboard Elin Run Tracker (its link is the
   `tracker` row of `runs/pages/links.csv`; no such row means no dashboard: skip the rest of this step). First upload `runs/stats.csv` with the Artifact
   tool (`url`, `asset: true`). Then update `datasets/stats` with ArtifactData: its
   `source.url` becomes the new `/_blob/...` and `updated` the time. The page's source is
   `tools/tracker/index.html`: edit it there, then `set` `files/index.html` with it.

## 6. Hand over

- Memory: the next run's plan file (what the user decided, what waits on them, the money and
  calendar pressures) and its line in `MEMORY.md`; delete the previous run's plan memory.
- Commit the lessons, facts, skills and tools with the attribution line (git ignores the logs and records: they stay on this PC);
  never push without the user's yes, and only after
  `python -I tools/publishcheck.py --history` says clean. Run logs say "unattended" or "the user watching", never
  where the user is or when they sleep; quotes lose those words too (2026-11-04).
- **Everything off** (the user, 2026-11-03: "make sure the Ollama server and things go off when we exit"; KB #155).
  Last, because `kb.py embed` and `bench` above need the server, and when no more edits to facts or notes are coming:
  1. `TaskStop` any Monitor or background task of this session that is still running.
  2. `python -I tools/ollama_stop.py` (the only allowed way to end it), on its own, so the allow rule matches.
  3. `python -I tools/offcheck.py`: exit 0 means nothing is left. Anything listed gets dealt with now by its printed
     command, or named to the user; monitors from another project's session are only reported. Paste its lines into the run log.
- Tell the user: the goals and results in a few lines, the open questions, the page link, what `offcheck.py` said,
  and every row of `runs/waivers.csv` from this run, grouped and counted, or that there were none (the user, 2026-11-06:
  run 42 skipped the blanket rule on every circuit and the close-out only said they had run out). A later request that needs the graph starts the server again, and this step runs again after it.

## What this skill changed

New 2026-10-17 (runs 03-05). Measure: lessons that leaked (an error that repeated while its lesson
was text, or a failure only in the log). Baseline runs 12-20: 11 repeats, 9 rows naming no tool, 2
failures never recorded. Latest: the rules above, checked by hygiene.py from run 21 on.
