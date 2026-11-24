---
name: elin-home
description: Keeping the home base in Elin organized, clean and safe (run 04, the user's request) - the routine on every return home (arrive.py, packcheck.py --move, the books, the box tally, stock.py --ship), where everything lives (the town's houses, the yard chest and the big wagons, from tools/home.py), the fewer-bigger-boxes rule (G54), what to keep, ship or sell and the stock caps, carried storage, placing furniture, the open projects, home safety and feeding the residents, craft pushes, and an old reference for the farm, spring and training day loops. Use on every return home, at session start for the box tally, and whenever storage, junk, furniture, residents or the base layout comes up.
---

# Home: organized, clean, nicer, safer

This skill is the place itself: where things live, what goes, what's being built. The user's aim (run 04): less junk,
organized stuff, clear rules for what to sell and what to keep, a nicer and safer place to live. Since run 45 (G54):
**fewer, bigger boxes**. The kit and the triage of the pack are **elin-pack**; guild books and decoding **elin-guilds**.

## 1. On every return home (in this order)

**`tools/arrive.py` runs the scripted part in one go (run 19):** a hostile in view or low HP stops it first; then the
Dishes box shared, a drained attribute or harmful mutation cured (run 35), `packcheck.py --move`, the mail
(`unpack.py --take --pickup`: each package emptied into the pack and grabbed, the spam packages shipped, run 45; a tax
bill there is paid, run 35), `yardchests.py` (Poppy's chests lying loose, run 43), `trash.py`, `town.py`, and a food
line. Every step runs `farmday.home_guard` first (section 6). **Since run 58 (G70 done):** Samata buys first (`sell.py --excess`; no shop at
some hours: the step says so), chests emptied by uid, a nefia map read, a closing pass with `shipstar.py`; its last line is the measure (0 out of place).

0. **`packcheck.py --move` is the sort** (the user, run 11: "on entering base you organize your packs... when leaving
   base you must clean your packs of useless inventory... it is a loss of treasure by not having those slots free"). It
   checks the pack, the bags and the Cooler Box against the trip kit and carries every other item to its box by the
   routes in section 2; junk goes to the trash can; **anything without a rule is reported and left in place, never
   shipped** (run 12: the old ship-by-default sold the ☆Forest Necklace). Unidentified gear stays in the pack for
   Appraising. **`leave.py` refuses to leave home** until `packcheck.py` reports 0 out of place (`--pack-ok` only for a
   deliberate haul). Read its whole output: a refused move names a full chain (section 2, rule 2).
1. `look.py`: hostiles wander in (home is danger 5 since run 15's Border Watch: a Lv12 killer squirrel came at danger 7
   in run 14; run 41: an orc warrior Lv11 and a scorpion Lv7). Shoot or fight them first (`shoot.py`, `fight.py`), from
   range for anything at or above my level.
2. **Books and recipes on every return:** `decode.py --fetch`, `readskills.py`, and `readrecipes.py [--known]` (run 41,
   the user: "Why don't you read the recipes you have available to you?": 101 lay in 12 boxes, 37 never learned, because
   a skill said to read them and no tool did; a new one opens a first craft worth an old ticket and skill exp, and every
   read frees a box slot). `chests.py` for any mystic chest in the pack. Read `gearcheck.py` before `shipstar.py`
   (elin-pack 3, elin-gear).
3. **Tally the boxes by kind before planning or buying** (the user, run 40; at session start too): `stock.py` prints the
   caps table and what is over it across the pack, the bags and every home box; `stock.py --find TEXT` finds any stack
   with its place. **Its ENCHANT rows are read at once** (run 56, after runs 52, 55 and 56 each found enchant scrolls
   riding or boxed while worn pieces sat under the cap): an enchant scroll is listed there while a worn piece of its kind is
   under that scroll's cap (plain +2, `*great*` +4, +1 blessed), read with `picker.py "SCROLL" Read PIECE`, lowest plus
   first, the body's first among equals (it gives the most PV a plus). Then **`stock.py --ship [N]`** carries the excess to the shipping chest box by box (the chest takes 40
   stacks a morning, fact #1001; it pays out each morning, more than a shop, and adds gold bars by volume). One bridge
   client at a time: nothing else beside it (run 45: 4 of 36 shipped when I walked to the loom).
4. **Garbage goes to the trash can, never the chest** (the user, run 08): `trash.py` (in arrive.py) walks every garbage
   pile, then drags each garbage, rotten-food, bottle and can stack into the trash can 58,51 for Ecopo; the chest pays 0
   for it. Residents drop garbage every day (run 08: ~50 piles after a month away).
5. **What packcheck left:** a "no rule" item is a decision (wear it, read it, ship it by hand with
   `box.py "shipping chest" ITEM`), and its kind gets a route in packcheck the same session. One item out of a box:
   `box.py WHERE --take ITEM`. Loose things on the map: `find.py` (rule 3).
6. Leave: sleep on the world-map tile (`sleep.py`), not at home (section 6: time at home costs the residents' food;
   `sleep.py` refuses on the home map without `--home-ok`).

## 2. Where everything lives (world_4, Meadow; the town built in run 18, the big containers in runs 42-45)

Every coordinate lives in `tools/home.py`; the tools read it from there, and this table is written from it (last: after
run 45's G54). `tools/town.py` checks the town against the game's own rooms (G12).

| Place (walls, door) | Stations | Containers (home.py name, cell: what it holds) |
|---|---|---|
| **Workshop** (oak plank 46-56 x 55-61, door 51,55) | back row z=60: loom 47, wall workshop 48, spinner 49, drafting table 51, signboard workshop 52, mason's table 53, stonecutter 54, tinker's table 55 (the newer one at 54,58 has a reachable side, run 37); front row z=56: sawmill 47, workbench 49, carpenter's table 50; the Gene Machine 54,59 | WOOD_BOX 48,57: logs, planks, branches, sticks, bark, resin, spare walls and room boards; PARTS_BOX 53,56 ('Parts'): bones, nails, batteries, microchips, scrap, fangs; MAPS_BOX 55,56 (**shared**, distribution off): treasure maps for Poppy, nothing else; **BAG_PARTS[0] 48,59** (the box still named 'Armory 2', private; G56 M2, run 48): threads, fiber, textures, ropes, beside the loom and spinner; **STONE_BOX_2 52,58 ('Stone 2'; G56 M2)**: stone, cut stone, bricks, beside the stonecutter and the mason's table |
| **Forge** (granite 58-62 x 55-61, door 60,55) | kiln 59,60, smelter 60,60, blacksmith's table 61,60 | STONE_BOX 61,57 ('Stone and ore'): ores, ingots, glass, sand, clay, soil, pebbles (stone and cut stone go to 'Stone 2' in the Workshop since G56 M2) |
| **Kitchen** (oak plank 64-69 x 55-60, door 66,55) | bonfire 65,59 (cook from 65,58), the cutting board 68,58 (the millstone and ration maker moved to the Farmhouse, G56 M2) | PANTRY 68,57 and PANTRY_3 65,57: oils, herbs, drinks, condiments; DISH_BOX 68,59, the small fridge 'Dishes' (**shared at home, private away**, food, priority 1, nothing rots): the residents' dishes |
| **Farmhouse** (cedar plank 57-61 x 40-45, door 57,43) | the millstone 58,44 and the ration maker 60,42 beside the grain (G56 M2, run 48; ration.py stands at 59,43); the farm sign 51,47 and the field outside | HARVEST_BOX 60,44 (shared, food, priority 10: grain and seasonings); HARVEST_FRIDGE 60,43 (shared, food, priority 20: Delegated Farming's crops land where they don't rot, run 33); FODDER_BOX 60,41 (shared: grass, leaves); FARM_BOX2 59,41 (seeds when the Farm box is full) |
| **Storehouse** (rosewood plank 63-69 x 37-42, door 66,42) | | LIBRARY 67,40 ('Library 5') and the BOOKSHELF 65,38 (the library's tail); the valuables shelf 68,39; COLLECTIBLES 68,40 (display shelf: cards, figures) |
| **Depot** (oak plank 41-46 x 45-52, door 46,49; Private; G28, run 30) | | sturdy boxes (35 slots) along x=42: FARM_BOX 42,46 'Farm' (every seed and farm tool), SPARES2 42,47, LIBRARY 42,48 'Library 3', VALUABLES 42,49 'Valuables 7' (decorations too), ARMORY3 42,50, PANTRY_2 42,51; along x=44: valuables 44,47 and 44,49, LIBRARY 44,48 'Library 6', SPARES4 44,50 |
| **The east yard** (north of the Storehouse; G47, run 42; inside G56's storage quarter 51-71 x 35-47, home.STORAGE_QUARTER) | | **the two moved ★Storage Chests (G56 M1, run 48): STORAGE_CHEST 64,46 (Ashland's, fireproof, no rename: the library's and the spares' overflow) and STORAGE_CHEST_2 63,46 (`rebalance.py`'s overflow)**; a magic chest carries its contents weightless (grabbed with 240 stacks at burden phase 0, so `move.py` moves it whole); Nino's wagons (60 slots, 2x2): 66,46 and 69,46 (valuables: coins, bars, platinum, medals, tickets, genes, gems), 70,44 (ARMORY5: gear when the armory boxes are full); **the yard chest 68,44** (the third ★Storage Chest, Miral's, 9 wrenches since run 44: 280 slots by its window): spares (potions, scrolls, rods), the library's tail, and the last stop of every chain |
| **The big wagons** (south-west of the Storehouse; G54, run 45; 96 slots each on 4x4 cells) | | BIG_WAGONS[0] 54,38 (cells x 51-54, z 38-41): the overflow and valuables of the five retired mystic chests, books; BIG_WAGONS[1] 58,35 (cells x 55-58, z 35-38): the armory overflow, the bag parts (threads, fiber, strings, ropes, skins, bolts), the valuables overflow, and the second-last stop of every chain. **Run 48: both lay uninstalled all run** ("Pick (a big wagon)", no Open act: every route through them refused); `town.py --storage` fails on a loose container now; the fix is pickup.py and place.py on the same anchor (Squashed for a moment, no walk) |
| **Residence** (grass rooms: mine 59-62 x 51-53, door 60,51; the residents' 62-68 x 49-53, door 65,49) | | ARMORY 66,51 (shared, priority 5, weapons and armour: residents take what beats theirs); my pine bed 60,52 |

Outside on purpose (the office, since G56 M3 in run 49): mail post 62,47, tax chest 63,47, house board 58,48, the labelled
mail package 60,50 (no Grab), shipping chest 56,52 (empties every morning; it takes anything, valued or not, so a refusal means it is full for the day, ~40 stacks, and a container ships only when it is empty: the user, run 50, fact #1479), trash can 58,51, the home, quest and resident
boards 54,50-52, the hearth stone 55,50, Fiama's lock-50 quest chest 54,50, the dummy 60,46 and practice chest 61,46; the
sitting corner 55-57 x 48-49 (G56 B, run 50). **The field is 49-53 x 43-49, 33 cells under two farm signs (51,47 and 51,43)**
(G56 M4, run 50; home.FIELD); its edge cells and the old dig scars are lawn floor. The lake (stand at 48,41) stays unroofed;
the four graves of Rolord stand in a row at 43-46 x 43 by it (G56 C). **Flower beds by all seven houses' doors** (yellow
flowers from Gikrak's seeds, Yowyn; `town.py --garden` checks them): they are seed crops, so winter (months 12-2) likely
takes them, as run 32's went; 3 spare seeds wait in the Farm box for a spring replant (hold the seed, `act.py DX DZ Plant right`
on grass beside the door: farm.py plants field cells only).

**Floors without a shovel (run 50, facts #1457-#1458):** a floor item laid on a cell replaces its floor, crops included:
lawn floor (flooring workshop, 1 tuft of grass, 0 SP) turns a tilled cell or a bare-soil scar into lawn; soil floor (1 tuft of
soil) on grass, then the hoe's Plow, makes a field cell. Grass comes from wild weeds on nefia floors (`runs/jobs/gather.txt`
"weed grass N" makes the ladder cut them; every weed at home is an edge cell). **Storage wrenches** (Miral, 4 medals each, +20
slots): held (`item.py "wrenches" Grab`), then `act.py DX DZ Upgrade right` beside a ★Storage Chest, one per wrench; run 50 put
five on 64,46 and five on 63,46.

**Where a kind goes** (packcheck's ROUTES, first match wins; each chain is tried in order): seeds and farm tools -> the
Farm box, Farm box 2; wood and building parts -> the wood box; stone, ore, ingots, glass -> the two stone boxes; treasure
maps -> the Maps box only; threads, fiber, skins, bolts -> the second big wagon, the wagon 70,44, the yard chest; bones,
nails, scrap, parts -> the Parts box, 70,44, the big wagons, the yard chest; leaves and grass -> the fodder box; potions,
scrolls, rods -> the yard chest, Spares 2, Spares 4, the Storage Chest, the first big wagon; coins, bars, medals, tickets,
figures, cards, genes, gems -> the valuables boxes, the Storage Chest, the big wagons, the yard chest; books, recipes,
letters -> the library chain; condiments and drinks -> the pantries, then the yard's wagons; ration grain -> the harvest
box; organs, fresh corpses, graves and listed odd loot -> the shipping chest; plans -> read now; garbage -> the trash
can. **Since run 45 every box chain ends at the second big wagon and the yard chest** (`packcheck._with_big_tail`).

**Rules**
1. **One theme a container, inside its house.** Rename each box by its theme (`bridge.py boxcfg name=...` with it open).
2. **Fewer, bigger boxes (G54, the user, 2026-11-08):** a theme that fills gets a bigger container behind it, not
   another small box. Retire the small ones (mystic chests 15 slots, packages 20, wooden boxes 24) into ★Storage Chests
   with wrenches or a big wagon (section 7), and repoint every route in `home.py` and packcheck **before** the box goes
   (run 44: a route of full boxes left four items unmoved while the big chest sat off it). Keep the fridges, the Dishes
   box, the armory, the office boxes and the collectibles shelf. `rebalance.py [--dry]` moves the last stacks of every
   box at 90%+ into the second ★Storage Chest (run 31).
3. **Nothing lies loose.** Every return: `trash.py` (residents drop ~2 garbage a day), then the detritus pass: `find.py`
   loose things on the map (`bridge.py find` with an empty name lists everything; keep the not-installed ones) and put
   each away; `trash.py` misses piles it can't reach (48,46 behind a tree, run 11).
4. **No trees or bushes on field cells.** No harvestable tree is left inside the home's bounds 40-70 x 35-65: wood
   comes from field maps (`woodrun.py` on a forest tile).
5. **The pack is a carrier, not a store.** The spoils bag carries the kit's overflow; the loot bag is the haul.
6. **Moving a box or station:** `tools/move.py FX,FZ TX,TZ [NAME]` for an empty one; `tools/boxshift.py FX,FZ TX,TZ`
   for one with contents (empties it into the loot bag by Shift+click, moves it, refills it; `--contents` into a box
   already at the target, in light trips). Then update `tools/home.py` in the same session; packcheck, stock, town.py
   and the home loops read it. `move.grab` takes the first thing on a cell: check a cell with two things first (run 42
   shipped a wall torch).
7. **A count that includes what no route can reach flatters it** (run 45: 26 spam packages were 520 of the home's 861
   "free" slots): `boxcount.py` walks the ★Storage Chests and reads each window's "USED / SIZE" (the stock op reports
   one as 96 slots whatever its wrenches, fact #1014); report the slots a route can use.

**Building a house** (run 18; elin-build has the facing rules): wall workshop (Loytel's recipe):
plank wall = 1 plank, stone wall = 1 stone, both 0 SP; a sawmill makes 2 planks from a log for
1 SP. Clear the outline (a flower or bush under a wall is replaced; a bush inside can stay), place
the walls with `place.py` and **the door cell's wall last from a cell outside** (run 18 walled
itself into the Forge and mined its way out), the door on that wall, `rotate.py` the facings (hold
a spare wall; stand next to each side), a room board inside (placed from inside: cells behind new
walls offer no Place from outside), "Change name" with `bridge.py input NAME`, Access Type by
its context menu. Separate houses need a 1-cell gap or different room-board groups (0-4).


## 3. Keep, ship or sell

**The keep rule: sell unless used** (the user, 2026-11-21, setting G70 Smart Storage after run 56 ended with every route
full). Keep what a tool, a recipe in use, a goal or the trip kit needs, and one working stack of each crafting material;
everything else sells, ships or goes to the trash can. **Cards and figures sell too** (the user, approving the audit: "sell
the cards and figures. They just increase tourist value - unless they have another purpose?": the game tags them 'tourism'
only, no recipe takes one). The calls per kind are **`tools/keep.py`** (knowledge/storage-audit.md from `tools/audit.py`, approved 2026-11-21):
keep, caps (stock.py), sell, read, identify, gear (gearcheck.py first). Where this section and keep.py disagree, keep.py is newer.

**The outlets (G70 M3, run 57):**
- **Samata the healer at home buys anything** (fact #1586): `tools/sell.py Samata uid:N ... --find` (the resident board's
  Find walks me to her, the user's tip: fact #1587). She pays ~91% of the chest's price. **Her shop fills**: a sale is refused
  silently once her own container is full of what I sold; her window's **Restock (-1 Influence)** empties it, and sell.py
  presses it once before giving up.
- **arrive.py sells on every return**: what keep.py calls "sell" in the pack goes to Samata before packcheck files the rest.
- **The clear-out of the boxes:** `tools/clearout.py [--batches N]` takes keep.py's "sell" stacks out of the boxes a grid's
  worth at a time (the pack's own grid: move the kit's loose stacks into a bag first, packcheck --move restores them) and
  sells them. Gear waits for gearcheck.py; unidentified things for Aliyun.
- **The shipping chest** still pays the most (x1.1) for ☆ gear and stock.py's cap excess, ~40 stacks a morning.

**Trash can at once** (`trash.py`): garbage (burnable, unburnable), empty bottles and cans, rotten
food and offal: the can pays Ecopo, the chest 0 (the user, run 08).

**Ship at once** (chest): junk stones, granite "a tool", cursed or doomed items (never equip, read or wear
one: the user's warning; a cursed or gifted item can't be taken back off a pet),
things made only for their first-craft ticket (signs, plates, doors, furniture with no place),
dead furniture (the Defense Training gallows, 56 weight each: carry one at a time, two made me
Squashed), spare torches beyond one.

**Keep:** crafting materials (one stack each), gold bars, coins and medals, undecoded ancient books, potions, scrolls, rods
and spellbooks under stock.py's caps, food, seeds, tools, the kit, 2 old tickets (for a fortune drum), quest items (★),
treasure maps (Poppy).

**Stock caps (the user, run 27; `tools/stock.py`, run 28):** the pack, the bags and every home box count
together (bridge `stock` reads them all in one call). A spellbook of a spell at 100+ casts is excess; under it,
**read it** (`stock.py --read`: +3-9 casts a charge, Literacy exp, the book falls apart at 0 and frees the slot;
never a cursed one: x3 difficulty). Genes: superior ones stay, plain and inferior ones are excess (run 49: 246 gene stacks had filled the valuables chain; G38's crew is done). Rods: teleport and cure all, speed 2, every other kind 1 (the most charges);
hostile summons, strip blessing and empty rods none. Potions: heals all, debuffs none, the rest 5. Scrolls:
teleport all, return 8, evacuation 6, identify 10, levitate none (the Ether Wing). `stock.py` reports, then
`stock.py --ship` carries the excess to the shipping chest box by box. Run it on any visit where arrive.py
reports a full box.

**Never sell or ship anything unidentified** (the user: it loses value). **Identify, then decide:**
unidentified items ride along for Appraising (elin-pack 3); Aliyun the mage at Tinker's Camp (3
east, 5 north of home) identifies by the count (`kb.py facts Aliyun`). Spellbooks and rods first
(run 04: a tome was Cure Minor Wound, a rod was identify).

**Sell in town:** old tickets (114 orens each in Mysilia, keep 2). At home, Samata (above): any shop that trades for orens
buys any sellable item at ~91% of the chest's price, +2% a point of Negotiation (fact #1584); not the guest store of Open For
Business (the user, 2026-11-21). Farris is no longer a resident (run 57's board: Samata is the one shopkeeper).

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
| Storage room (**G70 Smart Storage** since 2026-11-21) | run 56: every route full (the shipping chest at 40, the armory, the yard chest): the audit and the keep rule first, then capacity where a kept theme still fills (wrenches, wagons) | run 36: every valuables box full again; the Depot's empty mystic chests (45,51; 44,46; 43,46) and 70,51 / 67,52 are `home.VALUABLES_OVERFLOW`, the bookshelf 65,38 is the library's tail; run 45 (G54): the five mystic chests retired into Nino's two big wagons south-west of the Storehouse (54,38 and 58,35, 96 slots each, 4x4 cells), which are the overflow now |

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

- **A long walk at home has stops too** (run 41: **two deaths at home in one night**: arrive.py's box walk from hunger
  70 to 93 and HP -3 with meals in the Cooler Box, then an orc warrior Lv11 and a scorpion Lv7 taking 263 -> -1 while
  the mover went box to box without a swing): `farmday.home_guard` runs before every step of arrive.py,
  `packcheck --move`, the trash sweep and boxcount.py, by the numbers in elin-play's table (a meal, a stop when no meal
  landed, a fight with what's at or under my level, the walk's HP floor). A tool's "no meal" is a stop for me as well:
  never start the next long job on it. (41)
- **Burden phase 3 at home squashes on every walk** (run 47: arrive.py's sweep and box walk took 352 -> 127):
  `farmday.home_guard` stops there now. Drop the heaviest bag on my own floor (`item.py BAG Drop`: the pouch of cans and
  ores was 111 weight), heal, then take its contents to the boxes. (47)
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

## 7. Crafting, containers and income at home

**The home board** carries story quests (☆) and residents' jobs, +1 karma each, with the next
story quest a day later; check it on every return. A reward drops on my cell; on the board's cell
(54,50) step off and back on to pick it up.

**Platinum before a craft push** (the user, 2026-11-06: "you should enhance the skills so they level easier"; fact #1296): a trainer's +10 potential is
temporary and wears down with each level-up of that skill, so train it right before the crafts, not months ahead: under skill 10, +200 costs 30 platinum and
cuts the SP to a level by about 40% at first. Ceroyon (Olvina) and Frealord (Palmia) train the craft skills; the coins must be carried. `bridge.py skills` prints `pot`. `trainpot.py NAME=POT ...` clicks a trainer's open list up to a potential.

**A craft push (G48, run 42):** `craftrun.py STATION:RECIPE[:USE] ...` crafts a list one by one and carries each made thing to the shipping chest (the yard's wagon when it's full); `craftcycle.py` repeats the cheapest recipes with meals and sleeps until Blacksmith and Carpentry reach their targets. Materials bind, not SP: the sawmill pays 18 exp a SP at Carpentry 6 and a desk ~10 at 8, but all 277 planks and ~120 logs went on Carpentry 6 -> 10; bolts from scrap pay 12 a SP at Blacksmith 4. The carpenter's Scrap (1 log, 4 SP) pays Carpentry and makes the Blacksmith's scrap. A recipe's variants each count as a first craft (a second Signpost pays its own ticket): `firstcraft.py STATION --craft`, standing by the station. The smelter stops with "not enough fuel" unless logs ride in the pack. Wood: `woodrun.py` on a forest tile (a log and two branches a tree, 44 logs in 7 real minutes beside home); scrap: a Machinarium's metal walls by `wallmine.py`, or runs/jobs/wood.txt and scrap.txt with a target make the ladder gather on its floors. The carpenter's Scrap (1 log, 4 SP) then pays most Carpentry a log.

**Big containers (G47, run 42):** `freecells.py` maps the free floor. A wagon is 2x2 and stands outdoors; carrying one is what's dangerous: a zone change at burden phase 3 can tumble you for MaxHP x burden% / 200 (269 -> 57 at 161%), so stay under 150% (a wagon's 80 weight with the bags left home) and let the tools refuse. `boxshift.py FX,FZ TX,TZ --contents` empties a box into a big one in about a minute; then repoint `tools/home.py` and ship the empty box. `move.grab` takes the first thing on a cell: check a cell with two things first (run 42 shipped a wall torch).

**Fewer, bigger boxes (G54, the user 2026-11-08):** "Worth selling off more of the cardboard boxes and other random containers and consolidating them down." **Count by hand** (the user: "you may need to hand count the boxes and do a full sweep to check inventory"): the bridge's stock op reports a ★Storage Chest as 96 slots whatever its wrenches (fact #1014; the yard chest holds 276), so the real count walks and opens each container once and writes down its kind, size and contents (`tools/boxcount.py`, run 45: only a ★Storage Chest's window shows "USED / SIZE"; every other kind's size is fixed and the stock op reads it right, so the tool walks only the Storage Chests unless `--walk-all`). **Mail-spam packages** pile up around the office (run 45: 26 of the 72 containers, one junk item each): arrive.py empties, grabs and ships them now. Retire the small ones (mystic chests 15, packages 20, wooden boxes 24) into ★Storage Chests with wrenches (Miral: 20 + 4 medals each) or a big wagon (Nino, 79 bars), `boxshift.py` for the contents, then update every route in home.py and packcheck before the box goes (run 44: a route of full boxes left four items unmoved while the big chest sat off it). Keep the fridges, the Dishes box, the armory, the office boxes and the collectibles shelf.

**Income at home:** first-time crafts pay old tickets (`firstcraft.py STATION [--craft]`; 114 orens
each in Mysilia); ☆ gear and valuables ship for more than a shop pays and each one also feeds the
hearth (level 2); home board supply jobs.

**Stations draw from every box** on the map, one stack per slot, the first big enough: keep each
material in one stack in one box (`box.py` moves it), and never leave a reserved stack within
reach of a recipe that could spend it. `gather.py OBJ ITEM N` holds the right tool, skips edges
and unripe crops, stops on "too difficult"; rocks outside the zone's bounds can't be mined.

**Converter grids run the whole stack as one task** (the butcher's tool, the spinner, the kiln: run 25): a dragged stack
of 124 fibers spins thread after thread until the stack or the stamina is gone, and item pickups show nothing until it
ends. Drag what the SP covers (~1 SP a thread, 6 a texture), watch SP not the AI state, and never close the grid early
(the open grid restarts the crafter; the bridge's stamina floor cancels it each time). `convert.py DX DZ ACT [--max N]
STACK...` checks each stack against SP. (25, 28)

## Reference: the day loops (old, check before trusting)

The farm, spring and training day loops carried runs 10-25; the run logs last name springday in run 31 and trainday in
run 37 (the circuit is the engine now, and under the run score a training day at home is a loss: lessons, Superseded). The tools still exist (`springday.py`, `farmday.py`, `trainday.py`, `train.py`, `minewalls.py`,
`cookdishes.py`, `ration.py`, `farm.py`, `water.py`, `reap.py`, `fish.py`, `lockpick.py`); their notes are in
knowledge/tool-notes.md. Before using one again, test its hunger stop and eat step by hand (run 18), and stop one
with `stopjob.py springday` only.

**Why the field stays** (the user, 2026-11-14): "Farming is only useful if our crops are particularly high quality which,
after many cycles, they are" (the seeds in the boxes run +13 to +24). The field is kept for that quality, not for
rations, which are bought (G14 dropped); G56 M4 (run 50) made it one rectangle under two farm signs, and the user called the
town good (G56 done 495-08-23).

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

**Exp:** elin-train (the dummy, trainers' potential, music, Quick Craft).

**Food:** the farm (section 2's field; tomatoes and imo for food, mushrooms for seeds and food),
the bonfire 65,59 in the Kitchen (weed stew from 5 grass, meat on the bone from corpses, roasted
fruit; it burns a branch from the pack), fishing from 48,41 (bait from offal or mushrooms), animals beside home
(pigs, ducks, goats: corpses, and skins 1 in 10). Keep 3+ days in the Cooler Box; buy in Mysilia
only when the farm can't cover a trip.

## What this skill changed

New in run 04; the town in runs 11-18 (G12); the big containers in runs 42-45 (G47, G54). Measure: errors.csv repeats
in the home domain, the orens per real hour of home time (stats.csv), and the free slots a route can reach
(`boxcount.py`). Enforced by tools: `common.ready` stops a loop at Hungry and on a failed meal, sleep.py refuses at
home without `--home-ok`, the dishes go private when I leave, `farmday.home_guard` guards every long walk (run 41),
and every packcheck chain ends at a big container (run 45). The review of 2026-11-11 rewrote sections 1-2 from `tools/home.py`.
