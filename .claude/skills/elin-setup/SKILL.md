---
name: elin-setup
description: First run for a new player of this repo - the questions to ask, the local player.md that records the player, world and goals, making or choosing a character, tools/newgame.py to archive the previous character's data, and choosing starting goals from knowledge/goals-catalog.md. Use at once, before anything else, when player.md is missing, and whenever the player asks for a new character, a new world, or to set things up again.
---

# First run

`player.md` in the repo's root says who is playing, in which save, toward what. If it's missing, this is a first run and
nothing else happens until it's done. It takes a few minutes; don't start playing mid-way.

## 1. Is the mod in?

`python -I tools/bridge.py ping`. No answer usually just means Elin is closed: start it with `explorer.exe steam://rungameid/2135150`
(it exits 1; that's normal), give the title screen a minute, and ping again. Still no answer means the mod isn't installed: walk the
player through the README's "Using it as a skill", steps 1 to 3 (they build and install it themselves: **never write into the game
folder**). If Elin isn't in Steam's default folder, note where in `player.md`. The dev-loop commands in `CLAUDE.md` work from any clone;
the allow rules it mentions are the player's to add (README step 5).

## 2. Ask

Ask these together, in plain words, using a question tool if you have one. Offer the default; "you decide" is an answer
wherever it makes sense.

1. **What should I call you?** Optional. It stays in `player.md`; everything tracked says "the user".
2. **A new character, or one you already have?**
   - New, and I make it at random (default for trying this out).
   - New, and I make it to your choices: race, class, name.
   - New, and you make it yourself in the game, then tell me when you're in. Best if the look or the story matters to you.
   - An existing local save: list the `world_N` folders in `Save` and ask which. **Cloud saves can't be used** (below).
3. **Will you watch?** Watching and sending tips, mostly solo, or a mix. Solo turns on the unattended rules (a lower floor
   limit, no risky jobs). Tell a solo player: Claude Code stops at every permission prompt, so an unattended run stalls without auto
   mode or the allow rules in README step 5. That setting is theirs to choose.
4. **How much should I ask you?** The default: Claude makes the in-game calls (gear, feats, spending, routes) and asks only
   on major goals. The alternative is asking more often.
