---
name: elin-build
description: Gathering, crafting and placing in Elin - what each plant, tree and rock drops, workbench and Quick Craft recipes with costs, and the procedure to build the first grass house with a door and bed. Use when gathering materials, crafting at a station, placing furniture, walls or doors, or doing Way of Crafter.
---

# Gather, craft, place

## What drops what (observed, EA 23.355)

| Source | Tool | Drops |
|---|---|---|
| weed | any held tool at range, or bare hands adjacent | 1-4 tufts of grass + a leaf |
| vine bush | right-click Collect (needs a path to it) | 1-3 vines; **the bush is destroyed** (run 09, three bushes) |
| field cell (tilled floor) | shovel Dig | 1 chunk of soil a dig and the cell stays a field: endless soil, Digging exp (run 09) |
| grass floor | shovel Dig | a tuft of grass; the floor turns to soil, which can't be dug again |
| shell (beach) | by hand, adjacent | a bone fragment (glass at the kiln) |
| cactus (beach) | by hand | a bone needle; ripe ones a fruit and a seed (`needles.py`) |
| palulu tree (beach) | axe | a big leaf, palulu logs, a branch |
| salt rock / big rock | pickaxe | 1-4 ores by the zone's danger (steel never below danger 5: G18); the iron pickaxe at Mining 30 opens them (run 20; too hard for granite at Mining 5-10, run 09) |
| mature tree (cedar, birch) | axe | 2-3 logs, bark, resin; the tree falls |
| young tree (fir seen) | axe | 2 branches; the tree goes (a putit may drop out) |
| flowers | hammer | flower, leaf, seed (wiki) |
| stone / big rock | pickaxe (wiki) | stone |

Find with `find.py weed` / `find.py "vine bush"` / `find.py tree`; gather with
`harvest.py DX DZ` while holding the axe. Measured on a new character: a tree about 1 SP, a weed about 0.5 on average (some free), so count them when SP is short.

## Recipes seen (cost, SP)

- Quick Craft (ability): Workbench = 2 logs (5 SP); Bonfire; Bandage; Sleeping bag; Bait;
  Makeshift arrow; Flower crown.
- Workbench: Grass wall = grass + leaf (0 SP); Grass door = grass + log (2); Grass floor = grass;
  String = 2 vines (2); Torch = branch + string + 2 resin (3); Makeshift bed = 2 grass + 4
  leaves (4); Sawmill = 3 logs + 3 stones; Fishing rod; Carpenter's table; Tinker's table.

- Sawmill (3 logs + 3 stones; granite stones come from small "a stone" objects, not pebbles):
  its act is "Saw"; with it open, `item.py "rosewood log" Saw` turns the WHOLE stack into planks
  (1 log -> 2 planks) and branches into sticks.
- Carpenter's table (4 planks of one wood + 2 stones): Wooden weapon = 2 logs + string + 2
  sticks (gave a rosewood short sword 2d4, 3 SP); Buckler = 6 planks + string (4 SP); Pair of
  shoes = 3 grass + 4 bark + 2 strings (3 SP); also Sling, Wooden bow (2 bones), Boomerang,
  Cane, light gloves (needles), boxes, chairs, doors. A "rune" slot is optional ("Extra").
- Bonfire: Meat on the bone (corpse, 2 SP), Roasted fruit (cacti too: 14 each), Weed stew (5 grass
  + herb), Roasted marshmallow (a fresh marshmallow from a marshmallow monster).
