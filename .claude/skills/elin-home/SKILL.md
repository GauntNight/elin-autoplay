---
name: elin-home
description: Keeping the home base in Elin organized, clean, nicer and safer (run 04, the user's request) - where everything lives (one category per container), the Meadow by zones and, since 2026-10-21, as a town (G12 - six themed houses: Workshop, Forge, Kitchen, Farmhouse, Storehouse, Residence; each station and its materials box inside its house; the game's room rules), what to keep, ship or sell, the cleaning routine (mail, garbage, dead furniture, weeds), carried storage (hotbar slots, bags), placing and mounting furniture (height), the improvement projects with their recipes, and home safety. Use on every return home and whenever storage, junk, furniture or base layout comes up.
---

# Home: organized, clean, nicer, safer

The day-to-day routine (the farm round, exp, food, first crafts) is section 7 below.
skill is the place itself: where things live, what goes, what's being built. The user's aim (run
04): less junk, organized stuff, clear rules for what to sell and what to keep, a nicer and safer
place to live.

## 1. On every return home (10 minutes, in this order)

**`tools/arrive.py` runs steps 0-3 and the town check in one go (run 19):** the Dishes box shared,
packcheck --move, the mail, trash.py, town.py, and a food line. A hostile in view stops it first.

**Books and recipes on every return:** `decode.py --fetch`, `readskills.py`, and `readrecipes.py [--known]` (run 41, the user: "Why don't you read the recipes you have available to you?": 101 lay in 12 boxes, 37 never learned, because a skill said to read them and no tool did; a new one opens a first craft worth an old ticket and skill exp, and every read frees a box slot). `chests.py` for any mystic chest in the pack. Read `gearcheck.py` before `shipstar.py`.

