# Goals register

The long-term goals the user and I set, how far each has come, and what's next for it. The method
(how a goal is chosen, broken down, measured and reviewed) is the **elin-goals** skill. This file is
the data: read it at session start, update it at session end.

Status: **active** (being worked), **next** (chosen, waiting), **proposed** (my suggestion, the user
decides), **done**, **dropped**. Every goal has a measure that can be read in the game.

**Scoring rules (the user, 2026-10-26: "to avoid any gaming the system").** The run score (tools/score.py)
pays 300 for a goal done and 25 for a milestone, so the register is the ledger:
1. Only goals the user set score; my proposals (the Backlog) score nothing until the user sets them.
2. Milestones are frozen once the user has approved them: `knowledge/milestones.csv` lists every approved
   one, and hygiene.py flags a milestone here that isn't in it. Adding, splitting or rewording one needs
   the user's yes in chat, written into the goal with the date, and its row in milestones.csv.
3. A milestone scores when ticked as `- [x] Mn (DATE, run NN)` with something readable in the game; a
   partial `[~]` scores nothing; a bundled milestone scores when every part is done. From run 26 on,
   stats.py counts these ticks (and the Done table's rows) per run instead of a typed number.
4. A goal scores only when its done-when is met as written; a goal without one can't score until the
   user gives it one. Its last milestone usually is the done-when.
5. Parking, dropping or reopening a goal scores nothing, and a reopened goal's old milestones don't
   score again.

## Next

## Active

## Parked

## Backlog (proposed: candidates for the user to set)

| Id | Category | Goal | Why | First measurable step |
|---|---|---|---|---|

## Done

The record of each finished goal is in [goals-done.md](goals-done.md).

| Goal | Category | Done | Run |
|---|---|---|---|
