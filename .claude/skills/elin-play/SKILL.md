---
name: elin-play
description: Operating manual for playing Elin through the ElinBridge mod in this repo. Use at the start of every Elin play session and whenever acting in the game - launching and loading, the knowledge graph (kb.py), the perceive-act-verify loop, the tool scripts (look, talk, talkto, item, harvest, craft, fight, shoot, hunt, ladder, leave, gather, firstcraft, find, train), safety rules learned in earlier runs, and the bridge rebuild cycle.
---

# Playing Elin through the bridge

Related skills: **elin-goals** (long-term goals: the register in knowledge/goals.md and how to
plan sessions by it), **elin-home** (the base: storage by category, keep/ship rules, cleaning, furniture,
safety), **elin-town-trip** (Mysilia and back: road, ambushes, tax, shopping), **elin-closeout** (ending
a session: logs, facts, the summary and its rendered page), elin-build, elin-opening.

Every action goes through the game's own code paths (ActPlan, InvOwner, the UI's own
buttons), so the game's rules, warnings and costs still apply. Read state, act once, verify.

## Rule zero: don't die (the user's #1 goal; everything else is secondary)

Speed, quests, loot and looks all yield to survival. Before any risky step, ask "what kills me
here, and how do I leave?" The numbers below are the only ones (the run 12 review found seven
HP floors stated in five places); the other skills point here. **In code they are `THRESHOLDS` in
`tools/common.py`**, which the tools read and `hygiene.py` checks against this table (the review of
2026-10-23 found the gate at 8 here and 7 in ladder.py, Hungry at 70 here and 80 in farmday).

**Thresholds (one table; the tools default to it)**

