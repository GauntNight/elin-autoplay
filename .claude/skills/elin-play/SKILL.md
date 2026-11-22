---
name: elin-play
description: Operating manual for playing Elin through the ElinBridge mod in this repo - launching and loading the save, the knowledge graph (kb.py), the perceive-act-verify loop, the bridge's own guards, the hard rules (one dialog, one bridge client, never a shell chain over game actions but seq.py, exit codes), the thresholds table every tool reads (HP floors, the swarm count, the floor gate, the throw distance, Hungry), where the tool index lives, quick-saves, ending a session and the bridge rebuild cycle. Use at the start of every Elin play session and whenever acting in the game. It points to elin-delve (nefias), elin-travel (the world map and towns), elin-guilds, elin-home, elin-pack and elin-gear for the procedures.
---

# Playing Elin through the bridge

Every action goes through the game's own code paths (ActPlan, InvOwner, the UI's own buttons), so the game's rules, warnings
and costs still apply. Read state, act once, verify.

**The procedures are in their own skills** (load one when its task comes up):
- **elin-delve**: nefia circuits, the ladder's stops, the floor gate, fights on a floor, exploders, leaving a floor.
- **elin-travel**: the world map (`wgo.py`), ambushes, Fast Travel, trip food and bed, towns and board jobs, treasure maps.
- **elin-guilds**: Thieves, Merchants, Mages, Fighters: the method and the promotion for each.
- **elin-home**: every return home, the boxes, keep or ship, safety at home. **elin-pack**: the kit, the triage, shops.
- **elin-gear**: is this piece better? (`gearcompare.py`, `gearcheck.py` before `shipstar.py`; one weapon, the other hand
  empty).
- **elin-train**: exp training (G55, run 46): the dummy ridden on Kaberg, a trainer's potential, music, Quick Craft, and
  what each costs in food, game days, karma and the score.
- **elin-goals** (planning by the register), **elin-closeout** (ending a session), elin-build, elin-opening, elin-setup.

## Rule zero: don't die (the user's #1 goal; everything else is secondary)

Speed, quests, loot and looks all yield to survival. Before any risky step, ask "what kills me here, and how do I leave?" The
numbers below are the only ones (the run 12 review found seven HP floors stated in five places); the other skills point here.
**In code they are `THRESHOLDS` in `tools/common.py`**, which the tools read and `hygiene.py` checks against this table (the
review of 2026-10-23 found the gate at 8 here and 7 in ladder.py, Hungry at 70 here and 80 in farmday).

**Thresholds (one table; the tools default to it)**

