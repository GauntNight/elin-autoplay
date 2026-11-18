---
name: elin-guilds
description: Guild work in Elin - the user's guild rule (every guild keeps rising to rank 6), reading contribution in the journal, where each promotion is given, and each guild's method. Thieves by stealing in Derphy and selling to the fence (steal.py, fence.py, the karma budget, the fence's hours, the Fighting Bull worn, the named-witness rule). Merchants by investing in shops (invest.py, cost per contribution point, low-level shops first, never a town secretary). Mages by decoding ancient books (decode.py --fetch on every return, the clerk's place). Fighters (done at rank 6). Use when a guild goal is in the session plan, in Derphy, Lumiest, Port Kapul or the Merchants Guild office, before any theft, investment or decode, and when a promotion is open.
---

# Guilds: Thieves, Merchants, Mages, Fighters

**The rule (the user, 2026-11-01):** "all guilds should keep increasing until they are max rank". Rank 6 is the game's
cap. A guild goal done sets the next rank as a goal at once (elin-goals); the goals and their milestones are in
`knowledge/goals.md` (G62 Thieves rank 6, G63 Mages rank 5, G58 Merchants rank 6 at this writing; G57 and G49 done in run 52; the Fighters are done).
The review of 2026-11-11: the three ride along with the circuits and the trips, without a plan slot of their own.

**Read the number:** `python -I tools/journal.py guilds` prints each guild's rank and contribution from the journal
(never during a running circuit: its window stops the loop). The overflow past a rank's bar carries over (G50, run 43).
A promotion is asked for at the guild's clerk once the bar is full: one dialog at a time (elin-play).

| Guild | Earned by | Tool | Promotion at | Binding resource |
|---|---|---|---|---|
| Thieves | selling stolen goods to a black market | `steal.py`, `fence.py` | Monazess, Derphy B1 (stand in the east room, 72,72, to see her) | karma: -1 a theft, about +5 a conquest |
| Merchants | investing in shops | `invest.py` | Rosetta (39,35), the Merchants Guild office next to Mysilia | orens above the six-bill reserve |
| Mages | decoding ancient books | `decode.py --fetch` | Lovashy, Lumiest B1 (near 40,93, beside Fleaun) | ancient books from nefia chests |
| Fighters | the elites killed on floors (G31: "1000/1000 from the elites of runs 30-33") | the circuit | Narford, Port Kapul | done: rank 6 (G40, run 43) |

## Thieves (G27, G32, G51, G53)

