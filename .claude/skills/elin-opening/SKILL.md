---
name: elin-opening
description: Step-by-step procedure for Elin's opening tutorial chain on a new character (land deed, Fiama's pet and shop, Ashland's board quests one at a time, Frontier Inspector/Loytel, Defense Training punk and boar, Way of Crafter up to the first house). Use when a game is in its first days or any tutorial quest from Ashland, Fiama or Loytel is open.
---

# The fast path (Start Runs 1-7)

Everything below is the reasoning; for a new game these tools do it. The first game's Lv2 took 250 minutes and its Lv8 1,982; with this path Lv2 took 14 and Lv8 96. In two hours four Yerles Warriors earned 843-1,116 exp, a random Warmage 870, a Thief 661 (out of food and money), a Gunner 875 with no deaths (Start Run 7, the best pattern for a character the rules weren't tuned on: armor by minute 39, jobs from minute 52, Riding at 84). Level 10 hasn't been reached: the best is Lv8, about 300 exp short.

1. `tools/newchar.py RACE CLASS` (or `random random`) from the title. Then `tools/opening.py`: speed x5 (`bridge.py speed 3`, the game's own control, reset by every load), the whole
   chain to Way of Crafter's training dummy beside a bed in about 7 minutes. A stop names its stage: finish by hand, then `--from STAGE`.
2. **Read any starter books down**: a class's spellbooks take about 7 reads and no SP for three spells and a Literacy level. A Teleport spell saves lives even with one cast in three failing at Casting 4.
3. `tools/tickets.py`: every first-time craft pays an old ticket (117 orens anywhere): sawmill, carpenter's and tinker's tables and their recipes. It skips what has paid. Hand-broken stones need no pickaxe. **Stop at about 10 tickets, minute 15**; `firstcraft.py STATION --craft` picks up the rest later. Make the **Boomerang** (4 planks, 2 strings): it returns and it kills.
4. **The camp, not the capital** (the user, Start Run 5: "The local tinker camp is probably a better place to go until you have food/things under control. Long trips are dangerous until you have sufficient food and equipment for the road."). Tinker's Camp is 5 miles from home and always allowed; `roam.py` refuses anywhere further under PV 10 without food for the road. Three deaths in Start Run 5 came from overriding the route limit at Lv1-2. Sell tickets at any shop. **Armor first**: the second number is PV (a stone breastplate [0, 9] for 208 took Start Run 7 from PV 7 to 16 at Lv3; it died zero times). Then a real melee weapon (a mace 4d4+2 for 162 tripled the damage), and a scroll of teleport (58 at the mage). **The camp sells no food.** Shopkeepers sleep at odd hours: come back. NPC names change per world: the role id.
5. **`tools/earlyday.py N --rotate` until the melee skills reach about 9: nothing pays like it.** Crops, meal, the bar on the dummy at the lowest skill I can hold or throw, sleep, in cycles of 14 seconds: 30-40 exp a real minute at the start, because a hit also trains Tactics and Strategy from level 1. With no food it cooks corpses and weed stew at about a third of the speed, which still gets to level 3-4. Start Run 4 did this from minute 66 (435 exp in 26 minutes against 240 in the 60 before); Start Runs 2-3 from minute 20.
6. **Food trips, armored, with a scroll, and leaving under hunger 50:** `buyfood.py` at Mysilia's inn (bones 13 orens for 27; the inn sometimes has no wares). A leg costs 20-30 hunger and an ambush more; starving drains HP and SP fast: Start Run 6 died three times at hunger 91 walking for food it had left too late for. The dummy eats 60-100 hunger a real minute at x5, so `earlyday.py` stops with 2 meals in hand. **Nothing else nearby sells food.** With no money: desks sell for 19, a raw corpse is 14 hunger, `earlyday.py N --rotate --no-reserve` holds hunger near 59 on weed stews at 7 exp a minute while the boards refill, and a job is the real answer: the camp's and Mysilia's boards can each go dry for several visits. `startloop.py MINUTES --cycles 10` runs the circle of jobs, food and dummy: Start Run 7's last 40 minutes earned 442 exp on it.
   **The tax clock:** bills come monthly from the first month and lie in the home's mail: the fourth unpaid one (first of the fourth month, 485-09-01 from a 485-05-12 start) costs Karma -50, and Mysilia's guards (Lv40) then kill on sight. At x5 that's about 100 real minutes away. Pay one (G1's chest), or stay away from Mysilia after it; the camp still takes a wanted character's jobs and teaches, though its smith's shop didn't open once.
7. **Jobs from level 4, with the ally beside me at 70%+** (`board.py --take` refuses less; under Lv4 only with PV 15 and 2 scrolls to spend: HP 22 -> 4 three times at Lv3): `board.py`, `board.py --take NAME`, `arena.py`. Monster hunting, Monster extermination and Troubled home pay 155-295 orens, influence and sub rewards in a minute, little exp (more while armor skills are at 1). At PV 19 three in a row cost 4 HP. A Danger number says nothing about the count: Danger 1 sent ten foes at once. Check both boards: Mysilia's and the camp's each go long without one. **Instance job first, count jobs after** (a cap of about 5; Troublesome monsters and Foul race are count jobs). **An ally who fell rejoins only when I next arrive home:** look for the `party:` line before walking to a board.
8. **Past skill 8-9 the dummy pays 2-5 exp a minute. Refuel it:** a cheap weapon of each untrained kind (spear 208, scimitar 162, war sickle 304: 20-40 exp a minute again). **Riding at the first 5 platinum (4 with Fast Learner), which jobs pay:** a mounted 19-mile leg paid 31 exp in 26 seconds at Riding 1, 18 in 25 at Riding 4; ride only with PV 10+, it lowers speed. `tools/roam.py Meadow Mysilia --danger-ok 5` runs the road with its own ambush routine. Desks at the carpenter's pay 11 skill exp a SP at Carpentry 1-2 and sell for 19.
   **A foe above my level at home:** keep throwing the boomerang (5 throws took a crab Lv6 from 70% to 25%, Throwing 7); running lets it heal, and leaving the map brings me back beside it. Fiama kills what reaches her.