| Situation | Number | Where it came from |
|---|---|---|
| Fight a target | at or below my level, or restrained; `fight.py` refuses 3+ above me | runs 03-06 |
| Drink a cure potion | at 70% HP (`delve.py` stops there); with no foe in view `cure.py` (the spell) before a potion | runs 04, 25 |
| Read teleport at once | under 50% HP after drinking; a turn that cost over 15% and left me under 70% (run 24: at 178 HP the plain 15% rule stopped routine fights at 84%), or over 25% at any HP; two hits in a row over 15%; two or more foes above my level closing in; a teleport that lands within 2 of a foe at or above my level (teleport again). **One exception, once a fight:** a lone foe at 10% HP or less gets one more round when the same hit again would leave me at 40%+ (`last_swing_hp`; run 37: the iron maiden master at 1%, two teleports had already reset the fight, one swing killed it for 4 HP) | runs 04, 07, 37 |
| Leave the floor | when going on would spend the **escape reserve** (2 teleports + 3 heals untouched), or an "avoid"-group kind (threat.py) near my level holds the floor; otherwise, after a bad fight, heal to 80% with no foe in view and go on (run 16, the user: "you may be teleporting out too early"; knowledge/risk.md). **The floor gate:** `delve.py` refuses a floor above `MAX_DANGER` (**34 at Lv48** (run 56, **G67 done**: up to 33 by G67 M1-M3, **back to 32** by the step rule for a near-death on the Minotaur's Nest B5 at danger 30: Ungogo's melee round 398 -> 132, fact #1573; **33 again** on Ancient Forest B2 at danger 31, lowest 94%, no drink, fact #1581; **34** on its B3 at danger 32, 44 fights, lowest 96%, no drink, G67 M4, fact #1582): run 51 raised it three times to 20, G59 done; the user stepped it to 21 after the run; run 52 four steps to 25, G61 done: Traditional Ruin B1-B4 at danger 20-23, each at the unattended limit, lowest 94%, no drink, its master 『Stalker』 Lv34 on B4; G64 Floor gate 30 set by the user after run 53: run 53's one floor at 24 fell to 59% on a named Wyvern; run 54 stepped to 26, G64 M1: Unknown Cave B5 at danger 24, lowest 91%, no drink, its master 『Asura』 Lv36; run 55 to 27, G64 M2: Dangerous Ruin B5 at danger 25, lowest 76% on the floor, no drink, its master 『Monster mushroom』 Lv37; and to 28, G64 M3: Sunken Temple of Lurie B2 at danger 26, lowest 90%, no drink; and to 29, G64 M4: its B3 at danger 27, lowest 90%, no drink; and to 30, G64 M5, G64 done: its B4 at danger 28, lowest 80%, no drink; **back to 29** by the step rule for run 55's near-death on the Minotaur's Nest B4 at danger 29, applied after the run; **G67 Floor gate 34** set by the user 2026-11-20; run 56 to 30: Dangerous Cave B1 at danger 28, the unattended limit, 8 fights, lowest 91%, no drink, G67's step with no milestone; and to 31, G67 M1: its B2 at danger 29, 13 fights, lowest 96%, no drink; and to 32, G67 M2: its B3 at danger 30, 16 fights, lowest 98%, no drink; and to 33, G67 M3: its B4 at danger 31, 35 fights, lowest 81%, no drink); `ladder.py` takes the same gate for every floor (one less with `--unattended`). Its history and the rule for raising it: elin-delve 5 | runs 05-45 |
| Swarm | 6+ hostiles, or 4+ with any at or above my level, or over 15% HP a turn: teleport, then `leave.py --force` (`delve.py`, `hunt.py` and `wgo.py --ambush` stop on the count rule; `fight.py` stops on a round that cost over 15% and reads teleport at or under 10%). **Hostiles 12+ levels under mine count half** (run 21: two stops on Lv1-7 crowds of 6-7 at Lv21, fought for no loss; then twelve Lv4-8 at Machinarium B3 cost 140 -> 106, so they count, at half; unseen ones count in full). **25+ levels under mine don't count** (run 43: twelve Lv4 geese at Lv37, PV 82) | runs 03, 08, 21, 43 |
| Swarm ability (`swarm_ability_min` 3, `swarm_ability_sp` 40) | `fight.py` casts it instead of a swing when 3+ hostiles stand within 3 cells and SP is 40+ (elin-delve 6) | run 40 |
| Suicide attackers (kamikaze yeek, hot guy, **bomb rock**, any ActSuicide: threat.py's exploder flag) | never adjacent: soak with a thrown potion (Wet stops the blast), throw from **5+ cells** (`kamikaze_dist`; `delve.py` steps back to 5 first); **a named exploder halts delve: its death blast is past any HP** (two deaths). The rest: elin-delve 6 | runs 04, 12, 33, 37, 41 |
| Threat order (the user, run 16) | `threat.py`: an **avoid** kind (high offense + high defense) within 8 levels of mine stops `delve.py` and `fight.py`; 15+ levels under mine it's an ordinary foe (`avoid_ignore_below`). The order and the range kinds: elin-delve 6 | runs 16, 17, 43 |
| World-map routes | `wgo.py` refuses a route whose worst ambush level is over **20** (`route_max`) unless `--danger-ok [N]` is given for a deliberate crossing; a walk stops under 60% HP, at Hungry and at Very Sleepy (elin-travel 2) | runs 21, 28, 41 |
| A long walk at home (`farmday.home_guard`) | a meal at hunger 65, a stop at 80 with no meal landed, fight what's at or under my level, stop under 60% HP; a home loop stops under 80% (elin-home 6) | run 41 |
| Jobs with "(Danger Lv.N)" or "kill N" | my level >= N + 3, 5+ potions, a light, and I could beat 4 of its monsters at once; an instance job moves me in the moment the dialog ends | runs 03, 05 |
| Status | Starving, Exhausted, Burden phase 3+ and poison kill over time: fix first (blue herb or troll blood for poison); confused or afraid: stay put until it clears. **A loop never works at Hungry (70+) and never sleeps hungry**: springday, farmday, trainday and minewalls stop at 70 (`common.ready`), springday stops when a meal fails at hunger 60+, `sleep.py` refuses at 50, in a nefia, and at home without `--home-ok`; no unattended loop starts without 3 days of my own food (run 18: **death by starvation** in a home loop with nothing edible left; a harvest load Squashed me to 22% HP: burden phase 3 stops every loop, 4 stops the game's own walk). **Stamina: the bridge cancels any work task (Task*, AI_UseCrafter, the dummy, fishing) once SP is at or under 3** (0.32.0 `spguard floor=N`; run 25: **death by overwork**: one drag of 124 fibers onto the spinner's grid ran as a single task, SP 51 -> -19, HP to -5, 594 orens dropped) | runs 03, 06, 11, 18, 25 |
| Unattended play (nobody watching) | home loops and nefias at the limit - 1 (`ladder.py --unattended`; was - 2 until run 16); no client-based instance jobs (deliveries and kill-count jobs are fine); `springday --once`-style steps, never a loop that waits; a town past fields over the limit only by Fast Travel | runs 03, 07, 10, 14 |

**Rules for every session, one line each (the run that cost it)**
- Know what you eat: `item.py NAME info`; `Eat` refuses foods listed harmful in foods.md and harmful traits; unknown
  mushrooms go to bait. Food lives in the Cooler Box (it rots loose). `eat.py` is a meal from the shell. (03, 05, 06)
- Don't wait (the user, runs 05 and 11): every idle hour burns food; sleep when sleepy, otherwise do SP-free work or travel.
  `wait.py` refuses without `--user-ok`.
- Quick-save before a planned risk; never reload to undo an outcome. Every death gets a cause in the run log and a line in
  the table or in the skill that covers it; the beginner period ended on 485-08-12, so a death costs items and gold.
- Deaths and near-deaths (the stories are in the run logs): 03, 07, 11, 12 (a hot guy), 17 (underwater), 18 (**starved**), 19
  (**drowned**), 25 (**overwork**), 28 (190 -> 0: a paralysis; the Godbane Necklace since), 33 and 37 (a named exploder's
  death blast), 41 (**two at home**: a walk with no stops). Most deaths were tools, not fights: every new loop or route gets
  its stops tested once before it runs unattended.
- Time-passing stretches are marked (`tools/activity.py TAG start|end`; the loops mark their own) so the close-out shows the
  rate; rent runs whatever I do (elin-travel 1).

## Start a session

**How long:** the window the player gives (`player.md` has their usual one). When they give a duration or an end ("keep at it
for the next 5 hours"), run `python -I tools/session_end.py 5h` at once: `bridge.py quit` refuses before that end without
`--early-ok` (run 21 quit two hours early; run 22 played the rest). **Who decides** (the user, run 09: "in general I'd like
you to make decisions, and then structure the rules on what happened"): the in-game calls are mine, by these rules, and each
outcome becomes a rule; I ask only about major goals. Rule zero still binds.

0. Read `player.md`, then the last run's summary if there is one (`runs/*-summary.md`: results, the graph, and the plan for
   this session), then the run log it points to, then `knowledge/goals.md` (the long-term goals: plan the session by the
   elin-goals ladder: needs, upkeep, the active goal's next milestone).
1. `grep versionText "/c/Program Files (x86)/Steam/steamapps/common/Elin/version.json"` (or the Elin folder in `player.md`):
   note any change. `python -I tools/offcheck.py`: anything a dead session left running (end a leftover server with
   `tools/ollama_stop.py`; other projects' monitors are only reported, to the user). If Ollama is installed (optional, for
   `kb.py ask`), start the repo-local one: `bash tools/ollama_serve.sh` in the background (it reuses a server already
   answering on 11435, and it ends itself after 12 hours), then `python -I tools/kb.py embed`.
2. If Elin isn't running, launch straight into the save (Elin has no "continue" launch option; the bridge's one-shot autoload
   does it): `printf SAVE > mod/dist/ElinBridge/autoload.txt` (SAVE: the save in `player.md`), then `explorer.exe
   steam://rungameid/2135150` (it exits 1; that's normal), then `python -I tools/wait_ingame.py` (prints the bridge version
   and a look once loaded).
3. Already at the title instead: `bridge.py act Cancel` (news pop-up), then `bridge.py load SAVE`. **Never use the title's
   Continue/load list**: it shows the user's cloud saves, including their own characters under the same ids.
4. `python -I tools/look.py`: a compact state (HP/MP/SP, hunger, held item, AI, creatures, items, log, and a DANGER line when
   something threatens survival). **Game speed:** `python -I tools/bridge.py speed 3` is the game's own x5 control, reset by
   every load (the user, 2026-11-06: "5x is fine", watched or not; elin-delve 1). Real time stops binding; food and money
   bind.
5. `python -I tools/power.py --log RUN`: the power card, logged to `runs/power.csv` (again at the end of the session, so each
   run shows its change).
6. At home, once there's a base (no `runs/no-base.txt`): `arrive.py`, then the rest of elin-home 1 (the box tally, `stock.py
   --find`, the books), and the kit and its resupply (elin-pack 1) before `leave.py`.

## Look it up before you guess: the knowledge graph

`tools/kb.py` joins the game's own data tables (every item, recipe, station, creature, element, zone, quest; exported through
the bridge) with what earlier runs observed (`knowledge/facts.jsonl`: prices, places, fights, foods, outcomes). Ask it before
reading game code or the wiki:
- `kb.py make "roasted fruit"` (station and ingredients), `kb.py uses blueberry` (every recipe that takes it), `kb.py station
  bonfire` (what a station makes), `kb.py show "old ticket"` (fields, elements, edges, observed facts), `kb.py find TEXT`,
  `kb.py facts TEXT` (superseded facts hidden; `--all` shows them).
- `kb.py ask "what heals HP quickly"`: plain-language search by meaning over our notes and the game's text
  (`--notes`/`--game` to narrow). Needs the repo-local Ollama; without it, `ask` falls back to keywords.

After a new observation (a price, a location, what a food or monster did), record it: `kb.py add "travel ration" costs "50
orens" --run 03 --where Mysilia --note "Tiguen (inn)"` (`--supersedes N` when it corrects fact N). New game version
(`version.json`): `kb.py build` with the game running (about 10 s). Ingredients match an item's id or its origin, `#x` means
category x, `+` is optional.

## The loop: perceive, act once, verify

The tools are indexed in **`tools/README.md`** (generated from each tool's docstring by `python -I tools/toolindex.py`:
purpose, usage, exit codes), and what each tool's domain taught the runs is in **`knowledge/tool-notes.md`**: read a tool's
entry before its first use in a session. The ones every session uses: `look.py` (state), `bridge.py` (acts, cells, map,
buttons, inv), `item.py NAME ACTION`, `act.py DX DZ TEXT`, `talkto.py`/`talk.py`, `close.py`, `fight.py`, `seq.py` (a chain
that stops at the first refusal), `kb.py`, `journal.py`, `power.py --log`, `activity.py`; the rest are named in the skill
that owns their task. The shared helpers are `tools/common.py` (`run`, `walk`, `wait_idle`, `cells`, `pick`/`matches`,
`ready`, `grab`, `pack_full`, `THRESHOLDS`).

Coordinates are map deltas from me (`DX DZ`); `goto X Z` takes absolute cells. Most acts walk there themselves; Talk needs
distance <= 2, melee and installed stations need adjacency. Local maps are isometric: screen n(-1,+1) ne(0,+1) e(+1,+1)
se(+1,0) s(+1,-1) sw(0,-1) w(-1,-1) nw(-1,0); plan in map deltas (`step dx dz`). The world map is top-down (+x east, +z
north): `move n|s|e|w` there, `step` goes the wrong way (runs 01, 03).

**The bridge's own guard (0.30.0):** every world op (goto, walkto, move, step, do, invdo, invacts, drag, shiftclick,
autocombat, and `act` except Cancel/Confirm/Menu*/Log/Report/QuickSave) is refused with "window open: X", "context menu open"
or "drama open" while one is open, a read of a return or evacuation scroll is refused while one counts down, a drag onto a
stack of the same item is refused (run 13's lost textures), and a walk is refused at Squashed or when its path would enter
deep water (`why: water`, before the first step). `force=1` bypasses a guard on purpose, never by habit.

## Hard rules (each one cost something before)

- **Never chain game-acting tools with `;`, and never run a later step after a refusal** (runs 21, 28, 29, 42, 43, 45: an
  Enter after a refused wgo.py walked me back into the place I had left, twice; a `;` chain walked home without the wagon
  after a failed pick-up, a wasted 25-game-hour leg). Use `python -I tools/seq.py "act.py 0 0 'Pick all'" "leave.py" "wgo.py
  12 34"`: each argument is one tool call without the `python -I tools/` prefix; it stops at the first non-zero exit and
  exits with that code. **No shell loops over game actions** either (run 19: a `for` loop of tool calls ran on under a
  shipping report window; run 51: a `for` loop of fight.py over six foes): the loop tools check windows and stops
  themselves. The user's PreToolUse hook (the chain check in `.claude/hooks/`, its loop rule installed 2026-11-17) refuses both: two acting
  tools in one line, and one inside a `for`/`while`/`until`/`foreach`/`xargs` loop. With a pipe, `set -o pipefail` (run 21: `tool |
  tail -1 && next` gated on tail).
- **Read the exit code, not the text:** 0 done, 1 refused, 2 the bridge, 3 stopped for a decision. A tool that moves items
  prints everything it moved: never pipe it through `tail`.
- **One bridge client at a time** (runs 42, 45): the bridge serves one connection, so nothing else touches it while a
  background tool runs (a route plan timed out beside a dig; `stock.py --ship` broke when I walked to the loom beside it, 4
  of 36 shipped). **A background loop is running until its task says it ended** (run 44): its stop lines can be steps it
  handles itself. Wait for the task's completion notice, then act.
- **One dialog at a time.** After every click in a dialog, run `talk.py` until it reports `[dialog closed; top layer: None]`
  before opening anything else. A quest script's `completeQuest` completes whatever quest its dialog was opened for; a second
  quest opened under a waiting choice gets completed instead (run 02 lost Loytel's whole chain this way).
- **Never pick by index from a menu you haven't just listed.** Menus differ per item (a stack's entry 0 is "Split"). Use
  `item.py NAME ACTION`, and re-run `buttons` before every `click`. **Any** `buttons` call replaces the bridge's saved
  listing, including the one inside look.py and close.py: run 14's Policy-tab loop ran look.py between clicks and pressed the
  wrong rows. Click with `expect=TEXT` (bridge 0.25.0: refused unless button N still shows TEXT), and in a loop list again
  right before each click.
- **Act by exact text** on a busy cell: `act.py DX DZ "Grab (an exquisite"`; plain "Grab" picked up the home board once (run
  06). The act's wording changes with the cell (run 45: one big wagon is "Pick (a big wagon)", two are "Pick all"):
  `pickup.py NAME` takes a thing whatever the wording and exits non-zero unless the pack count rose.
- **Check the top layer after every action.** A pop-up (Nerun, a Dialog, LayerCraft) blocks play: read it with `talk.py` or
  `texts`; close crafting with its `button close`; other windows with `close.py` (never a blind `act Cancel`: it opens the
  System menu).
- **Never guess on a dialog you can't read.** Irreversible picks (pet, Fiama's "I want to die", quest choices) get decided
  from knowledge, not by default.
- **A death prompt is answered, never closed** (Start Run 3: closing it left the game at HP -1 with no dialog and no way on):
  `common.crawl_up`; `close.py` refuses at HP under 0, loops crawl up and stop.
- **Speed is damage and escape** (run 08: 105 fell to 73 over a sleepless week). Sleepiness costs -10/-20% speed ("You need
  to sleep now!"), Hungry -10%, Starving -30%, one ally over the party cap -20%. Sleep every night (`sleep.py` works on the
  world map), eat at Hungry, and check `power.py`'s speed before any dungeon.
- **Watch SP and hunger.** Each gathering tool stops at its own `min_sp` (none under 3); negative SP costs HP. Work SP comes
  back only from sleep, and a bed sleeps only when sleepy or Very tired (SP under ~20%); each sleep costs 20 hunger. Eat at
  "Hungry". Night hides cells beyond the torch.
- **Read the number, never infer it** (run 06 guessed karma at "about -50"; it was +10, and run 07's kicks made me a
  criminal). **Count from the inventory, not the log** (the log is a fixed-size ring: butcher.py once reported one skin four
  times); the worn toolbelt's stacks show in `buttons --all`, not `inv` (four skins hid there, run 13). Check twice before
  reporting a loss (runs 11, 13, 16).
- **Watch a log only with `tools/watchlog.py`, never `tail -f | grep`** (KB #155: on 2026-11-02, 141 such pipelines from this
  repo's sessions were still running days later, ~1.4 GB, and blocked the Git upgrade). Make it the Monitor tool's command:
  `python -I tools/watchlog.py runs/jobs/X.log --match 'RE' --until 'done:' --max 1790` with `timeout_ms` 1800000, so it
  exits before the harness kills it; re-arm on exit 3 while the loop runs. One per loop, and `--match` must also catch the
  failures (`Traceback|STOP|refused`): silence isn't success. Bash with `run_in_background` already reports a loop's end, so
  a monitor is only for what happens during it.
- **Never leave time passing unwatched.** Bed Pass Time runs until cancelled (21 game hours in run 03, and Loytel died
  meanwhile): `bridge.py cancel` stops a task; `wait.py HH:MM` only with the player's yes.
- **Names in full.** Tools refuse a name that fits two things ("rod of" fits two rods) and match whole words; a `craft.py
  --use` material that fills no slot is refused (run 11's threads, run 12's carbon log). Give the full name, with its count
  and charges when two differ only there. Pickers (identify, shrines, blending) are drag grids: `picker.py`, never a `click`.
- **A thing's kind comes from the game's table or its uid, never a word in its name** (runs 47-50): "iron shovel" refused a pine
  shovel, "ring" matched Ring Mail in gearcheck (48) and in item.py's two-rings guard (50), a meal list by name ate nothing (49), and
  "stir fried gourds" had no food word (50). Two tools deciding the same thing read the same table (items.meals, items.kind, the
  category in things.json); a container is named by `uid:N` when two share a name (chests.py since run 50).
- **Frame rate:** after many hours Elin fell to ~4 fps and every script timed out. If `ping` frames crawl, quit through the
  bridge and relaunch (run 06: back to ~58).
- **Quick-save after milestones and right after any big haul:** `python -I tools/bridge.py act QuickSave` (the log shows
  `*Saved*`; run 19: a game hang lost 12 minutes, and a 2,249-oren chest had to be looted again from the save).
- Play honestly: no debug, console, save edits or reloads to undo outcomes.

## End a session

Follow **elin-closeout**: the power card and `python -I tools/bridge.py quit` (the only allowed way: it saves first), the run
log, metrics and milestones, facts, lessons and skills, the summary with its diagrams, the rendered page
(`tools/summary_page.py`, published and checked), the memory, a local commit, then everything off: `tools/ollama_stop.py` and
`tools/offcheck.py`.

## Changing the bridge

Edit `mod/ElinBridge/Bridge.cs`, bump `Version`, compile-check into the scratchpad with `bash mod/build.sh
"-p:OutputPath=<scratchpad>/bridgecheck/"`, then: `bridge.py quit`, wait for Elin.exe to exit, `bash mod/build.sh`, write
`autoload.txt`, launch, `wait_ingame.py` (shows the new version). About 60 s. Batch changes to save restarts. Read the game's
own code first (raw.githubusercontent.com/Elin-Modding-Resources/Elin-Decompiled/main/Elin/<Class>.cs; Plugins.UI types are
not there).
