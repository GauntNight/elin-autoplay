"""The Meadow's coordinates (world_4) in one place: moving a box is one edit here (run 12 review:
55,44 and 56,51 were repeated in four scripts). The elin-home skill's section 2a is the map.

Boxes are (x, z); BOX_STR gives the "x,z" form box.py and packcheck.py take.

These are one game's coordinates. In a new game (tools/newgame.py, runs/no-base.txt) the home routines below refuse to run,
so none walks to boxes that don't exist there; tools that only borrow a helper from them (box, heal, ladder) still work.
Build the base (elin-home), put its cells here, delete the marker.
"""
import sys as _sys
from pathlib import Path as _Path

_ROUTINES = {"cookdishes", "dishes", "farmday", "lockpick", "minewalls", "packcheck", "paths", "ration", "readskills", "rebalance",
             "shipstar", "springday", "stock", "town", "trainday", "unpack", "water"}
if (_Path(_sys.argv[0] or "x").stem in _ROUTINES
        and (_Path(__file__).resolve().parent.parent / "runs" / "no-base.txt").exists()):
    _sys.exit("refused: this game has no base yet (runs/no-base.txt): tools/home.py still holds the last game's coordinates. "
              "Do this job by hand for now. Once the boxes exist, put their cells in tools/home.py and delete the marker.")

# Farm zone
FARM_BOX = (42, 46)        # run 30 (G28): the sturdy box 'Farm' (35 slots) in the Depot, beside the field; every seed, sickle, hoe, shovel,
                           # watering can, fishing rod (private). Was the 20-slot mail package at 58,44 in the Farmhouse (shipped)
HARVEST_BOX = (60, 44)     # run 18: in the Farmhouse; shared, food only, priority 10: Delegated Farming's crops land here
HARVEST_FRIDGE = (60, 43)  # run 33 (G3 M6, the user): Hill Cave's fridge (16 slots, 5 MW), shared, food, priority 20 over the
                           # harvest box's 10, so Delegated Farming's crops land where they don't rot; grain and seasonings stay in 60,44
FARM_SIGN = (51, 47)
FARM_SIGNS = [(51, 47), (51, 43)]  # run 50 (G56 M4): the spare sign from the Storehouse's doorstep (66,43) covers the south half
FIELD = [(x, z) for z in range(43, 50) for x in range(49, 54) if (x, z) not in FARM_SIGNS]  # run 50 (G56 M4): one 5x7
# rectangle 49-53 x 43-49 under the two signs, 33 field cells (was 48-54, 38 ragged cells); the six cells outside and the
# sign's own cell 51,43 are lawn floor (flooring workshop, 1 grass each: a floor laid over a tilled cell replaces it)
LAKE_STAND, LAKE_WATER = (48, 41), (47, 40)
PASTURE_SPOT = (57, 47)

# Kitchen
# The Kitchen: a plank house 64-69 x 55-60, door 66,55 (G12, run 18)
BONFIRE = (65, 59)
BONFIRE_STAND = (65, 58)   # craft at the bonfire from here: offset BONFIRE - BONFIRE_STAND
PANTRY = (68, 57)          # 'Pantry': oils, herbs, drinks, organs for jobs, spare food
PANTRY_2 = (42, 51)        # run 30 (G28): the sturdy box 'Pantry 2' in the Depot (was the mail package at 68,56, run 14)
DISH_BOX = (68, 59)        # run 19 (G15): the small fridge from Olvina (3 tickets), 'Dishes': food, priority 1,
                           # powered (5 of the home's 20; nothing in it rots while on). Cooked dishes for the
                           # residents (they eat only prepared food from shared boxes while I'm home; run 17);
                           # shared while I'm home, private while away (dishes.py, leave.py, arrive.py)
PANTRY_3 = (65, 57)        # run 19: the old Dishes box, now a private pantry (the fridge took its job)

# Workshop: a plank house 46-56 x 55-61, door 51,55 (G12, run 18); stations along the back wall
# z=60 and the front row z=56, boxes in the front row
STATIONS = {"loom": (47, 60), "wall workshop": (48, 60), "spinner": (49, 60), "drafting table": (51, 60),
            "signboard workshop": (52, 60), "mason's table": (53, 60), "stonecutter": (54, 60),
            "tinker's table": (55, 60), "carpenter's table": (50, 56), "sawmill": (47, 56), "workbench": (49, 56),
            "kiln": (59, 60), "smelter": (60, 60), "blacksmith's table": (61, 60),  # the Forge (run 18)
            "millstone": (58, 44), "ration maker": (60, 42),  # run 18: in the Kitchen; G56 M2 (run 48): into the Farmhouse beside the grain
            "flooring workshop": (55, 58)}  # run 50 (G56 M4): lawn and soil floors for the field's edge; stepping stones (G30 M4)