**The code** (`steal.py`'s docstring; AI_Steal, ShopTransaction): only **Sleight of Hand** marks a thing stolen. A plain
Grab of NPC property costs karma without the flag, and goods bought in the guild's own shops lose it at the counter. A
theft is 20 turns beside the thing, 4 checks; at each, every witness within 4 with line of sight rolls rnd(PER x 2.5,
doubled for a unique) against my Pickpocket + DEX (+30 when it can't see me); one hit cancels the theft and turns the
witness hostile. A stolen unit sold to a black market pays the guild (int)sqrt(unit price) / 2. Below rank 4 only Derphy
town (Siyun), Port Kapul (Minwer) and my own land buy stolen goods; rank 4 lets Leoban and the guild's own fences buy.

**The method (run 43; G53's How):**

1. **Derphy town only** (no guards there: a witness who notices only turns hostile). Wear **the Fighting Bull** in Derphy
   (it protects from thieves, or the pickpockets take thousands; it lives in the loot bag and `shipstar.py` never ships
   it; a swap leaves both pieces mine: shipstar keeps the swap pair since run 44).
2. `python -I tools/steal.py auto TARGET 70 --bold`: the marks best first until their contribution adds up to TARGET. At
   DEX 61 a plain townsperson can't notice (run 43: 66 thefts in minutes; the old levels and the sneak guard had refused
   nearly every mark for 13 runs).
3. **The named-witness rule:** a named NPC from Lv15 still blocks a theft beside them (run 43: Monazess Lv26, a unique,
   caught one and stayed hostile, after I had raised the limit from 15 to 30 without a reason). The limit changes on a
   read of the formula against today's numbers, never in the moment.
   **A witness behind a door is not in view** (run 48: Anastazija, the doorman, Lv32, caught a theft by the pub's stairway
   from the next room and broke the door down): when one turns hostile, walk away or take the stairs. Her death cost
   Karma -5, the karma the thefts spend: `fight.py` refuses in a town without `--town-ok`.
4. **The karma budget:** `steal.py auto` stops itself at karma 20 (`--karma-floor N`; 0 is the last non-criminal value)
   and at burden phase 2 (`--burden-phase 3` only while staying for the sale) (run 44: run 43's batch ended Overweight
   with the fence asleep). **Phase 3 only with the fence open and a few cells away**: an Overweight walk costs HP on
   every step (run 49: furniture batches of cat statues and laundries, Siyun asleep, then 403 -> 277 over ~10 cells to
   her; the heaviest non-stolen things dropped to get back to phase 2). **Start a phase-3 batch beside the fence:** past phase
   1 `steal.py` takes only marks within 6 cells of where the batch began (run 53: a batch ended 17 cells off, ~23 HP a step;
   hung meats, a sofa and side tables are the heavy marks). Karma is the binding resource: -1 a theft, about +5 a conquest, so thefts alternate with
   circuits (run 45: 60 thefts took karma 80 -> 20; ten conquests paid it back to 65 for 45 more).
5. **Sell:** `python -I tools/fence.py Siyun` (Derphy ~95,81; Josotta or any prostitute gives directions). It sells what
   steal.py logged to `runs/stolen.txt`, pulls 8 stacks a bag a pass (run it two or three times), never sells kit items,
   checks that the gold moved, and closes the shop: **the contribution is booked when the shop window closes**.
6. **The fence's hours:** Siyun traded about 15:40-21:40 and slept at night in run 44 (run 43: asleep at 05:37 and
   13:04, trading at 19:37 and 23:56); run 45 sold at 20:25, 20:17 and also 10:42: her hours vary. A theft batch at night
   (sleepers can't witness), the sale in the afternoon or evening; **try the sale and read fence.py's result** rather
   than write down "asleep" unchecked (run 45). Leoban on B1 refuses a high-karma buyer ("a straight-laced adventurer", karma 73)
   but **bought a night batch at 01:00 with karma at the floor 20** (run 51, fact #1492): end a batch at the floor and sell to
   him at once (`bridge.py walkto 63 65`, `fence.py Leoban`), no wait for Siyun. **Run 52: he bought at karma 45 too**, and Siyun at 06:14 and 17:32. A stolen "cargo" container sells
   for ~120 (a few points): fence.py sells it now, though runs/carry.txt keeps it from being dropped or shipped.
7. **An ether disease can end a theft night** (run 52, fact #1512): with Enemy of All Living Things every townsperson turns hostile
   on sight; steal.py fights those 20+ levels under mine and goes on, but a second night got 0 thefts. Cure it before a batch.
   Incognito (scroll or spell) is no cure (fact #1514): a read calms everyone once, but the disease's roll ignores my disguise,
   so it buys a quick sale or shop visit, never a batch. **Cured in run 53** (the antibody at Miral's): that night 69 thefts,
   Thieves 42 -> 240; both fences ran out of money by morning (Siyun after ~33 sales, Leoban after ~20), so a big night
   sells across both and the next afternoon.

Yield: about 4 contribution a theft at DEX 61 (run 44), about 2.9 once sold in run 45 (0 -> 310/1,000 over two visits,
105 thefts). `steal.py [R]` alone lists the marks in reach (weight against Pickpocket x 200 + STR x 100 + 1000, the
stolen sell price, the contribution a unit); `steal.py take UID ... --skip` takes named things under the bridge's sneak
guard (run 33); `steal.py R --steel` lists liftable always-steel marks (run 32, the user's idea: alarm clocks, wall lamps, monitors;
Aquli Teola's mica solar panels weigh 4,800, under my limit).

**The guild's place:** Derphy, stairs at 68,73 in the pub (doorman Anastazija; member since 485-12-10, run 07). B1 is
seen only from inside its rooms: from the stairs and Kerona's counter the bridge shows nobody. The clerk Monazess has
"Where is..." (Kerona's shop ~64,66, Leoban's black market, the trainer Gizhert: Gun, Marksman, Greater Evasion,
Pickpocket). Derphy as a town (the way in, the Lockpicking trainer, the board): elin-travel's reference.

Crimes outside this method (mining or hammering town property, `sneakmine.py`): elin-travel 5. Below karma 0 the law
towns refuse to trade and their guards attack.

## Merchants (G26, G39, G42, G50)

- **Joining (run 17):** 30 flyers handed out with `tools/flyer.py` (the adjacent "Gift" to Lv1-8 townsfolk; never twice to
  one NPC); Negotiation from Levadear. Salaries come to the home mail post as parcels (rank 5: 500 a month). The office
  (next to Mysilia) serves members only.
- **Contribution is investment:** `python -I tools/invest.py NAME [MAX=600] [TIMES=1]` talks to the shopkeeper, reads the
  shop level and the price, says Yes only at or under MAX orens, then Bye, and prints the guild contribution. Each direct
  investment raises the shop one level and pays 5 + the shop's new level. The price climbs with the level
  (CalcMoney.Invest: max(c x 700, c² x 80 + 200), less CHA/2 + Investing).
- **What a shop's level buys** (fact #1456, the game's code): more items a restock (about 4 at level 1, 8 at 10, 10 at
  15), made at the shop's level, always of normal rarity. It never makes a shop sell ☆ gear (the user asked, after run 49).
- **Which shops: the ones that stock what runs short** (the user, 2026-10-30, fact #1025: the shops we frequent that
  have valuable stuff, not shops picked for cheap points; 2026-11-16, agreed for these stores: "they close a gap we tend
  to [have] and are high value"). Potions and scrolls aren't short (stock.py ships the excess every
  visit); the waivers are: fireproof blankets (98 rows to run 49) and lockpicks (52). Both turn up at random in general
  stores and the thieves' shop: Sesa and Sayig (Aquli Teola, never invested), Gizbird (Mysilia), Tarraf (Palmia), Kerona
  (Derphy B1). A store taken from 1 to 10 shows about twice the items a visit, so about twice the chance of either.
- **Low-level shops first among those, then the rest** (run 29; G50's How): a level 1 shop cost 143 orens for +6, level 2 504 for +7, level 7-10
  3,000-4,800. Run 43: Ilass 2 -> 11 and Diefon 1 -> 12 at 158-245 orens a point, against 375-440 at levels 13-14. Runs
  44-45: Palmia's and Derphy B1's shops 7 -> 10 at ~220-225 a point. **Run 50's all-in (G50 done, rank 5):** a step from
  level L costs about 2,500 (L 8), 3,050 (9), 3,600 (10), 4,450 (11), 5,350 (12), 6,350 (13), 7,450 (14), 8,600 (15),
  9,450 (16) and pays 5 + L + 1; capped at ~7,600-8,700 a step it came to ~330 orens a point over 17 shops. **Shops at 14-17
  now:** Palmia (Tarraf 18, Eligin, Monashy, Kazretta, Koflord, Shuzastan, Semnof), Aquli Teola (Sesa, Sayig, Esdor), Derphy
  (Siyun, Kerona, Leoban, Erobird, Fortoli 17), Lumiest (Robean, Vuten 16, Tomyin 13), Noyel (Bethberk 14, Alecgan 12), Willow (Chim 12:
  8 -> 12 for 2,485, 2,840, 3,388, 4,159, a few percent under the table above at 9-12, fact #1480). **Run 53 read
  and raised:** Noyel Miscold 3 -> 9, Nuwert 1 -> 4; Olvina Wyward 9 -> 12, Hesbald 2 -> 8, Vanloot 3 -> 7, Raiyas 5 -> 6,
  Iofael 9 (fact #1528); **Lumiest's Teolarg and Raydorre were already 13** (this list had them as never invested);
  Sayig 15. Still unread (G58's possible cheap points): Willow's Agasard (the butcher; fact #1481 lists the town); Noyel's
  Ceshed, Oldotta, Teoyan; Mysilia, Tinker's Camp and Yowyn shops (levels from runs 21-43). Monazess's guild shop takes no investment.
- **Never a town secretary:** that investment pays the guild nothing (fact #1336).
- **The budget:** only orens above the six-bill reserve; G58 (rank 6, 2,600) takes what the circuits and the chest bring in.
- The guild's informers buy fame: `famesale.py` (elin-delve 2: a sale also pulls the nefia refill back under the gate).

## Mages (G34, G36, G43, G49)

- **Contribution is decoding ancient books:** 5 + 2 x tier each, once a title (a deciphered copy refuses and stacks).
  The books come from nefia boss chests.
- **`python -I tools/decode.py --fetch` on every return home** (it is in elin-home's arrival list; run 40: my notes said
  three books waited, the boxes held ~40): it takes the undecoded books from the home's boxes, as many as the free cards
  allow and no two of one name, decodes them highest tier first, ships the deciphered copies and repeats until no box
  holds one. Never a cursed book. Run 33: 13 books took the guild 0 -> 100/100 in one night; run 43: 108 -> 254/1,000.
- **The risk** (TraitAncientbook): a read is ~16 checks (Literacy 25) against 10 + 15 x tier; a failure spends a charge
  and drains half the max mana, confuses, teleports or summons read-fail monsters, even at home. **decode.py refuses
  under half MP: below that the mana drain overflows into HP** (run 33: 199 -> 109 at MP 7), never reads confused, and
  stops on any hostile in view.
- **The clerk's place:** Lovashy on Lumiest B1, near 40,93 beside Fleaun (not found on three visits; the fourth found
  her, run 39; run 52: asleep at ~05:40, at her desk by ~08:40). To Lumiest by Fast Travel, never a walk (fact #1168). Rank 4
  done in run 52 (G49); rank 5 is G63.

## Fighters (G31, G37, G40: done)

Rank 6 since run 43 (492-05-21, promoted by Narford): nothing left to earn. For the record: the guild is in Port Kapul
(Doria the watchman on the stairway at 58,98; the trial was 20 yeeks; the office below; Narford the clerk's "Where
is..." finds Stanmock the trainer: Dual Wield, Mind's Eye, 10 platinum each), and its contribution came from the elites
killed on nefia floors. **Port Kapul's harbour is deep water: I drowned there in run 19** (elin-travel 5).

## What this skill changed

New at the review of 2026-11-11 (plan D): guild work lived under the old town-trip skill's "Other places (runs 03-05)", two
tool-notes rows and the goals' "How" paragraphs. Measure: errors.csv repeats in the thief domain, and contribution per
real hour for each guild goal (the goals' run notes).
