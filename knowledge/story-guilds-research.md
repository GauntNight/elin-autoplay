# Elin story, side quests and guilds: research for a Lv28 character (2026-10-28)

Text drawn from Ylvapedia (https://ylvapedia.wiki, its contributors) is CC BY-SA 4.0; this file adapts it.

> Kept from run 29's research agent (2026-10-28). Corrections from play since: the journal had Gold Beneath at
> **step 4** (talk to Loytel in Vernis), not 5; the Mages trial worked exactly as below (Raydorre's letter, Lexus);
> investing pays 5 + the shop's new count, but a town shop starts at its own level (Lumiest's were 1-10), so the
> "~180 for 6" holds only for a level 1 shop (facts #944, #954). The user picked the guild goals G24-G27 from it.

Sources: the decompiled game code (github.com/Elin-Modding-Resources/Elin-Decompiled, main, last
commit 2026-10-13 "EA 23.356.1 Nightly", one build newer than the installed 23.355), the project's
exported tables (knowledge/game/quests.json, zones.json, charas.json, things.json, elements.json,
materials.json), observed facts (knowledge/facts.jsonl), and ylvapedia (Elin:Home_Quest,
Elin:ホームクエスト, Elin:Sub_Quest, Elin:Guilds, Elin:Crypt_of_the_Damned,
Elin:Sunken_Temple_of_Lurie, Elin:Village_of_Atonement, Elin:Quests).

Many story steps live in drama spreadsheets (the game's Lang/Dialog files), not in code. Those were
not read (the task said not to touch the install). Anything that depends on them is marked
**UNCONFIRMED**.

## 0. Mechanics that govern the whole story chain

- **Timers.** `QuestManager.Add(id, chara)` puts a quest in `globalList` with
  `startDate = world.date.GetRaw() + N`. GetRaw counts minutes, so 1440 is 1 day, 7200 is 5 days,
  14400 is 10, 28800 is 20 and 43200 is 30.
- **Where they show.** `Quest.IsVisibleOnQuestBoard()` hides a quest until `GetRaw() >= startDate`
  and `CanStartQuest()` is true. A non-random quest shows only on a board in a **PC-faction zone**
  (the home or Vernis). A quest whose client is Loytel also needs Loytel to be in a PC-faction zone.
  `QuestDialog` sets `RequireClientInSameZone => false`, so the client doesn't have to be present.
- **Conversation events.** A QuestDialog quest completes as soon as it is accepted. Its
  `OnDropReward` then schedules the next one (QuestDialog.OnDropReward).
- **Danger.** A top zone's danger is `_dangerLv (zones.json LV) + |lv| + DangerLvFix`. A floor below
  it is `top.DangerLv + |lv| - 1` (Zone.DangerLv). That gives Crypt 32 on the map, matching the
  run-03 fact.
- **Quest-dungeon scaling.** `Zone_QuestDungeon.DangerLvBoost` lifts quest dungeons to
  FameLv x 2/3 only when the game's "scaleQuest" oath is on (GamePrincipal). It is off by default.
- **The rest of the story is locked behind Gold Beneath.** `pre_debt` is added in
  `QuestVernis.OnComplete` (and in a pre-0.22.52 save migration), and every later story quest chains
  from it. Nothing in the code adds any of them on game date, home rank, fame or level. The answer
  to "startable without finishing Vernis?" is **no** for after_vernis through stone_dream.
  farrisSister is UNCONFIRMED (section 1).

## 1. The story after Vernis, in order

### vernis_gold (Gold Beneath): the gate. Journal: step 4 (corrected)
QuestVernis.CanUpdateOnTalk: past phase 0, Loytel advances the quest only when you talk to him
**in Vernis**.
- **Phase 4 → 5:** talk to Loytel in Vernis once `_zone.IsPCFaction` (Vernis is claimed, so this
  works now). OnChangePhase(5) moves Quruitzia, Kettle and Farris to Vernis and makes all four
  Vernis branch members.
- **Phase 5 → 6:** `IsCompleted("quru_past2")` and Vernis branch level ≥ 2, reported in Vernis.
  quru_past1 "Ill-Eyed Girl" (Kettle) is added 1 day after quru_sing completes. quru_past2
  "Speaking of the Devil" (Farris) is added 1 day after quru_past1 (QuestDialog.OnDropReward). Both
  show on a home/Vernis quest board.
- **Phase 6 → 7:** talk to Loytel. OnChangePhase(7) drops 3 potions (id 8506; the wiki says
  acid-proof liquid) and a fireproof blanket.
- **Phase 7 → 8:** entering the Vernis Mine boss level (OnEnterZone).
- **Phase 8 → 9:** killing Tephra (`vernis_boss`, LV16), Vernis Mine B8. The project's goals note
  B8 is about danger 13.
- **Phase 9 and 10:** talk to Loytel in Vernis.
- **OnComplete:** Corgon becomes a resident; **mokyu** is added for +10 days and **pre_debt** for
  +20 days.

### after_vernis "Adventurer" (Loytel, "Ahem, come here.")
No code adds it; it is a QuestDialog, so a drama adds it. It probably comes from Loytel's final
Vernis talk. **UNCONFIRMED**, and the wiki doesn't list it. Expect a board conversation event after
Vernis.

### mokyu "Dragonic Language Lesson" (Corgon)
Added 10 days after Vernis completes (QuestVernis.OnComplete). An auto-completing board
conversation. Reward not stated.

### pre_debt "Beyond Despair" (Farris)
Added 20 days after Vernis completes. On completion (QuestDialog.OnDropReward "pre_debt"):
- Loytel moves to **Olvina (59,66)**, set noMove and invulnerable.
- `flags.loytelEscaped = true`.
- **pre_debt_runaway** "Missing Inspector" starts at once.

### pre_debt_runaway "Missing Inspector"
Find Loytel in Olvina's wine cellar (the wiki: the north-east corner near the vineyards). Olvina is
(+2,-13) from home (fact). Talking to him with loytelEscaped set (Chara.ShowDialog):
- completes pre_debt_runaway;
- adds **debt**;
- plays "loytelEscaped".

OnDropReward then adds **exile_meet** for **+30 days**. The wiki says "may need to wait until the
start of the next month".

### debt "And Thus Into Legend": open-ended
- **OnStart:** Loytel joins your home branch and party; you get cassette 109. `player.debt` starts
  at 20,000,000.
- **Bills.** Ask Loytel ("great debt") for a bill and pay it in a tax box. Paying from the bank
  works too (InvOwnerDeliver.PayBill). Talk to Loytel again: `stage++` and a reward
  (QuestDebt.GiveReward). Bill amounts are `{1,3,6,10,30,50,100}x10,000`:

| Bill | Amount | Cumulative | Reward |
|---|---|---|---|
| 1 | 10,000 | 10,000 | massage ticket |
| 2 | 30,000 | 40,000 | arm-pillow ticket |
| 3 | 60,000 | 100,000 | champagne ticket |
| 4 | 100,000 | 200,000 | resident ticket |
| 5 | 300,000 | 500,000 | Loytel Mart |
| 6 | 500,000 | 1,000,000 | Mart Lv1 |
| 7 | 1,000,000 | 2,000,000 | Mart Lv2 (spells and scrolls) |

- `CanGiveBill()` is `stage < 7`, so there are **no bills after 2,000,000**. The remaining
  18,000,000 can't be paid in this build, and nothing completes the quest: **open-ended**.
- The wiki: "Repaying the debt has no bearing on the scenario's progress."
- While it runs, every 1 November mails a Lumiest Crim Ale (GameDate).

### The exile conversations (all auto-complete on the home board)
- **exile_meet** "Whispers of Fate" (Quruitzia): added 30 days after Missing Inspector. Reward:
  Demitas becomes a resident.
- **exile_quru** "Long Night" (Quruitzia): +1 day after exile_meet.
- After exile_quru: **exile_kettle** "Creeping Shadow" (Kettle) at +1 day, and **into_darkness**
  (Kettle) at +5 days, unless it is already complete.
- **exile_whisper** "Hot Topic" (Farris): +1 day after exile_kettle.
- **exile_voice** "Voice in the Shadow" (Loytel): +1 day after exile_whisper.

### into_darkness "Into Darkness" (Kettle, ★)
- **On accept:** adds **demitas_spellwriter** for +1 day (QuestIntoDarkness.OnStart). Phase 0 then
  waits for Negotiation.
- **Phases 0 → 4.** Player.cs (on entering a PC-faction zone): when into_darkness is at phase 0 and
  negotiation_darkness at phase 5, Negotiation completes and into_darkness advances. Phases 1-3 then
  advance on each later home entry (scenes). The wiki says you receive 2 Bubbling Mysterious Vials.
- **Phase 4:** use the ★Pool of Stagnation (TraitDamnPool) on **Crypt of the Damned B6**.
  `event_az` spawns **Azrasizzle** ("Impure", LV38 undead god, warmage, staff_magius) and 6
  **cocoons** (LV28). The wiki: the field effect hatches the cocoons into spiders.
- **Phase 5 → 6:** killing Azrasizzle (Chara.cs).
- **Phase 6:** talk to Kettle at home. Phase 7: "await Issizzle's visit".
- **OnComplete:** Sorin becomes a resident. `reward_sorin` adds the **relic body slot** and the
  Embryolith (relic_lesser) recipe; the wiki adds the Dried Mandrake shop.
- Issizzle is the story's name for the dark power; the boss you fight is Azrasizzle. The code has
  no `issizzle` character.
- **Crypt of the Damned** (cave_dead, LV31): 6 floors, **danger 32 (B1) to 37 (B6)**. `LockExit`
  is false, so it can be entered at any time; Azrasizzle appears only through the quest event. B1
  and B6 are static maps.

### demitas_spellwriter "Spellwriter" (Demitas)
Added 1 day after into_darkness is accepted. Reward: Demitas copies spellbooks
(TraitDemitas.CanSpellwrite).

### negotiation_darkness "Negotiation with Darkness" (Loytel, ★)
Added on the first day-tick after demitas_spellwriter completes (GameDate). The drama gives the
Bracelet of Forgiveness (wiki) for the barrier at the **Village of Atonement**.

Phases:
- **0 → 1:** enter the village (Zone_Exile.OnActivate).
- **1 → 2:** talk to Bicerin (elder exile, LV25).
- **2 → 3:** see Duponne on Sunken Temple B5 (CardRenderer).
- **3 → 4:** either kill Duponne (Chara.cs: `killedDuponne`) or capture her with the ★Duponne
  capture ball (ActThrow).
  - The ball comes from the drama `duponne_capture`, which consumes the ★Minotaur's Great Horn.
  - The horn drops from **Ungogo** (minotaur king, LV32), Minotaur's Nest B5.
- **4 → 5:** report to Bicerin; the "duponne_rescued", "duponne_gone" and "duponne_killed" branches
  apply here.
- **5:** go home; it completes via Player.cs.

Reward (`duponne_reward`): Adventurer's Weekly #12, earth/sun/mana crystals, and 3 rune-mold
recipes. The wiki: killing Duponne is irreversible but gives the same reward; sparing her changes
Demitas's shipping picture.

- **Sunken Temple of Lurie** (temple_undersea): `IsUnderwater => true`, so you need water
  breathing or very high Swimming (wiki). The wiki notes coralwood equipment and ★Ribbon items as
  sources.
  - Danger by zones.json LV24: **25 (B1) to 29 (B5)**. The wiki says "entrance Lv.19", probably
    from an older version; trust the game table, verify in game.
  - Stairs at B4 are locked unless negotiation phase ≥ 2 (`LockExit lv<=-4`, `CanUnlockExit`).
  - Boss **Duponne**: LV30 sea dragon, equips ribbon_duponne, which has water breathing 10.
  - Respawn rate x3.
- **Minotaur's Nest** (cave_mino, LV25): danger 26-30. Not locked. Boss Ungogo on B5.
- **Village of Atonement:** (+49,-7) from home, computed from zones.json pos. It is always on the
  map; the barrier needs the quest.

**Observed in play (run 55, G66; the user's goal):** the quest came from the home board (Demitas gave the Bracelet of
Forgiveness). The village is at world 81,97, as computed above; Bicerin was in its one roofed room (phase 1 -> 2). The
temple's floors read 25 (B1) to 29 (B5), as zones.json says, and served as the floor gate's evidence ladder 26 -> 30
(facts #1545-#1547). B4's stairs showed as a "locked corridor" that opened on Use at phase 2. Duponne came into view on
B5 (phase 3) and stole salads from the pack; `ladder.py --spare Duponne` kept every tool from fighting her. **The user
chose capture** (2026-11-20). It needs Ungogo's horn from the Minotaur's Nest B5 at danger 30, whose B4 minotaur mages
cast Gravity (fact #1555).

**The capture ball in the code** (Elin-Decompiled main at EA 23.360.1 Nightly, read 2026-11-20: TraitDuponneBall,
TraitMonsterBall, ActThrow, QuestNegotiationDarkness; fact #1560):
- `TraitDuponneBall : TraitMonsterBall` overrides only `IsDuponneBall`.
- **The throw:** ActThrow's MonsterBall case checks only that the target is `lurie_boss`, not of my faction, and not in
  Zone_Exile or a user zone. No HP threshold, no level check and no roll: a plain monster ball's "HP <= 10%" and "level
  <= the ball's" checks sit in the other branch. A ball throw skips the attack roll, so it can't miss.
- **After:** the ball turns copper and holds her. At phase 3 the quest moves to phase 4 (`AfterTakeCareDuponne`).
- **A wrong target:** "monsterball_invalid", and the ball stays.
- **The release:** a filled ball releases only in Zone_Exile (the Village of Atonement) or survival mode. She becomes a
  Friend with the village as her home, influence +20, and the ball is used up.
- **Not found in this read:** the "duponne_rescued" branch, and the drama that makes the ball.

### stone_dream "Nightly Routine" (Loytel)
Added on the first day-tick after into_darkness completes (GameDate). Reward (`reward_stone_dream`):
Farris learns Song of Pebbles (6754) at 50.

### farrisSister "Visiting Little Sister" (Farris)
QuestFarrisSister is a stub (`CanUpdateOnTalk` returns false). No code starts it. A hidden zone,
Zone_SisterHouse, exists, and the drama has a `sister_money` condition (pc gold ≥ 10,000). It is
probably started from Farris's dialogue and could be open now. **UNCONFIRMED**; the wiki has
nothing on it.

**Rough story clock after Vernis completes:**

| Step | Earliest |
|---|---|
| pre_debt | day 20 |
| exile_meet | day 50+ (counted from Missing Inspector's completion) |
| into_darkness | ~day 56 |
| negotiation | ~day 58 |

Then come the Lurie temple (needs water breathing) and the Crypt (danger 37 with an LV38 boss).

## 2. Side stories

**Curry: "Last Spice"**
- **Start:** talk to Tyche at Doga Ruins Camp, (+15,+45) from home, computed. The drama starts
  it; no prerequisites are known.
- **Dungeon:** Factory of Doga (curryruin_dungeon). `DangerLv => 33 + |lv|` gives **34-38**. Its
  stairs are locked until QuestCurry has started.
- **Boss:** Doga (machine gunner, LV42) on B5. Killing it advances the quest; report to Tyche.
- **Reward:** cassette 110 and 3 red-pepper seeds. Tyche and VISHNU (LV28) become recruitable;
  Bambi sells red-pepper seeds.
- **Reachable:** no; well above the cap.

**Nasu: "Seeking the Legendary Bag!"**
- **Start:** talk to Nanasu at Specwing 3F (wiki). Specwing is (+32,+39) from home, computed.
  Nanasu joins the party.
- **Dungeon:** Forest of the Lost Way (cave_fairy, LV18): **danger 19-23**, 5 floors. Stairs unlock
  only with Nanasu in the party or after the quest is done.
- **Bosses:** Raina (LV19, lightning) and Poina (LV24, poison boxer) on B5. Killing both drops
  the ★bag of holding; give it to Nanasu.
- **Reward:** 77 eggplants, **10 coralwood seeds**, 10 feywood seeds. Nanasu keeps the bag and
  leaves the faction. Raina and Poina later appear at Specwing as recruits.
- **Coralwood has Water Breathing 10** (materials.json), so these seeds are a route to the
  underwater temple and underwater nefias.
- **Reachable:** stretch (danger 19-23 against a cap of 10).

**Melilith: "Haunted Manor"**
- **Start:** talk to Melilith in The Cursed Manor (danger 10, (-15,+28) from home). The basement
  stairs stay locked until the quest starts. The DLC check `Steam.HasDLC(CursedManor)` always
  returns true.
- **Floors:** B1 to B6. B2 and below are cursed_manor_dungeon.
  - By the floor formula the danger is **10-15**. The dungeon row says LV30, so treat it as
    possibly harder until seen. **UNCONFIRMED.**
- **Task:** take **one** treasure from B6. Choices:
  - Rod of Wish (1 charge)
  - 20 gold bars
  - a wig
  - the ticket to befriend Melilith
  - a few other treasures

  A second treasure gives "Curse of the mansion" (LUK -10; Melilith won't join).
- **Boss:** "Alone..." (LV35), optional.
- **Reachable:** yes; the best story-adjacent target now.

**Lumiest: "Unknown Crater"**
QuestLumiest is a bare stub, and the wiki says unimplemented. Lumiest Crater (LV20, danger 20) is
just an explorable zone. Not a quest.

**Council: "Tyris Council"**
QuestCouncil is a stub. The wiki: "Older versions allowed you to receive it, but it no longer
appears." Unimplemented.

**home2: "Mysilia Reconstruction" (the "news from Mysilia" question)**
QuestHome stops at phase 2: `CanAutoAdvance => false`, and the only phase change in code is
DramaOutcome setting phase 2 at Ashland's report. Nothing advances or completes it. It is a
placeholder for unimplemented content; there is **no trigger** in code, and the wiki gives none.

## 3. Guilds

**General (FactionRelation, Guild, QuestGuild, CalcPlat)**
- **Rank thresholds.** `ExpToNext = 100 + rank² x 100`:

| From rank | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| Contribution to next | 100 | 200 | 500 | 1,000 | 1,700 | 2,600 |

  `MaxRank = 6`, so the total from 0 to 6 is 6,100.
- **Promotion.** Talk to the guild clerk (drama `guild_promote` when exp ≥ ExpToNext).
  `Promote()` does `exp -= ExpToNext`, so the overflow is kept and the counter isn't zeroed.
- **Salary:** rank x 100 orens a month, summed over all guilds (GetFactionSalary).
- **Benefits by rank** (QuestGuild.GetDetailText):
  - rank 2: trainer;
  - rank 4: "benefit2";
  - rank 6: "benefit3";
  - rank 8: a feat. That last one is unreachable while MaxRank is 6.
- **Trainer price:** a guild-tagged skill costs **x2 platinum below rank 2** (CalcPlat.Learn and
  CalcPlat.Train). The guild trainer lists only its own guild's skills.
- **Guild shop level:** promotion sets the guild zone's development to `(10 + 5 x rank) x 10`, which
  raises the guild shops' level.
- **Guild Orders** (order_fighter/mage/thief/merchant, QuestGuildOrder*): empty classes that nothing
  ever creates, so they are **unimplemented**. The journal "task" line is only the contribution
  source (`<guild>_task1`).

**Fighters** (Kapul B1). Now rank 1, 200/200: **promotion is available now**.
- **Contribution:** killing a non-unique monster of rarity ≥ Legendary (an elite, 『』 name)
  that is hostile by origin or an evolved boss pays `10 + min(LV,200)/5` (Card.cs). A Lv30 elite
  gives 16.
- **Services:** members pay `x100/(125 + 2 x rank)` for meal, heal, picklock and identify anywhere
  (CalcMoney). That is about 20% off.
- **Rank 4 bounty:** an elite kill can pay `rndHalf(200 + curve(LV) x 20)` orens. At ranks 4-5 it
  applies to half of the elites (uid parity); at rank 6, to two thirds.
- **Skills:** Dual Wield, Tactics, Mind's Eye.

**Mages** (Lumiest B1). Not joined.
- **Trial:**
  1. Talk to the doorman (wiki: Lexus). `TraitDoorman_Mage.GiveTrial` starts guild_mage at phase 0.
  2. Have **`letter_trial`** in the pack. It is a parchment "letter" whose title is "Recommendation
     for the Academy", so **Raydorre's 1,815-oren letter is the item**; Aliyun sold the same for
     1,900.
  3. The `letterTrial` choice runs `guild_mageTrial`: phase 1, and one letter is consumed.
  4. `guild_join` makes you a Member (phase 10).
- **Letter stock:** Magic-type shops stock it only while you are not a member. In Lumiest's town
  level it always appears; elsewhere a restock has a 1-in-4 chance (Trait.cs ShopType.Magic).
- **Contribution:** decoding an ancient book as the PC pays `5 + 2 x refVal` (TraitBaseSpellbook,
  Type.Ancient). That ranges from Voynich 5 to Apocalypse 33 (wiki table).
- **Benefits:**
  - spellbooks cost `x100/(120 + rank/2)` (about 17% off);
  - rank 4: change a domain at the guild master;
  - rank 6: +1 domain, and with Magic Mastery, the "high" element spells.
- **Skills:** Control Magic, Magic Capacity, Memorization.

**Thieves** (Derphy B1). Rank 0, 0/100.
- **Contribution:** for each stolen unit sold to a shop, `floor(sqrt(unit price))/2`, summed per
  unit (ShopTransaction). For example, a stolen item that sells for 2,500 gives 25.
  - NPC shoppers buying stolen goods or charas at your own shop also pay `sqrt(price)/2`
    (AI_Shopping).
  - The wiki: selling a resident with a bill of sale counts (-1 karma); shipping boxes don't.
  - Stolen goods come from Pickpocket (guild trainer, 10 platinum below rank 2) or from taking NPC
    property.
- **Benefits:**
  - stolen goods sell at `x100/(190 - 2 x rank)` instead of x0.5;
  - rank 4: the black market. Below rank 4 a black marketeer refuses in the guild itself and
    anywhere except Derphy town, Kapul and your own land;
  - rank 6: a better quality roll on generated enchantable items (wiki: "furniture").
- **Skills:** Gun, Marksman, Greater Evasion, Pickpocket.

**Merchants** (south-west of Mysilia). Rank 0, 0/100.
- **Contribution:** each **direct** investment in a shopkeeper (talk, then Invest) pays
  `5 + c_invest` after the increment (DramaCustomSequence `_investShop`). Zone investments and
  investments through the secretary give nothing.
- **Cost:** `max(c_invest x 700, c_invest² x 80 + 200)`, then x100/(110 + rank/2), then
  reduced by CHA/2 + Investing (CalcMoney.Invest).
  - A never-invested shop costs about 180 or less for 6 points; the second investment there about
    640 for 7; the third about 1,270 for 8.
  - **Spreading across fresh shops reaches 100 points for about 3,000 orens.** It also raises each
    shop's level, so its stock improves.
- **Benefits:**
  - investing costs `x100/(110 + rank/2)`;
  - rank 4: the Exotic Merchant (TraitMerchantExotic);
  - rank 6: invested shops grow 10% more (InvestBonus).
- **Skills:** Travel, Negotiation.

## 4. Candidate goals

1. **Finish Gold Beneath (G13).**
   - Steps: talk to Loytel in Vernis (step 4 → 5, now); quru_past1 and quru_past2 from the board;
     the Vernis hearth to Lv2; Tephra (LV16) on Mine B8.
   - Done when the journal shows Gold Beneath completed and Corgon is a resident. This starts the
     +10 and +20 day story timers; nothing else in the story moves until then.
2. **Guild ranks for cheaper training.**
   - M1: Fighters promoted to rank 2 at the Kapul clerk; that needs only a visit.
   - M2: Mages Guild joined (Raydorre's letter, 1,815, then the Lumiest B1 doorman).
   - M3: Mages rank 2 (300 contribution from ancient books).
   - M4: Merchants rank 1 (100 from about 15 first investments in the shops already in use).
   - Done when the journal shows Fighters rank 2, Mages Member at rank 2 or higher, and Merchants
     rank 1 or higher.
3. **Haunted Manor.**
   - Done when exactly one treasure is home (Rod of Wish, or the 20 gold bars), Melilith has had
     the report, and there is no "Curse of the mansion" feat.
   - Stop rule: a floor showing danger above 15 ends the attempt.
   - Stretch follow-up: Nasu, for coralwood seeds, gives water breathing for Lurie and underwater
     nefias.
