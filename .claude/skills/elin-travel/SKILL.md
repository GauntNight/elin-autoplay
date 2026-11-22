---
name: elin-travel
description: Travel on Elin's world map and what towns are used for - wgo.py and its stops, route danger and the route limit, ambushes and bandit demands, Fast Travel and its ration fares, trip food and the sleeping bag, treasure maps (digmap.py, far maps with --danger-ok), finding people through guards, board jobs (harvest, escort, hunt, supply), Small Medals, karma and town crimes, deep water, and an old per-town reference of shops, prices and coordinates. Use before any walk on the world map, when planning a trip or a route, on an ambush map, in any town, when a job is taken from a board, and when treasure maps are carried.
---

# Travel: the world map, ambushes, towns, treasure maps

Read elin-play first (rule zero and the thresholds table: the numbers are there). Nefias: **elin-delve**. Guild errands
in a town: **elin-guilds**. The kit and shops by name: **elin-pack**. Ask `kb.py facts PLACE` for a town's current prices
and people before trusting the reference at the end.

## 1. Before leaving home

- `leave.py` is the door: it refuses until `packcheck.py` passes (the kit and nothing else, elin-pack 1), under 6 meals
  carried (the pack and every bag; `--food-ok`, run 32), without a bed (`--bed-ok`), without the shovel, and under the
  kit minimums (elin-pack's resupply rule). It makes the Dishes box private on the way out.
- Rested (SP > 2/3), fed (hunger < 50), full HP. Not sleepy? Leave anyway and sleep on the road.
- **Plan the trip before leaving** (the review of runs 03-12: two thirds of run 12's game days went to walking): list the
  errands per town and batch them, carry what the jobs need (a sickle for a harvest job, bars for Nino's recipes).
- **Food for a long trip is real meals** (run 44: 24 mini salads, ~2-6 hunger each, lasted about an hour, and a dig walk
  with five ambushes in a row went Starving, HP 273 -> 65, because wgo skipped its hunger check after an ambush: fixed).
  Buy inn food (soups, roasts, bread) or cook bigger dishes; eat_one keeps 5 travel rations back as fares and eats the
  rest. `buyfood.py` beside an innkeeper sells the old tickets and buys by food per oren. (44)
- **The bed is the sleeping bag** (packcheck's kit; Quick Craft makes one: elin-build). `sleep.py` uses the F-key "Use bed
  in inventory" slot on the world map or any local map outside a nefia, and refuses hungry. **No bed carried: `sleep.py`
  falls back to the Rest ability** (run 44: the sleeping bag left the pack at a home sort; Rest slept me on the world map
  and in a village). A real bed sleeps better but weighs 28 (Burden).
- **Travel rations are the Fast Travel fare** (1 + hours/24), not food. You can't eat on the world map: enter a local map.
- **Rent runs whatever I do** (the review of 2026-10-23): ~70 orens a game day; a 3-day walk costs ~200. Price a long
  walk in rent and prefer Fast Travel when rations are carried.

## 2. The world map: `wgo.py`

`python -I tools/wgo.py NAME [--weak-ok] [--ambush] [--danger-ok N]` (or `X Z`): the game's own click-to-travel pathing
(the user's tip, run 08: it goes around cliffs). The world map is top-down (+x east, +z north): `move n|s|e|w` there,
never `step`.

- **Its stops (exit 3):** an ambush (a local map: `look.py`), a hostile within 4, HP under the walk floor, Hungry, Very
  Sleepy, SP under 5, burden phase 3, a window, not moving. It cancels the leftover walk (run 08: a leftover goto walked
  me 14 game hours further). It eats on the way (a meal stop on the tile's local map at hunger 45, up to six small meals
  since run 44; on home's own tile it steps one tile off first, run 56: the home map's departure checks stranded a
  circuit there), sleeps at Very Sleepy, and closes the morning shipping report itself (run 21). An Enter after a refused
  or stopped wgo.py walks back into the place just left (run 21, twice): gate the next step on its exit code.
- **`--ambush`** handles the ambush map itself by the table's rules (the swarm row, 3+ levels above me: stop), then
  `fight.py` one foe at a time, `loot.py 20`, `purge.py --free 3`, `leave.py`, and walks on (the review of 2026-10-23:
  travel was the largest real-time sink). `--weak-ok` keeps walking past hostiles 3+ levels below me.
- **The route limit** (`route_max`, the table's row: 20): `wgo.py` refuses a route whose worst ambush level is over it
  unless `--danger-ok [N]` is given for a deliberate crossing, and **every leg checks the tiles actually reached** (run 28:
  the game's pathing swung east of the straight Mysilia -> Mifu line into a danger-26 ambush where the line said 19; run
  43: a 13-tile hop ran 30 tiles round). It was 12 from Lv21 to run 41's Lv35 (run 21: a walk north met a level 21 field,
  a stone golem Lv22 and a cupid Lv18; level 9-10 crossings at Lv21 cost less than a tenth of my HP; fact #1186: a level 24 field cost
  0 HP at Lv35).
- **Route danger:** `tools/dangergrid.py [R] [X0 X1 Z0 Z1]` prints the ambush level of every tile around me (# blocked,
  R road): max(0, road distance - 4) + min(home distance / 4, 10) (Player.EnterLocalZone); on a road it never passes 10.
  Ambushes roll 1 in 12 a step off-road, 1 in 22 on a road, never on shore tiles, with 5-9 safe steps after one
  (Chara.cs, run 09). Field danger grows with the distance from a road (`bridge.py terrain`).
- **Time (run 12, Chara.cs):** a world-map step is 180 game minutes at base (+rain or snow). Every leg is logged to
  knowledge/travel.csv and, for 3+ steps, the graph (the user's request). **Count the steps before accepting an escort.**
- A name that fits two places is refused; an underwater dungeon is refused without `--breathe` (elin-delve 2).
- **World-map monsters:** one that keeps 4 cells away follows every step and can't be targeted from there (run 23: a hot
  guy, a jellyfish): `wgo.py --weak-ok` past a weak one, Fast Travel past an exploder. A hostile in view cancels eating
  and goto; a key into a cliff slides along it.

## 3. Ambushes and bandits

- **An ambush** is a local map; I start mid-map and `zone.bounds` gives the edges. By hand: `look.py`; on the table's
  swarm row, or anything 3+ levels above me (`fight.py` refuses it), leave at once with `leave.py --force` (it walks to the
  nearest edge and takes its Enter; on a lake ambush `wade.py` steps to the edge checking each cell, run 29). Otherwise
  fight one at a time (`fight.py NAME`, `shoot.py` for floating eyes and hard hitters), `loot.py`, then `leave.py`. A
  swarm closing in: teleport, not return. Exploders: elin-delve 6 (the table's distance, soak first).
- **World-map monsters are bandit groups** (run 18): walking into a roaming "hot guy" brought two of them 2 cells away
  and a demand ("Give me paralysis, or your life is forfeit!"). Against exploders, pay a cheap demand (they turn Neutral);
  against weak bandits answer "Try me".
- **A bandit's demand is read before it's paid** (Start Run 4: an automatic surrender gave up all 8 gold bars): `roam.py`
  refuses demands for gold bars, platinum, tickets or the weapon. A surrender ends a lone bandit; a gang keeps hitting
  (Start Run 3). (Start Runs 3, 4)
- On any map with water, check the cell before stepping; never wander a dark map to search for a quest client (a client
  who can't be found is a failed job, -5 karma, not a reason to risk it). (07)

## 4. Fast Travel, and going home

- **`python -I tools/fasttravel.py [NAME]`** (run 25) from my own world-map tile: a button per visited place with its
  ration cost and days; it refuses a fare over the rations carried, clicks by name, and reports the new zone. No
  ambushes, no confirmation, autosaved on arrival. The fare is 1 + hours/24 rations (from Mysilia: Meadow 3 / 2 days,
  Palmia 6 / 5 days, fact #876; from Port Kapul: Vernis 3, Meadow 5, fact #708). The time passes the same as a walk.
- **Rations are bought** (the user, 2026-11-14, dropping G14: "at our current wealth level we just buy rations unless
  there is some reason to farm them"): inns (Olvina's Upan 13 tiles from home, Tiguen in Mysilia, Chisierra in Yowyn,
  Semnof in Palmia; 3-4 a restock, 50 each). `ration.py` makes them at home only for a reason the run log names.
- **Unattended, a town past fields over the limit is reached only by Fast Travel**; to Lumiest by Fast Travel, never a
  walk (fact #1168). It is also the safe way to move an escort (run 16).
- **Home over 10 tiles away is a recall, never a walk** (run 49: 17 game days of detours and ambushes from 24,149): `wgo.py` refuses it (`--walk-ok` overrides); enter any tile's map, then `recall.py`.
- **Home:** Fast Travel to Meadow, or a scroll of return read on a local map (`recall.py`: one read, ~19-36 turns, never
  a combat escape; a claimed zone becomes the home and recall.py refuses then). On arrival `arrive.py` (elin-home 1).
- **A pick-up gates the walk after it** (run 45: a `;` chain walked home without the big wagon, a wasted 25-game-hour
  leg): `pickup.py NAME` exits non-zero unless the pack count rose; chain with `seq.py` (elin-play's hard rule).

## 5. In town

- Enter in daylight. Shops sleep at night (and at odd hours): **count a walk's game hours and plan the arrival by the
  clock** (run 55 reached Willow and Mysilia at night, shops shut; Tiguen's inn trades at night). **Don't wait for them** (the user, run 05: waiting burns
  food): work the board, sell, or sleep in an inn bed when sleepy (a visitor may: SP 16 -> 57, run 05), and come back.
- **Find anyone through a guard:** `whereis.py GUARD "name or service"` (guards walk you there). **A delivery or job
  target missing from the "Where is" list has its own line in any guard's main menu** ("Do you know Havin the guard?
  (Small errand)": the user's tip, run 15). **Never sweep a town for a job target** (run 17 did it again in Willow at
  night, then slept 14 hours and the tilefish rotted; the user: "if you ask the guard the 'quest' stuff is always at the
  top level"): `whereis.py any TARGET` finds a guard first.
- **Small Medals on every town or named map the wiki lists** (the user, 2026-10-29): `look.py` prints a MEDALS line
  there; `medals.py --take` walks onto each reachable hidden medal and picks it up, and reports the ones under furniture,
  behind walls or in deep water for a deliberate step. knowledge/medals.md lists all 141 by map.
- **A shop's stock:** `shop.py NAME [--record WHERE --run N] [--keep-open]`; buying and selling by name: elin-pack 6.
  **New skills before upgrades** at any trainer (the user's rule: 5 platinum for an unlearned skill, 1 for an upgrade);
  the coins must be carried.
- **Karma below 0 (a criminal):** Mysilia, Olvina and Tinker's Camp refuse to trade and their guards attack; Derphy
  trades. A scroll of incognito read inside the town (not on the world map) opens the shops for a while (run 07); the
  scroll lives at home (packcheck's home-only list): take it out for such a trip.
- **Mining, digging and hammering property in a town are crimes** (run 23, facts #818, #823): Karma -1 each (a hammered
  thing 2 times in 3), the game asks "Really commit a crime?", and every progress tick rolls 1 in 10 per human within
  Distance 3 with line of sight (asleep too) to call the nearest guard (Aquli Teola's are Lv40). Only with
  `tools/sneakmine.py` (the bridge's sneak guard cancels the task when a possible witness is within 3); never by hand.
  A claimed zone is mine: no crime there, but **a claim makes that zone the home** (the return scroll then skips Meadow:
  "Set as your Home" at Meadow's hearth). Town furniture is someone's property (theft: Karma -1).
- **Deep water drowns** (run 19: **death** in Port Kapul's harbour): the game's own pathing swims, and every step and
  turn in deep water suffocates (Cell.CanSuffocate; shallow water only wets). The bridge's walkto refuses a deep-water
  target and stops before its path enters one (`why: water`); `state.pc.pathWater` shows it for any walk (a guard's
  directions: whereis.py cancels). Never sweep waypoints over a map without checking them, and a walk that stops in water
  is followed by getting out, not by retries.
- **Plans for home policies** come from scholars (Nenord in Mysilia, Casaneck at Tinker's Camp, one in Willow); a restock
  costs 2 influence. Old tickets sell anywhere (114 orens); a fortune drum only when that month's prizes show something a
  goal needs.

### Board jobs

The board pays +1 town influence a job plus a sub reward (platinum, a gold bar or a furniture ticket), +1 karma each. It
refreshes only when you enter the town, at most once a game day, so take several at once. Run `look.py` after every dialog.

- **"(Danger Lv.N)" or "kill N" jobs** move you into a closed instance the moment the dialog ends: only by the table's
  job row (the run 03 death). Unattended: no client-based instance jobs (deliveries and kill-count jobs are fine).
- **"Hunt any X" jobs ("Foul race!", kill N of a race) have no deadline and hold one of the 5 quest slots until
  finished** (the user, run 15: "they are persistent... I've accidentally accepted too many and have not been able to
  accept new quests"). Hold at most two, finish them before taking another, and read the journal's Remaining Time ("-" =
  none) rather than the board. "Regular patrol" counts hostile kills anywhere and completes where you are; a "kill 15 in
  13 days" job finishes itself on the next nefia.
- **Supply and procurement jobs** ("bring me 6 units of gem") take one stack holding the whole count
  (QuestDeliver.IsDestThing): 4 onyx + 4 lapis are not 6 gems (run 20). Check the boxes for one such stack
  (`stock.py --find`) before accepting (run 14 took a needles job with none left).
- **Harvest jobs** ("Harvest season", "Farm worker wanted", "Harvest for me") are 180-game-minute instances; the rules
  live in `harvestjob.py [min_sp] [load] [radius] --ends HH:MM`: one job, by day, ripe giants by size by the chest
  (heaviest size words first), the chest's **Deliver All** in ~35s loads (dragging stacks in loses them uncounted; 92s
  carried was Squashed, run 18), and **no chasing mobs** (the user, run 19: "Should avoid chasing mobs in a harvest
  quest"; then "Range attack or ignore"). Failing costs fame (-25 to -45); the bonus is 4 orens a s delivered.
- **Escorts and tourists take an ally slot** (run 16: over the cap, speed 113 -> 91) and **don't show in the party list**
  (run 17): read the journal's "Escort NAME", see that NPC beside you before leaving town, and keep `delve` from
  wandering off on an ambush map with a client along (leave.py answers No to "abandon the quest?" and stops). "Escort
  ???" means the client never appeared: that job fails. Mysilia's "(1 day left)" escorts to Olvina and Derphy can't be
  done: count the steps. Run 16: two Mysilia escorts from Olvina (392 + 236) and one back (243) paid 871 in 5 days by Fast Travel.
- **Music jobs:** a dark hall, carry a light; `perform.py` on the hall's own instruments. A hostile caster in view ends
  a performance (11).

## 6. Treasure maps (G44, run 41)

The dig is on the world-map tile itself, with the shovel in hand ("Dig (Easy)"); nothing guards it and the chest is
unlocked: about 1,900 orens, 2-4 gold bars, 1-2 medals and 1-3 pieces a map, whatever its level. 17 maps in 26 real
minutes paid 75,600 orens an hour against a circuit's 9,345 (run 41).

- `bridge.py places` lists each carried map's spot, nested in bags too. `digmap.py --list`, `digmap.py --plan [X,Z]` (a
  greedy tour with each leg's worst ambush level), `digmap.py N [--max-dist D] [--danger-ok L]` walks, eats, sleeps and
  digs nearest first (a route over `route_max` is skipped); each dig is a row in runs/digs.csv.
- The chests ride home closed and their money counts as carried: `chests.py --field` on a local map empties them and
  leaves them (15 weight each, Burden 2 at five); `chests.py` at home ships them. Some are locked: `unlock.py` (lock 29
  opened on its 7th try at Lockpicking 63).
- **Weight on a tour** (run 47: 12 maps, 22,004 orens and 26+ gold bars in ~10 real minutes): the chests and bars put me
  at **burden phase 3 on the world map, where the squash took 352 -> 209** and nothing can be dropped (no Drop there) and
  a zone change can tumble for MaxHP x burden% / 200. So: heal to above that number with potions first (the spell does
  nothing on the world map), then Enter, `chests.py --field` (it takes chests out of the bags since run 47), and on.
  Unload at home before a circuit: the bars and medals.
- Every boss chest's map gets dug on the way when its spot is near; the rest wait in the shared Maps box for Poppy
  (elin-home). **A far map barely pays its walk** (run 50, fact #1476: 73 tiles, ten game days for 2,356 orens and 3 bars,
  about its own rent; the 1-9-tile maps paid 1,269-2,913 in hours): dig what lies within a day or two, and ride a far one
  only on a trip already going that way. 12 maps in run 50: ~27,000 orens, ~30 gold bars, ~20 medals.
- **digmap's meal and unload steps Enter the tile they stand on**; on a nefia's tile that is the nefia (run 50: twice, once
  a danger-14 B1 beside a kamikaze samurai). `digmap.off_nefia()` steps one tile aside first since run 50.
- **Fame sales away from Palmia and Olvina:** Noyel's informer is Ras (fact #1477; Noyel's guard lists an inn, a mage and
  seven shops).
- **A background dig is running until its task says it ended** (run 44: digmap walked on after a hunger stop while I
  drove the game by hand): its stop lines can be steps it handles itself.
- **Far maps** (the user, 2026-11-06: "You can cross those fields, with teleport, return, et. it is safe I think.
  Possibly it won't [be] as hard to fight as expected"): routes over `route_max`, up to ambush level 46, are allowed for a
  dig with `--danger-ok L`. Lowest first, and each step of L up only after a crossing at the last one cost no potion.
  Leave home with the nefia kit (`ladder.py`'s counts). An ambush keeps rule zero and the table: fight what `fight.py`
  allows and note the result by level, because this is what tests the user's guess; for the rest teleport, then
  `leave.py --force`, or read the return scroll from a safe spot. x1 for a named exploder. Log each crossing's ambush
  level, HP lost and potions in the run log, so the limit moves on numbers.

## Reference (old, check before trusting)

Per-town notes from runs 03-25. Prices, stocks and people move: `kb.py facts PLACE` and `shop.py` are newer than this.

- **Home's edges:** north 52,34 offers Enter; the Meadow is at 32,104 on the world map. The tax is paid at home (the tax
  chest 62,49; arrive.py pays a bill from the mail, run 35); with a bill carried in a town: `act.py find "tax chest" Use`,
  then `item.py "Tax Bill" Deliver`.
- **Mysilia** (~2.5 days, 25 tiles by road, at most level-10 ambushes): Tiguen's inn (stock rotates every ~5 days; bread
  28-36, rations 50); Minron (cure potions 50, rod of cure critical (7) 375); Wyneck (teleport 60, short teleport 53,
  return 155); Diefon (armour and weapons: weapons can only be bought); Gizbird (general goods: blankets, lockpicks at
  random); Nazs (furniture tickets for influence: right-click the shop stack; a town bed costs 3 tickets); Nenord the
  scholar. West edge 42,70; the delivery box 56,82 takes heavy finds home (not containers). Trash cans 88,84 and 77,70.
- **Tinker's Camp** (3 east and 5 north of home, ~14 h): Aliyun the mage identifies (run 08: one Miracle item 45, the
  pack 180-225; refuses Godly ones: artifact service only) and sells teleport scrolls (60); Pery trains (new skills 5
  platinum, a known one 1); Nino sells station recipes for gold bars (loom and blacksmith's table 3 each) and wanders (in
  daylight near 49,50); Ilass the blacksmith; Casaneck's plans (he sleeps odd hours; Nino has "Where is..."); Moyer's
  junk shop beside Ilass (scrap junk 40-70 each); Sorrotta the bartender revives allies; the ★Fortune Drum at 54,54; the
  board ~7 east of Aliyun.
- **Olvina** (~2 days; Fast Travel home 2 rations): the inn (Upan), healer, trainer (Ceroyon: craft skills), goods,
  souvenir and furniture shops, a dyer; no tax chest; the Concert Hall for music jobs; a stone chest (container) for
  tickets.
- **Vernis** (24 north, 4 west; home -> Vernis 19 road steps): an abandoned camp (runs 03-05). Rock throwers (Lv8) roamed
  the world map south of it.
- **Port Kapul** (run 19; Vernis -> Kapul 23 road steps, ~2.5 days, no ambush): the inn (Mico, 69,98) has only 2-4
  rations; the Fighters Guild (elin-guilds). **The harbour is deep water.**
- **Derphy** (16,116): a ring of cliffs; `wgo.py Derphy` paths around them (by hand: 21,115 -> 21,114 -> 20,114 ->
  19,114 -> 18,115 -> 17,116). No guards; **pickpockets take about 90 gold an hour on the surface** without the Fighting
  Bull. The Lockpicking trainer is Nornack in the surface pub's west room (~57,73), no guild needed. The board is on the
  surface at ~66,61 (reach it from 66,60); Derphy takes criminals, but clients wander and can't be found (run 07's ale job). Kerona on B1 (~64,66) sells lockpicks (restocks every
  ~5 days: 8-20 charges, 270-410), scrolls of incognito (123), small gamble chests (lock training, 115-160), melons (10).
  Fields around it ran danger 7-12 (run 14). The Thieves Guild: elin-guilds.
- **Palmia, Yowyn, Lumiest, Aquli Teola, Noyel:** no notes here; the facts hold their shops (Semnof's inn and Frealord
  the craft trainer in Palmia, Sesa and Sayig in Aquli Teola).
- **The Village of Atonement** (run 55, G66): world 81,97, ~30 tiles east of Mysilia (7 rations by Fast Travel once
  visited); its barrier opens only with ★Negotiation with Darkness taken (the Bracelet of Forgiveness). Bicerin, the elder,
  is in the village's one roofed room. The **Sunken Temple of Lurie** is underwater (elin-delve 2: `--breathe`, the Forest
  Gloves worn at its door); its B4 stairs are a "locked corridor" that opens on Use once the quest reaches phase 2.
  The **Minotaur's Nest** (danger 26-30) has minotaur mages that cast Gravity on B4 (no teleport moves you: elin-delve 7);
  Ungogo, who drops ★Minotaur's Great Horn for the capture ball, is on B5. knowledge/story-guilds-research.md has the quest's phases.
- **Town furniture for tickets** (run 06): the secretary sells tickets at 1 influence; hold one by a piece of town
  furniture for "Collect X (N Tickets)" (Mysilia: display shelves are 20-slot containers). Check the thing id first
  (`kb.py show thing:ID`): the wardrobe and the shelf "backpacks" were decor.
- **Identify in town, ship ☆ gear from home** (run 09): elin-pack 3.

## What this skill changed

New in run 03 as elin-town-trip (Mysilia and back); reshaped at the review of 2026-11-11 into travel as a whole (the
routes row, trip food, the bed, bandits, deep water, town crimes and treasure maps came from elin-play; guild errands
went to elin-guilds). Measure: errors.csv repeats in the travel and jobs domains and the orens per real hour of travel
and job time (stats.csv). The harvest-job rules live in harvestjob.py and whereis.py asks a guard first.
