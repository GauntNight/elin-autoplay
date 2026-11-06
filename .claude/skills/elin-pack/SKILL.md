---
name: elin-pack
description: Inventory management in Elin (run 08, the user's request) - the fixed delving kit, what never rides in the pack (coins, bars, collectibles, books, materials, spares), the triage before every trip and after every return (identify, equip, sell or ship, trash can, store), carrying unidentified items for identification, taking dungeon furniture to sell, bags and containers as the top equipment priority, and buying and selling by name. Use before leaving home, on every return, whenever the pack fills, and in any shop.
---

# The pack: carry the kit, not the house

The pack holds about 35 stacks. Run 08 hit the limit three times in one session (a boss chest's
loot wouldn't fit) while it carried coins, three ancient books, pebbles, a gold bar and spare
gear. The user's rule (run 08): **the pack is for the trip; everything else lives at home.**

## 1. The delving kit (what rides along, and nothing else)

| Slot | Item | Minimum |
|---|---|---|
| worn | weapon, armour, torch (light slot) | - |
| hotbar 1-9 | Putit In Amber, bow, cure potions, bandages, rod of teleport, Cooler Box, throwing daggers, pickaxe, shovel, evacuation | the hotbar is free space outside the pack grid; the shovel (the user, 2026-10-29: medals) and leave.py refuses home without one |
| pack | scrolls of teleport | 2+ for a dungeon, 4 is comfortable (road ambushes used 2 in run 08) |
| pack | scroll of evacuation, scroll of return | 1 each |
| pack | cure minor wound, plus one cure major | 5+ potions |
| pack | lockpick (boss chests), the makeshift bed (road sleep with `sleep.py`; the bag burned in run 12) | 1 each |
| pack | fireproof blankets with charges left (each charge saves the pack's items from one fire, fact #862) | 3 (the user, 2026-10-26 and 2026-10-30): leave.py refuses under 3 while storage holds one; none left: Aquli Teola (Sesa, Sayig) or Mysilia (Gizbird) ~360, or the loom (5 textures + 4 carbon logs) |
| pack | one throwable status potion (silence, slow): soaks kamikaze yeeks | 1-2 |
| pack | rods that save a fight: slow, holy shield, magic map | optional, light |
| pack | scroll of incognito when a law town is on the route (karma below 0) | 1 |
| Cooler Box | food for the trip: preserved food (melons 11 each, Kerona 10 orens), corpses to cook | 3+ days |

Target at departure: **the kit and nothing else** (about 29-32 stacks; `packcheck.py` prints the
count), so a boss chest and a floor of loot fit before loot.py's 42-stack bag routing starts.

## 2. Never carried (store at home, elin-home section 2 says where)

- **Currencies with special uses (the user: keep them all):** gold bars (Nino's recipes, Casaneck's
  policies), platinum coins (trainers), strange copper and silver coins (gacha), Small Medals,
  furniture tickets, Ecopo.
- Collectibles: cards, figures, genes.
- Books that aren't spellbooks for the trip: ancient books (decode at home: knowledge facts), journals.
- Materials (skins, stones, ores, logs, bones), spare weapons and armour, quest papers.
- Throwing pebbles once better throwables exist (mica daggers, the Putit).

## 3. Triage, every time

**Enforced, not remembered (the user, run 11):** I left home twice in run 11 carrying sticks, gold
bars, furniture tickets, figures, coins, books and Ecopo, and the pack filled in the dungeon (a
treasure map and a recipe couldn't be taken). Now `leave.py` runs `packcheck.py` on the home map and
refuses to leave while the pack, the backpack or the Cooler Box holds anything off the kit;
`packcheck.py --move` carries each item to its zone box (elin-home 2a). Run it on every arrival home
too. Its KIT list in the script is the kit of section 1: change both together.

**Fire-safe storage (the user, run 12):** scrolls, potions and rods ride in the backpack, not the
open pack: a hot guy's blast burned a rod, the sleeping bag and two scrolls carried loose. Only
the teleport scrolls and cure potions stay in the main pack (an escape must be one action);
packcheck accepts any potion, scroll or rod inside the backpack. The kit also holds the Edible
Necklace (worn), the makeshift bed (road sleep: `sleep.py`, 0.72 weight; the pine bed weighs 28
and caused Burden), the copper hammer, a potion of silence, the rod of holy light and the
butcher's tool (run 13: butcher corpses where they fall with `butcher.py`).

**packcheck never ships by default (run 12):** its old fallback was the shipping chest, and it
sold the ☆Forest Necklace (193) before I saw it: I had read the output through `tail`. Now
junk goes to the trash (scrap junk such as empty cans to the parts box, for `scrap.py`), plans
are "read it now", identified gear and jewelry go to the armory (66,51, before any material rule:
a glass staff had gone to the stone box) except ☆ gear, a decide item: wear it or ship it (run 13:
the armory handed a ☆ shirt to a resident within the hour), books to the library,
and anything without a rule is reported and left in place. Never truncate the output of a tool
that moves items; after any mis-route, list the whole shipping chest.

**Before leaving home** (`packcheck.py`, then `bridge.py inv` for a last look): kit (section 1), or
store, or ship. Read unlearned recipes and skill books on the spot (a skill book = a new skill =
character exp).

**item.py's own refusals (the review of 2026-10-23):** Equip, Read, Use, Drink or Eat of a cursed or
doomed item needs `--cursed-ok`; Equip of gear that "prevents teleportation" needs `--teleport-ok`
(it switches off every escape scroll); an Equip that would replace the main-hand weapon needs
`--main` (run 20: the axe came off for a grass sword); a scroll of return or evacuation is not read
while one counts down (the bridge refuses it too). The bridge refuses a drag onto a stack of the
same item (run 13: three textures vanished in a merge): move both into one container instead.

**Unidentified items ride along** (the user, run 08): Appraising rolls on each unidentified item in
the pack every game hour, and Aliyun at Tinker's Camp identifies the pack for 45 an item. Never sell
or ship one unidentified: Kerona paid 1-14 for Miracle gear that sold for 163-213 identified.

**On return, in this order:**
1. Identify (Aliyun, or wait for Appraising): **Godly items need the artifact identify (660 in run 16;
   it gave ☆The Immortal Necklace: no blindness, fear or thieves), Miracle and Good ones the
   identify-all (132-264, it covers the carried bags)**; unidentified items sell for 1-15, so identify
   before shipping (the user, run 15). Equip what beats worn gear (`item.py X info`, compare
   PV/DV, damage and enchantments; refuse anything that "prevents teleportation"). **Artifact
   identification (678 for Godly or Miracle) only when the item's slot can beat the worn piece**:
   2,079 spent over runs 07-12 brought 373 back in sales (the review), and run 19 paid 652 for a
   Godly breastplate that shipped for 193 (three such identifies: -1,442 net; errors.csv); a Miracle
   piece that can't be worn rides home for Appraising (free, hourly) and ships once identified.
2. **`gearcheck.py` first, then `shipstar.py`** (run 40, the user: "how often do you look at current equipment versus new?"): gearcheck prints each ☆ piece
   beside the worn one, whole lines: read them; shipstar carries to the shipping chest only what gearcheck has shown (`--dry` lists, `--keep NAME` leaves a piece). Weigh
   duplicates: an immunity two pieces give is spare (Their Fist's sleep and blindness); a resistance one gives can cancel another's weakness (the Bucket and the copper ring).
   **Enchant scrolls:** `picker.py`; plain caps at +2, great +4, blessed +1 (ActEffect); armor +2 PV a plus, rings take them too. **Books at home: `decode.py --fetch` (ancient books, Mages
   contribution) and `readskills.py` (specialized books, skill levels and character exp)**: run both on every return; run 40 found 38 and 28.
   Sell or ship the identified surplus. **Ship ☆ (Miracle) gear from home, never sell it in a shop**
   (run 09: the chest paid 763 for a ☆ hand axe; Aliyun pays 166-178 for that kind, so three pieces
   sold in town lost about 1,700). Junk and plain gear pay about a shop's price either way; carry ☆
   pieces home even from a town where they were identified.
   The pack refuses the 44th stack ("You can't put that in your backpack!", run 09): in a dungeon,
   drop ores, stones and bones before the boss loot, not after.
3. Garbage, rotten food, bottles, cans, candy canes: `trash.py` (the trash can pays Ecopo).
4. Store the rest by category.
5. Every few trips, audit the home boxes too: ship spare gear and jewelry nobody wears.

- **Worn gear corrodes on the road** (run 20: the helm lost a shrine +1, the girdle fell to -1):
  blend an acidproof liquid onto each worn piece (`picker.py "acidproof liquids" Blend NAME`; the
  spares chest holds them) whenever a new piece goes on.

### Carried chests and the money inside them (run 25)

- **A chest opened from the pack is a registered window** until its menu's "Close" is pressed (`item.py
  NAME Close`; the menu shows "Open" once it is closed). Every Shift+click move while one is open goes
  into the chest: the afternoon of run 25 lost the mushrooms, the identify rod, a gold bar and the Miracle
  gear into two mystic treasure chests, one take after another. bag.py now closes chests before a take;
  by hand, check the chest's menu first.
- **Money inside a carried container counts in the purse and leaves with the container:** dropping a
  chest on B3 to shed weight read gold 0 and gold bars 0 until I went back for it. Take orens, gold bars
  and medals out first (`bag.py CHEST --take "N orens" "N gold bars"` with only that chest open).
- **A mystic treasure chest weighs 10-18 and is worth ~112-200 shipped:** empty it at home, ship it or
  install it as a spares box the same day; two of them put the pack at burden phase 2 on every pickup.
- **Leave home with 3 free grid slots** (run 25): the pack grid holds 35 cards; at 35 every take from a bag,
  a chest or a box is refused or lands in another window (the day's meals, the identify rod, the gold bars, the
  roasts at a nefia's door: three ladder starts stopped at Hungry). packcheck.py refuses departure under 3 free
  slots (FREE_SLOTS), so leave.py does too.
- **Materials for a craft under way ride in runs/carry.txt** (hide fiber, thread, texture, the blankets,
  the identify rod and scroll, carbon logs): packcheck --move carried the identify items back to Spares 3
  twice between a take and its use (run 24's medals again).

## 4. Taking valuables off the map

- Dungeon and nefia furniture belongs to nobody (the user's tip, run 08: wall lights, base value
  1,400). `valuables.py` lists installed furniture by value. Take it with a right-click Grab
  (pick up whatever lies on top first), then `hotbar.py --deselect` puts it in the pack. Ship it.
- Cobwebs can't be taken by hand (Collect destroys them). Crystal needs a harder pickaxe than granite.
- Town furniture is someone's property (theft: Karma -1).
- `loot.py` picks up valuables only; special mobs' corpses go in the Cooler Box.
- **A boss chest is emptied completely** (the user, run 17: "there were two magical items"): its
  plain-named gear (cotton boots, a paper shirt) can be magical; identify, then wear or ship. Use
  every shrine on the floor before leaving (Wheel: a recipe; a material shrine, ★Shrine 《X Hammer》,
  recasts one item: coral gave a mica helm PV +5).
- **Cursed items** double their power like blessed ones but flip helpful effects: a cursed cure
  potion or rod hurts (an attack to throw at foes), a cursed attack rod is just stronger. Never use a
  cursed heal on yourself or an ally (run 17: an escort 41% -> 11%).
  The cursed rod of summon animal summons any level (a Lv16 sea lion at Lv11): never a training tool (run 11).

## 5. More slots: the top equipment priority (G6)

Any bag, backpack or carryable chest beats almost any other find (the user, run 08): a bag holds
about 35 stacks in one pack slot. Check every shop and chest for one; the Cooler Box shows how a
carried container works (`bag.py`). G6's crafting route (loom, needles, bolts) is in goals.md. A
lame purse holds 4 items.

**A bag takes storage wrenches (G45, run 41):** one vertical and one horizontal wrench (Miral, 6 medals each, 2 of each in stock) make 7x5 into 8x6, 48 slots: empty it, `place.py` it on a cell, stand on it, hold the wrench, right-click Upgrade, each axis once, right-click Grab. The loot bag has them (common.BAG_SLOTS). A fourth bag, 'a haul bag', since run 41. **Weight:** Dragon Slayer weighs 28 and Gravity Point takes 10 off the limit: Burden sets in at about 100 and phase 2 at about 120, so the heavy stacks stay home (51 troll blood, 29 restore body, 54 uncurse).

**The backpack (run 10, 35 slots, wool):** holds what rides along but is rarely used: the rods
(holy shield, slow, silence, teleport 11 charges), spare potions (hero, troll blood, paralysis, cure
mutation, restore body), acidproof liquids, hero and magic-map scrolls, spare bandages, materials
picked up on a trip. The main pack keeps what a fight needs at once: scrolls of teleport, cure
potions, the Putit, throwing daggers, the bow, the pickaxe. Food stays in the Cooler Box only: the
backpack doesn't keep it fresh (run 10: `bag.py` sent stews and tomatoes into it until fixed).

## 6. Shops: buying and selling by name

- Read the price first: `item.py NAME` lists "Sell 1 (N orens)" or "Buy 1 (N orens)", and with a
  shop open it prints what I already carry of it (the pack and the open backpack; run 20 bought 2
  evacuation scrolls with 14 in the backpack). `power.py`'s kit line counts open bag windows too.
- Buy by the full name without the count ("scroll of teleport", not "7 scrolls of teleport" and
  not "of teleport": the bare form bought a 516-oren spellbook and a 315-oren rod, runs 08 and 11).
  Item tools match whole words and plurals, and refuse a name that fits two things.
- A shop window that won't close: `bridge.py closetop` (close.py does it now).

## What this skill changed

New in run 08; enforced by packcheck.py and leave.py since run 11. Measure: errors.csv repeats in
the elin-pack domain and orens lost to the pack (shipped by mistake, burned, identified to ship).
Baseline runs 12-20: 8 errors, 0 repeats, ~1,100 orens lost (the Forest Necklace 193, the identify
459 net, the evacuation scrolls 176, a shirt, a skin). Run 24: 2 errors, 1 repeat (the medals carried back).
Latest, run 25: 3 errors, 1 repeat (the identify items carried back to Spares 3: run 24's medals again),
~0 orens lost (the purse dropped inside a chest on B3 was recovered) but ~50 real minutes to the carried
chests' hidden windows; bag.py closes chests before a take and runs/carry.txt names craft materials.
