# Lessons

Three sections (restructured after run 12's review, 2026-10-19). **Live** holds the one-off lessons
nothing enforces yet: read them before playing. A lesson leaves Live in the session a tool starts
enforcing it or a skill states it (it then lives in the code or the skill, and git history keeps
the original). **Promoted** says where the rest went. **Superseded** keeps the pairs that were
reversed, so an old run log isn't taken for the current rule. The run in brackets is the source.

## Live

Each line carries the run it came from; a line 3 runs old or more is promoted, made a fact,
superseded or dropped at the close-out (hygiene.py flags it). After the 2026-10-23 review's triage
(34 lines: 11 became facts #751-#761, 17 were already in a skill or a tool, 4 got tool guards the
same day, 2 were empty headings) Live holds only what nothing enforces yet.




- Measure where the exp comes from before planning the next hour: run 44 spent minutes 6-66 on shops, jobs and roads at 4 exp a minute with the 30-a-minute dummy beside its bed; the 20-second samples showed it at once, afterwards. (44)
- A rate measured at one level is that level's rate: the dummy's 39 a minute at skill 3 is 3 at skill 10, and "walking beats the dummy" (run 43, at skill 10+) read as a general rule until run 44 measured both at low skill. Say at what state a rate holds. (44)
- The largest gains of a run can sit unread in the home's boxes: tally them by kind (stock) at every session start. Run 40's ancient books, skill books and enchant armor scrolls had waited for runs. (40)
- A file cut to its last line hides what a check showed: a tool's output that decides something gets read whole; the two guns were recorded as read when they weren't. (40)
- A claim about what I compared stands only if I compared it: "none are better" was written over 14 pieces whose lines I never read. (40)
- Trip food for a long night is bought or cooked dishes, not raw crops: the Cooler Box slows rot, it doesn't stop it
  (fact #1169). (39)
- To Lumiest, Fast Travel from home (fact #1168), never a walk: the game's path swings east from the west too
  (Palmia -> Lumiest took 3.3 days) and onto level 24-28 tiles from the north (74,99). (39)
- Unattended circuits take base 3-8: under the gate of 12 a base-9 nefia gives B1-B4 and a base-10 B1-B3, while the
  masters sit on B2-B5 (nefias.csv); Capricious Forest (9) ran four floors with no master. (38)
- A Short Teleport lands at random a few cells off and can land beside the exploder it was cast to escape (twice in
  run 38): against an adjacent exploder read a teleport scroll; cast.py now stops on an exploder inside 3 cells. (38)
- After wgo.py arrives on a town or home tile, the first `do 0` (Enter) was ignored three times: check the zone after
  an Enter and enter again. (38)
- Before planning a purchase, look for the thing in the bags and every home box (`stock.py --list KIND`): five enchant
  weapon scrolls, 19 undecoded ancient books, 50 uncurse scrolls and a rod of identify were already at hand. (38)
- A boss chest's furniture (a drum can bath) and stones put the pack at Burden phase 2 by the next nefia's door: drop
  chest furniture on the floor it came from. (38)

## Promoted (where the older lessons live now)

- the level 1 trials (runs 41-44): armor before arenas and no caves under Lv10 -> board.py --take and arena.py --any refuse, elin-opening's fast path; a flee that doesn't move -> leave.py; a death prompt -> common.crawl_up and close.py; a demand paid unread -> roam.py KEEP; full pack -> earlyday.tidy JUNK_FULL; paid recipes re-crafted -> tickets.py
- run 40 triage: a neutral master that steals (37) -> a fact, and The Fighting Bull ring protects from thieves
- run 39 triage (the run-36 lessons): the named exploder by the down stairway -> fact #1174; grassland nefias run long
  -> fact #1175 (run 39 again: 40-70 real minutes each); Return needs a local map -> recall.py refuses on the world map
  ("enter a local map first"), and the circuit ends each conquest on the nefia's tile
- run 38 triage: a hand-run ladder needs --no-wrecks (35) -> tool-notes' ladder row; party members can't be talked to on the world map (35) -> a fact (kb.py)
- run 37's close: a gear choice that touches a hand is compared against the empty off hand too (run 30 chose the shield over the scimitar and never against the axe alone: 9.5 against 22.8 a turn for seven runs) -> item.py refuses an off-hand Equip beside a lone weapon (--offhand-ok), common.empty_slots counts a lone weapon as a full hand, power.py logs my_melee (the old column summed the party); fact #1137
- run 37 triage: base 11-12 nefias under the gate (34; again run 37's Unknown Machinarium) -> fact #1136 and the circuit's --danger 3-10
- run 34 triage: the harvest box (33) -> G3 M6, the harvest fridge (home.HARVEST_FRIDGE; cookdishes reads it); lifting a door (31), blessed and plain stack names (31), the crew's first nefias (31) -> facts #1086-#1088; the avoid kind far under my level (32) -> threat.avoid's 30% rule (run 33); unidentified gear filling the bags (32) -> facts #1083-#1084 (34 pieces identified, 9,782 orens and 5 bars shipped); sell fame once the near nefias run over the gate (32) -> circuit.py's no-nefia stop names the fame sale; run 34's own: trip food left in the pantry -> leave.py counts only meals eat_one reaches
- run 33 triage: the run-30 lessons -> facts #1040 (carried platinum for a skill trip), #1041 (theft success by
  time; steal.py's sneak guard), #1042 (packcheck needs free grid cards; ladder room_check), #1043 (boxes refill ~10
  stacks a nefia)
- run 32 triage: the run-29 unattended base-5 lesson -> run 32's base 3-6 lesson (five danger-10 stops on base 7-8);
  boxed coins before a coin trip (29) and the invisible stalker (29) -> facts (kb.py facts 'boxed coins', 'stalker ally')
- run 31 triage: shift-click into whichever window is open (28) -> bag.py closes the carried containers first; the
  ★Storage Chest's pages (28) -> box.py pages its category tabs; poison wakes a sleeper (28) -> fact #1000; the
  shipping chest's 40 stacks (28) -> fact #1001 and stock.py --ship N
- run 30 triage: the stairs walk's late zone change (27, again in 30), the Cure Minor Wound stock on ladder days (27) and the missing ranged zap (27) -> facts (kb.py facts 'stairs=True', 'Cure Minor Wound', 'attack rods')
- run 29 triage: the full pack within two nefias (26) -> elin-play's nefia row (unload every two nefias) and `stock.py --ship`; walking is where the rent goes (26) -> elin-play's rent rule
- run 28 triage: the boxed-in floor (25) -> elin-play's nefia rules (a rod of teleport gets out; the Teleport spell fizzles at Casting 3); the exp engine (25) -> fact #935; the box Split slider (25) -> fact #936
- review 2026-10-23 / run 24: rent runs whatever I do -> elin-play's rent rule and the loops' marks in
  runs/activity.csv (stats.py's rent per hour).
- Town people's sleep times (runs 21-22) -> fact #868; a supply job's "I have the requested stuff" board choice (run 22) -> fact #869. (promoted run 25)
- run 24: the lost potions -> bridge 0.31.5 skills.ether/corruption and facts #845-#846 (buy one at a
  time while a disease lasts; the antibody cures); exploders by name -> delve.py and fight.py read
  threat.py's exploder flag; errand items put back by --move -> runs/carry.txt; riding -> bridge 0.31.6
  `ride` and leave.py's mounted refusal; unmatched foods -> farmday.MEALS and packcheck.FOOD_OK; a
  bag quick move into an open shop -> bag.py refuses with another container open; the 15% round
  rule at 178 HP -> fight.py's hit_pct and hit_pct_any.
- run 23: a scroll of return read right after claiming land (the claim made Vernis the home: no Meadow
  in the list) -> recall.py's home check (bridge 0.31.3 zone.home); town mining and hammering ->
  elin-play's crime rule and tools/sneakmine.py; world-map stalkers -> elin-play's World map line.
- run 21: "You kick X" walking through a party member (18) -> fact #796; the tool changes of run 21
  (route danger, meal stops, burden stops, shrines, chests, the swarm count, pipefail) -> wgo.py,
  ladder.py, loot.py, craft.py, delve.py and elin-play's rows.
- review 2026-10-23 (the Live triage): the isometric map deltas and the top-down world map (01, 03)
  -> elin-play's coordinates paragraph; a key into a cliff slides, no eating on the world map (06)
  -> elin-play's World map line; blind: no reading, no targeting (06) -> delve.py's ConBlind stop and
  elin-play; "Move to Hearth Stone" stores a resident (15) -> elin-home 6; a sell-back refunds only in
  the same window (11) -> elin-play's Buy row; quests +1 karma, boards refresh on entering, hunt jobs
  complete in the field (05, 09, 11) -> elin-town-trip 3; read the number, never infer it (07),
  count from the inventory not the log ring (13), the toolbelt's hidden stacks (11, 13, 16), no shell
  loops over game actions (19) -> elin-play's hard rules; crafted furniture Squashes (14) -> craft.py
  stops a batch at Burden; never merge stacks by drag (13) -> bridge 0.30.0 refuses a same-name drop;
  gear that prevents teleportation is never worn (13) and a one-handed Equip can take the main hand
  (20) -> item.py refuses without --teleport-ok / --main; list the backpack before buying kit (20) ->
  power.kit() counts open bags and item.py prints the carried counts in a shop; identify a Godly item
  only to wear it (19) -> elin-pack 3 and errors.csv; the two-hand style (19) -> fact #707 and G19;
  known-spell books ship (14, 20) -> elin-pack 3 and fact #755; the restart keys (15) were already
  Promoted; Nino and Casaneck by day (09, 12) -> elin-town-trip; residents claim unowned beds (03) ->
  elin-home 5; the Bed Options and Ride menus (03, 18) -> the review's open items (a `menu` op);
  heredoc backslashes (12, 13, 16) -> the user's working preferences, not a game lesson.
- run 20: a second scroll of return during the countdown cancels both (05, 10, 20) -> tools/recall.py
  reads one and waits up to 60 turns (it took 19-36); supply jobs need the stock and one stack of the
  whole count (14, 20) -> elin-town-trip's board-job rule; a healing rod zapped at an ally (20) ->
  heal.py tries the rod first; nefia floors persist within a visit (14) and random nefias expire
  within days (20) -> elin-play's Find nefias row; Wait on a stairway takes it (20) -> elin-play's
  ladder row and recall.py; the CHA join rule (20) -> elin-home; gear corrodes (20) -> elin-pack 3.
- goto onto a stairway takes the stairs (03) -> bridge walkto refuses a stairway unless stairs=true.
- The stairway I arrive on in a nefia is the way back (05) -> explore.py reports "stairs (not the way in)".
- Crafting SP adds up (12) -> craft.py --dry prints the stamina before a batch.
- Residents eat real food only at home; away a stocked shared box is eaten down (18) -> elin-home 6;
  dishes.py, leave.py (private) and arrive.py (shared), run 19.
- A harvest job is a race against its 180 minutes (19) -> elin-town-trip (daylight, no chasing, the
  user's rule) and harvestjob.py --ends.
- The party pets eat the residents' dishes too (19) -> elin-home 6.
- Quick-save right after a big haul (19) -> elin-play's quick-save section.
- Deep water drowns, and the game's pathing swims: the death in Port Kapul (19) -> bridge 0.28.0
  walkto refuses/stops before deep water, whereis.py, elin-play's rule.
- dangergrid printed the world-map wanderers' level, 5 above the ambush level (19) -> the tool
  prints the ambush level; elin-play's Route danger row.

- run 18 (lessons): eat_one's meal words include roast and salad and the home loop never mines or sleeps
  hungry (elin-play's status row; the starvation death); the spoils bag carries the kit's overflow and
  place.py opens the carried bags (packcheck; runs 17-18: items landing in bags at the stack limit);
  half the bill is fame x 2 (elin-town-trip 3, the Merchants Guild line; G9 is in goals-done.md); world-map bandits and paying a cheap demand to exploders
  (elin-town-trip 2, fact #675).
- run 18: the town's layout and building procedure (elin-home 2), boxes with contents moved through a
  bag (boxshift.py), the door cell's wall placed from outside (elin-home 2), harvest jobs by day in
  ~35s loads (elin-town-trip 3, facts #667, #676), Mining practice on my own walls (minewalls.py), no
  loop works or sleeps hungry (elin-play's status row), the Dishes box's priority (elin-home 2),
  walk_beside skips door cells, fight.py approaches by any free neighbour and matches camelCase ids.

- run 17: no underwater dungeons (wgo.py, delve.py refuse; elin-play), no waiting (wait.py needs
  --user-ok), a guard's "Do you know" line for job targets (whereis.py any; elin-town-trip),
  resident dishes kept by springday, eat_one refuses with a dialog open, gather.py stops on
  hostiles, the avoid-kind refusal at 8 levels (fight.py, delve.py), leave.py answers No to an
  abandon prompt, vomit is never auto-junk, the lake is ice in winter (springday skips watering),
  unpack.py opens mail-post parcels, paytax.py finds a bill on the ground or in a bag, the menu keys'
  hotbar fallback (common.open_inventory); resident food (elin-home 6), escort clients, harvest
  jobs and the Merchants Guild (elin-town-trip 3), boss chests, shrines and cursed items (elin-pack 4); potions thrown at allies, never gifted
  (heal.py, runs 16-17), kamikazes soaked Wet with a thrown potion (delve.py, runs 04, 17).

- run 16: escorts and tourists take an ally slot (elin-town-trip; Party Animal +1); carried orens
  can't be boxed and a death drops 33-67% on the tile (elin-play's carried-gold row); nefias found
  with `places 60` + dangergrid (elin-play's tool table); the toolbelt count (fish.py); Godly and
  Miracle identification prices (elin-pack's triage step 1).

- run 15 cleanup: stale button listings (bridge 0.25.0 `click expect=`, craft.py re-lists its
  slots, policy.py; elin-play hard rules), home rocks outside the zone's bounds (harvest.py and
  gather.py skip them), one stack per recipe slot (craft.py --use refuses a default stack),
  never truncating a mover's output (elin-play: read the exit code), foods.md (elin-play: know
  what you eat; item.py Eat refuses harmful foods).

- elin-play hard rules (run 14 cleanup): the ~4 fps slowdown after ~9 hours: check `ping`, quit
  and relaunch (06).
- tools (run 13): empty cans and other scrap junk are never trash (loot, trash, packcheck keep
  them; scrap.py breaks them with the hammer); farm food goes to the harvest box, not the Cooler
  Box (springday); ☆ gear is a decide item, never the armory (packcheck); recipe names match
  case-insensitively and the craft window closes after crafting (craft.py).
- elin-play rule zero: the deaths of runs 03 and 07 and the near-deaths of 11 and 12 (instance
  jobs, the Derphy sea, the danger-6 floor, the caster at the party, the hot guy), HP floors,
  the swarm rule, target order, suicide attackers, the escape kit, speed and sleep.
- elin-play's tool table: dialogs one at a time, stale button indices, `act Cancel` opening the
  System menu, pickers as drag grids, converters as tasks, the return list, the F-key bed.
- elin-pack: the kit, what never rides along, identify-then-decide, ship ☆ gear from home, buy by
  the full name, the backpack as fire-safe storage, packcheck at the door.
- elin-home: one theme a box, garbage to the trash can, mail, burden, shared boxes and residents,
  beds, home danger and spawns, the field and watering.
- elin-town-trip: roads and ambush odds, step time, escorts against steps, guards' "Where is...",
  karma below zero and incognito, Derphy's pickpockets, scholars and plans.
- elin-goals and elin-closeout: the goal ladder, the summary and its page; the exp rules (skill
  level-ups only; the dummy pays only low skills: run 14) are in elin-home 7.
- The tools themselves: find.py (one `find` op), gather.py (right tool, ripe only), harvest.py,
  item.py (exact action, transfer check, whole-word names), bag.py, box.py (no open window,
  worn gear skipped), trash.py, loot.py (junk, property, a full pack), fight.py (hostiles
  only), hunt.py (cats and allies spared), delve.py (target order, throws, soaking), leave.py
  (water, unexplored cells, packcheck), wgo.py (stops, the travel log), springday.py (the whole
  farm round), water.py, packcheck.py, look.py (burden, shrines, windows), train.py, perform.py.

## Superseded (old -> new; the old run logs still say the first)
- "Mounted training at home is the best exp per real hour; pair each hour with a nefia trip" (24) -> under the
  run score it is a loss (run 26: ~195 exp and ~26 game days a real hour, about -140 points an hour; facts #851,
  #762); nefia conquests are the engine (runs 26-27: 7 and 8 conquests) (27).
- "A skill's first ~10 levels pay at the dummy, 15+ nothing" (14, 17, 21) -> several low skills at once
  (two weapons, lockpicking, riding) kept paying past 15 (24, fact in kb.py: 'training dummy').
- "The bridge can't press Enter at the death prompt" (05) -> bridge input TEXT types the last words and
  presses Enter; then the menu: "Crawl up in TOWN", "Crawl up", "Buried" (never Buried) (19).
- "Equipping a second weapon puts it in the shield hand (dual wield)" (03) -> with one good weapon,
  dual wielding drops the two-hand bonus at any Dual Wield level (fact #707) (19).

- Gold can't be stored (14, open) -> picked-up orens are an item stack: box them before a
  nefia, take them back before the tax day (15).
- Godly and Miracle items both need the artifact identify (14) -> Godly only (15).

- Load world_2 (02) -> world_4; world_2 is retired (CLAUDE.md).
- The bed sleeps when Tired or Exhausted (03) -> Sleepy, or SP under 20% (code, 05).
- One bait per cast (03) -> one cast uses every bait held (03, later the same day).
- A world-map step is 2h50m (03) -> 180 game minutes at base, from the code (12).
- The pack holds ~35 stacks (03) -> it refuses the 44th (09).
- `craft.py --use` picks the biggest matching stack (04) -> the first matching stack from any
  box in reach (11) -> whole-word matches, and a slot nothing matches is refused (12).
- Danger 4 is my limit (05, Lv7) -> danger 5 at Lv9 (07) -> danger 8 fine, 9 not, at Lv12 (12):
  the floor gate in elin-play's thresholds table.
- Shipping pays almost nothing for gear (06) -> ☆ gear ships for 3-4x a shop's offer; plain gear
  pays a shop's price x1.1 (09, 11).
- Buy by the bare name "of teleport" (08) -> by the full name: "of teleport" bought a 516-oren
  spellbook, "of cure minor wound" a 315-oren rod (08, 11).
- Digging is the best exp at Lv10 (09) -> 40 digs gave +1 at Lv10 (10); tilling new field cells
  still paid +41 in run 12 (Farming, not Digging).
- Converters work one unit at a time (09) -> the whole stack converts if the window stays open
  until the task ends (10).
- The dummy gives ~11 exp a bar (03) -> 0 from Lv8 (06, 12) -> 0 only for high skills: a never-used
  weapon on it earned +26-42 character exp a bar (14; elin-home, tools/trainday.py).
- Deliveries land by the hearth (03) -> in the mail post (04).
- Kaberg's gloves need an uncurse scroll (04) -> they were a gift, taken back by force in run 06;
  a better gift replaces gear (12).
- A script holding the bridge connection blocks the tools it launches (04, 12) -> bridge 0.23.0
  serves each client on its own thread; common.run still closes first out of habit.
- Butchering needs livestock / shearing gives skins (12, the user's reading) -> a corpse through
  the butcher's tool gives a random body part, skin 20%; shearing gives fiber only (code, 12).
- The sleeping bag is the road bed (05) -> it burned in run 12; any bed in the pack works with
  the F-key slot (the makeshift bed rides in the kit).
- Blind: bump attacks with `move` still work (06) -> a step into an unseen foe does nothing; walk
  away until it clears (14; elin-play rule, delve.py stops on ConBlind).
- Fast Travel starts only from a town or home tile, never mid-field (15) -> run 20: it started from the
  field tile where an expired nefia had stood (Meadow, 6 rations); a plain field tile offers none
  (fact #760).