9. `feat.py` for each point (Tough, then Stone, Iron and Steel Defense: PV 1 -> 23 with step 4). `tools/ability.py Rest` heals fast, free on the world map (3 -> 28 HP in seconds), and sleeps under 20% SP; `Pray` is free Faith.

Don't: enter a field tile by hand; force a fight the tool refuses; take caves or nefias under Lv10 (`arena.py --any` refuses); melee kinds on elin-delve's range list (section 6); sleep by hand at hunger 60+ (Starving costs HP fast); carry over 33 cards (meals fall to the ground). Before day 90 a death costs nothing but time: Crawl up (`common.crawl_up`). Past Lv7 the road can still kill in one exchange: a danger 6 field took a 62 HP character down in seconds.

**What this skill's fast path changed** (seven 2-hour Start Runs, 2026-11-04 and 05). Measure: minutes to Lv8. Baseline: 1,982 (Rolord). Latest: 96 (Start Run 2), 106 (Start Run 3), 111 (Start Run 5); the three others never reached it in two hours. Deaths in the seven: 4, 0, 5, 3, 5, 5, 0; Lv10 was not reached in any.

# The opening, in order

Uses the tools from the elin-play skill. After each numbered step, `look.py` and check the
expected result before going on. One quest dialog at a time (see elin-play hard rules).

1. **Wake up.** `talk.py 40` through the intro and Nerun (Adventure Log). Pick up the vegetable
   soup by the bonfire (food for later; it's yours).
2. **Deed.** `talkto.py Ashland`: he drops the land deed at your feet; answer `Bye.`.
   `acts 0 0 all` -> Pick; `item.py "Land Deed" Read`; Dialog "Really claim this land?" -> Yes.
   Expect: "You claimed the land", a Hearth Stone, danger 1 -> 3. Quick-save.
3. **Rewards.** `talkto.py Ashland` again: iron woodcutter's axe and 10 gold bars on the ground.
   `Bye.`, then Pick all.
4. **Fiama.** `talkto.py Fiama`: pet choice -> **A little girl!** (full humanoid equipment slots).
   Then "Let me see your home equipment": buy **a home board** and **a resident board**
   (1 gold bar each, via `invacts`/`invdo` "Buy 1"). Keep the other 8 bars for hiring.
   Close the shop with `act Cancel`; Nerun's axe tips follow (`talk.py`).
5. **Board quests, one at a time** (`acts` on the quest board -> View Works -> `click` one).
   a. *Essential Equipment*: a sturdy box drops. Pick it, `item.py "sturdy box" Grab`, place with
      `acts 1 1 right` -> Place, open it, `winbtn buttonShared` (tip must read "Shared"), close,
      `talkto.py Ashland`. Expect "You complete the quest", Karma +1.
   b. *Frontier Inspector* (appears after a.): choose **"I want the help of a frontier
      inspector."**, `talk.py` to the end. Expect the log line **"Frontier Inspector 『Loytel』
      joins you."** If it's missing, stop: the quest went wrong.
   c. *Defense Training*: a punk (Lv 1) is tied to a gallows behind the board
      (west, about 47-48,55). `fight.py punk`. Report to Ashland: he drops 20 granite pebbles,
      potions of blindness and confusion, 5 bandages. Pick all. The boar (Lv 8) is tied at the
      same gallows: `item.py "granite pebble" Grab`, then throw from 3+ cells
      (`acts DX DZ right` -> Throw) until dead. Pick up pebbles, corpse and skin from the cell
      beside the gallows. Report: the last phase is "defeat 100 enemies" (open-ended).
   d. *Tax Liability*: just wait for the bill; pay it when it arrives.
   e. *Way of Crafter*: see the elin-build skill (logs -> Quick Craft workbench -> string -> torch,
      equip it -> walls + door -> house). Report to Ashland after the workbench, after the
      torch, and after the house.
6. **Loytel.** Talk to him for *First Shipping Box* (a shipping box made of **palm/Palulu**
   wood, installed). Later quests unlock after waiting a few in-game days.
7. **Fiama's later topics.** Her week-one "Vision for the Future": never pick "I want to die".

## Before you start

Check `power.py`: a weak character can't afford this order as written. Budget stamina (it only comes back with sleep; see
**elin-setup** section 7), use `act.py` by name and `loot.py R --all`, and stay home until about level 5. Rewards land on the
cell you're standing on or beside: read it after each report.

## Known outcomes

- The new-game test (Lefess, a Lich Pianist with 10 HP and 25 SP, 2026-11-04): this order held, Essential Equipment to the house in
  20 real minutes on the first try. She ran out of stamina at the workbench and died on the road at Lv1: both now above.

- Run 02 (no skill): Frontier Inspector and Defense Training got crossed by batching; Loytel
  never joined. Run 03 (with this order): both correct on the first try.
