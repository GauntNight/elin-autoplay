---
name: elin-delve
description: Nefia circuits in Elin, the main activity (47% of logged time) - finding nefias and selling fame when the near ones run over the gate (famesale.py), the circuit loop and its flags (circuit.py), what the ladder does on each floor and what to do at each of its stops (ladder.py, delve.py), the floor gate and how it is raised, exploders and the throw distance, threat order, the escape reserve, the kit, the unload cadence, food and sleep on floors, leaving a floor, and monitoring an unattended loop. Use before entering any nefia or dungeon, when starting or watching a circuit, at every ladder or delve stop, and when a fight on a floor goes wrong.
---

# Delving: nefia circuits

The numbers (HP floors, the swarm count, the gate, the throw distance) are **elin-play's thresholds table**, read by the
tools from `THRESHOLDS` in `tools/common.py`; this skill is the procedure around them. What a death costs and why the
layers stand in this order: `knowledge/risk.md` (the user, run 16). Kit: **elin-pack 1**. Routes between nefias: **elin-travel**.

## 1. Before the first nefia of a session

- **The kit** (elin-pack 1): `ladder.py` refuses to start under 2 scrolls of teleport, 3 cure potions, an evacuation and a
  return (it opens the backpack to count; `--kit-ok 'why'` and `--blanket-ok 'why'` override, each with a row in
  `runs/waivers.csv`), under 3 free grid cards (`ladder.room_check`, run 33) or with an ether disease it doesn't allow
  (`ladder.ether_check`). A light (night maps and quest instances show 8 cells without one, run 05), the pickaxe, the Putit. (05, 08, 20)
- **Go in at all:** the floor gate and the kit decide; power.py's level-only table is advice only (it predicts the median
  fight 50x too high, run 16): `threat.py NAME` per kind decides; Lv5+ for the first. (04, 05, 16)
- **Carried gold:** spend down first, or box it at home: carried orens are currency and can't be boxed (run 16), but
  picked-up coins are an item stack (`box.py 57,54 "685 orens"`, back with `--take` before the tax day). A death past the
  beginner period drops 33-67% of the carried orens on the death tile (Chara.ApplyDeathPenalty; no items or levels are
  lost; run 12 took 1,373 into danger 8-9). (the user, run 03; run 15)