| Situation | Number | Where it came from |
|---|---|---|
| Fight a target | at or below my level, or restrained; `fight.py` refuses 3+ above me | runs 03-06 |
| Drink a cure potion | at 70% HP (`delve.py` stops there) | run 04 |
| Read teleport at once | under 50% HP after drinking; a turn that cost over 15% and left me under 70% (run 24: at 178 HP the plain 15% rule stopped routine fights at 84%), or over 25% at any HP; two hits in a row over 15%; two or more foes above my level closing in; a teleport that lands within 2 of a foe at or above my level (teleport again). **One exception, once a fight:** a lone foe at 10% HP or less gets one more round when the same hit again would leave me at 40%+ (`last_swing_hp`; run 37: the iron maiden master at 1%, two teleports had already reset the fight, one swing killed it for 4 HP) | runs 04, 07, 37 |
| Leave the floor | when going on would spend the **escape reserve** (2 teleports + 3 heals untouched), or an "avoid"-group kind (threat.py) near my level holds the floor; otherwise, after a bad fight, heal to 80% with no foe in view and go on (run 16, the user: "you may be teleporting out too early"; knowledge/risk.md). **The floor gate:** `delve.py` refuses a floor above `MAX_DANGER` (**14 at Lv35** since run 40: two danger-12 floors at the unattended limit cleared without a drink; 13 at Lv33 from run 36: a near-death, 218 -> 0 in one round on Dark Ruin B5 at danger 12 under the unattended 13; it was 14 from run 34's Chilly Cave B3; raised one step only after a floor at the limit was cleared without a drink; each change is in fact #1047 and its successors); `ladder.py` takes the same gate for every floor (one less with `--unattended`) | runs 05, 07, 12, 15 |
| Swarm | 6+ hostiles, or 4+ with any at or above my level, or over 15% HP a turn: teleport, then `leave.py --force` (`delve.py`, `hunt.py` and `wgo.py --ambush` stop on the count rule; `fight.py` stops on a round that cost over 15% and reads teleport at or under 10%). **Hostiles 12+ levels under mine count half** (run 21: two stops on Lv1-7 crowds of 6-7 at Lv21, fought for no loss; then twelve Lv4-8 at Machinarium B3 cost 140 -> 106, so they count, at half; unseen ones count in full) | runs 03, 08, 21 |
| World-map routes | `wgo.py` refuses a route whose worst ambush level (along the straight line, the best tile within a step) is over **20** (`route_max`; 12 from Lv21 to run 41's Lv35: the same share of my level, PV 91, and fact #1186's level 24 field cost 0 HP) unless `--danger-ok [N]` is given for a deliberate crossing; **every leg checks the tiles actually reached** against the allowed level (run 28: the game's pathing swung east of the straight Mysilia -> Mifu line into a danger-26 ambush where the line said 19); a walk stops at Hungry and at Very Sleepy (20 s legs) | run 21: a walk north met a level 21 field (a stone golem Lv22, a cupid Lv18); level 9-10 crossings at Lv21 cost under 10% HP |
| Swarm ability (`swarm_ability_min` 3, `swarm_ability_sp` 40) | `fight.py` casts it instead of a swing when 3+ hostiles stand within 3 cells and SP is 40+, never beside an exploder or a slime (12 SP; a 0.9x melee blow on each: the code, ActSwarm) | run 40 (50 platinum at Eligin) |
| Suicide attackers (kamikaze yeek, hot guy, **bomb rock**, any ActSuicide: threat.py's exploder flag, or 'kamikaze' in the id; run 24's bomb rock took 145 -> 0 in melee when delve read names only) | never adjacent: soak with a thrown potion (Wet stops the blast), throw from **5+ cells** (a kill at 2 cells still cost 30 HP, run 40's throw a blast took 49%, and run 41's two took 46% and 77%; `delve.py` steps back to 5 first) ; **a named exploder halts delve: its death blast is past any HP** (run 33: **death**, 214 -> -342; run 37: **death** again, 216 -> -478: the state lists a named one as plain 'Hot guy', the 『』 only in the log, so the check never fired until `common.named` read the capital; kill it from 5+ by hand) | runs 04, 12, 33 |
| Casters, archers, yeek warriors, shamans, mummies, drones, slimes, floating eyes | from range first (the Putit, the bow with arrows, the rod of slow); melee only what shrugs at range | runs 06, 08, 12 |
| **Evasive kinds** (threat.py `evasive`: race DV 20+, or 15+ at speed 150+: bats, fairies, the metal bells) | the user, run 34: "that kind of adversary we should know is hard to kill with swords": fight.py casts an arrow spell each round (Fire Bolt solo: a bolt's line can hit the crew) while MP >= 25, then throws the ★Putit In Amber (hit 128% against the axe's 105%); melee last (`--melee` to force it) | run 34 (a vampire bat: 20% a round, the axe missing) |
| Kit for a nefia | elin-pack 1 (2+ scrolls of teleport, an evacuation, a return, 5+ cure potions, a light, the pickaxe, the Putit); `ladder.py` refuses to start under 2 teleports, 3 cures, an evacuation and a return (it opens the backpack to count; `--kit-ok` overrides) | runs 05, 08, 20 |
| Go into a nefia at all | the floor gate and the kit; power.py's level-only table is advice only (it predicts the median fight 50x too high, run 16): `threat.py NAME` per kind decides; Lv5+ for the first | runs 04, 05, 16 |
| Threat order (the user, run 16) | `threat.py`: exploders never adjacent; **kill first** high offense + low defense, casters, summoners, blinders, paralysers, healers (from range); **kill last** high defense + low offense; an **avoid** kind (high offense + high defense) within 8 levels of mine (4 until run 17: two Lv12 lizardmen took 45% of my HP in two turns at Lv18) stops delve.py and fight.py: range it or leave | run 16 |
| Allies (the user, run 16) | **solo is the default since run 38** (the user, 2026-11-01: "solo seems to work better for now at least so we'll stick with it and optimize"; G38: solo 7.4 real minutes a conquest against the crew's 10.0, exp even; fact #1139): the allies wait at home; with one along, take it as an expendable shield (`delve.py --expendable`): back home free in 0-7 days (Zone.Revive), -10 affinity; Strategy tab "Always stay by you while in combat" on; a teleport scroll leaves her behind; two slots at CHA 19 with Party Animal (CHA 20 opens a third; Lonely Soul pays +3% HP and speed per empty slot: facts #746-#747) | runs 04, 05, 16, 20 |
| Auto-combat net (bridge 0.26.0) | fight.py fights in the game's GoalAutoCombat: a lethal hit on anyone healthy at its start leaves them at 0 HP once (Card.DamageHP); at 0 HP the next action is a teleport | run 16 |
| Jobs with "(Danger Lv.N)" or "kill N" | my level >= N + 3, 5+ potions, a light, and I could beat 4 of its monsters at once; an instance job moves me in the moment the dialog ends | runs 03, 05 |
| Status | Starving, Exhausted, Burden phase 3+ and poison kill over time: fix first (blue herb or troll blood for poison); confused or afraid: stay put until it clears. **A loop never works at Hungry (70+) and never sleeps hungry**: springday, farmday, trainday and minewalls stop at 70 (`common.ready`), springday stops when a meal fails at hunger 60+, `sleep.py` refuses at 50, in a nefia, and at home without `--home-ok`; no unattended loop starts without 3 days of my own food (run 18: **death by starvation** in a home loop with nothing edible left; a harvest load Squashed me to 22% HP: burden phase 3 stops every loop, 4 stops the game's own walk). **Stamina: the bridge cancels any work task (Task*, AI_UseCrafter, the dummy, fishing) once SP is at or under 3** (0.32.0 `spguard floor=N`; run 25: **death by overwork**: one drag of 124 fibers onto the spinner's grid ran as a single task, SP 51 -> -19, HP to -5, 594 orens dropped) | runs 03, 06, 11, 18, 25 |
| Unattended play (nobody watching) | home loops and nefias at the limit - 1 (`ladder.py --unattended`; was - 2 until run 16: the net, the reserve and boxed gold now stand between a bad turn and death); no client-based instance jobs (deliveries and kill-count jobs are fine); `springday --once`-style steps, never a loop that waits; a town past fields over the limit (Derphy: danger 7-12) only by Fast Travel (no ambushes; 1 + hours/24 rations, 50 each at inns) | runs 03, 07, 10, 14 |
| Carried gold into a nefia | spend down first, or box it at home: carried orens are currency and can't be boxed (run 16), but picked-up coins are an item stack (`box.py 57,54 "685 orens"`, take it back with `--take` before the tax day: springday pays from carried gold) (a death past the beginner period drops 33-67% of it on the death tile, the code: Chara.ApplyDeathPenalty; no items or levels are lost; run 12 took 1,373 into danger 8-9) | the user, run 03; the review; run 15 |

**Rules, one line each (the run that cost it)**
- **A long walk at home has stops too** (run 41: **two deaths at home in one night**: arrive.py's box walk from hunger 70 to 93 and HP -3 with meals in the Cooler Box, then an orc warrior Lv11 and a scorpion Lv7 taking 263 -> -1 while the mover went box to box without a swing): `farmday.home_guard` before every step of arrive.py, `packcheck --move` and the trash sweep: a meal at 65, a stop at 80 with no meal landed, fight what's at or under my level, stop under 60% HP. A tool's "no meal" is a stop for me as well: never start the next long job on it. (41)
- **"Enemy spotted" with nobody in view is an invisible foe beside me** (run 41: a walk to the stairs ended four times): See Invisible (`ladder.see_unseen` does it once a floor), then fight what it shows. (41)
- **Read the game's table, not an id** (run 41): `samurai_kamikaze` has no ActSuicide (knowledge/game/charas.json): 'kamikaze' in its id cost teleports for 7 runs. A real exploder has ActSuicide: yeek_kamikaze, hardgay, bombrock. (41)
- **Bomb rocks blink in** (run 41: 77%, 46%, 47% through ranged throws at 4 cells): 5+ cells, soak first (`delve.SOAK` falls back to a thrown cure minor wound: any thrown potion wets). **A named exploder I can't out-damage from range is a reason to leave the floor** (Mossy Grassland B5: a named Kamikaze yeek adjacent twice in 30 turns, arrows ~1% a cast at Casting 11): `namedexploder.py` when the spell can kill it, else the stairs. (41)
- **A flee has to move** (Start Run 3: 56 -> -4 and 43 -> -4 HP on one cell): `leave.py --force` hands back after an attempt that moved under 2 cells, and a teleport-less `fight.py` fights on while no foe is above my level and HP holds 40%: walking away from what I can kill is what killed. (Start Run 3)
- **A death prompt is answered, never closed** (Start Run 3: closing it left the game at HP -1 with no dialog and no way on): `common.crawl_up`; `close.py` refuses at HP under 0, loops crawl up and stop. (Start Run 3)
- **A bandit's demand is read before it's paid** (Start Run 4: an automatic surrender gave up all 8 gold bars): `roam.py` refuses demands for gold bars, platinum, tickets or the weapon. A surrender ends a lone bandit; a gang keeps hitting (Start Run 3). (Start Runs 3, 4)
- **One weapon, the other hand empty** (the user, after run 37: "our damage per hit has gone way down"): anything else in a
  hand, a shield or a second weapon, switches off the game's two-hand style (x1.5 damage, +25 to-hit): the axe alone 22.8
  a turn vs Lv33, 9.5 beside the Dreadbane Small Shield (fact #1137); worn from run 21 (a second weapon) and run 30 (the
  shield), unseen because the power card's melee column summed the party. `item.py` refuses an off-hand Equip beside a
  lone weapon (`--offhand-ok`), `common.empty_slots` counts a lone weapon as a full hand, and the card logs `my_melee`:
  judge any hand change on it. (37)
- Target order by damage out over time to kill (tools/threat.py since run 16, by each kind's offense and defense): casters and potion-throwers first, hard-to-kill
  ones last (a goblin wizard did most of a 57 -> 29 drop beside a special Orc). (06)
- HP decides, not the count: weak foes in numbers are a normal fight while HP holds. (04)
- **A foe that keeps running away gets thrown weapons, spells or ranged attacks, not a chase** (the
  user, run 21): fight.py throws the Putit In Amber at a target that kept its distance after one
  approach or moved away. (21)
- Never Rest, Wait, Pass Time or sleep in a dungeon: monsters keep coming (Kaberg was knocked
  out during a Rest). To recover, leave and rest outside. (04)
- Evacuation (10-19 turns) or the stairs only with no foe in view; the return scroll (~18 turns)
  is for going home from a safe spot, never an escape (read at 12 HP, it never fired). (03, 07)
- On any map with water, check the cell before stepping; never wander a dark map to search for a
  quest client (a client who can't be found is a failed job, -5 karma, not a reason to risk it). (07)
- A hostile caster in view ends a performance; under paralysis an HP floor can't be trusted:
  leave at the first big hit. (11)
- Blind (a master yeek's darkness bolt): no Attack act and a step into the unseen foe does nothing;
  walk away until it clears (~7 turns), drink at 70%, then kill the yeek from range. delve.py stops
  on ConBlind. (14)
- **Boxed in on a floor** (runs 25, 28): delve's "no way down" / explore.py's walks that go nowhere mean a pocket (a wreck trap, a Machinarium's metal walls): **zap a rod of teleport** (the Teleport spell fizzles at Casting 3), then explore again; mining toward the known map (granite 18, copper blocks 34) is the slow way. (25, 28)
- **No underwater dungeons** (the user, run 17: "you can't do those kinds of dungeons"): an
  "Underwater Ruin" (Zone_dungeon_water) suffocates every turn (ConSuffocation) on top of the fight:
  112 -> 20 HP on a danger 4 B1 while delve.py waited on its HP rule, and the user walked me out.
  wgo.py and delve.py refuse them unless `--breathe`, which is for water breathing in hand. (17)
- **Deep water drowns** (run 19: **death** in Port Kapul's harbour): the game's own pathing swims, and every step
  and turn in deep water suffocates (Cell.CanSuffocate; shallow water only wets). Bridge 0.28.0's walkto refuses a
  deep-water target and stops before its path enters one (why "water"); `state.pc.pathWater` shows it for any walk
  (a guard's directions: whereis.py cancels); `cell` has `suffocate`. Never sweep waypoints over a map without
  checking them, and a walk that stops in water must be followed by getting out, not by retries. (19)
- **Mining, digging and hammering property in a town are crimes** (run 23, facts #818, #823): Karma -1
  each (a hammered thing 2 times in 3), the game asks "Really commit a crime?", and every progress tick
  rolls 1 in 10 per human within Distance 3 with line of sight (asleep too) to call the nearest guard
  (Aquli Teola's are Lv40). Only with `tools/sneakmine.py` (bridge 0.31.2's sneak guard cancels the task
  at the start of my turn when a possible witness is within 3); never by hand. A claimed zone is mine:
  no crime there, but **a claim makes that zone the home** (the return scroll then skips Meadow:
  "Set as your Home" at Meadow's hearth; recall.py refuses). (23)
- **Butcher only after combat or when safe** (the user, run 15: "trying to butcher while in combat is
  high risk and we keep getting stuck"): a butchering task with a foe just out of sight got me hit
  and stuck. **But don't leave the meat behind** (the user, same run): between fights the corpses
  are picked up, not butchered (`loot.py --no-butcher`; at most 5 wait in the pack), and every stop
  of delve butchers them when nothing hostile is in view; loot.py won't butcher with a hostile in
  view and butcher.py stops when one appears. On an ambush map, `loot.py 20` before leaving. (15)
- Special mobs (a capitalized name) carry the best loot: fight and loot them first when at or
  below my level; never leave a map with one alive. (04)
- Carry a light: night maps and quest instances show 8 cells without one. (05)
- Know what you eat: `item.py NAME info`; `Eat` refuses foods listed harmful in foods.md and
  harmful traits; unknown mushrooms go to bait. Food lives in the Cooler Box (it rots loose). (03, 05, 06)
- Don't wait (the user, runs 05 and 11): every idle hour burns food; sleep when sleepy (any bed in
  the pack works on the road), otherwise do SP-free work or travel. `wait.py` only for a timed
  event with no other way.
- Speed is damage and escape: sleepiness costs 10-20% speed, Hungry 10%, Starving 30%; sleep every
  night, eat at Hungry, read `power.py`'s speed before a dungeon. (08)
- **Sleepy at a dungeon's door? Sleep on the overworld first** (the user, run 17): `sleep.py` on the world map tile, then enter. (17)
- Quick-save before a planned risk; never reload to undo an outcome. Every death gets a cause in
  the run log and a line in the thresholds or the rules above; the beginner period ended on
  485-08-12, so a death costs items and gold.
- Deaths and near-deaths (the stories are in the run logs): 03, 07, 11, 12 (a hot guy), 17 (underwater), 18
  (**starved**), 19 (**drowned**), 25 (**overwork**), 28 (190 -> 0: a paralysis; the Godbane Necklace since), 33 (a named kamikaze's
  death blast), 37 (a named hot guy's death blast: the named check had never worked; 74,437 dropped orens recovered from the grave). Six of the eight deaths were tools, not fights: every new loop or route gets its stops tested once before it runs unattended.
- **Converter grids run the whole stack as one task** (the butcher's tool, the spinner: run 25): a dragged stack of
  124 fibers spins thread after thread until the stack or the stamina is gone, and item pickups show nothing
  until it ends. Drag what the SP covers (~1 SP a thread, 6 a texture), watch SP not the AI state, and never
  close the grid early (the open grid restarts the crafter; the bridge's floor cancels it each time). (25)
- **Rent runs whatever I do** (the review of 2026-10-23): ~70 orens a game day, and a training-day
  loop passes 20-40 game days a real hour (1,400-2,900 of tax an hour for ~0 orens earned); a 3-day
  walk costs ~200. Price a time-passing stretch in rent before starting it; the loops mark their
  start and end in `runs/activity.csv` (`tools/activity.py`) so the close-out shows the rate.

## Before leaving home: the pack

The method is **elin-pack**: the kit, what never rides along, `packcheck.py --move` on every
arrival and `leave.py`'s refusal to leave until it passes. In one line: use now (unlearned
recipes, better gear, food that would rot), bring the kit, store the rest by theme, never ship by
default. Carry only modest money.

## Start a session

**How long:** the window the player gives (`player.md` has their usual one). When they give a duration or an end
("keep at it for the next 5 hours"), run `python -I tools/session_end.py 5h` at once: `bridge.py quit`
refuses before that end without `--early-ok` (run 21 quit two hours early; run 22 played the rest).

**Who decides** (the user, run 09: "in general I'd like you to make decisions, and then structure
the rules on what happened"): I make the in-game calls (gear, feats, spending, routes, risk) by these
rules and turn each outcome into a rule; I ask the user only about major goals. Rule zero still binds.

0. Read `player.md`, then the last run's summary if there is one (`runs/*-summary.md`: results, the graph, and the plan for this
   session), then the run log it points to, then `knowledge/goals.md` (the long-term goals:
   plan the session by the elin-goals ladder: needs, upkeep, the active goal's next milestone).
1. `grep versionText "/c/Program Files (x86)/Steam/steamapps/common/Elin/version.json"` (or the Elin folder in `player.md`): note any change.
   `python -I tools/offcheck.py`: anything a dead session left running (end a leftover server with
   `tools/ollama_stop.py`; other projects' monitors are only reported, to the user).
   If Ollama is installed (optional, for `kb.py ask`), start the repo-local one: `bash tools/ollama_serve.sh` in the background (it reuses a
   server already answering on 11435, and it ends itself after 12 hours),
   then `python -I tools/kb.py embed`.
2. If Elin isn't running, launch straight into the save (Elin has no "continue" launch
   option; the bridge's one-shot autoload does it):
   `printf SAVE > mod/dist/ElinBridge/autoload.txt` (SAVE: the save in `player.md`), then
   `explorer.exe steam://rungameid/2135150` (it exits 1; that's normal), then
   `python -I tools/wait_ingame.py` (prints the bridge version and a look once loaded).
3. Already at the title instead: `bridge.py act Cancel` (news pop-up), then
   `bridge.py load SAVE`. **Never use the title's Continue/load list**: it shows the user's
   cloud saves, including their own characters under the same ids.
4. `python -I tools/look.py`: a compact state (HP/MP/SP, hunger, held item, AI, creatures,
   items, log, and a DANGER line when something threatens survival).
   **Game speed** (trials, Start Runs 1-4): `python -I tools/bridge.py speed 3` is the game's own x5 control, reset by every load: 31 SP on the dummy in about 5 s, a sleep in about 4 s, 60
   world-map hours in about 2 s. Real time stops binding; food and money bind. `fight.py` drops to x1 for its rounds and puts it back. **Floors at x5 were tested in run 41:** a conquest in about 8 real minutes against run 40's 28, 22+ in a window, and no blast or fight went worse for it: `fight.py` drops to x1 for its rounds and `ladder.descend` takes the stairs at x1 (at x5 the walk to them ended short). **The user's call (2026-11-06): "5x is fine", watched or not.** `speed 1` only the moment a named exploder or a hard stop is in play.
5. `python -I tools/power.py --log RUN`: the power card, logged to `runs/power.csv` (again at
   the end of the session, so each run shows its change).
6. At home, once there's a base (no `runs/no-base.txt`): `arrive.py` (the Dishes box shared, `packcheck.py --move`, the mail, trash,
   town.py, a food line), then the farm round (`springday.py 1 UNTIL --once`), per elin-home.

Reading descriptions: `bridge.py hover N` shows button N's tooltip as a mouse hover would and
prints it (policies, items, abilities). Toggle buttons show `[x]` in `buttons` when checked.
Context menus opened by a bridge command stay open: list them with `buttons --all`.

## Look it up before you guess: the knowledge graph

`tools/kb.py` joins the game's own data tables (every item, recipe, station, creature, element,
zone, quest; exported through the bridge) with what earlier runs observed (`knowledge/facts.jsonl`:
prices, places, fights, foods, outcomes). Ask it before reading game code or the wiki:
- `kb.py make "roasted fruit"`: station and ingredients (any of: apple, blueberry, ...).
- `kb.py uses blueberry`: every recipe that takes it (through its origin and category too).
- `kb.py station bonfire`: what a station makes, and which recipes are known from the start.
- `kb.py show "old ticket"`: fields, elements (nutrition is element 10), edges, observed facts.
- `kb.py find TEXT`, `kb.py facts TEXT`.
- `kb.py ask "what heals HP quickly"`: plain-language search by meaning over our notes and the
  game's text (`--notes`/`--game` to narrow). Needs the repo-local Ollama
  (`bash tools/ollama_serve.sh` in the background, then `kb.py embed` after adding facts);
  without it, `ask` falls back to keywords.
After a new observation (a price, a location, what a food or monster did), record it:
`kb.py add "travel ration" costs "50 orens" --run 03 --where Mysilia --note "Tiguen (inn)"`.
New game version (`version.json`): `kb.py build` with the game running (about 10 s).
Ingredients match an item's id or its origin, `#x` means category x, `+` is optional.

## The loop: perceive, act once, verify

The tools (110) are indexed in **`tools/README.md`** (generated from each tool's docstring by `python -I tools/toolindex.py`;
purpose, usage, exit codes), and what each tool's domain taught the runs is in **`knowledge/tool-notes.md`** (the table that
lived here until the 2026-10-30 review). The ones every session uses: `look.py` (state), `bridge.py` (acts, cells, map,
buttons, inv), `item.py NAME ACTION`, `talkto.py`/`talk.py`, `fight.py`, `delve.py`/`ladder.py` (floors), `loot.py`,
`purge.py --free N`, `stairs.py up|down`, `evac.py`/`recall.py` (out and home), `wgo.py` (the world map), `leave.py`,
`arrive.py`/`packcheck.py --move` (home), `digmap.py`/`chests.py` (treasure maps, the best orens an hour there is: section below), `eat.py` (a meal from the shell), `readrecipes.py`, `namedexploder.py`, `kb.py` (the graph), `journal.py guilds`, `power.py --log`, `activity.py`.
Every tool: exit 0 done, 1 refused, 2 the bridge, 3 stopped for a decision; callers branch on the code, never the text.
The shared helpers are `tools/common.py` (`run`, `walk`, `wait_idle`, `cells`, `pick`/`matches`, `ready`, `grab`,
`pack_full`, `THRESHOLDS`).

Coordinates are map deltas from me (`DX DZ`); `goto X Z` takes absolute cells. Most acts walk
there themselves; Talk needs distance <= 2, melee and installed stations need adjacency. Local
maps are isometric: screen n(-1,+1) ne(0,+1) e(+1,+1) se(+1,0) s(+1,-1) sw(0,-1) w(-1,-1) nw(-1,0);
plan in map deltas (`step dx dz`). The world map is top-down (+x east, +z north): `move n|s|e|w`
there, `step` goes the wrong way (runs 01, 03).

**The bridge's own guard (0.30.0):** every world op (goto, walkto, move, step, do, invdo, invacts,
drag, shiftclick, autocombat, and `act` except Cancel/Confirm/Menu*/Log/Report/QuickSave) is
refused with "window open: X", "context menu open" or "drama open" while one is open, a read of a
return or evacuation scroll is refused while one counts down, a drag onto a stack of the same item
is refused (run 13's lost textures), and a walk is refused at Squashed or when its path would enter
deep water (`why: water`, before the first step). `force=1` bypasses a guard on purpose, never by habit.

## Hard rules (each one cost something before)

- **One dialog at a time.** After every click in a dialog, run `talk.py` until it reports
  `[dialog closed; top layer: None]` before opening anything else. A quest script's
  `completeQuest` completes whatever quest its dialog was opened for; a second quest opened
  under a waiting choice gets completed instead (run 02 lost Loytel's whole chain this way).
- **Never pick by index from a menu you haven't just listed.** Menus differ per item (a stack's
  entry 0 is "Split"). Use `item.py NAME ACTION`, and re-run `buttons` before every `click`.
  **Any** `buttons` call replaces the bridge's saved listing, including the one inside look.py and
  close.py: run 14's Policy-tab loop ran look.py between clicks and pressed the wrong rows. Click
  with `expect=TEXT` (bridge 0.25.0: refused unless button N still shows TEXT), and in a loop list
  again right before each click.
- **Check the top layer after every action.** A pop-up (Nerun, a Dialog, LayerCraft) blocks
  play: read it with `talk.py` or `texts`; close crafting with its `button close`.
- **Never guess on a dialog you can't read.** Irreversible picks (pet, Fiama's "I want to die",
  quest choices) get decided from knowledge, not by default.
- **Speed is damage and escape** (run 08: 105 fell to 73 over a sleepless week). Sleepiness costs
  -10/-20% speed ("You need to sleep now!"), Hungry -10%, Starving -30%, one ally over the party cap
  -20%. Sleep every night (`sleep.py` works on the world map), eat at Hungry, and check `power.py`'s
  speed before any dungeon.
- **Watch SP and hunger.** Each gathering tool stops at its own `min_sp` (none under 3); negative
  SP costs HP. Work SP comes back only from sleep, and a bed sleeps only when sleepy or Very tired
  (SP under ~20%); each sleep costs 20 hunger. Eat at "Hungry". Night hides cells beyond the torch.
- **Read the number, never infer it** (run 06 guessed karma at "about -50"; it was +10, and run 07's
  kicks made me a criminal). **Count from the inventory, not the log** (the log is a fixed-size ring:
  butcher.py once reported one skin four times); the worn toolbelt's stacks show in `buttons --all`,
  not `inv` (four skins hid there, run 13). Check twice before reporting a loss (runs 11, 13, 16).
- **No shell loops over game actions** (run 19: a `for` loop of tool calls ran on under a shipping
  report window, and a refused leave.py was followed by a sleep at home): the loop tools check
  windows and stops themselves; a hand-run sequence gates each step on the last exit code. **Use
  `set -o pipefail` and `&&`** (run 21: `tool | tail -1 && next` gated on tail, not the tool, and
  an Enter after a refused wgo.py walked me back into the place I had left, twice).
- **Watch a log only with `tools/watchlog.py`, never `tail -f | grep`** (KB #155: on 2026-11-02, 141 such pipelines
  from this repo's sessions were still running days later, ~1.4 GB, and blocked the Git upgrade). Make it the Monitor
  tool's command: `python -I tools/watchlog.py runs/jobs/X.log --match 'RE' --until 'done:' --max 1790` with `timeout_ms`
  1800000, so it exits before the harness kills it; re-arm on exit 3 while the loop runs. One per loop, and `--match`
  must also catch the failures (`Traceback|STOP|refused`): silence isn't success. Bash with `run_in_background` already
  reports a loop's end, so a monitor is only for what happens during it.
- **Never leave time passing unwatched.** Bed Pass Time runs until cancelled (21 game hours in
  run 03, and Loytel died meanwhile): use `wait.py HH:MM`, and only when nothing else pays.
- **Names in full.** Tools refuse a name that fits two things ("rod of" fits two rods) and match
  whole words, so "(1" no longer picks "(11 Charges)"; a `craft.py --use` material that fills
  no slot is refused rather than falling back to the default stack (run 11's threads, run 12's
  carbon log). Give the full name, with its count and charges when two differ only there.
- **Read the exit code, not the text:** 0 done, 1 refused, 2 the bridge, 3 stopped for a
  decision. A tool that moves items prints everything it moved: never pipe it through `tail`.
- **Harvest crops only when ripe** (`find`/`cell` show `ripe`): an unripe berry bush is
  destroyed for a branch. `gather.py` skips unripe plants.
- **Map edges** offer "Enter" (leave the zone). Don't harvest or walk there by accident.
- Play honestly: no debug, console, save edits or reloads to undo outcomes.

- **Pickers are drag grids** (identify, Armor shrine, recycling, blending; a shop's artifact identification opens one **under the drama**, so its drag needs `force=1`, run 25): `bridge.py drag ITEM 0`
  onto the 'ing1' slot; a `click` opens the hotbar picker and spends the charge (run 06).
- **Act by exact text** on a busy cell: `act.py DX DZ "Grab (an exquisite"`; plain "Grab" picked up
  the home board once (run 06). List `buttons` right before every `click`: a look.py in between
  shifted the list and a return scroll took me to the wrong place.
- **Frame rate:** after many hours Elin fell to ~4 fps and every script timed out. If `ping` frames
  crawl, quit through the bridge and relaunch (run 06: back to ~58).
- **World map:** you can't eat there (enter a local map); a hostile in view cancels eating and goto;
  a key into a cliff slides along it (`wgo.py` paths around cliffs). A world-map monster that keeps
  4 cells away follows every step and can't be targeted from there (run 23: a hot guy, a jellyfish):
  `wgo.py --weak-ok` past a weak one, Fast Travel past an exploder.

## Treasure maps (G44, run 41)

The dig is on the world-map tile itself, with the shovel in hand ("Dig (Easy)"); nothing guards it and the chest is unlocked: about 1,900 orens, 2-4 gold bars, 1-2 medals and 1-3 pieces a map, whatever its level. `bridge.py places` lists each carried map's spot, nested in bags too. `digmap.py --plan` is a tour with each leg's worst ambush level, `digmap.py N [--max-dist D] [--danger-ok L]` walks, eats, sleeps and digs nearest first (a route over `route_max` is skipped), `chests.py --field` on a local map empties the chests and leaves them (15 weight each, Burden 2 at five), `chests.py` at home ships them. 17 maps in 26 real minutes paid 75,600 orens an hour against a circuit's 9,345. Every boss chest's map gets dug on the way when its spot is near; the rest wait in the shared Maps box for Poppy.

## Quick-save after milestones

`python -I tools/bridge.py act QuickSave` (log shows `*Saved*`). **And right after any big haul**
(run 19: a game hang lost 12 minutes, and a 2,249-oren chest had to be looted again from the save).

## End a session

Follow **elin-closeout**: the power card and `python -I tools/bridge.py quit` (the only allowed
way: it saves first), the run log, metrics and milestones, facts, lessons and skills, the summary
with its diagrams, the rendered page (`tools/summary_page.py`, published and checked), the memory, a local commit,
then everything off: `tools/ollama_stop.py` and `tools/offcheck.py`.

## Changing the bridge

Edit `mod/ElinBridge/Bridge.cs`, bump `Version`, compile-check into the scratchpad with
`bash mod/build.sh "-p:OutputPath=<scratchpad>/bridgecheck/"`, then: `bridge.py quit`, wait for
Elin.exe to exit, `bash mod/build.sh`, write `autoload.txt`, launch, `wait_ingame.py` (shows
the new version). About 60 s. Batch changes to save restarts. Read the game's own code first
(raw.githubusercontent.com/Elin-Modding-Resources/Elin-Decompiled/main/Elin/<Class>.cs;
Plugins.UI types are not there).
