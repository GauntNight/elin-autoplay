---
name: elin-town-trip
description: Procedure for a trip from home to Mysilia and back in Elin (run 03, done four times) - departure checks, the road route and ambush handling, finding NPCs through guards, paying the tax bill, selling old tickets, buying food, rations, potions and escape scrolls, and fast travel home; board jobs for town influence and the goals' shopping list (run 05). Use whenever a trip to a town is planned (the tax is paid at home since run 05).
---

# Town trip (Mysilia), step by step

Read elin-play first (rule zero). Ask `kb.py facts Mysilia` for current prices and places.

## 1. Before leaving home

- Rested (SP > 2/3), fed (hunger < 50), full HP, daylight. `packcheck.py` passes (the kit and
  nothing else, ~30 stacks: a full pack refuses items silently). Not sleepy? Leave anyway and sleep
  on the road with the makeshift bed (`sleep.py`); the dummy no longer tires me for anything.
- Carry: 5+ potions of cure minor wound, bandages, food for 4 days (in the Cooler Box), an escape
  kit (scroll of teleport and short teleport act at once; scroll of return takes turns), weapon,
  bow + arrows (check the arrows: run 12's bow was empty all trip), a light, the makeshift bed,
  old tickets and anything identified to sell.
- **The tax is paid at home now** (G1, run 05: the tax chest 62,49 by the mail post), so a trip
  is for selling, buying, the board (influence) and the goals' shopping list.
- Travel rations are the fast-travel fare (1 + hours/24: 3 between home and Mysilia), not food.

## 2. The road (about 3 game days, 25 tiles)

- Leave home by the north edge (52,34 offers Enter). Route on the world map from the Meadow
  (32,104): `wgo.py Mysilia` (the game's own pathing; it stops on ambushes, a hostile within 4,
  HP under 60%, Hungry or SP under 5, and logs the leg to knowledge/travel.csv).
- **World-map monsters are bandit groups** (run 18): walking into a roaming "hot guy" brought two
  of them 2 cells away and a demand ("Give me paralysis, or your life is forfeit!"); against
  exploders, pay a cheap demand (they turn Neutral); against weak bandits answer "Try me".
- **Ambush** (a local map, you start mid-map, `zone.bounds` gives the edges). `wgo.py --ambush`
  runs this list itself and walks on (the review of 2026-10-23); by hand:
  - `look.py`; the swarm rule is elin-play's (6+ hostiles, or 4+ with any at or above my level;
    `hunt.py` and `delve.py` stop on it), and anything 3+ levels above me (`fight.py` refuses it):
    leave at once with `leave.py --force` (walks to the nearest edge and takes its Enter). A thrown
    potion of confusion or blindness was shaken off both times.
  - Otherwise fight one at a time (`fight.py NAME 60`, `shoot.py` for floating eyes and hard
    hitters), `loot.py`, then `leave.py`.
  - The thresholds are elin-play's table: drink at 70%; a swarm closing in: teleport, not return.
- `places` on the world map shows Mysilia's distance; overshooting by a tile is common.
- **Plan the trip before leaving (the review of runs 03-12: two thirds of run 12's game days went
  to walking):** list the errands per town and batch them (the tax, the board, the scholar, the
  healer, tickets), carry what the jobs need (a sickle for a harvest job, bars for Nino's
  recipes), and visit the camp's shops by day (Nino and Casaneck sleep at odd hours).