5. **How long is a usual session?** Default 1 hour. Long runs use a lot of a Claude plan: suggest starting short.
6. **Which goals?** Show the menu in `knowledge/goals-catalog.md`: its opening paragraphs on what goals are for, then each
   goal's name and what it's for (not the whole table if the player's screen is small). Up to three. "You pick some good first
   ones" is fine: suggest them, say why, and get a yes, since only goals the player approved score. They can name their own instead.
7. **Anything you want played differently?** The house rules are "How a session runs" in `CLAUDE.md`: read out their
   headings. Default: keep them all.

Don't ask about anything else. Decide it yourself and say so, or leave it to `player.md`, which they can edit any time.

## 3. Set up the repo

A game's logs and records are gitignored: they stay on the player's PC, so a fresh clone has none. This makes blank ones from
`templates/` (and, on a PC with another game's records, moves those to `archive/` first):

```bash
python -I tools/newgame.py          # shows what it would do
python -I tools/newgame.py --yes    # makes the records, resets the character-tuned numbers
```

For an existing character, set `max_danger` in `tools/common.py` and in `elin-play`'s table by level afterwards: the first game ran 7 at
level 12, 8 at 16, 9 at 25, 14 at 35. Commit what changed (the numbers, not the records: git ignores those).

Then copy `docs/player.template.md` to `player.md` and fill it in from the answers, with the run number `newgame.py` printed.
If the player gave a name or handle, add it to `.publish-terms` (one a line; gitignored), so `tools/publishcheck.py` refuses
it anywhere a push would send it.

## 4. The character

**Saves.** A new game is always a new local save: the game's character screen calls `Game.Create()`, which takes the first
`world_N` with no folder in `Save` and never touches an existing one. `bridge.py load` loads local saves only. **Never use the
title's Continue or its load list:** they follow the game's cloud setting and can show the player's cloud characters under
the same ids, so a misclick could load and autosave over one.

**Existing save:** launch it (the dev loop in `CLAUDE.md`, with this save's id). **Player makes it:** wait until they say
they're in, then read `Save` for the new folder.

**Claude makes it,** from the title (launch with no `autoload.txt`, so the game stays there):

1. `bridge.py act Cancel` closes the news pop-up. `bridge.py buttons` should list "Create an adventurer".
2. `bridge.py click N expect="Create an adventurer"`. The maker opens already rolled at random (name, alias, attributes).
3. **Random:** the first Reroll button (index 1) rolls a new name. The race and class come from the two List buttons
   just before the attribute rows (indices 10 and 11 on EA 23.355: check the rows `buttons` prints): each opens a list; click an
   entry. Choose them with a real random pick, not a favorite: the game's first offer isn't guaranteed to vary.
4. Press **Create** (`ButtonEmbark`). The World Law screen opens: a difficulty (Novice Adventurer is the default; keep it unless
   the player asked otherwise) and optional oaths, one of them **Permadeath: never touch it** unless the player asked by name.
   Its own **Create** (`ButtonEmbark (1)`) starts the game about 80 seconds later, in the intro's dialog. There is no world
   seed to choose: every new game rolls its own world on the same map.

Read the new `world_N` from `Save` for `player.md`.

## 5. Goals and the graph

- `python -I tools/kb.py build` with the game running: the game's tables, exported from the player's own copy. Plain-language
  search (`kb.py ask`) needs Ollama and is optional: without it, skip those steps in **elin-play**'s start routine and use `kb.py find`,
  `show`, `make` and `facts`.
- Write each chosen goal into `knowledge/goals.md` in the shape `elin-goals` gives, with its milestones in
  `knowledge/milestones.csv` (approved: "the player's first-run choice" and the date). The player's choice in step 2 is the
  approval the scoring rules ask for.

## 6. First session

Say back in a few lines what was set up: the character, the save, the goals, the rules on. Then start:
`python -I tools/session_end.py WINDOW`, **elin-opening** for a new character (it walks the tutorial chain), and **elin-play**
for everything else.

The first game's base is not this game's base: `tools/home.py` and the tables in **elin-home** hold its coordinates. Until there's
a base, `runs/no-base.txt` makes the home routines refuse and `leave.py` skip its departure checks. Once the boxes exist, put their
cells in `home.py` and delete the marker. The world map's layout carries over; so do facts about game rules, monsters and foods.
Facts about a named person or a particular dungeon came from another world: check them, and correct them with
`kb.py add --supersedes`.

## 7. A new character's first hours

What the first test of this skill cost (a Lich Pianist with 10 HP and 25 stamina, who died at 30 minutes):

- **Read the character first.** `power.py`: HP and SP decide everything early. Rolord's numbers are not this character's.
- **Stay home until about level 5.** A road ambush kills a 10 HP character outright, even a level 1 puppy, and walking away
  doesn't save her. `wgo.py` now caps a route's ambush level at the character's level + 1.
- **Exp comes from skill level-ups** (10-14 each), not kills. Low skills are the fuel, and the **dummy is the best engine until they reach about 9**: a hit also trains Tactics and Strategy
  (`earlyday.py N --rotate`; **elin-opening**'s fast path). First-time crafts (`firstcraft.py STATION --craft`) pay money and skill too. A weak character gets more from this, not less: a Warmage with 29 SP
  ran 30-40 exp a real minute.
- **Budget stamina before gathering.** It only comes back with sleep, and sleep needs SP under 20% (or being sleepy). **No bed is
  needed for that:** the Rest ability at low SP falls asleep where you stand (measured: SP 3 to 18 of 25 in 7 hours; a bed: 4 to 25).
  A log takes about 1 SP, a weed about 0.5 on average, a workbench 5, a bed 4. Below 0, each point of deficit is an HP of damage, so
  rest rather than craft into it. The first test took 4 of her 10 HP for a bed it didn't need.
- **Rest heals, fast and free:** the Rest ability took her from 2 HP to 10 in about 10 game minutes and stopped by itself. Fight from
  range (`throw.py NAME "granite pebble"`), Rest after every fight. "At or below my level" is not safe at 10 HP: a level 1 putit took 8
  of them in melee.
- **Food is corpses at a bonfire:** "Meat on the bone" took hunger from 45 to 16; a blueberry takes off 8. Keep corpses (`loot.py --all`).
- **A pet at low HP dies at night:** Zinel died off-screen at 44%. Sleep heals her; she comes back within days if she falls.
- **Materials are the valuables now:** `loot.py R --all`. Its default keeps only what a late character wants.
- **One step, then read the result.** Chaining commands put down the gold bars and shared the toolbelt. Use `act.py` by name:
  an index read a moment ago can become Attack when a pet steps onto the cell (the bridge now refuses that).
- **Death is cheap at first:** "the blessing of Elin" means nothing is lost early on (until 485-08-12 in the first game, unless the
  player took the oath against it). The game asks for a last word, then **Crawl up, never Buried**: `common.crawl_up` answers both; closing that prompt hangs the game (run 43).
  Log the cause in `runs/errors.csv`, and fix what let it happen.
