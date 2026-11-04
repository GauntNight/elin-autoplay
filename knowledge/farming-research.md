# Farming: what the game code says (research, run 06, 2026-10-17)

A research agent read the decompiled code (EA 23.355) and the wiki page Elin:Farming after the
user asked why farming wasn't working ("Do we not understand it carefully"). The user tabled G3
for now (2026-10-17); this is the reference for when it resumes. Unverified items are marked.

## What we got wrong

- "No weeds grow on a field" is false: `Cell.CanGrowWeed` is true for an empty field cell, so the
  19 empty tilled cells each roll 1/20 a day for growth that eats fertility.
- The poor yields were the soil penalty: below zero fertility every harvest and reap loses items
  (`num2 -= rnd(2 + over/20)` for crops, `-= rnd(2 + over/10)` for reaped seeds).
- "Each plant gives food or seeds" holds only without **Delegated Farming** (policy 2707).
- Farming skill and fertilizer don't change crop yield.
- Winter: ripe crops wither rather than vanish; a roof blocks growth all year unless a sun lamp
  covers the cell.
- Water on the planting day is wasted (the sprout tick doesn't grow).

## Yield

- Hand harvest (`GrowSystem.PopHarvest`): `rnd(max)+1` (imo 1-3, mean 2), minus the soil penalty
  when the soil cost is over MaxSoil.
- Plant quality +N (`ApplySeed`) raises the food's effect, not the count.
- The stub after a harvest never regrows on a field; cutting it: leaf + seed ~12.4% on a field
  (5% off a field, ~60% if withered).
- Sickle "Reap seeds": 1/2/3 seeds with odds 1/3, 1/2, 1/6 (mean 1.83), no food; ripe crops only.
  Manual break-even for seed stock: reap ~55% of ripe plants, harvest the rest, cut every stub.
- Seed improvement (`TraitSeed.MakeSeed`, home only) depends on Farming - seed level, watering,
  fertilizer, the Kumiromi feat.

## Seeds

- No crop can be planted or turned into a seed. The wooden mortar (40 logs) converts one +N seed
  into one +0 seed (mercury / angel's blood keep the level). Kumiromi's "Favor of the Harvest":
  rotting food in the pack becomes up to 3 random seeds.
- **Nefia patches:** plain and forest dungeons generate ripe wild crops (imo, sweet imo, carrot,
  cabbage, radish, cabocchi, cotton, crim, api; 1 in 6 withered): reap with the sickle, no soil
  penalty there, seeds pre-improved.
- Seed merchant (Mifu): rice, cabbage, carrot, imo, corn, tea, 4-7 each. Ecopo merchant (Yowyn):
  random seeds. Loytel's farm quest: pasture, tomato, mushroom seeds.

## Growth and winter

- One tick at 06:00: 5, or 10 if watered that day; 30 a stage; imo ripe after ~9 watered or ~18
  dry ticks plus the sprout day. Rain: ~64% of days while away.
- Fertilizer: one extra growth step on a plant; sprouts a planted seed at once; on an empty cell
  it creates a weed. Defertilizer (millstone) stops growth and exempts a crop from winter.
- Winter = months 12-2: each day a crop has a 1/4 chance to perish (sprouts always); seeds kept as
  items are safe. Sun lamps (machine bench, sun crystal, -10 electricity, radius 6) allow winter
  farming; mushrooms need no sun.

## Soil fertility

- Cost = sum of every object's costSoil / 10 (imo 3, cabbage/corn 4, weed/flower 1, tree 0.5);
  `MaxSoil = (sqrt(W*H)*3 + 5*fSoil) * (100 + 25*Fertile)/100`; the bar shows Max - cost.
- At or above zero: no bonus; below zero: the penalties above.
- Raise it: clear wild plants, keep tilled cells planted, the **Weed Pulling Campaign** policy
  (2703, ~20x less wild regrowth), residents with Gardening work or hobby (+5 Max each).

## The fix: Delegated Farming

- Policy 2707 (no upkeep), available at home level 2+; its area is 5x5 around a farm sign
  (signboard workshop, 1 log) or a scarecrow (loom).
- Inside: crops auto-harvest when they leave the ripe stage (~0.6 imo a plant) and a **guaranteed
  seed is replanted** on the cell. Hand-harvesting a ripe crop there keeps the full 1-3 and still
  gets the free replant (about 6 dry / 3 watered days to do it).

## Procedure (for when G3 resumes)

1. Fertility to +5 or more: clear wild growth, check the Home board, turn on Weed Pulling.
2. No empty tilled cells: plant them or leave them untilled.
3. If Delegated Farming is available: turn it on, a farm sign at the plot's centre, plant, water
   daily, hand-harvest every ripe crop, cut nothing.
4. Otherwise: reap ~55-60% of ripe crops, harvest the rest, cut every stub.
5. More seeds: plain or forest nefias with a sickle, the seed merchant, Ecopo.
6. Before month 12: harvest or reap everything, store the seeds, replant in month 3.

Not verified: our map size, MaxSoil, home level, whether Weed Pulling is on, the farm sign's
area inside walled rooms.