0. **`packcheck.py --move` first** (the user, run 11: "on entering base you organize your packs...
   when leaving base you must clean your packs of useless inventory... it is a loss of treasure by
   not having those slots free"). It checks the pack, the backpack and the Cooler Box against the
   trip kit and carries every other item to its zone box (valuables, library, wood, stone and ore,
   bag parts, parts, pantry, farm, spares, the armory; junk to the trash can; **anything without a
   rule is reported and left in place, never shipped** (run 12: the old ship-by-default sold the
   ☆Forest Necklace).
   Unidentified gear stays in the pack for Appraising. **`leave.py` refuses to leave home** until
   `packcheck.py` reports 0 out of place (`--pack-ok` only for a deliberate haul).
1. `look.py`: hostiles wander in (home is danger 5 since run 15's Border Watch: a Lv12 killer
   squirrel came at danger 7 in run 14; goblins, gnomes, putits and a Lv7 kobold at danger 3). Shoot or fight them first (`shoot.py`, `fight.py`), from range for anything at
   or above my level.
2. **Mail:** `unpack.py` lists every package; `unpack.py --take --pickup` empties new ones and picks
   them up (the library bin is skipped). Read and triage what came.
3. **Garbage into the trash can (the user, run 08):** `trash.py` walks every garbage pile on the
   map, picks it up, then drags each garbage, rotten-food, bottle and can stack into the trash can
   58,51 for Ecopo. Never ship garbage: the chest pays 0 for it. Residents drop garbage every day;
   run 08 found ~50 piles after a month away.
4. **Ship the other junk** (section 3) with `box.py "shipping chest" ITEM ...`. The chest pays out
   each morning, more than a shop, and adds gold bars by volume.
5. **Put the haul away by category** (section 2) with `box.py WHERE ITEM ...`. Merge stacks: a
   recipe slot takes one stack only. Then the detritus pass (section 2a, rule 3): `find.py` loose
   things on the map (`bridge.py find` with an empty name lists everything; keep the not-installed
   ones) and put each away; `trash.py` misses piles it can't reach (48,46 behind a tree, run 11).
6. The farm round (`springday.py 1 UNTIL --once`, after 06:00), then leave: sleep on the world-map
   tile (`sleep.py` with the kit's bed), not at home (section 6: time at home costs the residents'
   food; `sleep.py` refuses on the home map without `--home-ok`, which the home loops pass on purpose).

## 2. Where everything lives: the town (world_4, Meadow; built run 18, 487-02-15/19)

Every coordinate below lives in `tools/home.py`; the tools read it from there. `tools/town.py`
checks the town against the game's own rooms (G12's done-when, met 487-03-01).

| House (walls, door) | Stations | Boxes (home.py name: what it holds) |
|---|---|---|
| **Workshop** (oak plank 46-56 x 55-61, door 51,55) | back row z=60: loom 47, wall workshop 48, spinner 49, drafting table 51, signboard workshop 52, mason's table 53, stonecutter 54, tinker's table 55; front row z=56: sawmill 47, workbench 49, carpenter's table 50; research equipment 55,57 (Kettle's); the home's iron big rock stands at 50,59 (G11: Mining 7 with the iron pickaxe) | WOOD_BOX 48,57: logs, planks, branches, sticks, bark, resin, spare walls and room boards; PARTS_BOX 53,56 (sturdy box 'Parts'): bones, nails, batteries, microchips, scrap, fangs; BAG_PARTS 54,56 (boss chest): threads, fiber, strings, ropes, skins, bolts; MAPS_BOX 55,56 (**shared**, distribution off): treasure maps for Poppy; STORAGE_CHEST 47,58 (Ashland's ★Storage Chest, 100 slots, fireproof, no rename): the library's and the spares' overflow |
| **Forge** (granite stone 58-62 x 55-61, door 60,55) | kiln 59,60, smelter 60,60 (auto-refuel on), blacksmith's table 61,60 | STONE_BOX 61,57 ('Stone and ore') and STONE_BOX_2 61,56 ('Stone 2', run 20): stones, cut stone, ores, ingots, glass, bricks, soil |
| **Kitchen** (oak plank 64-69 x 55-60, door 66,55) | bonfire 65,59 (cook from 65,58), millstone 66,59, ration maker 67,59; the small fridge 68,59 | PANTRY 68,57 ('Pantry'), PANTRY_2 68,56, PANTRY_3 65,57: oils, herbs, drinks, condiments, organs for jobs; DISH_BOX = the fridge 68,59 (**shared at home, private away**, food, priority 1, nothing rots): the residents' dishes and the farm's fresh food (G15, runs 19-20) |
| **Farmhouse** (cedar plank 57-61 x 40-45, door 57,43 facing the field) | (the farm sign 51,47 and the field outside) | FARM_BOX 58,44 (a 20-slot package: every seed, sickle, hoe, shovel, watering can, fishing rod, bait); FARM_BOX2 59,41 ('Farm box 2': seeds when the first is full); HARVEST_BOX 60,44 (shared, food: Delegated Farming's crops land here); FODDER_BOX 60,41 (shared sturdy box: grass, leaves, odd logs) |
| **Storehouse** (rosewood plank 63-69 x 37-42, door 66,42) | | LIBRARY 66,38 (box) and 64,38 (package bin: Lutz journals, house plate, ancient books), overflow in the Storage Chest; BOOKSHELF 65,38; VALUABLES 64,39, 67,38, 68,38, the shelf 68,39, the stone chest 64,40, and 'Valuables 6' 66,39 (run 20): coins, gold bars, platinum, medals, tickets, genes, figures, cards, gems (**full in run 20: 62 platinum refused; a box is full at 14 of 16**); COLLECTIBLES 68,40 (shelf); SPARES 65,41 (boss chest), SPARES2 67,41 (package), SPARE_BOX 68,41: potions, scrolls, rods |
| **Depot** (oak plank 41-46 x 45-52, door 46,49 facing the field; board 'Depot', Private; G28, run 30) | | six sturdy boxes (35 slots) along x=42, z 46-51: FARM_BOX 'Farm' (every seed and farm tool), SPARES2 'Spares 2', LIBRARY 'Library 3', VALUABLES 'Valuables 7', ARMORY3 'Armory 3', PANTRY_2 'Pantry 2'; they replaced the mail-package bins (the user, run 30: no cardboard boxes as storage) |
| **Residence** (the grass rooms: my room 59-62 x 51-53, door 60,51; residents' room 62-68 x 49-53, door 65,49; board 'Residence', Only Resident) | | ARMORY 66,51 (shared, weapons and armour: residents take what beats theirs); beds: my pine bed 60,52 (full SP), a spare 61,52, the residents' 63-65,50-52 |

Outside on purpose (the office): mail post 61,50 (bills and salary parcels; pay at the **tax
chest 62,49**), the labelled mail package 60,50 (no Grab), shipping chest 56,52 (empties every
morning), trash can 58,51 (garbage, rotten food, bottles, cans: `trash.py`; never ship garbage),
the home, quest and resident boards 54,50-52, the hearth stone 55,50, Fiama's lock-50 quest chest
54,50, the dummy 60,46 and practice chest 61,46. The field 48-54 x 43-49 and the lake 43-47 x
38-41 stay unroofed. The Mining strip for `tools/minewalls.py` is 47-50 x 52-53.

**Rules**
1. **One theme a container, inside its house.** Rename each box by its theme (`bridge.py boxcfg
   name=...` with it open). A new box for a full theme goes in the same house.
2. **A box is full at 14 of 16 slots:** build the next one before it fills (sturdy box: 4 planks +
   2 ingots + 2 nails; wooden box: 2 planks + 2 strings; carpenter's table).
3. **Nothing lies loose.** Every return: `trash.py` (residents drop ~2 garbage a day), Kaberg's logs
   and bark to the wood box, dropped seeds boxed.
4. **No trees or bushes on field cells.** No harvestable tree is left inside the home's bounds
   40-70 x 35-65: wood comes from field maps (the forest tile south of home).
5. **The pack is a carrier, not a store** (springday stops at 37 loose stacks). The spoils bag
   carries the kit's overflow; the loot bag is the haul.
6. **Moving a box or station:** `tools/move.py FX,FZ TX,TZ [NAME]` for an empty one;
   `tools/boxshift.py FX,FZ TX,TZ` for one with contents (empties it into the loot bag by Shift+click,
   moves it, refills it; `--contents` into a box already at the target, in light trips). Then
   update `tools/home.py` in the same session; packcheck, springday, farmday, water and town.py
   read it.

**Building a house** (run 18; elin-build has the facing rules): wall workshop (Loytel's recipe):
plank wall = 1 plank, stone wall = 1 stone, both 0 SP; a sawmill makes 2 planks from a log for
1 SP. Clear the outline (a flower or bush under a wall is replaced; a bush inside can stay), place
the walls with `place.py` and **the door cell's wall last from a cell outside** (run 18 walled
itself into the Forge and mined its way out), the door on that wall, `rotate.py` the facings (hold
a spare wall; stand next to each side), a room board inside (placed from inside: cells behind new
walls offer no Place from outside), "Change name" with `bridge.py input NAME`, Access Type by
its context menu. Separate houses need a 1-cell gap or different room-board groups (0-4).


## 3. Keep, ship or sell

**Trash can at once** (`trash.py`): garbage (burnable, unburnable), empty bottles and cans, rotten
food and offal: the can pays Ecopo, the chest 0 (the user, run 08).

**Ship at once** (chest): junk stones, granite "a tool", cursed or doomed items (never equip, read or wear
one: the user's warning; a cursed or gifted item can't be taken back off a pet),
things made only for their first-craft ticket (signs, plates, doors, furniture with no place),
dead furniture (the Defense Training gallows, 56 weight each: carry one at a time, two made me
Squashed), spare torches beyond one.

**Keep:** crafting materials (one stack each), gold bars, gems and ores, spellbooks and tomes, potions
and scrolls, food, seeds, tools, one spare of each weapon type, 2 old tickets (for a fortune drum),
quest items (★).

**Stock caps (the user, run 27; `tools/stock.py`, run 28):** the pack, the bags and every home box count
together (bridge `stock` reads them all in one call). A spellbook of a spell at 100+ casts is excess; under it,
**read it** (`stock.py --read`: +3-9 casts a charge, Literacy exp, the book falls apart at 0 and frees the slot;
never a cursed one: x3 difficulty). Rods: teleport and cure all, speed 2, every other kind 1 (the most charges);
hostile summons, strip blessing and empty rods none. Potions: heals all, debuffs none, the rest 5. Scrolls:
teleport all, return 8, evacuation 6, identify 10, levitate none (the Ether Wing). `stock.py` reports, then
`stock.py --ship` carries the excess to the shipping chest box by box. Run it on any visit where arrive.py
reports a full box.

**Never sell or ship anything unidentified** (the user: it loses value). **Identify, then decide:**
unidentified items ride along for Appraising (elin-pack 3); Aliyun the mage at Tinker's Camp (3
east, 5 north of home) identifies by the count (`kb.py facts Aliyun`). Spellbooks and rods first
(run 04: a tome was Cure Minor Wound, a rod was identify).

**Sell in town:** old tickets (114 orens each in Mysilia, keep 2). Everything else ships from home.

**Unsure?** `kb.py show ITEM` gives the base value: under about 100 with no recipe use, ship it.

## 4. Carried storage

- **Hotbar slots are free pack space** (the user's tip): they're pack items on grid row 1, outside the
  backpack grid. `hotbar.py ITEM ...` puts items on empty slots, `hotbar.py --take ITEM` brings one
  back, `hotbar.py` lists the page. Kit on the hotbar (run 04): Putit In Amber, bow, cure potions,
  teleport scrolls, short teleport, Cooler Box, throwing daggers, basalt pickaxe (hardness 52, run 11; the user: always
  take a pickaxe delving, for wrecks and rocks), stone arrows.
- A hotbar item becomes the **held** item when its slot is selected, and right-click then means
  Throw or Shoot: empty the hands before hand jobs. `unpack.put_away()` clicks the widget's
  Deselect; `gather.py` does it for hand jobs.
- **Bags:** a container in the pack holds many items in one slot. `bag.py "Cooler Box" ITEM` moves
  food in; `item.py` finds items inside an open bag. The three bags (G6, done run 14: the backpack,
  the loot bag, the spoils bag) are the kit's overflow (elin-pack 5).

## 5. Making it nicer: projects

The finished projects (the door, the torch, boxes, the pine bed, the tax chest, the watering can,
the trash can, the three bags, the bookshelf, the residents' beds, the blacksmith's table, the
butcher's tool, the kiln, the six houses) are in the run logs and goals-done.md. Open:

| Project | Recipe | Status |
|---|---|---|
| Waste boxes (burnable, unburnable) and a compost box | 8 planks + 2 tight ropes each (tight rope = string + big leaf at the workbench) | open: first-craft tickets and real trash bins; need planks from the sawmill and big leaves |
| More light | wall torches by the doors; the wall lights from nefias (run 16) | open: night visibility beyond the office torch |
| Storage room | the valuables are full (run 20): a seventh box, or the Storage Chest for the overflow | run 36: every valuables box full again; the Depot's empty mystic chests (45,51; 44,46; 43,46) and 70,51 / 67,52 are `home.VALUABLES_OVERFLOW`, the bookshelf 65,38 is the library's tail |

**The crew's genes (G38, run 36):** the Gene Machine (54,59, powered by the Truce Ground generator) puts a gene into a
home member (never me: a Juere has no Predatory Evolution). `gene.py plan [MEMBER]` lists each member's feat points,
gene slots and every carried or boxed gene that would take (bridge 0.37.0 `genes`); `gene.py start MEMBER GENE` (the
gene carried in the pack: `box.py X,Z --take` first) suspends them and drags it in; `gene.py finish` applies it when
the incubation is done (cost^2/2 game hours: a cost-1 gene at once, cost 2 about 2 hours). Feat points bind: cost-2
attribute genes give the most per point; Inferior genes give nothing (fact #1112): ship them.

Placing: `place.py ITEM X,Z` (it waits out a pet on the cell; "Throw" or "Gift" offered means a
creature is standing there: try a neighbour). Wall items go on the floor cell in front of the wall,
then up with `--height` (the torch at 62,50 sits at +4; +7 was too high, +0 on the floor). Rotation:
`rotate.py`. Crafted furniture lands in the pack: `craft.py` stops a batch at Burden (run 14's Squashed).

## 6. Safety

- Monsters wander onto the home map. Check `look.py` on arrival and after every long task; never
  leave time passing unwatched (`springday.py` stops on threats and never waits with `--once`).
- Valuables in private boxes; the pack light (a death drops carried items and gold).
- Carry heavy furniture one piece at a time (Squashed is deadly).
- Light: the wall torch by the door; more torches would help night visibility (open).
- Monsters spawn at home only while I'm on the map and awake (FactionBranch: 1 in 10 an hour, 1 in 5
  at night, 4 at most), at HomeEnemy(danger): 7 at home level 2, **5 with Border Watch** (on since
  run 15, 3 AP). Animal Prohibited Zone (on since run 15, 0 AP) deletes hostile animal spawns and
  stops neutral visitors (none left to shear). **Policies:** `tools/policy.py` lists them and
  `policy.py on|off "Exact Name"` switches one and checks no other row moved (run 14's row clicks
  hit the wrong policies because a look.py re-listed the buttons in between).
  Quruitzia (Lv14 warmage) is the strongest resident; the residents' house walls the beds in.
- Never let springday or hunt kill a cat, hostile or not (Karma -1; run 12 lost one to a kitten).
- **Feed the residents** (run 17: Kettle starved at home). They eat only **prepared food** (weed
  stew, boiled egg, meat on the bone, bread, sweets, jerky: TraitFoodPrepared), never raw farm food.
  `springday` keeps 6+ dishes (RESIDENT_DISHES) in the Dishes box: corpses first (meat on the bone at
  the bonfire), then weed stews from the fodder box's grass; `cookdishes.py` adds salads and roasts.
- **Time at home is what costs food** (the user, after run 18; code: kb #685). Away, the game feeds
  the residents from any shared box that holds prepared food, and for free only when none does; at
  home there's no free meal (~8 dishes a home day for 6). So:
  - **Short, errand-shaped stays.** Sleep on the world map (`sleep.py`, the bed in the kit) rather
    than at home; no multi-day grinds at home (run 18's wall mining was G10's, now done). For a long
    stay, park the residents who add nothing in the hearth stone (4 slots, #572; never Loytel: +2
    admin) and recall them before leaving.
  - **Dishes leave shared reach when I leave and come back when I arrive** (built run 19):
    `leave.py` makes the Dishes box private (`dishes.py unshare`), `arrive.py` shares it again first
    thing. The Dishes box is the small fridge in the Kitchen (68,59, G15): powered, nothing in it rots
    (2 roasts unrotted after 8.7 days). No other shared box may hold prepared food. **The party pets
    eat from it too** (run 19: 7 dishes in an hour): stock it for the residents, and put a dish meant
    to wait for a trip in only after it is private.
  - **Fresh farm food goes in the fridge too** (the user, run 20: "shouldn't we put food in the
    fridge?"; ~60 stacks had rotted in the harvest box and the pantry): `springday`'s store_food puts
    the round's crops there first (residents eat only prepared food, so raw crops are safe in it) and
    grain plus the overflow in the harvest box; `cookdishes` cooks from both, and collects its dishes
    from the Cooler Box when the pack is full. Raw white and red mushrooms stay out of salads.
  - **The ★Storage Chest (47,58, the Workshop's middle row)**: Ashland's 100-slot fireproof gift,
    the library's and the spares' overflow (home.STORAGE_CHEST; no rename). **Samata the healer**
    (hired run 20, a resident) sells cure potions at home and has "I need healing". A resident hired from
    the Recruit tab joins the party only with CHA >= its best attribute (Samata needs 43; mine 19);
    pets don't need it: read the rule before paying the gold bars.
  - **Treasure maps go in the shared Maps box (55,56)**, distribution off: Poppy's Treasure Hunt
    turns one into a mystic treasure chest (run 19: two in ~36 days, ~3,860 orens, 3 gold bars,
    3 Small Medals, a Godly breastplate). The chest drops by Poppy (no shared box takes it);
    `yardchests.py` (in arrive.py since run 43: seven lay in the yard, because this line claimed a pick-up no tool did) opens and empties each. **She locks them too** (16-31): keep the lockpick stocked.

## 7. Days at home (elin-home-loop, folded in after run 12)

**A day:** `springday.py 1 UNTIL --once` after 06:00: mushrooms reaped and cut, ripe crops reaped
(seeds) or harvested (food), stubs cut, every bare cell replanted from the Farm box, the field
watered (refilling at the lake; only dry cells), a meal, then return. **Rain waters the field**
(the user's rule, run 15: "raining means you don't need to water plants... everything is already
wet"; Zone.RainWater marks every unroofed field cell watered): with no dry field cell the round
skips the can entirely (`farmday.dry_cells`). **Food threshold** (the user, run 15: "we need a
threshold for farming, right now we have a lot of mushrooms and food"): the harvest box held 92
rotten mushrooms and ~20 other rotten stacks on 486-08-22, because Delegated Farming and the cut
cells bring far more than the 2-3 a day I eat. Each round (`springday.surplus`) sends rotten food
there to the trash can and ships fresh farm food above `FOOD_KEEP` (30 items) while it still sells;
the surplus becomes rations once the ration maker exists (G14). Seeds need no cap: the reaped
mushroom seeds go straight back into the field. Never a loop that waits (the
user, runs 05 and 11): fill the rest of the day with crafting, tilling, hunting beside home, or a
trip, and sleep when sleepy. `sleep.py` refuses at hunger 50+: eat first.

**Exp (G10):** character exp comes from skill level-ups only (10-14 each), not kills. **Best (run
14): a low weapon skill on the dummy** with `tools/trainday.py` (a hit pays clamp((20 - skill)/2, 1,
10), so a never-used weapon earns ~9x the Long Sword: staff, unarmed, the Putit (`--throw`), a spear:
~380 exp a real hour, Lv13 -> 15). Also: new skills (buy every useful unlearned one at a trainer, 5
platinum, before upgrades: the user's rule), tilling new field cells (+41 in run 12), first crafts,
nefia fights. The Long Sword (18) on the dummy gives ~nothing (run 12's measure). **Run 16: the bow at the dummy**
(`trainday.py --shoot "forest long bow"`: Bow and Marksman, both new, +28 exp a bar of SP) with home-made
arrows, and **lockpicking at the practice chest** (61,46; the user's tip) between bars: Lv16 186 -> Lv17
419 over the run. When the branches run out, trainday falls back to the staff in melee (~9 a day).
Every level gives a feat point (I pick: Lonely Soul at Lv11, Lv12; Party Animal at Lv17 for the
follower plan).

**The home board** carries story quests (☆) and residents' jobs, +1 karma each, with the next
story quest a day later; check it on every return. A reward drops on my cell; on the board's cell
(54,50) step off and back on to pick it up.

**Food:** the farm (section 2's field; tomatoes and imo for food, mushrooms for seeds and food),
the bonfire 65,59 in the Kitchen (weed stew from 5 grass, meat on the bone from corpses, roasted
fruit; it burns a branch from the pack), fishing from 48,41 (bait from offal or mushrooms), animals beside home
(pigs, ducks, goats: corpses, and skins 1 in 10). Keep 3+ days in the Cooler Box; buy in Mysilia
only when the farm can't cover a trip.

**Platinum before a craft push** (the user, 2026-11-06: "you should enhance the skills so they level easier"; fact #1296): a trainer's +10 potential is
temporary and wears down with each level-up of that skill, so train it right before the crafts, not months ahead: under skill 10, +200 costs 30 platinum and
cuts the SP to a level by about 40% at first. Ceroyon (Olvina) and Frealord (Palmia) train the craft skills; the coins must be carried. `bridge.py skills` prints `pot`. `trainpot.py NAME=POT ...` clicks a trainer's open list up to a potential.

**A craft push (G48, run 42):** `craftrun.py STATION:RECIPE[:USE] ...` crafts a list one by one and carries each made thing to the shipping chest (the yard's wagon when it's full); `craftcycle.py` repeats the cheapest recipes with meals and sleeps until Blacksmith and Carpentry reach their targets. Materials bind, not SP: the sawmill pays 18 exp a SP at Carpentry 6 and a desk ~10 at 8, but all 277 planks and ~120 logs went on Carpentry 6 -> 10; bolts from scrap pay 12 a SP at Blacksmith 4. The carpenter's Scrap (1 log, 4 SP) pays Carpentry and makes the Blacksmith's scrap. A recipe's variants each count as a first craft (a second Signpost pays its own ticket): `firstcraft.py STATION --craft`, standing by the station. The smelter stops with "not enough fuel" unless logs ride in the pack. Wood: `woodrun.py` on a forest tile (a log and two branches a tree, 44 logs in 7 real minutes beside home); scrap: a Machinarium's metal walls by `wallmine.py`, or runs/jobs/wood.txt and scrap.txt with a target make the ladder gather on its floors. The carpenter's Scrap (1 log, 4 SP) then pays most Carpentry a log.

**Big containers (G47, run 42):** `freecells.py` maps the free floor. A wagon is 2x2 and stands outdoors; carrying one is what's dangerous: a zone change at burden phase 3 can tumble you for MaxHP x burden% / 200 (269 -> 57 at 161%), so stay under 150% (a wagon's 80 weight with the bags left home) and let the tools refuse. `boxshift.py FX,FZ TX,TZ --contents` empties a box into a big one in about a minute; then repoint `tools/home.py` and ship the empty box. `move.grab` takes the first thing on a cell: check a cell with two things first (run 42 shipped a wall torch).

**Fewer, bigger boxes (G54, the user 2026-11-08):** "Worth selling off more of the cardboard boxes and other random containers and consolidating them down." **Count by hand** (the user: "you may need to hand count the boxes and do a full sweep to check inventory"): the bridge's stock op reports a ★Storage Chest as 96 slots whatever its wrenches (fact #1014; the yard chest holds 276), so the real count walks and opens each container once and writes down its kind, size and contents. Retire the small ones (mystic chests 15, packages 20, wooden boxes 24) into ★Storage Chests with wrenches (Miral: 20 + 4 medals each) or a big wagon (Nino, 79 bars), `boxshift.py` for the contents, then update every route in home.py and packcheck before the box goes (run 44: a route of full boxes left four items unmoved while the big chest sat off it). Keep the fridges, the Dishes box, the armory, the office boxes and the collectibles shelf.

**Income at home:** first-time crafts pay old tickets (`firstcraft.py STATION [--craft]`; 114 orens
each in Mysilia); ☆ gear and valuables ship for more than a shop pays and each one also feeds the
hearth (level 2); home board supply jobs.

**Stations draw from every box** on the map, one stack per slot, the first big enough: keep each
material in one stack in one box (`box.py` moves it), and never leave a reserved stack within
reach of a recipe that could spend it. `gather.py OBJ ITEM N` holds the right tool, skips edges
and unripe crops, stops on "too difficult"; rocks outside the zone's bounds can't be mined.

## What this skill changed

New in run 04; the town in runs 11-18 (G12). Measure: errors.csv repeats in the elin-home domain
and the orens per real hour of home time (stats.csv). Baseline runs 12-20: 7 errors, 3 repeats
(a kitten, a substring dump, two containers open), one resident starved, one death in a home loop;
home time earned ~0 orens an hour. Latest: the loops stop at Hungry 70 and on a failed meal
(`common.ready`), sleep.py refuses at home without `--home-ok`, the dishes go private when I leave.
