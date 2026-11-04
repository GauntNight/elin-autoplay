# Foods: what eating them did (observed)

`tools/item.py NAME Eat` reads this file: it refuses anything under **Harmful**, and shows the
tooltip (nutrition, freshness, traits) before eating anything else. A tooltip doesn't list
side effects (the white mushroom showed none), so a new food is unknown until eaten once.
Add every new food here after eating it. Unknown wild mushrooms go to bait, not the mouth.

## Safe

| Food | Nutrition | Notes | Run |
|---|---|---|---|
| vegetable soup | ~20 | "so so" taste | 02, 03 |
| travel ration | 51 | preserved; also the Fast Travel fare (inns 50); eaten on the road runs 15-19 | 15-19 |
| boar on the bone (cooked corpse) | ~25 | "Gee what a good taste!" | 03 |
| mushroom (plain, id mushroom) | 13 | raw is fine (Nerun: tasty, not filling, spoils) | 03 |
| blueberry | 8 | raw | 03 |
| roasted blueberry | 13 | bonfire, Cooking 1; small CHA/MAG traits | 03 |
| skewer of grilled goby | 20 | bonfire from any fish | 03 |
| raw hermit crab corpse | ~17 | "Ugh... raw meat", no side effects; cook if possible | 03 |
| skewer of grilled muddler | 25 | bonfire "Skewer of grilled fish"; STR/WIL traits | 03 |
| skewer of grilled tadpole | 15 | "pretty good"; DEX traits | 03 |
| tomato (home field) | 11 | raw is fine; CHA/PER traits; 1-4 per plant | 10 |
| yeek on the bone | 27 | bonfire "Meat on the bone" from a yeek corpse; STR/END traits | 10 |
| giant squirrel on the bone, rat on the bone | ~20-25 | bonfire from marbled meat or a corpse | 10 |
| heart | 3 | barely food; ships for 24 each: ship them | 10 |
| yeek / yeek archer / goblin warrior on the bone (cooked corpses, bonfire) | ~25 | no side effects | 06 |
| skewer of grilled bitterling, skewer of grilled goldfish | ~17 | fine | 06 |
| bush de noel (Jure gift) | ~30 | "taste is so so"; two filled hunger 47 -> 16 | 07 |
| delux snow putit cake (Jure gift) | ~25 | "Decent meal"; potential up | 07 |
| ginger bread man (Jure gift) | ~20 | two: hunger 62 -> 20 | 07 |
| round rice cake (New Year's gift) | ~20 | fine | 07 |
| bamboo shoot, leccho (Kerona, 7-9 orens) | ~10 each | raw is fine; both count as vegetables for recipes | 07 |
| skewer of grilled mackerel (bonfire) | ~25 | "potential of your learning increases" | 07 |
| corpse of goblin (raw) | 18 | "Ugh... raw meat", no harm | 07 |
| piece of melon (Kerona, 10 orens) | 11 | preserved food (keeps); "Wow! Terrific food!" | 08 |
| stale apple | 13 | stale is still edible | 08 |
| goblin / beth putit / rat / 『Yeek』 on the bone (bonfire; a log in the pack is fuel, sticks aren't) | ~25 | "Delicious!"; one hunger 61 -> 34 | 08 |
| candy cane | - | not food: paper decoration, can't be sold (trash can) | 08 |
| roasted cactus (bonfire: Roasted fruit with a cactus, 2 SP) | 14 | no side effects; the way to eat beach cacti | 09 |
| palulu (raw, beach palulu tree) | 18 | no side effects | 09 |
| 『Snail』 on the bone (special corpse, bonfire) | ~20 | "Delicious!" | 09 |

## Harmful

| Food | What happened | Run |
|---|---|---|
| white mushroom (id 699), raw | confusion, insanity, hallucination, fear; cleared after about 2 game hours of waiting | 03 |
| egg of kitten | Karma -5 and nausea ("about to throw up"): a cat's egg counts as eating cat (the primer: cat meat -5 karma) | 05 |
| egg of (any cat) / cat meat / humanoid corpses | Karma loss, insanity (the primer) | 05 |
| scorpion on the bone (marbled meat of 『Scorpion』, cooked) | Poison: HP 41 -> 34 while walking, slowed; a troll blood cleared it. Read the 【traits】 first (item.py now refuses harmful traits) | 06 |
| corpse of 『Yeek』 (raw, Royal Quality) | "You feel like you are about to throw up. It tasted awful!" (nausea; no karma change): cook special corpses or skip | 07 |
| red mushroom (id 700), raw (probably; eaten by farmday.eat_one from the Cooler Box) | Poison twice: 486-04-15 (HP 75 -> 30 with burden) and 04-18; a troll blood didn't clear it, a blue herb did | 11 |
| mini red mushroom salad (cooked from red mushrooms at the cutting board) | Poison: Kaberg and the snow putit ate two from the shared fridge and were poisoned (both back to ~97% within the hour). Cooking keeps the harm: cookdishes.py now skips every Harmful ingredient. The mini white mushroom salad went out the same day, effect unseen | 19 |
| raw carp (not blocked by item.py: "carp" would also catch a cooked one) | 13 nutrition, "It tasted awful! ... You feel like you are about to throw up." Grill fish at the bonfire first | 13 |
| raw cactus (not blocked by item.py: the name would also catch roasted cactus) | ~9 each, but the second one: "Awful taste!! ... You feel like you are about to throw up." Roast it instead | 09 |

## Cures (eat or drink when the condition hits)

| Item | Trait | Cures | Run |
|---|---|---|---|
| blue herb | 【Antidote】 Lv.3 Cure Poison | poison: eat one (the user's tip, run 06; keep 2 in the Cooler Box) | 06 |
| potion of troll blood | regeneration (ConHOT) | outheals poison; HP over time | 06 |

## Untested

(none; travel rations moved to Safe after runs 15-19)