- **Solo is the default since run 38** (the user, 2026-11-01: "solo seems to work better for now at least so we'll stick
  with it and optimize"; G38: solo 7.4 real minutes a conquest against the crew's 10.0, exp even; fact #1139): the allies
  wait at home. With one along, take it as an expendable shield (`delve.py --expendable`, the user, run 16): back home free
  in 0-7 days (Zone.Revive), -10 affinity; Strategy tab "Always stay by you while in combat" on; a teleport scroll leaves
  her behind; two slots at CHA 19 with Party Animal (CHA 20 opens a third; Lonely Soul pays +3% HP and speed per empty
  slot: facts #746-#747). `crewcheck.py` reads fights.csv by allies present.
- **Sleepy at a dungeon's door? Sleep on the overworld first** (the user, run 17): `sleep.py` on the world-map tile, then
  enter. Read `power.py`'s speed before a dungeon: sleepiness and hunger cost speed, and speed is damage and escape (08).
- **Game speed:** x5 on floors (`bridge.py speed 3`; the user, 2026-11-06: "5x is fine", watched or not; run 41: a conquest
  in about 8 real minutes against run 40's 28, and no blast or fight went worse for it). `fight.py` drops to x1 for its
  rounds and `ladder.descend` takes the stairs at x1 (at x5 the walk to them ended short). `speed 1` by hand only the
  moment a named exploder or a hard stop is in play.

## 2. Finding nefias, and fame sales

- `bridge.py places 60` on the world map lists them (radius 25 from home showed none in run 16; 60 listed 20); `circuit.py`
  reads the same list and takes the nearest unconquered one in its danger band. Floors persist within a visit (B2 -> B3 ->
  B2 showed the same floors): plan a nefia as one pass.
- **The spawn rule (Region.cs, run 27, fact #897):** 70 random sites region-wide, each lives 7 game days; the shortfall
  refills **once a game day when the world map is entered** (leaving any local map: a meal stop, a sleep stop, a town), at
  random points of the whole region, so walking the world map spawns nothing and nothing spawns "around me". Level: 1 in 3
  from my level (the danger 16-31 ones), 2 in 3 from FameLv x 75-124% - 3 + a little. Random nefias expire within days
  (run 20: two were gone after 3-4 day walks): look again on arrival.
- **Refills come in batches** (runs 51, 54, fact #1538; Region.CheckRandomSites): a check tops the region up to 70 sites at once, at most once a game day on a world-map entry, and every site lives 7 days, so a batch dies in the same hour: when every near nefia reads the same hours left, take the near ones first, fill the gap (a home stop, a map, a guild night) and be on the move a game day after the last check; the next batch is a full one (run 54: 12 left in the region, then 39 and 52).
- **When the near ones run over the gate, sell fame** (runs 27, 32-42): `famesale.py NAME [TIMES=3] [MIN=140]` beside an
  informer of the Merchants Guild (Gizon, Ishbear; `whereis.py any NAME` first). A sale takes 20% of fame (run 27 at
  Ishbear in Palmia: ~1,040 -> ~665 brought danger 3-7; run 42: 263 + 210 + 168 and 191 + 153 orens), half the tax bill is
  fame x 2, and since the refill scales with fame, new nefias come back under the gate. After a day passes, enter and leave
  a local map, then `places` again. `circuit.py`'s "no nefia" stop names the fame sale.
- **None left in reach is not the end of play** (run 50: 20 conquests in 156 days emptied home, Olvina, Willow, Derphy and
  Noyel, fact #1482; play stopped 90 minutes early). With time in the window: Fast Travel to a region not circuited lately
  (Mysilia, Yowyn, Tinker's Camp, the Merchants Guild), or the dummy (elin-train); the stop names them while the window has
  over 30 minutes, and `summary_page.py` refuses the close-out until its last 30 or the user's word.
- **Which danger** (the user asked, run 28: "what Nefia level is good for us"): `runs/nefias.csv` holds each conquest's
  base danger, master floor and boss chest. Through run 28 (19 conquests) the chest averaged 579 at base 3, ~760 at 4-5 and
  ~890 at 6-7, platinum 1-3 at every level; masters sit on B2-B4, so the band's top stays under the gate by the floors
  below the first (fact #1136: base 11-12 nefias met the gate before their master). **Add a row at every conquest**: the
  file has none after run 40 (the review of 2026-11-11), so the current mix is unrecorded.
- **Underwater ruins count while ★《Sea Dragon Ribbon》 is worn** (run 58: it lets me breathe water for good; `circuit.py` reads the
  game's breathesWater and passes `--breathe`). **Without water breathing, none** (the user, run 17: "you can't do those kinds of
  dungeons"): an "Underwater Ruin"
  (Zone_dungeon_water) suffocates every turn (ConSuffocation) on top of the fight: 112 -> 20 HP on a danger 4 B1 while
  delve.py waited on its HP rule, and the user walked me out. `wgo.py` and `delve.py` refuse them unless `--breathe`,
  which is for water breathing in hand. **With it** (run 55, the Sunken Temple of Lurie B1-B4 with the Forest Gloves on):
  `ladder.py --breathe` reads the game's breathesWater on every floor and pass and stops when it's gone; ConSuffocation
  still flickers on after each step and dies the next tick for no damage (fact #1544), so `common.bad_conditions` ignores it
  while breathing. The gloves and the water-breathing kit ride in the pack (packcheck). **Wear the water breathing before the
  walk there** (run 57): the temple's world-map tile reads as deep water, and the bridge's walk refuses a deep-water target
  unless I breathe water (WalkTo: CanSuffocate and not BreathesWater), so `wgo.py` stopped twice on "the target is deep
  water". ☆The Beautiful Necklace 『Queen』 (water breathing, DEX+4, fear) is the cheaper swap than the Forest Gloves.

## 3. The circuit

From the world map: `python -I tools/circuit.py [N=4] [--danger LO-HI] [--r TILES] [--floors 5] [--unattended] [--solo]
[--danger-ok N] [--skip NAME ...] [--until HH:MM] [--wrecks] [--blanket-ok 'why']`. It takes the nearest unconquered
nefia of that base danger within R tiles, `wgo.py` there, Enter, `ladder.py`, on "conquered" `evac.py` out, and repeats.

- **The line in use** (runs 43-46, the notes in `runs/activity.csv`): `circuit.py 8 --danger 3-12 --r 30 --unattended
  --solo` for most starts (run 46: without `--solo` and with no pet along, delve stopped B1 on "Kaberg is not in the
  party"; an empty party counts as solo now); a narrower band and radius (`--danger 3-10 --r 20` or `--r 25`) at other times. `--danger-ok 30` rides
  on the circuits since run 43 (two near nefias were skipped past level 22 fields; run 42's crossings up to 44 cost no
  potion: elin-travel's far-maps rule). The tool's own defaults (3-7, r 15) date from run 30.
- `--skip NAME` leaves out a nefia whose master lies below the gate; `--until HH:MM` starts no new nefia after that clock
  time (run 42: the shipping and the close-out wait on the circuit; a nefia is ~10 real minutes); `--wrecks` mines each
  floor's wrecks (off by default: wreck stones fill the bags; a ladder run by hand needs `--no-wrecks`, run 35: without
  it the floors mine wrecks into granite and logs, Burden twice).
- **The grid is what ends a circuit now** (run 47: refused at the door four times, after every second conquest): the
  ladder wants 3 free cards and purge can only drop junk by rule. Before leaving home, box the kit's spares (a second
  arrow stack, rods past one of a kind, a plain bow) in the yard chest 68,44.
- **A nefia's walk is its route** (run 49): circuit.py judges expiry and nearness by `wgo.route_steps` (a shortest path round blocked tiles: Derphy reads 16 steps for 14 tiles); two run-49 walks of 8-9 game days at 14-17 straight tiles had expired on the way. **Near the margin it runs long** (runs 51, 54): Warped Ruin read ~96 h and took 30; Strange Machinarium read 51 h against 67 h of life and was skipped, walked by hand it took ~40 with ~20 h to spare: a skip whose walk is under the life left is walked by hand (`wgo.py NAME`, then the circuit from its door).
- **What it does itself** (runs 39-44): sleeps on the tile when Sleepy before each Enter (run 47: twice the 9-hour nap
  outlived the nefia and the Enter landed on its field: the circuit stops, re-run it); eats before a nap (`fed_nap`) and
  takes the stairs up first when the meal stop left me on a floor; fights hostiles 10+ levels under mine before each
  evacuation (`clear_weak`); naps once to refill an empty list, **but not while a nefia it skipped as too far can still
  be walked inside its life** (run 55: twice the nap burned a batch's last hours): it stops and names them, for `wgo.py
  NAME` by hand; started on a nefia's floor it runs the ladder there first.
- **The unload:** every **four** conquests (`circuit.UNLOAD_EVERY`; run 40: was two, three bags carry 3-4 conquests) and
  whenever the carried bags are full, the circuit stops with "go home: ...". It doesn't unload: `recall.py`, then
  `arrive.py` (elin-home 1), then `circuit.py` again. Return needs a local map: the circuit ends each conquest on the
  nefia's world-map tile and `recall.py` refuses there ("enter a local map first", run 36).
- **It stops (exit 3) for a decision:** any ladder stop that isn't a conquest, no nefia in range, every nefia past the
  route limit, the unload. It registers as a job (`runs/jobs/circuit.json`: `journal.py` refuses while it runs, because its
  window stops the loop) and `runs/jobs/circuit.stop` ends it between nefias.
- Grassland nefias run long (fact #1175; run 39: 40-70 real minutes each).

## 4. The ladder: one floor at a time

`python -I tools/ladder.py [MAX_DANGER] [FLOORS=3] [--unattended] [--no-wrecks] [--solo] [--expendable] [--in X,Z]
[--breathe] [--spare NAME]` (the circuit calls it; `--breathe`: section 2; `--spare NAME`, run 55: delve stops on sight
of that creature and `fight.py` refuses it through runs/jobs/spare.txt, for a story boss whose fate is the user's call,
as Duponne on the Sunken Temple's B5). Per floor: `delve.py` until the floor is explored (frontier walking; fights at or below my level
with the Putit as opener, soaks exploders, stops on the HP rules), `loot.py`, a QuickSave, then the stairway that isn't the
way in. The gate covers every floor here (delve's own gate covers nefias only: Lesimas and Nymelle aren't).

**It does these itself** (runs 20-43): uses every safe shrine (replenish, armor (the picker gets the worn piece with the
lowest plus), knowledge, enlightenment, invention, wheel; never strife or material); opens every treasure chest (a locked
one with the lockpick, never pried) and a boss chest is emptied completely (elin-pack 4); ends on "conquered" when the
zone's name carries the mark; clears a wanderer in view before looting; frees 3 grid cards a floor (`purge.py --free 3`:
purge drops junk by rule and unclutters the grid into the emptiest bag); naps outside from any floor (evac, sleep, Enter;
re-walked floors don't spend the quota); casts See Invisible once a floor; waits up to 8 turns for allies over 3 cells
away; runs `tunnel.py` after the map and Teleport when a floor looks closed, and `tunnel.py --to` for magic-mapped stairs
in a closed room or a boss chest it can't reach; fights **Evolved** creatures at or below my level (their gene, a superior
one half the time; loot takes genes first) and stops above; gets off a mine trolley at once (`common.ready`); the walk to
the stairs ignores far weaker foes.

**Its stops, and what to do at each** (a stop is a decision: never fight past one, never chain the next step on it):

| Stop | Do |
|---|---|
| the floor's danger is over the cap | back up the stairs I came down (the arrival cell); `circuit.py --skip NAME` for that nefia |
| delve stopped on HP (the table's drink line) | no foe in view: `cure.py` (the Cure Minor Wound spell, free) before a potion; heal to the table's heal-to and go on while the escape reserve holds (section 7) |
| a swarm | teleport, then `leave.py --force` (the table's swarm row) |
| an "avoid" kind near my level | range it or leave (section 6) |
| an exploder close, or a **named** one | section 6; a named one is killed from range at x1 (`namedexploder.py`) or the floor is left |
| blindness (ConBlind) | walk away until it clears (~7 turns), drink by the table, then kill the caster from range (run 14) |
| low HP after a floor, SP under 10 | heal; SP comes back only from sleep: out, and sleep on the overworld |
| Sleepy | never in a dungeon: `evac.py`, `sleep.py` on the world-map tile, Enter again (the ladder's own nap does this; from Very Sleepy since run 48: the world map refused two naps at phase 1, which costs no speed) |
| a meal that didn't lower hunger, "no meal" | `eat.py` on the food actually in the pack; none: leave and restock (section 8) |
| no way down, a walk that ends where it began | a pocket: section 7 (a rod of teleport, `tunnel.py`); the true bottom or a locked story stairway is a hand decision |
| the pack at 42+ stacks, the bags full | `purge.py --free N`; bags full: the unload (section 3) |
| burden phase 2 or 3 | shed weight before any zone change (`purge.py --heavy`, section 7) |
| a foe in view that no attack reaches ("no target left") | delve and explore leave it alone for the floor after three such answers (runs/jobs/delve_unreachable.json), unless it comes adjacent (run 49: ~50 stops on a hot guy behind a wall, ~10 real minutes); stop a ladder gracefully with `runs/jobs/ladder.stop` (read between delve runs) |
| "Enemy spotted" with nobody in view | an invisible foe beside me (run 41: a walk to the stairs ended four times): See Invisible (`ladder.see_unseen` does it once a floor), then fight what it shows |
| a window, a dialog | read it first (`talk.py`, `read.py`), then `close.py` |
| a neutral Evolved creature ends the exploring | **leave it alone when it is within 5 levels of mine: take the stairs on (or `circuit.py --skip NAME`)**, never `fight.py --force` (run 48: a neutral Evolved Wasp out-traded me to 57% over 12 rounds; run 49: a neutral Evolved Candle Ghost Lv42 at my Lv43 hit back for 41% in its first round, a teleport and the nefia lost; fact #1448). One far under my level may be fought for its gene. Why delve stops: it lists the creature as a foe, and fight.py answers "target not in view" without `--force` |

## 5. The floor gate, and how it moves

`delve.py` refuses a floor above `MAX_DANGER` (`THRESHOLDS["max_danger"]`: **37** at Lv48 (run 57, **G71 M3**: Silent Grassland B2 at danger 35, explored over two visits (a <King> evacuated from, then killed from range with ice bolts), lowest 85%, no drink, fact #1604; **36** the same run, **G71 M2**: Silent Grassland (base 34) B1 at danger 34, the unattended limit, 20 fights, lowest 86% (414/481), no drink, fact #1603; before it Misty Cave B1 (65%) and Chilly Ruin B1 (58%) at 34 fell under the drink line and were not counted; **35** the same run, **G71 M1** (G71 Floor gate 39, set by the user at run 57's start): Damp Ruin (base 32) B2 at danger 33, the unattended limit, 38 fights, lowest 85% (390/460), no drink, fact #1600; run 56: Dangerous Cave B1 at danger 28, the unattended limit, lowest 91%, no drink: G67's step with no milestone, to 30; its B2 at danger 29, 13 fights, lowest 96%, no drink: G67 M1, to 31; its B3 at danger 30, 16 fights, lowest 98%, no drink: G67 M2, to 32; its B4 at danger 31, 35 fights, lowest 81%, no drink: G67 M3, to 33; then **back to 32** by the step rule: a near-death on the Minotaur's Nest B5 at danger 30, Ungogo Lv32's melee round 398 -> 132 of 435, fact #1573; and **33 again** on Ancient Forest (base 30) B2 at danger 31, ~23 fights, lowest 94%, no drink, on a second visit: the first had fallen to 64% and didn't count, fact #1581; and **34**, G67 M4 and **G67 done**: its B3 at danger 32, 44 fights, lowest 96%, no drink, no heal, fact #1582). G64 (**Floor gate 30**, set by the user after run 53) was done in run 55, and the gate went **back to 29** by the step rule for run 55's near-death on the Minotaur's Nest B4 at danger 29, the unattended limit (453 -> 113 under Gravity; applied after the close-out, which had missed it: `hygiene.py` checks it since). **G67 Floor gate 34** (the user, 2026-11-20: "raise the floor limit past 30 one step at a time"): the evidence floors sit at the unattended limit, now 33: a base 29-33 nefia's floor at 33 (Ancient Forest's B4, 6 tiles from home, while it lasts); a gate past 34 is a new goal, the user's call; **Ungogo (Minotaur's Nest B5) is not a floor-gate question**: at Lv47 his melee rounds took 40% and 61% of my HP while my blows took ~1% of his (fact #1573), so the horn waits on another method, not a gate step; `ladder.py` takes
the same number for every floor and **36** with `--unattended` (`unattended_minus` 1; it was minus 2 until run 16: the
auto-combat net, the reserve and boxed gold now stand between a bad turn and death). elin-play's table states the gate and
`hygiene.py` checks it against the code: `common.py`, the table and this section change together.

**The rule (the user, 2026-11-12): the gate is raised step by step, on evidence.** The evidence is the lowest HP on each
floor, recorded with the floor's danger: `circuit.py` writes a row per conquest to `runs/conquests.csv` (the zone, its
danger, the gate in force, my level, the lowest HP percent the ladder printed, unattended or not; `runs/nefias.csv` was
kept by hand and stops at run 40). Read that table before changing the gate. One step up
only after a floor at the limit was cleared without a drink; one step down after a near-death at or under the limit.
Each change goes into the `THRESHOLDS` comment and a fact (fact #1047 and its successors).

The steps so far: danger 4 at Lv7 (run 05), 5 at Lv9 (07), 8 at Lv12-16 (run 12; risk.md), 8 -> 9 at Lv23 (run 24: run
21's danger-8 den, 0 HP lost, no drink), 9 -> 10 at Lv26 (run 27: the Rustic Ruin's danger-9 B2, 6 HP lost, no drink), up
to 14 by run 34 (Vernis Mine B5-B7 at 10-12 in run 33; Chilly Cave B3 at 13), **down to 13 at Lv33** (run 36: a
near-death, 218 -> 0 in one round on Dark Ruin B5 at danger 12 under the unattended 13), 14 at Lv35 (run 40: two
danger-12 floors at the unattended limit cleared without a drink), 15 at Lv38 (run 43: Traditional Cave B4 at danger 13,
12 HP lost, no drink), 16 at Lv39 (run 45: Ruined Grassland B2, Mossy Grassland B3 and Warped Machinarium B3, all danger
14, cleared at full HP with no drink), 17 at Lv41 (run 46: Warped Ruin B3 at danger 15, the unattended limit, lowest HP
86%, no drink; the first raise read from runs/conquests.csv), **back to 16 at Lv42** the same run (Guiding Cave B4 at
danger 13: HP 354 -> 42 on a mine its master, a mine dog, had laid; the rule's step down, though the mine and not the
floor's danger was the cause), and **17 again** by the user's call after the run (2026-11-13: "we can try 16+ again"; a
mine is a threat flag now, not a reason to lower the gate), **18 at Lv44** (run 51: run 50's Arcane Forest B4 at danger
16, the unattended limit, lowest HP 97%, no drink; PV 74 -> ~88 from seven enchant scrolls the same day), **19 at Lv45** the
same run (G59 M1: Old Grassland B3 at danger 17, the unattended limit, 25 fights at a lowest 100%, no drink; Mystical
Grassland B3 at 17 the same day fell to 67% on the chip of ~30 fights and was not counted: a clear under the drink line is
not evidence), and **20** an hour later (G59 M2: Old Grassland B4 at danger 18, the new unattended limit, its master killed in
24 fights at a lowest 82%, no drink; run 46's precedent counted 86%), and **21** by the user's call after the run
(2026-11-17: "Let's step to 21"; Chilly Cave B4 at danger 19, the unattended limit at 20, 30 fights at a lowest 81%, no
drink: the evidence the run held back for the user, fact #1499), and **22** in run 52 (G61 M1: Traditional Ruin B1 at
danger 20, the unattended limit, explored at full HP with no drink: an asura Lv22 and kamikaze yeeks, few fights, fact #1506), and **23** the same
night (G61 M2: its B2 at danger 21, 8 fights, lowest 94%, no drink, explored after tunnel.py opened a wall, fact #1507), and **24** (G61 M3: its B3 at danger 22, explored at full HP, no
drink: a king scorpion Lv21, a living armor, fact #1508), and **25** (G61 M4, G61 done: its B4 at danger 23, the master
『Stalker』 Lv34 killed in ~15 fights at a lowest 100%, no drink, fact #1509), and **26** in run 54 (G64 M1: Unknown Cave, a base-20 nefia, B5 at danger 24, the unattended limit, its master 『Asura』 Lv36 on it, lowest 91%, no drink; B1 had needed a drink at danger 20 against a Santa Claus Lv40, not the evidence floor), and **27** in run 55 (G64 M2: Dangerous Ruin, a base-21 nefia east of the Village of Atonement, B5 at danger 25, the unattended limit, its master 『Monster mushroom』 Lv37 killed, lowest 76% on the floor, no drink; the conquest row's 64% was B4's iron-maiden bleed and yellow bits: the evidence is the limit floor's own lowest), and **28** the same night (G64 M3: the Sunken Temple of Lurie's B2 at danger 26, underwater with the Forest Gloves' water breathing (`ladder.py --breathe`), ~35 fights at a lowest 90%, no drink), and **29** (G64 M4: its B3 at danger 27, 22 fights at a lowest 90%, no drink), and **30** (G64 M5, **G64 done**: its B4 at danger 28, 27 fights at a lowest 80% from a deep jellyfish and a trooper Lv28, no drink: four steps in one night, a story dungeon's floors one per step), and **back to 29** after the run (the step
rule: the Minotaur's Nest B4 at danger 29, 453 -> 113 under Gravity; the user's guess, 2026-11-20: the Nest and its boss
Ungogo may be harder than their floors' numbers, as other floors have been). The circuits take `--danger 2-15` once the unattended
limit is 17+ (a base-15 nefia's B3 is the limit), `2-16` at 19, `2-17` at 20, `2-18` at 21 (a base-20 nefia's B1 or a base-18's B3 is the limit then), `2-19` at 22, `2-20` at 23, `2-22` at 24 (run 52: base-23 nefias, Capricious Ruin and Warded Forest, kept their masters past B2 at 24: explored, not conquered). The review of 2026-11-11: recorded base danger averaged 5-7 through run 40, so
most floors sit far under the gate.

## 6. Fights on a floor

- **Threat order** (the user, run 16; `threat.py NAME`, `--table [LV]`, `--write` refreshes knowledge/threat.csv): each
  kind's offense, defense, group and tricks from the game's race, job and spell tables plus fights.csv. Exploders never
  adjacent; **kill first** high offense + low defense, casters, potion-throwers, summoners, blinders, paralysers, healers,
  from range (a goblin wizard did most of a 57 -> 29 drop beside a special Orc, run 06); **kill last** high defense + low
  offense. An **avoid** kind (high offense + high defense) within 8 levels of mine (4 until run 17: two Lv12 lizardmen
  took 45% of my HP in two turns at Lv18) stops `delve.py` and `fight.py`: range it or leave; **15+ levels under mine
  it's an ordinary foe** (`avoid_ignore_below`, run 43: a master 『Lizardman』 Lv19 died in 11 turns for 3 HP at Lv38);
  at any level once a recorded fight cost 30% of my HP (`avoid_seen_pct`, run 33: aliens Lv18 at Lv30).
- **From range first:** casters, archers, yeek warriors, shamans, mummies, drones, slimes, floating eyes (the Putit, the
  bow with arrows, the rod of slow); melee only what shrugs at range. `shoot.py` exits "no ammo" without arrows or pebbles
  (the user caught a whole trip of empty shots, run 12), and delve then throws the Putit. (06, 08, 12) **Once a kill-first
  kind is already adjacent, the sword** (run 56: a named Lich Lv34's Putit round cost 20%, one melee round killed it for 6%):
  delve.py melees it; slimes, drones, exploders and floating eyes keep the ranged branch. The throw loop stops at the
  table's drink line (70%), not 55% (run 56: a named Mercenary mage's slide to 44% in rounds under 15%).
- **A boss that out-trades the sword is no gate question** (run 56, fact #1573: Ungogo Lv32, Critical 100 and Cleave 42,
  took 40% and 61% in single rounds at Lv47 while my blows took ~1%): `threat.avoid` now reads a recorded fight that cost
  30%+ at my level before the 15-levels-under exception, so fight.py refuses such a kind without `--force`.
- **Evasive kinds** (threat.py `evasive`: race DV 20+, or 15+ at speed 150+: bats, fairies, the metal bells; the user,
  run 34: "that kind of adversary we should know is hard to kill with swords"): `fight.py` casts an arrow spell each round
  (Fire Bolt solo: a bolt's line can hit the crew) while MP >= 25, then throws the ★Putit In Amber (hit 128% against the
  axe's 105%); melee last (`--melee` to force it). (34: a vampire bat, 20% a round, the axe missing)
- **A foe that keeps running away gets thrown weapons, spells or ranged attacks, not a chase** (the user, run 21):
  `fight.py` throws the Putit In Amber at a target that kept its distance after one approach or moved away.
- **Thorned kinds from range** (run 55, fact #1552): iron maidens carry featSpike (element 1221) and reflect melee as
  damage and bleeds, ~100 HP a maiden; threat.py's `thorns` flag gives them ranged rounds in fight.py. A thorned master
  that out-trades the arrows (Boring Cave's Lv40) is a reason to leave the floor.
- **Thieves** (run 55, fact #1558): a gnome steals items ("A gnome steals a treasure map from you"), fairies steal orens
  (1,200-2,240 a time in runs 51-55), a hungry sea lion took a can of spice. Kill them first when in reach; the four tools
  run 55 lost from the bags most likely went this way. `fight.py` and `delve.py` put each "... steals ... from you" line
  whole in the item ledger and the loop log (`common.note_thefts`), and a "protects you from thieves" piece is weighed
  before it ships (elin-gear).
- **The Swarm ability** (run 40, 50 platinum at Eligin): `fight.py` casts it in place of a swing by the table's row
  (3+ hostiles within 3 cells, SP 40+), never beside an exploder or a slime (12 SP; a 0.9x melee blow on each: ActSwarm).
- HP decides, not the count: weak foes in numbers are a normal fight while HP holds (04); the table's swarm row counts
  far weaker hostiles half or not at all (runs 21, 43).
- **The auto-combat net** (bridge 0.26.0, run 16): `fight.py` fights in the game's GoalAutoCombat: a lethal hit on anyone
  healthy at its start leaves them at 0 HP once (Card.DamageHP); at 0 HP the next action is a teleport.
- **A flee has to move** (Start Run 3: 56 -> -4 and 43 -> -4 HP on one cell): `leave.py --force` hands back after an
  attempt that moved under 2 cells, and a teleport-less `fight.py` fights on while no foe is above my level and HP holds
  40%: walking away from what I can kill is what killed.
- Blind (a master yeek's darkness bolt): no Attack act, and a step into the unseen foe does nothing; delve.py stops on
  ConBlind (14). Under paralysis an HP floor can't be trusted: leave at the first big hit (11).
- Special mobs (a capitalized name) carry the best loot: fight and loot them first when at or below my level; never leave
  a map with one alive (04). `fight.py` logs every fight itself (`fightlog.py`: knowledge/fights.csv, the tricks in
  knowledge/specials.csv; `power.py fight ...` only for a fight fight.py didn't run).
- **Butcher only after combat or when safe** (the user, run 15: "trying to butcher while in combat is high risk and we
  keep getting stuck"): a butchering task with a foe just out of sight got me hit and stuck. **But don't leave the meat
  behind** (the user, same run): between fights the corpses are picked up, not butchered (`loot.py --no-butcher`; at most
  5 wait in the pack), and every stop of delve butchers them when nothing hostile is in view; loot.py won't butcher with a
  hostile in view and butcher.py stops when one appears. On an ambush map, `loot.py 20` before leaving.

### Mine-layers (the mine dog: ActDropMine, threat.py's `minelayer`)

A mine dog buries mines as it fights; a laid mine does (50 + TrapLv x 2 + rnd 150) x 1.5 when stepped on: run 46, 354 ->
42 in one step; run 47, Ominous Cave B2, 280 -> 106 (fact #1413). **A levitating chara ignores a mine**, so the Levitate
spell is the counter: `delve.py` casts it the moment a mine-layer becomes the target (run 47, Tainted Cave B2: "Levitate
on", the dog killed at full HP) and `ladder.levitate_over_mines` between passes when a laid mine is on the floor. My
Casting fails some casts (it retries 4 times). **Gravity cancels it** (run 51, fact #1486: "Gravity nullifies your
levitation", and every cast failed under ConGravity): with Gravity on, don't step; kill the dog where it stands or from
range, and walk only cells already crossed. Hurt among mines: stand still (a mine fires on a step), drink, then teleport off
the area.

### Exploders (suicide attackers)

Kamikaze yeek, hot guy, **bomb rock**, any ActSuicide: threat.py's exploder flag. The distance is the table's row and the
code's `kamikaze_dist`: **5 cells** (3 until run 40, 4 until run 41).

- Never adjacent. Soak first: a thrown potion makes it Wet, and Wet stops the blast (`delve.SOAK`, which falls back to a
  thrown cure minor wound, then a cure major wound from the grid since run 55: any thrown potion wets; two bomb rocks
  blinked in for 29% and 26% while the soak potions rode in a bag). Then throw from the table's distance: `delve.py` steps back to it
  first, and `cast.py` stops on an exploder inside it. A kill at 2 cells still cost 30 HP (run 12), run 40's throw a
  blast took 49%, and run 41's took 77%, 46% and 47% through ranged throws at 4 cells: **bomb rocks blink in**.
- **A named exploder halts delve: its death blast is past any HP** (run 33: **death**, 214 -> -342; run 37: **death**
  again, 216 -> -478: the state lists a named one as plain 'Hot guy', the 『』 only in the log, so the check never fired
  until `common.named` read the capital). Kill it from the table's distance or more, at x1: `namedexploder.py` when the
  spell can kill it. **A named exploder I can't out-damage from range is a reason to leave the floor** (run 41, Mossy
  Grassland B5: a named Kamikaze yeek adjacent twice in 30 turns, arrows ~1% a cast at Casting 11): the stairs.
- **Read the game's table, not an id** (run 41): `samurai_kamikaze` has no ActSuicide (knowledge/game/charas.json):
  'kamikaze' in its id cost teleports for 7 runs. A real exploder has ActSuicide: yeek_kamikaze, hardgay, bombrock.
  Run 24's bomb rock took 145 -> 0 in melee when delve read names only.

## 7. The escape reserve, and leaving a floor

- **Gravity blocks teleports** (run 55, a near-death: 453 -> 113 on the Minotaur's Nest B4, fact #1555): under ConGravity
  (minotaur mages cast it) the Teleport spell and a scroll both left me beside two casters; `common.emergency_teleport` returns
  at once under it. The escape then is a drink, the kill (melee a wounded caster: they die fast) and an evacuation. Casters
  that Gravity you are a reason to leave a floor before HP runs low, not after.
- **The reserve: 2 teleports + 3 heals untouched** (`escape_teleports`, `escape_heals`). After a bad fight, heal to the
  table's heal-to with no foe in view and go on (the user, run 16: "you may be teleporting out too early"); **leave the
  floor when going on would spend the reserve**, or when an "avoid" kind near my level holds the floor. When to read the
  teleport is the table's row.
- Never Rest, Wait, Pass Time or sleep in a dungeon: monsters keep coming (Kaberg was knocked out during a Rest). To
  recover, leave and rest outside. (04)
- **Evacuation (10-19 turns) or the stairs only with no foe in view**; the return scroll (19-36 turns in run 20) is for
  going home from a safe spot, never an escape (read at 12 HP, it never fired). (03, 07) `evac.py` reads one evacuation
  and waits it out; `recall.py [Meadow]` reads ONE return and passes the turns (it fights an adjacent foe and steps off
  stairways): **a second read cancels it and spends both** (runs 05, 10, 20; the bridge refuses it now). An evacuation
  goes straight out of a conquered nefia. `stairs.py down` or `stairs.py up` steps into the known stairway from the cell
  beside it (the user's tip: a walk onto it does nothing); `act Wait` on a stairway takes the stairs: step off first.
- **Stuck on a floor** (the user, run 42: "looks like you may be stuck in the dirt, may need to mine to get a path"): one
  soil block held a cave floor for 17 real minutes. `tunnel.py` digs the thinnest wall to open ground out of reach; a walk
  that ends where it began stops exploring. **Boxed in** (runs 25, 28: delve's "no way down", explore.py's walks that go
  nowhere: a wreck trap, a Machinarium's metal walls): **zap a rod of teleport** (the Teleport spell fizzles at Casting
  3), then explore again; mining toward the known map (granite 18, copper blocks 34) is the slow way.
- **A zone change at burden phase 3 can tumble you** (run 42: a return scroll at 161% with a wagon: 269 -> 57; Scene.cs
  rolls 1 in 5, MaxHP x burden% / 200): recall, leave, stairs and evac refuse (`common.overweight_stop`); a boss chest's
  furniture goes by `purge.py --heavy`. Furniture worth taking: `valuables.py` (elin-pack 4).
- **An ether disease is weighed, not assumed bad** (the user's rule, 2026-11-02): the Single Ether Wing takes the back
  slot (the cloak falls into a bag) for speed: PV 88 -> 80, speed 132 -> 151 at Lv37, so it stays; `ladder.ether_check`
  allows the ones with no HP or attribute cost: Gravity Point, Hunger for Slaughter, the Wing, Third Eye, Mana Battery
  and Hoof Transformation (FEAT.cs; the ids and reasons are in its comments); since run 52 also Enemy of All Living Things
  (1563: CHA -14, so Lonely Soul's empty-slot HP falls, 438 -> 403; it turns townsfolk hostile and cuts a kill's karma loss to 30%:
  facts #1504, #1505, #1512), allowed for nefias, a reason to cure before any town or guild night. **Thick Neck** (1555, fact #1513) came back at
  corruption 500 in run 52: PV +(12 + Lv) (100 -> 150) for the neck slot and CHA -(5 + Lv/5) (speed 197 -> 172 through Lonely Soul): kept in run 52, cured in run 53 by the user's call ("we have to cure that"). A disease strikes at every 100 corruption;
  an antibody (Miral, 10 medals; Gikrak in Yowyn, 4,200 ecopos) takes the newest first, one per 100 boundary its drop
  crosses (fact #982). **A slot disease is weighed against the goal it blocks** (the user, 2026-11-17: "I think we should
  get the Ether antibody"): Hoof Transformation's speed (166 -> 215 at Lv45) lost to the boots' PV and DV once G60 (PV 100)
  was the goal. **Run 53:** one antibody (power 100) took 513 -> 313, Thick Neck and Enemy of All Living Things gone (fact
  #1517); with G60 done, Hoof's +39 speed outweighs the boots' PV 8 / DV 12, and a second drink would have crossed 200 too
  (the Wing's +14 speed): both kept, 4 antibodies carried for the next disease (the carry list keeps them).
- Quick-save after a conquest or a big haul (elin-play); every death or near-death gets its cause in the run log and a
  line here or in the table.

## 8. Food, sleep and weight on floors

- **Every unattended loop has a hunger stop on every branch and an eat step tested by hand on the food actually in the
  pack** (run 18 starved in a home loop with food in the bag; run 44: a ladder stopped at hunger 67 "no meal" with 11
  travel rations in the Cooler Box, because eat_one refused every ration under hunger 80: it keeps 5 back as fares now
  and eats the rest). A tool's "no meal" is a stop for me too: never start the next long job on it (41).
- **Real meals** (run 44: 24 mini salads, ~2-6 hunger each, lasted about an hour): inn food or cooked dishes in the
  Cooler Box (elin-travel 1); `leave.py` refuses home under 6 meals carried.
- The ladder stops Sleepy and naps outside; with no bed carried `sleep.py` uses the Rest ability (run 44).
- **Weight ends circuits early** (run 44: four stops at burden phase 2 or 42 stacks: 214 garbages in the pouch, ☆ gear
  and spent rods in the bags; delve won't loot at phase 2). `purge.py` runs every floor; the unload is section 3.

## 9. Watching an unattended circuit

- Run the circuit in the background with its output in a log, and **put a Monitor on that log at once** (run 42: a silent
  wait on a loop is how 17 stuck minutes went unseen; run 43: with watchers on every circuit each stop was read within
  seconds). The command is elin-play's watchlog rule: `python -I tools/watchlog.py LOG --match 'RE' --until 'done:' --max
  1790`; `--match` must catch the failures too (`stop:|Traceback|refused|go home`), and watchlog's `--idle` line (a log
  that hasn't grown) is a finding, not quiet: run 45's hang was a loop of steps that did nothing (the review of 2026-11-11).
- **And `python -I tools/pulse.py` in the background beside it** (the review of 2026-11-11): it reads the game's own
  turn counter and clock every few seconds and ends, calling the session back, when nothing has moved for five minutes
  (exit 3) or the bridge has stopped answering (exit 2); at `--max` it ends "still moving": re-arm it. A log can be
  quiet for a long step or a hang; the turn counter tells them apart. It only reads the state.
- **One client that acts at a time** (elin-play): nothing else touches the game while the circuit runs, `journal.py`
  included. **A loop's stop line isn't its end** (run 44): act only after the task's completion notice.
- Unattended means `--unattended` (the gate minus 1), no client-based instance jobs (deliveries and kill-count jobs are
  fine), and never a loop that waits.
- To end it: `--until HH:MM` at the start, or `runs/jobs/circuit.stop` (it ends between nefias).
- The ladder and the circuit mark themselves in `runs/activity.csv`; mark a hand-run stretch with `activity.py TAG
  start|end` (the review of 2026-11-11: about half of a run sat outside any marked loop).

## What this skill changed

New at the review of 2026-11-11 (plan D): the circuit had no skill, and its procedure was three cells of tool-notes that
still said gate 8/10 and an unload every two. Measure: errors.csv repeats in the dungeon and combat domains, exp and orens
per real hour of circuit time (stats.csv), and the loop minutes of each window (activity.csv).
