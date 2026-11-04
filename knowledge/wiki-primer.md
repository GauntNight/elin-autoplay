# Elin primer for an automated player (target build EA 23.355)

Compiled 2026-10-15 from ylvapedia.wiki (Elin pages; versions Beta to EA 23.352, changelog to
EA 23.350), plus the decompiled Elin source and Steam guides where the wiki is silent.
**(unverified)** = no Elin-specific wiki page confirms it. The wiki has no controls page, so first
open Esc > Config, screenshot the key bindings once, and correct section 1 from it.
Text drawn from Ylvapedia (https://ylvapedia.wiki, its contributors) is CC BY-SA 4.0; this file adapts it.

## 1. Controls

Confirmed on Elin wiki pages:
- **Esc**: system menu (Save/Load when allowed, World Law, Config, Widgets).
- **1-9**: select an Active Item hotbar slot (item, tool or spell). **Mouse wheel** also cycles slots.
- **Ctrl** (tapped alone): switch between hotbar 1 and hotbar 2. Hotbars sit bottom-right.
- **Q**: empty hand, i.e. clear the "active box" (the held item or readied spell). Press it before
  clicking allies so you don't cast on them by mistake.
- **B**: ability menu. Right-click an ability to use it: self-target ones fire at once, targeted
  ones go to the active box and you then click the target. Quick Craft (Workbench, bandages) is here.
- **V**: character sheet. Its Strategy tab (lower-right) sets the auto-combat AI profile.
- **Ctrl+F**: Property Search. Finds items in your base and bags, and merchants and people in towns;
  click a result to auto-walk there.
- **Middle-click**, or **R** as a stand-in: interact or context action on an item, creature or object
  (kick, flip switch, open or trade with an ally's pack, rotate held furniture or walls). On the
  **world map** it opens fast travel (costs traveler's rations).
- **Right-click**: on a hostile, a menu with **"Auto"** (auto-combat); on an inventory item, equip;
  on a ground item, grab it for placing; in menus, back/close (Steam UI guide).
- **Left-click**: move to a spot or act on it. Click the **minimap** to auto-travel (stops when an
  enemy comes into view). **Ctrl+click** a stack: split it. Holding a spell's hotbar key casts it on
  the whole party. **F11** opens the bug-report form: never press it.

Confirmed in the decompiled Elin input code (`AM_Adv.cs`). The actions exist, but the default
keys live in game data, not code:
- **Left Shift held**: run (turbo). **Shift + Fire**: re-target the nearest enemy.
- **Holding Left Ctrl blocks every action key** except Ctrl+F. If Ctrl is stuck down, nothing works.
- **Wait** passes a turn, cancels a long action, enters the local map from the world map, and
  changes zone when you stand on an auto-enter tile.
- **Fire**: shoots the held, hotbar or equipped ranged weapon, throwable or cane at the current
  target (or locks onto the nearest). **AutoCombat** attacks the hostile under the **mouse cursor**.
- Others: Meditate, Dump (auto-store into home chests), EmptyHand, QuickSave/QuickLoad (beep if
  saving is disabled), Chat, Search widget.

From fan key lists, unverified for this build:
- Movement: WASD, arrow keys or mouse click (a wiki user guide confirms these).
  Diagonals: hold **Alt** + direction (a Japanese play diary; the code has an `altKeyAxis` option),
  and the numpad 7/9/1/3 may also work (unverified). Diagonal steps take more game time than
  cardinal ones (wiki JP Time page).
- **Space** = Wait, **Z** = Auto-combat, **F** = Fire/throw, **G** = Take all, **X** = Examine,
  **I** = Inventory (there is also a bag icon), **J** = Journal, **F9** = Quick save,
  **E**/**T** = emulate left/right click. All unverified.
- Pick up: left-click the item, then "Pick all" (auto-pickup is a setting). Talk: left-click the
  NPC (unverified). Attack: walk into or left-click a hostile (unverified; the wiki is silent).
- Stairs: walk onto or click them; Wait on them changes zone (code). Leaving a local map: probably
  walk off its edge (unverified). No search key found; traps reveal through skill. The System Menu
  hotbar has a button that enlarges the message log.

Sources: https://ylvapedia.wiki/wiki/Elin:Widgets · https://ylvapedia.wiki/wiki/Elin:FAQ ·
https://ylvapedia.wiki/wiki/Elin:Adventure_Log · https://ylvapedia.wiki/wiki/Elin:Strategy ·
https://ylvapedia.wiki/wiki/Elin:Combat · https://ylvapedia.wiki/wiki/Elin:Travel ·
https://ylvapedia.wiki/wiki/Elin:Player_Guides (the "New Player's Guide", EA 23.16, and "Simple Tips") ·
https://raw.githubusercontent.com/Elin-Modding-Resources/Elin-Decompiled/main/Elin/AM_Adv.cs ·
https://steamcommunity.com/sharedfiles/filedetails/?id=3358770967 (Nov 2024) ·
https://steamcommunity.com/sharedfiles/filedetails/?id=3377934126 · a Japanese play diary on scrapbox.io/stall (Alt diagonal)

## 2. Opening sequence and tutorial

- In Story mode you choose a start map at creation: **Meadow** (default; has a lake, many plants and
  a tax spot nearby) or **Hill Cave** (few plants, no water; Ashland's tutorial also hands you a
  hammer). One Block mode has no story. The story is the same from either start.
- Story premise: two travellers, **Ashland** and **Fiama**, rescued you ("in the woods"). You start
  on your future home map with them, plus a "Punk" (thief) per the prologue data. **Nerun** is the
  guide character; the **Adventure Log** book replays her tutorial pop-ups.
- The wiki describes no special "tutorial cave". The early caves are the Hill Cave start map,
  the **Puppy Cave** (northwest of home, low danger) and **Nymelle** (southeast of home; the first
  main-quest dungeon).
- Tutorial chain, all at My Home. The client is Ashland unless noted; you report by talking to them:
  1. **New Home**: a land deed lies at your feet. Pick it up and read it to claim the land.
     **You cannot leave the map until this is done.** Reward: iron woodcutter's axe, 10 gold bars,
     and a pet. After reading, talk to Ashland, then "Pick all" the starting items and put the axe
     on the hotbar.
  2. Talk to **Fiama** and pick the pet: dog, cat, bear cub or **little girl**. Guides recommend the
     little girl because she has full humanoid equipment slots.
  3. **Essential Equipment**: pick up the sturdy box, place it, set a container to *shared*, report.
  4. **Pioneer Auditor**: choose the dialog option asking for a pioneer auditor's help. **Loytel**
     joins; the main quest and the home quests both need him.
  5. **Tax Liability**: wait for the tax bill, then pay it. Reward: a mailbox.
  6. **The Way of Crafter**: build a Wall Workshop at the Creator's table, craft and equip a torch,
     build a small house (grass walls plus a door), report. Reward: training dummy and recipes.
  7. **Defense Training**: kill the thief, then a boar (you get 20 granite pebbles to throw,
     blindness and confusion potions, and 5 bandages), then any 100 enemies. Reward: 10 platinum.
  8. Loytel's quests: **First Shipping Box** (make one from Palulu wood with a Workbench built via
     Quick Craft, place it, report), then **Preparing for Pioneering** (make a hoe and a shovel),
     then the home quest chain. Some steps need a few in-game days of waiting between them.
  9. Fiama, **A Request to Find a Puppy**: Puppy Cave B2F, talk to Poppy and bring her home. This
     expires once the main story moves Fiama away.
  10. Fiama, **Vision for the Future** (about a week in): **never pick "I want to die"**, because
      Fiama kills you. Options 1 (Nefia: ring, PV+10) and 3 (travel shoes) are the useful picks.
- Main quest **To the New Lands** (Ashland; needs Loytel; gives Scrolls of Return and Escape):
  Nymelle B2 talk to Farris, home talk to Farris (joins), beat the B5 boss, talk to Fiama on B6,
  report to Ashland. Ashland and Fiama then move to Willow; the story beyond is unimplemented.

Sources: https://ylvapedia.wiki/wiki/Elin:Quests · https://ylvapedia.wiki/wiki/Elin:Main_Quest ·
https://ylvapedia.wiki/wiki/Elin:Home_Quest · https://ylvapedia.wiki/wiki/Elin:My_Home ·
https://ylvapedia.wiki/wiki/Elin:%E3%83%9B%E3%83%BC%E3%83%A0 · https://ylvapedia.wiki/wiki/Elin:Player_Character ·
https://ylvapedia.wiki/wiki/Elin:Adventure_Log ·
https://raw.githubusercontent.com/Elin-Modding-Resources/Elin-Decompiled/main/Elin/Prologue.cs ·
https://steamcommunity.com/sharedfiles/filedetails/?id=3358334884 (tutorial walkthrough, Nov 2024)

## 3. "Novice Adventurer" and other creation choices

- Difficulty is the **World Law**, set at creation. Everything except permadeath can be changed later
  from Esc > World Law. There are two presets:
  - **Novice Adventurer**: no Oaths (challenges) active. **Manual save and load allowed.** No death
    penalty for a while after the start: the **first 90 days**.
  - **Adventurer**: manual save/load disabled, and no protection period at the start.
- Optional custom Oaths: no manual save/load; no initial death protection; fewer gains on Moongate
  user maps; quest dungeons scale with fame; **Permadeath** (can't be enabled later; the save is
  wiped on death; grants the "Fate" feat, which blocks lethal hits while stamina is above half).
- Race and class are permanent (starting skills, potentials, domains); name and gender are not.
- Saves: `%USERPROFILE%\AppData\LocalLow\Lafrontier\Elin\Save\world (#)`; auto-backup on by default
  (since EA 23.29; settings > Game). Autosave triggers are undocumented (unverified). The "Oath of
  Destiny/Eternity" names in older Steam guides are outdated.

Sources: https://ylvapedia.wiki/wiki/Elin:Difficulty · https://ylvapedia.wiki/wiki/Elin:Death ·
https://ylvapedia.wiki/wiki/Elin:Player_Character · https://ylvapedia.wiki/wiki/Elin:Save_Data ·
https://ylvapedia.wiki/wiki/Elin_meta:Changelog

## 4. Death, danger and upkeep

- You die when HP drops below 0 (Mana-body races run on MP instead). The game then offers a choice:
  - **"Buried"**: back to the title screen to reload the last save.
  - **"Crawl up"**: respawn at My Home (or the last town) with 1/3 HP, 0 MP, 0 stamina. Under
    Novice, during the first 90 days, Nerun revives you with **no penalty**. Pick Crawl up.
- After the grace period (the "Childhood's End" message), each death drops **40-60% of carried
  money** at the death spot (marked by a skull on the world map) and costs attribute experience.
  Items are not dropped, except a heavy item that crushed you. Dying on a request map fails the
  request (fame/karma loss).
- Allies knocked out return home after about a week, or a town bartender revives them for a fee.
  Fiama revives pets.
- **Early killers**: Nefia traps (spear, mine, paralysis, teleport, acid); monsters that explode,
  crit hard or paralyze when adjacent (fight them at range); fire and cold breath, which burn or
  freeze inventory; acid, which rusts gear; leaving the roads on the world map (ambush danger rises
  with distance from the highway). Nefia danger scales with fame and level, +1 per floor.
- **Self-inflicted killers**: **stamina debt** (at negative SP every stamina-costing act deals
  damage); **Starving** (damage every turn); **Overweight** (+50-79% over the limit: chance of damage
  each turn, and **changing map likely kills you**); **Squashed** (+80%: can't move, Escape/Return
  disabled, so drop items first).
- **Retreat**: climb the stairs back up; read a Scroll of Escape or Return (both take a few turns);
  use a tent (a private instance; it counts as abandoning a Nefia conquest); the Self-Harm ability
  teleports you to a random spot (Steam guide, unverified). Auto-combat spends stamina to survive
  a lethal blow.
- **Healing**: bandages (Quick Craft) and potions; **pray** at your god's altar once a day for a
  full heal; the Rest ability or a bed restores HP, MP and SP; Meditate restores MP and lets you
  sleep on the floor; the Regeneration skill comes from a trainer.
- **Hunger**: Hungry, then Very Hungry (no HP/MP regen, -10% speed), then **Starving** (damage,
  -30% speed). Eat before Very Hungry. Raw food rots (fish fastest); cooked food and nuts last longer.
  Rotten food causes ailments. Never eat humanoid corpses (insanity) or cat meat (-5 karma).
- **Stamina**: **Tired** below 25 SP (-10% speed); **Exhausted** below 0. Rest or sleep to fix it.
- **Sleepiness**: Sleepy, then Very Sleepy (speed penalties). Sleep in a bed to fix it; a comfy
  bed works best. Starvation or overwork stops natural recovery. Burden labels run Burden, Burden!,
  Overweight, Squashed.

Sources: https://ylvapedia.wiki/wiki/Elin:Death · https://ylvapedia.wiki/wiki/Elin:Status ·
https://ylvapedia.wiki/wiki/Elin:Nefia · https://ylvapedia.wiki/wiki/Elin:World_Map ·
https://ylvapedia.wiki/wiki/Elin:Beds · https://ylvapedia.wiki/wiki/Elin:Food/Overview ·
https://ylvapedia.wiki/wiki/Elin:Adventure_Log · https://ylvapedia.wiki/wiki/Elin:Player_Guides ·
https://steamcommunity.com/sharedfiles/filedetails/?id=3400762983

## 5. Early-game priorities (first hours)

1. Finish the Ashland, Fiama and Loytel tutorial quests in order. They hand out the axe, 10 gold
   bars, a pet, the box, Loytel, recipes and 10 platinum. One guide says "Complete every Loytel
   quest as soon as possible", because the best food and stat growth sit behind them.
2. Base basics: a Workbench (Quick Craft), a makeshift bed, a torch, a grass house with a door, and
   a shipping box (contents sell daily at 5 AM). Later: Sawmill, then Carpenter's table, then
   Tinker's table (for shovel, hoe, sickle). Buy the **Home Board** and **Resident Board** from
   Fiama with gold bars, then set the policy "Growth Suppression". Keep the Hearth Stone low
   (about level 5 is the caution point), because growth raises base danger.
3. Food first: plant mushrooms (they grow in a day) or tomatoes. Keep non-perishable food before trips.
4. Gear: fill **every armour slot before entering a Nefia**. Craft wooden or stone gear, or buy it
   in town. A wooden cane gives ranged damage that costs no charges. Fireproof and coldproof
   blankets protect your inventory.
5. Leveling: skills grow with use; levels only give feat points (the blue feather gauge). Spend
   platinum at town trainers (about 4 to learn a new skill; Regeneration is a common early pick;
   ask a guard "Where is ..." to find one). Train on the dummy and weak enemies. First dungeon:
   the Puppy Cave.
6. Money: ship crafted goods, crops and wine; take town-board requests (hunting requests are easy
   early). Before a Nefia, **bank or piggy-bank your money**, because death after day 90 drops
   up to ~60% of it.
7. **Taxes**: pay the monthly bill (tax box in Mysilia, a nearby town that guides place southeast
   of the Meadow; a home tax box can be bought later). Evasion costs -40 karma per month, and four
   unpaid months makes you a criminal.
8. Find an altar and worship a god early, for the daily prayer heal.
9. Avoid off-road travel, high-danger Nefia, unknown cursed gear and an overloaded pack. One fan
   guide says to avoid "mobs under lv 10" while still weak (unverified).

Sources: https://ylvapedia.wiki/wiki/Elin:Quests · https://ylvapedia.wiki/wiki/Elin:Home_Quest ·
https://ylvapedia.wiki/wiki/Elin:Adventure_Log · https://ylvapedia.wiki/wiki/Elin:Player_Guides
(Beginner's Guide, New Player's Guide, Simple Tips) · https://ylvapedia.wiki/wiki/Elin:Karma ·
https://steamcommunity.com/sharedfiles/filedetails/?id=3358334884

## 6. Core UI: where to look on a screenshot

The wiki lists the widgets but **not their default positions**. Calibrate on the first screenshot;
the positions below are hints.
- **HP/MP Panel**: HP, MP, Stamina from left to right. It can be switched to **numbers only**
  (Esc > Widgets), which is the best setting for OCR.
- **Status Info**: hunger, fatigue, sleepiness and buffs as text labels such as "Hungry", "Tired",
  "Burden!" and "Overweight". Ailments (Blind, Confused, Paralysis, Fear...) show as text in the
  **bottom-left**; hexes show as icons.
- **Main Text** (message log): along the bottom, "classic Elona" style, over the Bottom Bar.
  You can set its width and line count.
- **Active Item**: the 9-slot hotbar with two pages, **bottom-right**. The hand icon is the active
  box. Next to it, the **Equipment** hotbar holds the equipped weapon and armour (and the wallet).
- **Mini map**: current zone, and clickable. It sits beside a row of buttons including System.
- **Date Time**: date, clock, zone name, room and weather.
- **Hover Guide**: describes whatever the cursor is over. Hover a tile or monster to read it,
  including the enemy's strength.
- **Info Bar**: attributes, party size, currency. **Exp**: feat-point gauge.
- **Quest Tracker** (hidden by default; a **bell icon top-left** toggles it; a quest's Nerun icon
  navigates to the requester). Party Info and Skill Tracker are hidden too; turn on the first two.
- **System Menu**, **Chara Menu** (inventory, abilities, character, journal) and **Extra 1** (F-key
  shortcuts: Help, Recipe Search, Notes, Quest Tracker, backpack bed) are button hotbars.

Sources: https://ylvapedia.wiki/wiki/Elin:Widgets · https://ylvapedia.wiki/wiki/Elin:Status ·
https://ylvapedia.wiki/wiki/Elin:Player_Guides (New Player's Guide) ·
https://steamcommunity.com/sharedfiles/filedetails/?id=3377934126 (Dec 2024; positions may have changed) ·
https://steamcommunity.com/sharedfiles/filedetails/?id=3358770967

## 7. Avoiding traps and getting stuck

- **Crime and karma.** Below 0 karma you are a criminal: guards attack on sight and most shops
  refuse you (Derphy is the only safe town). Karma costs: **-1** for theft (picking up or using
  owned items in towns or homes), destroying items, walls or floors, harvesting someone else's crops,
  kicking a sleeping friendly NPC, taking back gear you gave a pet (under Respected), or killing a
  cat; **-3** failing or abandoning a request; **-5** murdering a citizen, guard or named NPC;
  **-8** opening a lost wallet; **-15** failing a delivery; **-20** killing a wandering merchant;
  **-40** per month of unpaid tax. Karma comes back from quests (+1), returning lost property (+5)
  and clearing a Nefia (+5).
  **Only attack red/hostile targets; white names are neutral.** Never use auto-combat or AoE spells
  near townsfolk.
- **Irreversible choices**: character creation; Fiama's "I want to die" option (it kills you);
  some boss-quest kills and quest-reward picks; mining or destroying non-regenerating maps; taking
  extra treasure in the Cursed Manor.
- **Requests can't be cancelled**: discarding one counts as failing it. Escort requests block
  teleporters.
- **Dialogs and menus.** Talk menus are lists of choices; click one to pick it. **Esc or
  right-click** backs out. Shops open from the vendor's talk menu, and the Feed widget pops up
  for buy/sell.
- **Navigation shortcuts**: ask a town guard "Where is ..." to auto-walk to a trainer, shop or tax
  box; Ctrl+F finds and walks to items and merchants; clicking the minimap auto-travels.
- **Map and travel**: you can't leave the start map until the land deed is read. The Wait action on
  the world map enters the location under you. Fast travel needs travel rations (innkeepers sell
  them), and food rots during long trips.
- **Input gotchas**: a held Ctrl blocks actions; Q clears a readied spell or item before you click
  allies; middle-click or R on furniture rotates it rather than using it. Workstations must be
  **placed**: grab the item, then click a tile.
- **Weight**: check for "Burden!" or "Overweight" before taking stairs. Squashed means you can't move
  and can't escape, so drop items.
- **Mods**: launching with `-nomod` disables them. If the map shows only mountains and sky, suspect
  mods or a corrupt save, and load a backup.

Sources: https://ylvapedia.wiki/wiki/Elin:Karma · https://ylvapedia.wiki/wiki/Elin:Requests ·
https://ylvapedia.wiki/wiki/Elin:Player_Guides (Irreversible choices, EA 23.352) ·
https://ylvapedia.wiki/wiki/Elin:Quests · https://ylvapedia.wiki/wiki/Elin:FAQ ·
https://ylvapedia.wiki/wiki/Elin:Player_Guides (Simple Tips) · https://steamcommunity.com/sharedfiles/filedetails/?id=3358770967