WOOD_BOX = (48, 57)        # logs, planks, branches, sticks, bark, resin (run 18: into the Workshop)
STONE_BOX = (61, 57)       # run 18: in the Forge (stone house 58-62 x 55-61, door 60,55); stones, cut stone, soil, glass, bricks, ores, ingots
STONE_BOX_2 = (52, 58)     # run 20: a wooden box 'Stone 2' beside the Forge's (61,56); G56 M2 (run 48): moved into the Workshop by the stonecutter and the mason's table: stone, cut stone, bricks
FODDER_BOX = (60, 41)      # run 18: in the Farmhouse; shared: grass, leaves, grass walls (materials only)

# Storage: the Storehouse, a rosewood house 63-69 x 37-42, door 66,42 (G12, run 18), except the
# Workshop's bag-parts and parts boxes
BAG_PARTS = [(48, 59), (58, 35)]  # G56 M2 (run 48): the box still named "Armory 2" beside the loom and spinner first, the big wagon after; run 18: in the Workshop; threads, fiber, strings, ropes, skins, bolts; G54 (run 45): the maniac chest
                           # 54,56 (15 slots) retired into the second big wagon (stations draw from any box at home)
MAPS_BOX = (55, 56)        # run 19 (the user): 'Maps', SHARED, distribution off (allow none): treasure maps only, for
                           # Poppy's Treasure Hunt (fact #688: it takes maps from shared boxes only)
PARTS_BOX = (53, 56)       # run 18: the sturdy box 'Parts' in the Workshop; bones, nails, batteries, microchips, scrap, fangs
SPARES = (68, 44)          # G47 (run 42): the yard's ★Storage Chest; the exquisite boss chest 65,41 (15 slots) retired
SPARES2 = (42, 47)         # run 30 (G28): the sturdy box 'Spares 2' in the Depot (was the mail package at 67,41, run 13)
# G47 (run 42): Nino's wagons, 60 slots each on 2x2, in the east yard north of the Storehouse; five small valuables boxes (64,39 64,40 66,39 67,38 68,38) emptied into them and retired
BIG_WAGONS = [(54, 38), (58, 35)]  # G54 M1 (run 45): Nino's two big wagons, 96 slots each, 4x4 cells (x 51-54 z 38-41; x 55-58 z 35-38),
                                   # south-west of the Storehouse; the anchor is the east and south corner. [0] takes the overflow and
                                   # valuables of the retired mystic chests, [1] the armory overflow and the bag parts
WAGONS = [(66, 46), (69, 46), (68, 44), (70, 44)] + BIG_WAGONS  # (68, 44): the third ★Storage Chest (Miral, 20 medals, 9 wrenches since run 44: 280 slots by its window), the yard too
VALUABLES = [(66, 46), (69, 46), (68, 39), (44, 47), (44, 49), (42, 49)]  # 'Valuables 7' stays last (packcheck's decorations use VALUABLES[-1]); coins, bars, medals, tickets, figures, cards, genes, gems
LIBRARY = [(67, 40), (42, 48), (64, 46), (54, 38), (44, 48), (65, 38), (68, 44)]  # run 45 (G54): 47,59's mystic chest -> the big wagon     # G47 (run 42): the boxes 66,38 and 48,58 retired into the yard's chest; [1] stays 'Library 3' (town.py) (run 30, G28: the Depot's sturdy box, was the bin
                           # package 64,38); books, spellbooks, recipes, letters;
                           # run 23: 'Library 2' (48,58), a wooden box in the Workshop, before the Storage Chest
                           # run 37: 'Library 5' (67,40), a sturdy box in the library room (nails from the new
                           # tinker's table at 54,58; the old one at 55,60 has no reachable side)
                           # run 39: 'Library 6' (44,48), a sturdy box in the Depot (oak planks, copper ingots,
                           # iron nails from scrap): the library chain was full again at the first unload
ARMORY2 = (68, 44)         # G56 M2 (run 48): 48,59 holds the bag parts now; its plain gear went into the yard chest. run 23: 'Armory 2', a wooden box in the Workshop (private): gear when the armory is full
ARMORY3 = (42, 50)         # run 30 (G28): 'Armory 3', a sturdy box in the Depot (private), when Armory 2 is full
ARMORY4 = (58, 35)         # run 37: 'Armory 4', a wooden box in the Depot at 45,50 (private), when Armory 3 is full; G54 (run 45): retired
                           # into the second big wagon
