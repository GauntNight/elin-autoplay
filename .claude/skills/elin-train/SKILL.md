---
name: elin-train
description: Training for character exp in Elin (G55, the exp research run 46) - what pays character exp at all (skill level-ups only), the home dummy ridden on Kaberg with low weapon skills (trainday.py), a trainer's potential bought just before (trainpot.py, Guroot), music in a town (music.py), Quick Craft, and what each costs in food, game days, rent, corruption, karma and the run score, with run 46's measured rates. Use when planning exp, before any training stretch, when a skill or level push is in the plan, and whenever the user asks how to level faster.
---

# Training for exp

**What pays** (the game's code, facts #1392-#1396): character exp comes only from a **Skill** level-up, 10 + rnd 5 each
(`ElementContainerCard.OnLevelUp`). Attributes, spells, feats, food, sleep, kills and quests pay none. A skill's gain is
scaled by potential / (100 + 25 x skill): low skills at high potential level fastest. A hit pays the weapon skill
clamp((target LV + 10 - skill)/2, 1, 10) + target LV/10 (+~25%), plus Tactics and the style skill: the LV10 home dummy pays
low skills only (Martial 14 well, a skill past ~25 little); the LV35 sand bag would pay ~5x, its recipe isn't known here.

## Run 46's measures (exp per real hour at x5, Lv40-41)

| Method | An hour | A game day | What it spends |
|---|---:|---:|---|
| The circuit (danger 6-16) | ~99 | ~5 | ~24 game days an hour; earns gold, nefias (+60 points each) and karma |
| The dummy, riding Kaberg, unarmed (Martial 14 -> 27), the practice chest between bars | ~945 | ~9 | ~105 game days an hour, a meal each |
| The dummy, riding Kaberg, a long spear after Guroot's +200 Polearm potential (38 platinum) | **~1,107** | **~14** | ~78 game days an hour; the potential is spent in ~5 level-ups |
| Music (a flute) in a town | ~490 | ~6.7 | ~73 game days an hour; ~2,000 orens of tips an hour; **~100 karma lost with the party along** |
| Quick Craft (bait) | ~0.06 exp a SP | | the normal window pays the station formula, not TaskCraft's +200 an item (that needs the game's altCraft option: the user's yes 2026-11-13, on from run 47; `craft.py` waits for LayerCraft, the floating window is LayerCraftFloat: facts #1400, #1409) |

**The cost side** (the user decides the trade; asked at run 46's close-out): at x5 a training stretch burns game days 4-6x
faster than a circuit. Each game day is a meal (~55 nutrition), a day's rent (~210 orens at 6,292 a month), corruption
(an ether disease came after ~210 game days in run 46), and 13 points of the run score. Per real hour the score had the
circuit near +755, the dummy -420 unarmed and +90 with trained potential, music -285.

## How to run a training stretch

1. **Food first:** ~1 meal a game day; a 45-minute dummy stretch eats ~100. Buy every dish (`buyfood.py --min-ratio 0`) at
   two or three shops (an inn has 20-40), keep them in the Cooler Box, and know which carry 【Waking】 Anti Sleep (a loop
   that sleeps refuses them; a floor doesn't).
2. **Potential just before:** `trainpot.py NAME=POT` with the trainer's list open (Guroot in Mysilia: weapon skills;
   Frealord, Ceroyon: crafts); the platinum is boxed at 66,46. +200 at a skill under 20 is ~38 platinum.
3. **The weapon:** the lowest weapon skill with a weapon in the boxes (`stock.py --find spear|mace|staff`); unarmed trains
   Martial Arts. Take the sword off first (item.py refuses a second weapon beside it).
4. **Mount Kaberg:** she waits at home; the resident board's Residents -> her row -> `bridge.py menu text=Find`, talk,
   "Join me!", then `bridge.py ride 488`. Riding trains every tick mounted.
5. `trainday.py N --no-farm` in the background with `pulse.py` and a watchlog monitor; it eats from the Cooler Box, the
   harvest box and the fridge (and returns a borrowed stack to its own box), fights weak hostiles before a meal, closes
   the shipping report, and sleeps in the pine bed. `runs/jobs/trainday.stop` ends it at the next day.
6. **After:** `bridge.py ride off`, Kaberg "Wait at your home", the sword back on.

**Watch:** the dummy's swings hit whoever stands beside it (a visiting guard turned hostile in run 46: karma -5, fact
#1402). Music only solo (`music.py` refuses with the party, stops on any karma loss), and move on when the tips stop: a
fresh crowd paid ~6x a bored one.

## What this skill changed

New in run 46 (G55). Measure: exp per real hour and per game day of each marked stretch (runs/activity.csv). Baseline:
the circuit, ~99 an hour and ~5 a game day (run 46). Latest: the dummy with trained potential, ~1,107 and ~14 (run 46).
