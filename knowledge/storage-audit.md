# Storage audit (G70 Smart Storage, M1)

Read at run 57's first home stop (497-09-04) with `tools/audit.py` (the bridge's `stock` op, every installed container at
home, sorted by the game's own category from things.json) and `tools/boxcount.py --run 57` (each container's USED / SIZE).
The per-kind rows are `runs/audit-57.csv` (gitignored: a game's records stay on this PC). "Recipes" counts the game's
recipes that take a kind by its id or its category (graph.json's `needs` edges), so a broad category (books, junk) scores
high without any recipe in use here; "used by" is my reading of what this repo's tools, the kit and the goals use.

**The keep rule (the user, 2026-11-21): sell unless used.** Keep what a tool, a recipe in use, a goal or the trip kit needs,
one working stack of each crafting material, and collectibles (cards, figures, medals); everything else sells, ships or goes
to the trash can.

## Capacity at the audit

40 containers, 2,225 slots, 1,622 used, **603 free**, but not where the routes look: the second ★Storage Chest 63,46 holds
92 / 360 (it is only `rebalance.py`'s overflow), 64,46 holds 208 / 340, and every other route is full or nearly so (the yard
chest 68,44 at 280 / 280, both wagons 60 / 60, the second big wagon 96 / 96, the Parts box, three Valuables boxes, Library 3
and 5, Spares 2, Armory 3, Pantry 2, the Stone and ore box). The shipping chest empties each morning but takes ~40 stacks a
day (fact #1001).

## The tally and the calls (M2)

**Approved by the user, 2026-11-21 (run 57): "Approve the list mostly. But sell the cards and figures. They just increase
tourist value - unless they have another purpose?"** They have none in the game's tables (tag 'tourism', traits Card and Figure,
no recipe), so both rows read sell; the keep rule's word "collectibles" now means medals only.

| Theme (game categories) | Stacks | Items | Used by | Proposed call |
|---|---:|---:|---|---|
| **Gear** (armor and weapons but ammo: amulets 41, torso 33, polearms 32, heads 25, feet 23, swords 22, the rest) | 354 | 355 | the worn set; the Luminescent Long Bow; the Forest Gloves (water breathing, G66's descent); the armory 66,51 that residents draw from | **sell**: keep the worn set, the bow, the water-breathing gloves and one tested spare per worn slot (gearcheck.py's pick); the armory keeps its 24 for the residents; every other piece identified, then sold or shipped (☆ by shipstar.py, the rest to Samata) |
| **Unidentified** (in boxes; 29 more in the pack) | 27 | 27 | nothing until read | **identify** at Aliyun (Tinker's Camp), then by the row its kind falls in; never sold unread (the user's rule) |
| **Ammo** (iron arrows 5,360, iron bullets 3,600, iron quarrels 2,216, energy cells 600, 11 small stacks) | 18 | 12,147 | the bow's arrows (one kind, the most) | **sell**: keep the iron arrows; bullets, quarrels, cells and the small arrow stacks go |
| **Cards** (monster cards) | 211 | 379 | nothing: the game tags them 'tourism' only (trait Card), no recipe takes one | **sell** (the user, 2026-11-21: "sell the cards and figures. They just increase tourist value - unless they have another purpose?") |
| **Figures** | 53 | 62 | nothing: 'tourism' only (trait Figure), no recipe | **sell** (the same answer) |
| **Currency** (gold bars 435 in 6 stacks, platinum 782 in 4, old tickets 60, dried mandrakes 17, medals, copper coins) | 34 | 3,078 | spending, trainers, Miral, Nino, Sorin (mandrakes, G68) | **keep**, one stack a kind (frees ~15 slots) |
| **Learned recipes** ("Learned xN") | 60 | 93 | nothing: already learned; the chest pays 0 for them (stock.NEVER_SELLS, run 42) | **trash** (after one test sale to Samata) |
| **Other books and letters** (story books, the Journal of Lutz 1-8, parchments, spam letters, unlearned recipes) | 41 | 82 | unlearned recipes: readrecipes.py; the rest nothing | **read** the unlearned recipes; **sell** the books; **trash** the spam letters |
| **Ancient books** | 41 | 86 | G63 (decode.py --fetch) | **keep** the undecoded; **sell** the decoded copies |
| **Spellbooks** | 61 | 61 | stock.py's 100-cast cap | **by the caps** (stock.py --ship), unchanged |
| **Rods** | 66 | 66 | stock.py's rod caps | **by the caps**, unchanged |
| **Scrolls** | 38 | 452 | stock.py's scroll caps; enchant scrolls for the worn set | **by the caps**, unchanged |
| **Potions and drinks** (restore body 46, restore mind 48, resistance 68, tea 66, liquids 64) | 55 | 1,106 | stock.py's potion caps (heals all, the rest 5) | **by the caps**; non-potion drinks (tea, liquids) **sell** |
| **Booze** (beer, ale, cocktails) | 44 | 173 | nothing | **sell** |
| **Genes** (superior ones kept since run 49) | 78 | 78 | gene.py, but the crew is out of feat points (5 fit now) | **sell** all but the ones a member can take today |
| **Food and cooking** (mushrooms 3,496 in 8 stacks, seasonings 24, sauces 20, spices 11, eggs, meat, herbs) | 101 | 4,175 | meals (items.meals), cookdishes.py, the Dishes box | **keep** one stack of each seasoning cookdishes uses and ~100 mushrooms; **sell** the rest (a mushroom stack is one chest slot) |
| **Materials** (wood 34, other resources 39 (bolts, gems, leaves), seeds 32, stone 14, textiles 13, skins and parts) | 149 | 2,212 | blanket.py (skins, fiber, thread, texture, carbon logs), craft pushes, the farm (seeds) | **keep one working stack of each** (the rule); duplicates merge; gems **sell** but one stack a kind |
| **Junk** (book piles, rubble, research equipment, toasters, lucky cats) | 73 | 982 | nothing | **sell** to Samata or the chest; garbage to the trash can |
| **Furniture and decorations** (holiday garlands and wreaths, paint, scraps, lights, pedestals) | 70 | 208 | scraps: craftrun's Blacksmith; placed pieces at home | **sell** what isn't placed; keep one stack of scraps |
| **Treasure maps** | 13 | 13 | Poppy (the Maps box) | **keep** |
| **Skill books** | 6 | 7 | reading them now | **read** |

**Where they go:** ☆ gear to the shipping chest (it pays ~1.1x a shop: fact #1584) by `shipstar.py` and `stock.py --ship`,
40 stacks a morning; everything else, and whatever the chest refuses that day, to Samata the healer at home (shop level 2
since run 57) by `tools/sell.py` (her row on the resident board's Find walks me to her).

## The shopkeeper at home (M0, run 57)

Samata the healer (a resident since 487-06-11, shop "I don't work at all", shop level 1 -> 2 for 96 orens) opens "Show me your
wares" with a Sell act on every thing in the pack's own grid. **She bought outside her line:** a ☆laser gun for 1,284 orens,
then two ☆ guns and a shuriken for 477, the gold moving each time: no category gate at a home shop (fact #1584's code
reading). **The chest pays ~1.1x her price** (the shop formula x1.1, fact #446). **A buying-gold limit:** none met in four
sales (1,761 orens); the Derphy fences ran dry each night (run 53), so `sell.py` stops at the first sale that moves no gold.
Farris (scrolls, recipes) is no longer a resident: the board lists 15 residents, Samata the one shopkeeper.
