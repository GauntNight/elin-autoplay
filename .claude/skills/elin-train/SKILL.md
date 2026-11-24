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
| **Run 47, the same method on fresh skills:** Staff 15 at pot 300 (38 platinum) for 31.6 minutes, then Mace 17 at pot 300 (21 platinum) for 14.1 | **~1,133** | **~12.7** | ~89 game days an hour (45.7 minutes, ~68 days, +863 exp); about break-even on the score (~884 for the days) |
| Music (a flute) in a town | ~490 | ~6.7 | ~73 game days an hour; ~2,000 orens of tips an hour; **~100 karma lost with the party along** |
| Quick Craft (bait) | ~0.06 exp a SP | | the normal window pays the station formula. TaskCraft's +200 an item has **no route in EA 23.355** (run 47, lead 4 closed): altCraft has no Options toggle (only Save/config.txt, flipped by the user with Elin closed), and its floating list is always empty because `Thing.GetRecipes` is a stub (bridge `qcraft` read 0 recipes beside the stations; facts #1410, #1411). **Off since 2026-11-14** (the user: "get rid of altcraft"): to recheck after a game update, ask the user to turn it on with Elin closed, then `bridge.py qcraft` |

**The cost side** (the user decides the trade; asked at run 46's close-out): at x5 a training stretch burns game days 4-6x
faster than a circuit. Each game day is a meal (~55 nutrition), a day's rent (~210 orens at 6,292 a month), corruption
(an ether disease came after ~210 game days in run 46), and 13 points of the run score. Per real hour the score had the
circuit near +755, the dummy -420 unarmed and +90 with trained potential, music -285.

## The way to train (G55 M2, adopted run 47)

**When exp is the aim: the home dummy, riding Kaberg, with the lowest weapon skill at a trainer's +200 potential bought
just before.** It paid ~1,107 (run 46) and ~1,133 (run 47) exp an hour against the circuit's ~99, on Polearm, then Staff,
then Mace. The user's rule (2026-11-13): training only in stretches that about break even on the score, because the dummy
burns ~80-90 game days an hour (13 points, a meal and a day's rent each). One skill's potential is spent in ~10 level-ups
(Staff 15 -> 25 in 31.6 minutes): then switch to the next lowest skill and buy its potential (Guroot: Martial Art, Long
Sword, Axe, Staff, Bow, Polearm, Short Sword, Crossbow, Scythe, Mace). Left: Bow 10, Crossbow 4 (ranged: `--shoot`
needs arrows), Short Sword 17, Scythe 20.

## What platinum buys, in order (the user, 2026-11-24: "once all skills are learned use what makes most sense next to optimize the points")

1. **An unlearned skill** (5): none left, 62 of 62 (a game update may add one: read `bridge.py skills` after it).
2. **A Shared Diary** (200, Eligin in Palmia) whenever 200 coins ride and Palmia is on the way: about 1.9 points a coin, no play time
   (the fact "platinum pays"). Read one, check the exp moved, then the rest; ten in stock, restocked every 360 days. The coins must be carried.
3. **A trainer's potential** only just before a stretch that uses the skill (1.5 points a coin at skill 10, 0.7 at 50): never to be rid of coins.

## How to run a training stretch

1. **Food first:** ~1 meal a game day; a 45-minute dummy stretch eats ~100. Buy every dish (`buyfood.py --min-ratio 0`) at
   two or three shops (an inn has 20-40), keep them in the Cooler Box, and know which carry 【Waking】 Anti Sleep (a loop
   that sleeps refuses them; a floor doesn't).
2. **Potential just before:** `trainpot.py NAME=POT` with the trainer's list open (Guroot in Mysilia: weapon skills;
   Frealord, Ceroyon: crafts). +200 at a skill under 20 is ~21-38 platinum. **The coins must ride to Mysilia: put
   `platinum coin` on runs/carry.txt first** (run 47: arrive.py's sort boxed the 280 coins, the list showed 0, and the
   round trip for them cost ~8 real minutes); take the line off after.
3. **The weapon:** the lowest weapon skill with a weapon in the boxes (`stock.py --find spear|mace|staff`); unarmed trains
   Martial Arts. Take the sword off first (item.py refuses a second weapon beside it). A skill trained once moves past the
   dummy's range: Polearm went 15 -> 29 in run 46, so run 47 took Staff 15 (the obsidian long staff, Armory 2 48,59).
   arrive.py's packcheck puts the training weapon back in its box: take it out after the arrival sort, not before.
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
the circuit, ~99 an hour and ~5 a game day (run 46). Latest: the dummy with trained potential, ~1,133 and ~12.7 (run 47,
Staff then Mace; run 46's Polearm ~1,107 and ~14).