- **Time (run 12, measured and read from Chara.cs):** a world-map step is 180 game minutes at base
  (+rain/snow), so Tinker's Camp is ~14 h, Mysilia ~2.5 days, Olvina ~2 days. The game's Fast
  Travel costs the same (3 h a step) plus rations. `wgo.py` logs every leg to knowledge/travel.csv
  and the graph (the user's request). **Count the steps before accepting an escort:** Mysilia's
  "(1 day left)" escorts to Olvina and Derphy can't be done.
- Sleep on the road with any bed in the pack (`sleep.py`, the F-key bed slot; the user: F5). The
  makeshift bed (0.72) rides in the kit; a real bed sleeps better but weighs 28 (Burden).
- Kamikaze yeeks on the road: throw the Putit from 3+ cells (elin-play's table; run 12: a kill at 2
  cells still took 30 HP from the blast).

## 3. In town

- **Small Medals on every town or named map the wiki lists** (the user, 2026-10-29): `look.py` prints a
  MEDALS line there; `medals.py --take` walks onto each reachable hidden medal (the step turns it loose) and
  picks it up, and reports the ones under furniture, behind walls or in deep water for a deliberate step
  (hammering or digging town property is a crime). knowledge/medals.md lists all 141 by map.
- Enter on the Mysilia tile in daylight. Shops sleep at night (Tiguen the innkeeper napped at
  14:50 too). **Don't wait for them** (the user, run 05: waiting burns food): work the board,
  sell, or sleep in an inn bed when sleepy (a visitor may: SP 16 -> 57, run 05).
- **"Hunt any X" jobs ("Foul race!", kill N of a race) have no deadline and hold one of the 5
  quest slots until finished** (the user, run 15: "they are persistent... I've accidentally accepted
  too many and have not been able to accept new quests"). Hold at most two, finish them before
  taking another, and read the journal's Remaining Time ("-" = none) rather than the board.
- **Escort clients don't show in the party list** (run 17): read the journal's "Escort NAME", see that
  NPC beside you before leaving town, and keep `delve` from wandering off on an ambush map with a
  client along (leave.py answers No to "abandon the quest?" and stops). "Escort ???" in the journal
  means the client never appeared: that job fails.
- **Harvest jobs ("Harvest season", "Farm worker wanted", "Harvest for me")** are 180-game-minute
  instances: harvest the ripe giant crops round the centre chest and press the chest's **Deliver
  All** (dragging stacks in loses them uncounted); failing costs fame (-25 to -45). Run 18 (four
  jobs, one failed, one Squashed me to 22% HP): **take one only by day and at <= ~50s**; heaviest size
  words first (legendary, monstrous, bigger than a man, very huge); **deliver every ~35s load** (stop at
  Heavy Burden: 92s carried was Squashed); the bonus is 4 orens a s delivered (152s paid 463);
  leaving early counts the same as the time limit.
  **Don't chase mobs in a harvest job** (the user, run 19: "Should avoid chasing mobs in a harvest
  quest"; then "Range attack or ignore"): the clock is the job. No `fight.py` or `hunt.py` toward a
  wanderer: shoot or throw from where I stand, or ignore it (the pets handle small ones), and stay on
  the fields by the chest (a bat chase took me ~25 cells away at dawn). Walk with `weak_ok`.
- **Merchants Guild** (run 17): 30 flyers handed out with `tools/flyer.py` (the adjacent "Gift" to
  Lv1-8 townsfolk; never twice to one NPC) to join; Negotiation from Levadear; salaries come to the
  home mail post as parcels; its informers buy fame (fame/5 orens, fame falls by as much: half the
  tax bill is fame x 2). `famesale.py NAME [TIMES=3] [MIN=140]` sells to one informer (Gizon, Ishbear; run 42: 263 + 210 + 168 and 191 + 153), and since the near
  nefia refill scales with fame, a sale also brings new nefias back under the gate.
- **Escorts and tourists take an ally slot** (run 16): with Kaberg along, one put me over the cap
  (speed 113 -> 91); Party Animal gives a second slot. Fast Travel (no ambushes; `tools/fasttravel.py NAME` from the world-map tile, run 25) is the safe way to
  move an escort; two Mysilia escorts from Olvina (392 + 236) and one back (243) paid 871 in 5 days.
- Find anyone: `whereis.py GUARD "name or service"` (guards walk you there). **A delivery or job
  target missing from the "Where is" list (guards never are on it) has its own line in any guard's
  main menu: "Do you know Havin the guard? (Small errand)"** (the user's tip, run 15: a night's
  sweep of Mysilia missed Havin at 55,92; the guard walked me there). whereis.py tries it first. **Never sweep a town for a job target** (run 17 did it again in Willow at night, then slept 14 hours and the tilefish rotted; the user: "if you ask the guard the 'quest' stuff is always at the top level"): `whereis.py any TARGET` finds a guard first. At Tinker's Camp
  Nino has "Where is..." (Casaneck stays out of view by Aliyun and sleeps odd hours).
- **Plans for home policies** come from scholars: Nenord in Mysilia, Casaneck at Tinker's Camp, one
  in Willow. A restock costs 2 influence (run 12: one restock brought Border Watch, 4 bars).
- Mysilia shops worth a stop: Minron (cure potions 50, rod of cure critical (7) 375), Nazs
  (furniture tickets for influence: right-click the shop stack; a town bed costs 3 tickets).
- Tax (only if a bill is carried): `act.py find "tax chest" Use`, then `item.py "Tax Bill" Deliver`.
- Sell old tickets (114 orens) anywhere; roll them on a fortune drum only when that month's prizes
  show something a goal needs (a bag: backpack2 sits in the third tier). Run 09's 15 tickets gave 4
  platinum, a TV and a sleeping bag where selling paid 1,710.
- Food: Tiguen's inn (stock rotates every ~5 days; seal on the bones 27 for 14 orens, bread 28-36,
  rations 50). Potions: Minron (cure minor 50). Escape scrolls: Wyneck (teleport 60, short
  teleport 53, return 155). Armour: Diefon (cloak 288, scimitar 152 in run 05; run 13: a blessed copper scimitar 435, a mica short sword 440: weapons can only be bought).
- **Shopping list for the goals** (2026-10-23; goals.md Active): junk shops and general stores for
  **alarm clocks**, wall lamps (candle4), electronics, monitors (G18: always steel, a hammer breaks
  each into a steel ingot; Moyer at Tinker's Camp had none in run 20, Fortoli in Derphy untried);
  **one-handed weapons** that beat the axe's 2d13+3 (G19); a **monster ball** (G20: Gizbird had one
  in run 12, none in run 20); record what's there and the price with `kb.py add`, even when it's too dear.
- **The quest board** pays +1 town influence per job plus a sub reward (platinum, a gold bar or a
  furniture ticket); it refreshes only when you enter the town, at most once a game day, so take
  several jobs at once. **Supply and procurement jobs** ("bring me 6 units of gem") take one stack
  holding the whole count (QuestDeliver.IsDestThing: `t.Num >= num`): 4 onyx + 4 lapis are not 6
  gems (run 20: Poppy's job failed). Check the boxes for one such stack, and `kb.py facts` for the
  stock, before accepting (run 14 took Kaberg's needles with none left). Run 05 did four in a week:
  - music party: dark hall, carry a light; `perform.py` on the hall's own instruments.
  - "Regular patrol" counts hostile kills anywhere and completes where you are.
  - "Farm worker wanted" needs ~66s of crops in 180 minutes: hold the hardest axe from the first
    minute and harvest the giant crops (the user: "you want crops", not seeds; the sickle's Reap
    seeds is for a few seeds only).
  - Any "(Danger Lv.N)" or "kill N" job moves you into a closed instance the moment the dialog
    ends: take it only at level >= N + 3 with 5+ potions and a light (the run 03 death; run 05
    did the same den solo with no damage). Run `look.py` after every dialog.

## Other places (runs 03-05)

- **Port Kapul (run 19, G16):** home -> Vernis 19 road steps, Vernis -> Kapul 23 (~2.5 days each, no
  ambush either way; road ambushes are at most level 10). Fast Travel from Kapul: Vernis 3 rations,
  Meadow 5, Yeek Cave 6 (fact #708); the inn (Mico, 69,98) has only 2-4 rations. The Fighters Guild:
  Doria the watchman on the stairway at 58,98 (the trial: 20 yeeks), the office below; Narford the
  clerk's 'Where is...' finds Stanmock the trainer (Dual Wield, Mind's Eye 10 platinum each). **The
  harbour is deep water: I drowned there in run 19** (bridge 0.28.0 now refuses and stops walks before it).

- Tinker's Camp, 3 east and 5 north of home (a day away): Aliyun the mage identifies (46 each,
  322 all) and sells teleport scrolls (60); Pery trains (Appraising, Literacy and more for 5
  platinum); Nino sells station recipes for gold bars (loom and blacksmith's table 3 each);
  Ilass the blacksmith; Casaneck's plans. `kb.py facts "Tinker's Camp"` has the stocks.
  **Moyer** (run 13) runs a junk shop beside Ilass: empty cans, research equipment and other scrap junk
  for 40-70 each (a hammer breaks them into scrap); the board takes jobs whose rewards land on the ground.
  Run 08: Aliyun identifies Miracle items one at a time (45) or the pack (180), refuses Godly ones
  (artifact service only), and buys artifacts at 158-305. **Run 09: identify there (225 for the whole
  pack), then carry ☆ gear home and ship it** (the chest paid 763 for a ☆ axe; Aliyun ~170). The
  quest board (~7 east of Aliyun) had a delivery Ilass wanted from my own Cooler Box and a den job
  for Lv3 monsters: +1 karma each. **Nino wanders:** absent on 486-02-17 and the night of 02-27, there
  in daylight on 02-30 near 49,50 (the Loom recipe bought then). **Pery:** new skills (Swimming,
  Weightlifting, Riding, Symbiosis, Anatomy) for 5 platinum each, training a known one for 1; the
  user's rule: always buy new skills before upgrades. **Sorrotta the bartender** revives allies
  (snow putit 458), but a dead pet also walks home in a day or two. **The ★Fortune Drum** (54,54)
  takes old tickets, one draw each, prizes shown per month (the wiki: also Port Kapul, Olvina,
  Noyel); run 09's 15 tickets gave a TV, a sleeping bag and 4 platinum. A shop's window may need
  `bridge.py closetop` (close.py does it).
- **Travel (the user's tip, run 08):** `wgo.py PLACE --weak-ok` uses the game's own click-to-travel
  pathing (around cliffs). Field danger grows with the distance from a road (`bridge.py terrain`):
  off-road fields west of home were danger 10-12 and cost four teleports in two ambushes.
- Olvina: `wgo.py Olvina` from home (2 days); inn (Upan), healer, trainer, goods, souvenir,
  furniture shops, dyer; no tax chest. Fast travel home costs 2 rations.
- Vernis (24 north, 4 west) is an abandoned camp; the Merchants Guild (next to Mysilia) serves
  members only. Rock throwers (Lv8) roam the world map south of Vernis: give them 5+ tiles.
- **Town furniture for tickets** (run 06): the secretary sells tickets at 1 influence; hold one by a
  piece of town furniture for "Collect X (N Tickets)". Mysilia: trash cans (88,84; 77,70: G5's
  Recycle can), display shelves (20-slot containers), quest pots; Olvina: a stone chest (container).
  Check the thing id first (`kb.py show thing:ID`): the wardrobe and the shelf "backpacks" were decor.
  Heavy finds go home in the town's delivery box (Mysilia 56,82); containers can't go in it.
- Olvina's board in run 06 had two music jobs (Wyward's "Baby!", "Performer wanted"): `perform.py
  harp ... --past` in the Concert Hall; +1 influence and platinum each.
- **Derphy** (16,116): a ring of cliffs; enter through 21,115 -> 21,114 -> 20,114 -> 19,114 ->
  18,115 -> 17,116 (`wgo.py Derphy` paths around the cliff). No guards, pickpockets. The
  Thieves' Guild (stairs 68,73 in the pub, doorman Anastazija; member since 485-12-10, run 07). The
  **Lockpicking trainer is Nornack in the surface pub's west room (~57,73)**, no guild needed; the guild
  trainer Gizhert teaches only Gun, Marksman, Greater Evasion, Pickpocket. In the guild (level -1) the
  clerk Monazess has "Where is..." (Kerona's shop, Leoban's black market, the trainer). Kerona sells
  lockpicks (restocks every ~5 days: 8-20 charges, 270-410), scrolls of incognito (123), one cure
  critical, small gamble chests (lock training, 115-160). Board jobs: Derphy takes criminals, but
  clients wander and can't be found (run 07's ale job). **Pickpockets: about 90 gold an hour on the
  surface** (rogues): shop and leave. Fast travel needs rations; Derphy's innkeeper wasn't found.
  Run 08: the quest board is on the surface at ~66,61 (reach it from 66,60); a "kill 15 in 13 days"
  job finishes itself on the next nefia (+1 karma). Kerona had melons (10, preserved food).
- **Karma below 0 (a criminal):** Mysilia, Olvina and Tinker's Camp refuse to trade and their guards
  attack; Derphy trades. Read a scroll of incognito inside the town (not on the world map) to shop there
  for a while (run 07: Tinker's Camp healer, identify, trainer).
- Buy what raises power (`power.py`): potions and teleport scrolls first, then gear that adds
  PV, damage or a new damage type. A neck item is a bonus, not a requirement (the gate counts
  power, not slots); the decorative amulet needs 2 gems at 800 each.

## 4. Home

- Buy 3 rations (Tiguen's stock varies; none some days), leave by the west edge (42,70),
  `act.py 0 0 "Fast Travel"`, click (Home)Meadow: 2.5 days, no ambushes. No rations: buy a scroll
  of return (Wyneck, 155) and read it in town (it takes about 18 turns; never as a combat
  escape). On arrival: shipping report window (`close.py`), deliveries by the hearth.

## What this skill changed

New in run 03. Measure: errors.csv repeats in the elin-town-trip domain and the orens per real
hour of job and travel time (stats.csv). Baseline runs 12-20: 9 errors, 2 repeats (a sweep for a
job target, a timed harvest job), four failed harvest jobs, two failed supply jobs; Fast Travel
job chains earned 2,000-3,200 orens an hour, jobs on foot 1,100-1,800. Latest: the harvest-job
rules live in harvestjob.py (one job, by day, ~35s loads, no chasing), whereis.py asks a guard first.