ARMORY5 = (70, 44)         # G47 (run 42): the third wagon, 60 slots, when the armory boxes are full
SPARES3 = (68, 44)         # G47 (run 42): was 'Spares 3', a wooden box at 49,58, retired
SPARES4 = (44, 50)         # run 38: 'Spares 4', a sturdy box in the Depot (private): the spares chests were all full
STORAGE_CHEST = (64, 46)   # run 20: Ashland's farewell gift, the ★Storage Chest (100 slots, fireproof; no rename): the
                           # library's overflow; G56 M1 (run 48): from the Workshop's 47,58 into the storage quarter. A magic
                           # chest carries its contents weightless: grabbed with 240 stacks, burden phase 0 (move.py)
STORAGE_CHEST_2 = (63, 46) # run 31 (G29 M1): the second ★Storage Chest (Miral, 20 medals; 3 wrenches: 96 + 60 slots): the
                           # overflow of every box at 90%+ (tools/rebalance.py); G56 M1 (run 48): from the Depot's 43,51
# G56 (the user, 2026-11-14; M0's plan, run 48): the storage quarter, the north band between the field and the Residence that
# holds the big wagons, the wagons and the three ★Storage Chests (town.py --storage checks every 60+ slot box is inside it)
STORAGE_QUARTER = ((51, 35), (71, 47))
# G54 (run 45): the five mystic chests used as overflow (45,51 43,46 44,46 45,47 47,59; 15 slots each) retired into the first
# big wagon; the names stay so the routes that use them don't change
OVERFLOW3 = (54, 38)       # run 31: a mystic treasure chest from a nefia (it rode in the loot bag), installed in the Depot
                           # beside the second Storage Chest: 15 more slots of overflow
OVERFLOW4 = [(54, 38)]     # run 31 (G30 M4, nothing loose): two loose mystic chests from the Residence and the
                           # Workshop installed in the Depot's south corner, as overflow
OVERFLOW5 = (54, 38)       # run 34: a mystic treasure chest from a nefia (it rode in the backpack), installed in the Depot's
                           # east side by the room board: 15 more slots of overflow
OVERFLOW2 = (54, 38)       # run 22: a madam's favorite mystic treasure chest from a nefia (the user's run 05 tip, fact
                           # #280: take emptied dungeon chests home as storage) beside it, when the Storage Chest is full
SHIPPING = (56, 52)
TRASH_CAN = (58, 51)       # run 18: was written 57,51 (the collectibles shelf)
COLLECTIBLES = (68, 40)    # display shelf: cards, figures, the decor backpack
FARM_BOX2 = (59, 41)       # run 18: the old condiments box, empty, for seeds when the Farm box (a 20-slot package) is full
SPARE_BOX = (68, 44)       # G47 (run 42): the wooden box 68,41 retired
MAIL_SPOTS = [(62, 48), (63, 48)]  # run 18: mail parcels (salary, deliveries) are set down beside the mail post (59-60,49
                           # then); run 49 (G56 M3): the post moved to 62,47, so the free cells beside it, ~ until one lands
MAIL_PACKAGE = (60, 50)    # "a package labelled Sender: Mysilia Post Office" beside the mail post: no Grab offered (office)
FIAMA_CHEST = (54, 50)     # Fiama's Lecture quest chest on the home board's cell: lock 50, worthless (fact #631)

# The Depot (run 30, G28, the user's clean-up goal): oak plank walls 41-46 x 45-52, door 46,49 facing the field,
# room board 45,46 (Private); six sturdy boxes (35 slots) along the west wall x=42, z 46-51
DEPOT = ((41, 45), (46, 52))

# Office and living
# run 49 (G56 M3): the office left the Residence's notch (62,49 is a wall of its one rectangle now, 61,50 its entry
# hall) for the cells beside the seating by the dummy, outside the new door 60,49
MAIL_POST = (62, 47)
TAX_CHEST = (63, 47)
MY_BED = (60, 52)          # the pine bed (run 12); the makeshift bed rides in the kit
RESIDENTS_HOUSE = ((62, 49), (68, 53))  # grass walls; door 65,49; torch 63,51
ARMORY = (66, 51)          # shared, priority 5, weapon + armour: residents take what beats theirs
DUMMY = (60, 46)
PRACTICE_CHEST = (61, 46)  # run 16 (the user's tip): Lockpicking practice, tools/lockpick.py
BOARDS = {"home": (54, 50), "quest": (54, 51), "resident": (54, 52)}
BOOKSHELF = (65, 38)       # run 36: in the library route's tail (24 slots, 2 used) once the boxes filled
# run 36: the valuables boxes all full (78 gene stacks among them, G38): the empty Depot chests take the overflow
VALUABLES_OVERFLOW = [OVERFLOW3, BIG_WAGONS[1]]  # run 39: (67, 52) dropped (the chest there is gone); run 45: (70, 51) had no container, the mystic chests became the big wagons


def BOX_STR(xy):
    return f"{xy[0]},{xy[1]}"
