---
name: elin-goals
description: Long-term goals in Elin (run 04, the user's request) - how a session's time is spent (needs, upkeep, growth, opportunity), the goal categories (Training, Home Improvement, Efficiency Gains, Exploration, Fame, Wealth, Equipment, Story), how to set up a goal (research the game's own rules, find the binding resource and its sources, measurable milestones), how goals drive each session plan, and how progress is tracked in knowledge/goals.md. Use at the start and end of every session, when planning a trip, and whenever the user sets or asks about a goal.
---

# Long-term goals

The register is `knowledge/goals.md`: active, next, proposed and done goals, each with its measure,
milestones and progress log. This skill is the method. The user sets the goals (or picks from the
backlog I propose); I work out the structure: what the game's rules are, what the binding resource
is, where it comes from, and the steps.

## 1. How a session's time is spent (the player model)

A ladder, top first. Nothing lower starts while something higher is unmet:

1. **Needs:** food, sleep and SP, HP, safety (elin-play's rule zero and HP thresholds).
2. **Upkeep:** the monthly tax bill, the pet, the base routine (elin-home), money for the next bill.
3. **Growth:** the active long-term goals, next milestone first.
4. **Opportunity:** what turns up on the way: a treasure chest, a wreck, a board quest, a new town.

**Efficiency goals shrink rungs 1 and 2** (a tax chest at home, a farm, a better bed, the hotbar
kit), so more of every session goes to rungs 3 and 4. They pay back every month: do them first
when they're cheap.

## 2. Categories

Tag each goal with one or two: **Training** (level, skills, spells, feats), **Home Improvement**
(furniture, stations, storage, beds, safety), **Efficiency Gains** (fewer days on upkeep, fewer
trips, less carrying), **Exploration** (towns, dungeons, the world map), **Fame or Infamy**
(reputation, ranks, karma), **Wealth** (income, reserves, gold bars), **Equipment** (PV, DV,
damage, the pet's gear), **Story** (main and side quests).

## 3. A goal's shape (copy it into goals.md)

- **Why:** what it unlocks, valued in game days saved per month, power gained, or risk removed.
- **Measure:** one number the game shows, and its target; plus leading measures for the resource
  that builds toward it (G1: tickets and influence lead to "chest installed").
- **What the game says:** the rules found (prices, formulas, sources, chances, conditions), each
  with where it came from (`kb.py`, the game code, the wiki, the user). Mark unchecked numbers `~`.
- **Milestones:** each one checkable. M0 is always "verify the rules in play" (a price on a label,
  a shop's stock) before spending anything on the plan.
- **Next session's tasks,** a dated **progress log**, **open questions**, **risks**.

## 4. Setting up a new goal (the procedure)

1. **Name the outcome and its measure** with the user.
2. **Research the rules.** `kb.py show/make/ask/facts` first, then the game's code
   (raw.githubusercontent.com/Elin-Modding-Resources/Elin-Decompiled/main/Elin/<Class>.cs: the
   Trait class of the item, the shop or quest class) for exact formulas and conditions. The user
   knows the game: their tips (G1: the secretary trades influence for tickets) go in with credit.
3. **Find the binding resource and every source of it**, with a rate: G1's chain is quests in
   Mysilia → influence → tickets at the secretary (~1 each) → ~13 tickets → the chest.
4. **Estimate** the total and the time (sessions, trips) from the rate; a skill target's SP comes from
   fact #1297 before it is proposed (2026-11-06: my Carpentry 20 was ~3,400 SP; the user took 12); say which numbers are
   guesses until M0.
5. **Milestones:** verify → accumulate → convert → install or use → confirm the benefit (the
   measure moved).
6. **Write it into goals.md** and put the first task into the next session's plan.

## 5. Every session

- **Start:** elin-play's start routine, then plan by the ladder: needs, then upkeep due before
  the next session ends, then the active goal's next milestone. **At most three goal items plus
  upkeep per session** (the review: 57% of planned items got done; what slipped waited on random
  drops or chains over three deep). A random-drop item names its expected attempts (a skin:
  ~5 corpses at 20%). **Stack goals on one trip:** a Mysilia trip pays the tax, earns influence,
  buys plans and potions. Write the plan's goal tasks into the run log.
- **During:** when a goal's resource moves (influence gained, a ticket earned, a price seen), note
  it with `kb.py add` so the rate is measured, not assumed.
- **End:** update every goal touched: a progress log line, the measure's current value, milestone
  checkboxes, next tasks, and an ETA from the observed rate. Move goals between sections; a
  finished goal goes to Done with the date and what it changed (G1: the next tax paid at home).
  **A guild goal done sets the next rank as a goal at once** (the user, 2026-11-01: "all guilds should keep
  increasing until they are max rank"): same shape, M1 the rank, its milestones.csv row citing that quote, up
  to rank 6 (the game's cap; goals.md's guild rule). Propose new candidates in the backlog when something worth a goal turned up. **Write the run's
  rates into each active goal's header** (the review of 2026-10-23): the exp and orens per real
  hour its activity produced, from `runs/activity_rates.csv` (stats.py pairs the loops' marks in
  runs/activity.csv); an activity that earns neither exp nor orens is upkeep, not a goal.
- **The register's shape** (goals.md): the Next block first (the plan and the standing Upkeep
  block: food days, rations, the next bill against the gold), then Active (the one to three goals
  being worked), then Parked (set by the user, waiting, unchanged), the Backlog and Done.

## 6. Choosing and ordering goals

- Value per cost: days saved per month, power toward the dungeon gate, risk removed, money.
- Prefer goals whose resource comes from things I do anyway (G1's influence comes from the town
  trips the tax already forces).
- Keep one or two active; more splits the trips.
- No goal overrides rule zero, the HP thresholds or honest play.

## 7. Measures I can read

Gold and the date (`look.py`), level and exp, offense and defense (`power.py`), items in the pack
(`bridge.py inv`) and in boxes (`box.py WHERE`), influence and the ticket price (the secretary's
shop window), fame (the character sheet: the exp bar opens it), days spent on the road and at home
(the run log's dates).

**The owner's measure is growth per real hour** (2026-10-23): exp, orens and goals. The record
(runs/stats.csv, derived by `tools/stats.py`) carries per run `exp_per_hour`, `income_gross` and
`bills_paid` (typed into runstats.csv from the log), `orens_per_hour`, `rent_per_hour`, `net_gold`
(power.csv's first and last gold), `wealth` (gold + 175 x gold bars + 50 x platinum), `tax_accrual`
(~70 orens a game day: rent runs whatever I do), `exp_per_game_day`, `planned_items`/`planned_done`;
and per activity (`runs/activity_rates.csv`, from the loops' own start/end marks in
runs/activity.csv) minutes, exp and orens per hour. Measured so far: nefia circuits ~2,000-2,500
orens and ~70 exp an hour; Fast Travel job chains 2,000-3,200 orens; a new skill at the dummy
380-530 exp and ~0 orens; farming, building and the main weapon at the dummy ~0 of both.

**The run score: points per hour** (the user, 2026-10-26: tracked from run 26 on; the headline
measure). `tools/score.py [N]` turns a run into points: a goal 300, a milestone 25, a nefia 60, an
exp 1 (no points for a level: its exp counts it), gold in days of rent (orens / the month's bill / 30
x 13), a game day -13, a death -1,000 (a near death costs nothing: survival is binary); rated per real
hour and per game day (stats.csv `points*`). `score.py --activities` ranks the marked loops. **Use it
to choose**: a risky step is worth it only if its points beat 1,000 x its chance of a death; a loop
that runs ~18 game days an hour pays ~230 points an hour of rent before it earns any.
**The scoring rules** (the user, 2026-10-26: no gaming the system) are at the top of goals.md: only
the user's goals score; milestones are frozen in `knowledge/milestones.csv` (hygiene.py flags one added
or split without the user's yes); a tick is `- [x] Mn (DATE, run NN)`, and from run 26 on stats.py
counts the ticks and the Done table per run instead of a typed number; a goal scores only on its
done-when as written.

## What this skill changed

New in run 04 (the user's request). Measure: goals done and goal steps per real hour (stats.csv).
Baseline runs 04-12: 0.11 goals and 0.72 steps an hour; runs 13-20: 0.20 and 1.15. Goals with a
concrete object took 1-2 runs; G9 took 12 (no done-when until run 17), G6 and G11 10 each (random drops).
