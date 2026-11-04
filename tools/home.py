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
FIELD = [(x, z) for z in range(43, 50) for x in range(48, 55)]  # tilled rectangle, 38 field cells
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
            "millstone": (66, 59), "ration maker": (67, 59)}  # run 18: in the Kitchen
WOOD_BOX = (48, 57)        # logs, planks, branches, sticks, bark, resin (run 18: into the Workshop)
STONE_BOX = (61, 57)       # run 18: in the Forge (stone house 58-62 x 55-61, door 60,55); stones, cut stone, soil, glass, bricks, ores, ingots
STONE_BOX_2 = (61, 56)     # run 20: a wooden box 'Stone 2' beside it (hide strings), for the overflow
FODDER_BOX = (60, 41)      # run 18: in the Farmhouse; shared: grass, leaves, grass walls (materials only)

# Storage: the Storehouse, a rosewood house 63-69 x 37-42, door 66,42 (G12, run 18), except the
# Workshop's bag-parts and parts boxes
BAG_PARTS = [(54, 56)]     # run 18: in the Workshop; threads, fiber, strings, ropes, skins, bolts
MAPS_BOX = (55, 56)        # run 19 (the user): 'Maps', SHARED, distribution off (allow none): treasure maps only, for
                           # Poppy's Treasure Hunt (fact #688: it takes maps from shared boxes only)
PARTS_BOX = (53, 56)       # run 18: the sturdy box 'Parts' in the Workshop; bones, nails, batteries, microchips, scrap, fangs
SPARES = (65, 41)          # the exquisite boss chest; potions, scrolls, rods (full since run 12)
SPARES2 = (42, 47)         # run 30 (G28): the sturdy box 'Spares 2' in the Depot (was the mail package at 67,41, run 13)
VALUABLES = [(64, 39), (67, 38), (68, 38), (68, 39), (64, 40), (66, 39), (44, 47), (44, 49), (42, 49)]  # run 39: 'Valuables 8' and 'Valuables 9' (Depot sturdy boxes) before Valuables 7, which stays last (packcheck's decorations use VALUABLES[-1]); boxes, the shelf 68,39 and the stone chest 64,40; coins, bars, medals, tickets, figures, cards, gems; run 20: 'Valuables 6' at the aisle's end (66,39: the other free cells would cut off the shelves)
LIBRARY = [(66, 38), (42, 48), (48, 58), (47, 58), (47, 59), (67, 40), (44, 48), (65, 38)]     # a box and 'Library 3' (run 30, G28: the Depot's sturdy box, was the bin
                           # package 64,38); books, spellbooks, recipes, letters;
                           # run 23: 'Library 2' (48,58), a wooden box in the Workshop, before the Storage Chest
                           # run 37: 'Library 5' (67,40), a sturdy box in the library room (nails from the new
                           # tinker's table at 54,58; the old one at 55,60 has no reachable side)
                           # run 39: 'Library 6' (44,48), a sturdy box in the Depot (oak planks, copper ingots,
                           # iron nails from scrap): the library chain was full again at the first unload
ARMORY2 = (48, 59)         # run 23: 'Armory 2', a wooden box in the Workshop (private): gear when the armory is full
ARMORY3 = (42, 50)         # run 30 (G28): 'Armory 3', a sturdy box in the Depot (private), when Armory 2 is full
ARMORY4 = (45, 50)         # run 37: 'Armory 4', a wooden box in the Depot (private), when Armory 3 is full
SPARES3 = (49, 58)         # run 23: 'Spares 3', a wooden box in the Workshop: potions, scrolls, rods when the others are full
SPARES4 = (44, 50)         # run 38: 'Spares 4', a sturdy box in the Depot (private): the spares chests were all full
STORAGE_CHEST = (47, 58)   # run 20: Ashland's farewell gift, the ★Storage Chest (100 slots, fireproof; no rename): the
                           # Workshop's middle row; the library's overflow
STORAGE_CHEST_2 = (43, 51) # run 31 (G29 M1): the second ★Storage Chest (Miral, 20 medals; 3 wrenches: 96 + 60 slots), in the
                           # Depot's NE corner: the overflow of every box at 90%+ (tools/rebalance.py)
OVERFLOW3 = (45, 51)       # run 31: a mystic treasure chest from a nefia (it rode in the loot bag), installed in the Depot
                           # beside the second Storage Chest: 15 more slots of overflow
OVERFLOW4 = [(43, 46), (44, 46)]  # run 31 (G30 M4, nothing loose): two loose mystic chests from the Residence and the
                           # Workshop installed in the Depot's south corner, as overflow
OVERFLOW5 = (45, 47)       # run 34: a mystic treasure chest from a nefia (it rode in the backpack), installed in the Depot's
                           # east side by the room board: 15 more slots of overflow
OVERFLOW2 = (47, 59)       # run 22: a madam's favorite mystic treasure chest from a nefia (the user's run 05 tip, fact
                           # #280: take emptied dungeon chests home as storage) beside it, when the Storage Chest is full
SHIPPING = (56, 52)
TRASH_CAN = (58, 51)       # run 18: was written 57,51 (the collectibles shelf)
COLLECTIBLES = (68, 40)    # display shelf: cards, figures, the decor backpack
FARM_BOX2 = (59, 41)       # run 18: the old condiments box, empty, for seeds when the Farm box (a 20-slot package) is full
SPARE_BOX = (68, 41)       # an empty wooden box in the Storehouse (run 18)
MAIL_SPOTS = [(59, 49), (60, 49)]  # run 18: mail parcels (salary, deliveries) are set down here by the mail post
MAIL_PACKAGE = (60, 50)    # "a package labelled Sender: Mysilia Post Office" beside the mail post: no Grab offered (office)
FIAMA_CHEST = (54, 50)     # Fiama's Lecture quest chest on the home board's cell: lock 50, worthless (fact #631)

# The Depot (run 30, G28, the user's clean-up goal): oak plank walls 41-46 x 45-52, door 46,49 facing the field,
# room board 45,46 (Private); six sturdy boxes (35 slots) along the west wall x=42, z 46-51
DEPOT = ((41, 45), (46, 52))

# Office and living
MAIL_POST = (61, 50)
TAX_CHEST = (62, 49)
MY_BED = (60, 52)          # the pine bed (run 12); the makeshift bed rides in the kit
RESIDENTS_HOUSE = ((62, 49), (68, 53))  # grass walls; door 65,49; torch 63,51
ARMORY = (66, 51)          # shared, priority 5, weapon + armour: residents take what beats theirs
DUMMY = (60, 46)
PRACTICE_CHEST = (61, 46)  # run 16 (the user's tip): Lockpicking practice, tools/lockpick.py
BOARDS = {"home": (54, 50), "quest": (54, 51), "resident": (54, 52)}
BOOKSHELF = (65, 38)       # run 36: in the library route's tail (24 slots, 2 used) once the boxes filled
# run 36: the valuables boxes all full (78 gene stacks among them, G38): the empty Depot chests take the overflow
VALUABLES_OVERFLOW = [OVERFLOW3, OVERFLOW4[1], OVERFLOW4[0], (70, 51)]  # run 39: (67, 52) dropped (the chest there is gone)


def BOX_STR(xy):
    return f"{xy[0]},{xy[1]}"