- **Converters** (stonecutter, sawmill, kiln, spinner, butcher's tool): open the station's act (Cut,
  Saw, Bake, Spin), then `bridge.py buttons --all` and `bridge.py drag PACK_SLOT ING1` (stocked box
  items can't be dragged: take them into the pack first). The drag starts a task (AI_UseCrafter):
  **keep the window open until the task ends**, then close; the whole stack converts in one go
  (run 10: 8 wool fiber -> 8 threads). Closing at once hands the input back (run 09's "one at a
  time, the rest later" was this).
  Stonecutter: rock -> 2 cut stone. Kiln: fragment -> 2 glass, sand chunk -> fragment, clay -> 2
  bricks, log -> charcoal; it **needs fuel first** (gauge 0%): Refuel opens a second grid, and its
  ing1 is the one listed without the Refuel buttons (2-5 logs fill it). Spinner: fiber -> thread.
- **The hammer breaks things into materials** (run 13, TaskHarvest): an installed thing becomes its
  first ingredient (~91% for one item, a whole stack at once) when its material hardness + 1 is at
  most the hammer's hardness + 1.5 x handicraft (copper hammer 34: copper, granite, silver yes; iron
  56 no). Scrap comes from junk this way (`scrap.py`: empty cans, research equipment, toasters, pots,
  junk tools; Moyer at Tinker's Camp sells junk), from iron scrap wrecks (1-3), and from fishing junk.
- **One stack per ingredient slot, split by material**: 5 scraps meant 5 iron scraps in one stack; 5
  textures must be one stack (run 13). Never merge stacks by `bridge.py drag` (3 textures vanished).
- **Weapons can't be crafted** (no station, not Quick Craft): a dagger-class blade for the butcher's
  tool is bought (Diefon, Mysilia: ~435) or found. `kb.py make` saying "no station listed" means this.
- **Butcher's tool** (tinker's table: 3 textiles + a dagger-class blade): `butcher.py` runs every
  corpse in the pack and the Cooler Box through it (a skin, fang, heart, offal or bone, 20% each).
  A skin goes to 2-3 hide fiber the same way (spinner -> thread, loom -> texture).
- Drafting table (run 09): Kiln = 20 soil + 10 cut stone (one stack each: 5 stones of one kind cut
  to 10); Spinner = 6 planks + 4 tight ropes + 4 glass + 5 needles; Loom = 4 planks + 2 tight ropes
  + 6 needles (recipe from Nino, 3 gold bars). Tight rope = workbench: string + big leaf.
- Loom: texture = 2 threads (8 SP); backpack = 5 textures (one stack, so one thread material) +
  tight rope + 4 skins + 2 bolts (13 SP, 35 slots; **made 486-03-11 from wool**, run 10); pouch = 3
  textures + string + skin (20 slots, books and scrolls). Workbench: string = 2 vines or 2 threads.
- **Fiber by shearing (run 10)**: hold the shears, right-click a furry creature ("Shear(Newly
  grown)"), 1 SP, +1 affinity; `shear.py [R]` does every one in view, `shearwalk.py` walks a map.
  Race fur (races.json): sheep/goat/alpaca/pig/cow/horse/sea lion wool, rabbit/squirrel cashmere,
  dodo/raccoon/bear hide, caterpillar/beetle silk, spider spider silk; dogs like Poppy none. Wild
  ones give 1-2 once per zone visit; Lv11+ animals give "+1" fiber that won't stack with plain.
- Tinker's table: Pair of shears = 2 stones + stick + string; shearing a snow putit gives cashmere
  fiber (1-2 at short fur, 12-17 at full fur; shearing resets it). **Shovel and pickaxe** are the same recipe shape (run 55
  remade both, a granite shovel and a slate pickaxe, after thieves took the old ones): the stick from the sawmill's Saw on
  a branch (`convert.py DX DZ Saw` beside the sawmill 47,56; Quick Craft has no stick, fact #192), the string at the
  workbench from 2 threads of **one** stack (two wool-thread stacks failed: spin 4 hide fibers into one stack,
  `convert.py DX DZ Spin` beside the spinner), then `craft.py` at the tinker's table with `--use` naming the stones. The butcher's tool is above.

Gear path from nothing (run 03, about 1.5 game days): stones -> sawmill -> planks ->
carpenter's table -> buckler, sword, shoes. Station row used: workbench, sawmill and
carpenter's table stacked along one line next to the hearth.

`craft.py DX DZ "Recipe" N --dry [--use MATERIAL]` shows needs and SP first; `--use` picks a
material stack (a slot takes one stack only, so mixed woods don't add up). The station's Craft act needs an
adjacent cell, and you must not be holding anything. A crafted item lands in your hand; put
it away (`acts 0 0 all` -> Put away) before using a station again.

## Placing

Hold the item (`item.py NAME Grab`), then `acts DX DZ right` -> Place. Rules learned:
- **A door goes on a wall cell.** Build the wall first, then place the door on it.
- A party member standing on the target blocks Place; the game shoves/kicks them aside for walls.
- Out-of-sight cells (night, behind new walls) offer nothing: move closer.
- If Place runs but nothing appears, check `look.py` actCount.

## Make it look right, not just count (the user's standing rule)

A build is done when it passes the game's check **and** looks deliberate: walls face along
their line, corners join at posts, nothing sticks out, the door sits centered on a face.

Walls are panels with a facing, `blockDir` (see `bridge.py cell DX DZ`): 0 = panel along the
x axis, 1 = panel along the z axis, 2 = corner piece. Every wall is placed as 0, so a fresh
build is always wrong on its z-axis sides. The corner piece is an L whose arms point to -x
and +z: it fits exactly only where the neighbouring walls are at x-1 and z+1.

For a rectangle spanning x0..x1, z0..z1 (screen: +x down-right, +z up-right), verified on
run 03's 4x3 hut:
- rows (z0 and z1, between the corners): 0; columns (x0 and x1, between the corners): 1
- front corner (x1, z0): 2, an exact fit
- left corner (x0, z0): 1, because 2 leaves a slab poking out to the left
- right corner (x1, z1): 2; back corner (x0, z1): 2 (posts meet; a notch shows above the roof)

Set facings with `tools/rotate.py DIR X,Z ...` while holding a spare wall (each rotation
steps 0 -> 1 -> 2 -> 0; wrapping past 2 toggles crossWall, so cycle a full turn to reset it).
Then **look**: `tools/view.py VX,VZ TX,TZ name` from 4-5 cells down-left of the building
(walls next to the player render cut away) and read the PNG. Fix anything odd before
reporting the build.

## Rebuild and beautify (run 31, G30)

- **Swapping walls:** the game won't place a wall onto a wall (the cell offers only "Rotate block"). `tools/rewall.py
  "plank walls" X,Z ...` notes each wall's blockDir, mines it with the pickaxe (own land: no crime), places the new wall
  and rotates it to the old facing. Plank walls come from the wall workshop (1 plank, 0 SP). A door cell is a wall with
  a door on it: lift the door from OUTSIDE (from inside it walls you in), swap the wall, then place the door.
- **Floors:** the flooring workshop (workbench: 2 planks + 2 cut stone + a tight rope; a tight rope is a string + a big
  leaf) lays a plank floor for 1 plank and 0 SP, under beds and stations too. `tools/floor.py ROOM` fills a room's
  cells; use each house's own wood (oak, cedar, rosewood). A log saws into 2 planks (1 SP); take a log stack only
  while it keeps the burden under phase 3 (box.py puts it back otherwise).
- **Paths:** stone road needs a recipe and stone floor costs 4 SP a cell; the **stepping stone** (1 stone, 1 SP, an
  obj that stays walkable) is the affordable stone path. `tools/paths.py` lays the breadth-first network.
- **Fire lights:** a wall torch (branch + string + resin at the workbench, ~2 SP) mounts from a floor cell beside a
  wall (`place.py "wall torches" X,Z --height 7`); string comes from 2 threads (the spinner turns fiber into thread at
  ~1 SP each). A watch fire is 2 logs + resin.
- **Wood:** mature trees on nefia floors give 3 logs each, wrecks oak logs; the forest field next to home and many nefia
  trees are saplings (a branch and a leaf).

## First house (Way of Crafter)

1. Chop one cedar (logs, resin), Quick Craft a **workbench**, place it near the hearth. Report.
2. Two vines -> **string**; a young tree -> **branch**; a second mature tree -> 2nd **resin**.
   Craft the **torch**, `item.py torch Equip`. Report.
3. Gather 14 leaves and about 14 grass (`gather.py weed leaf 14`): 10 walls + door + bed.
   Craft 11 grass walls (one spare to rotate with), a door and a makeshift bed.
   A 2x1 room needs a 4x3 ring = 10 cells (`place.py "grass wall" X,Z ...`): west side from
   outside, step in, the rest plus the bed from inside, step out, wall the doorway cell, then
   `place.py "grass door"` onto that wall (centered on the face toward camp).
4. Set the wall facings and check the look (section above). Then report to Ashland: house
   plate + room plate. Residents claim beds ("a makeshift bed for Loytel"): make a second
   bed for yourself.
