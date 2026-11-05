---
name: elin-opening
description: Step-by-step procedure for Elin's opening tutorial chain on a new character (land deed, Fiama's pet and shop, Ashland's board quests one at a time, Frontier Inspector/Loytel, Defense Training punk and boar, Way of Crafter up to the first house). Use when a game is in its first days or any tutorial quest from Ashland, Fiama or Loytel is open.
---

# The fast path (the level 1 trials, runs 41-44)

Everything below is the reasoning; for a new game these tools do it. Compared to the first game's Lv2 at minute 250: Lv2 at 14, Lv8 at 96.

1. `tools/newchar.py RACE CLASS` from the title. Then `tools/opening.py`: speed x5 (`bridge.py speed 3`, the game's own control, reset by every load), the whole
   chain to Way of Crafter's training dummy beside a bed in about 7 minutes. A stop names its stage: finish by hand, then `--from STAGE`.
2. `tools/tickets.py`: every first-time craft pays an old ticket (117 orens anywhere): sawmill, carpenter's and tinker's tables and their recipes. Hand-broken stones need no pickaxe.
3. **Walk** to Mysilia (`wgo.py --near 0`; a third of the hunger assumed, seconds of real time): sell tickets, buy the cheapest melee weapon and armor (PV 0 is what kills), then food by
   food per oren: bones and roasts 13 orens for 27, bread 27 for 31, rations 48 for 51. NPC names change per world: `whereis.py any blacksmith` (the role), by day.
4. `tools/earlyday.py N --rotate`: crops, meal, the rest of the bar on the dummy at the lowest skill I can hold, sleep. Yerles level fastest (Fast Learner); bare hands count.
5. From Lv3: `board.py`, `board.py --take NAME`, `arena.py`: Monster extermination, Monster hunting and Troubled home at Danger 1-2 pay 166-274 orens, influence and sub rewards in a minute. **Instance job first, count jobs after** (a cap of about 5). The ally along, armor on.
6. Food and gold go together: back to step 3 when the food runs out. `feat.py` for each point (Tough, Stone Defense first; SP feats do nothing past waking SP ~41 on a makeshift bed). `tools/ability.py Rest` heals fast and sleeps under 20% SP; `Pray` is free Faith.

Don't: enter a field tile by hand; force a fight the tool refuses; melee kinds on elin-play's range list; sleep by hand at hunger 60+ (Starving costs HP fast). Before day 90 a death costs nothing but time: Crawl up.

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
