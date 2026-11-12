# elin-autoplay — an agent that learns to play Elin

**Scope.** For fun: Claude plays Elin (Steam Early Access roguelike, Elona's successor), records
what happens, distills lessons and skills from each evening of play, and uses them the next
time. The aim is measurable improvement across sessions, not a one-off scripted bot. The game
and its wiki (https://ylvapedia.wiki/wiki/Main_Page) are the sources of truth.

**First, every session: read `player.md`** (gitignored: who is playing, in which save, toward what goals). **If it's
missing, this is a first run: load the `elin-setup` skill and do that before anything else.** Where this file names a
particular save (`world_4`), character, path or window size, it means the first owner's: for another player, `player.md` wins.
`KB #n` and `C:\Work` point at that owner's private notes, which aren't in this repo: don't go looking for them. Nor are that owner's
logs, which skills cite as "run 17" and the like: the citation is where a rule came from, not something to read. "The user" in the
skills is that owner, and rules credited to them are good defaults; the current player's word wins.

**Launch root.** `C:\GIT\elin-autoplay` (set up 2026-10-15 from a C:\Work session). Writable:
this folder only. Read-only: the Steam install (`C:\Program Files (x86)\Steam\steamapps\common\Elin`,
including `Package\`) and the saves (`%USERPROFILE%\AppData\LocalLow\Lafrontier\Elin\Save`).
The game writes saves itself as a result of play; Claude never edits, copies or deletes a save,
and never installs or copies a mod into the game folder: that step belongs to the user.

## Game facts (checked 2026-10-15)

- Elin EA 23.355, Stable channel, build 2026-10-11, Unity 2021.3.45. The game updates
  often; re-read `version.json` in the install folder at session start and note a change.
- Mod support ships with the game: BepInEx 6.0.0-pre.1, the `PackageLoader` plugin, and
  `Package\_ModdingKit`. A mod is a folder in `Package\` holding a `package.xml` and a DLL
  (see `Package\Mod_Slot`). Game code to reference is in `Elin_Data\Managed\Elin.dll`.
  In `package.xml`, `<version>` is the **game** version the mod targets. The loader logs
  "Skipped (made for game X)" to `%USERPROFILE%\AppData\LocalLow\Lafrontier\Elin\Player.log`
  when it's too old. Mod load messages go to that log, not BepInEx's.
- The window title is `Elin` and the client area is 2560x1377. The current game is the local
  save `world_4` (character Rolord), made by the user 2026-10-15 15:04; load it with
  `bridge.py load world_4`. `world_2` (Myshed) is retired after run 02's quest mix-up; don't load it.
- .NET SDK 8 is installed (for the bridge mod). Python is `C:\Python314\python.exe`, which has
  Pillow and numpy. Run scripts with `-I`, and ask before adding a package.

## Seeing and acting

- **See:** `python -I tools/elin_eye.py` writes `runs/captures/latest.png` (1600 px wide;
  multiply by the printed scale for game pixels). It copies the Elin window's own pixels
  and works while the game is behind other windows. **Never capture a screen region**: on
  2026-10-15 that recorded another app's private content lying on top of the game.
- **Read and act through the bridge:** `python -I tools/bridge.py state | buttons | texts |
  click N | choose N | act ACTION | move DIR | anykey`. The ElinBridge mod (`mod/ElinBridge`,
  built with `bash mod/build.sh`) runs inside the game and listens on 127.0.0.1:47323 only.
  It injects actions through the game's own input layer (`EInput`), so it doesn't need
  window focus and never touches the user's keyboard or mouse. `state` reports only what the
  player can see (`pc.CanSee`). Verify each action with a fresh `state` or capture.
- **The tool scripts share `tools/common.py`** (run 12 review): `run(tool, ...)` for a tool as a
  subprocess, `walk`/`wait_idle`/`cells` on the bridge's deferred ops, one name matcher that
  refuses ambiguity, and the exit codes 0 done / 1 refused / 2 bridge / 3 stopped for a decision.
  `tools/home.py` holds the home's coordinates. The graph: `kb.py facts` hides superseded facts
  (`--all` shows them; `add --supersedes N` marks one).
- **What is carried** (the review of 2026-11-11): `tools/items.py` reads the bridge's `items` listing (0.40.0):
  every carried thing at any depth by category, kind and container, never by a word in its name. Tools that
  eat, read, drop, ship or sell ask it (`meals()`, `find()`, `protected()`); `item.py`, `bag.py` and `box.py`
  take `uid:N` for the thing itself.
- **Chains and watching** (the same review): several tool calls in one line go through
  `python -I tools/seq.py "TOOL ARGS" "TOOL ARGS"`, which ends at the first refusal or stop, never through `;`
  (broken in runs 21, 28, 29, 42, 43, 45). Beside every unattended loop, `python -I tools/pulse.py` in the
  background: it ends when the game's turn counter hasn't moved for five minutes or the bridge stops answering.
- **Focus mode is gone** (the user, 2026-10-19: "I'll never use it the way I do things"). The
  real-keystroke tool (`elin_hand.py`, SendInput to the foreground window) was deleted after run
  12; every input goes through the bridge's own layer (`EInput`), which never touches the user's
  keyboard or mouse. The game ignores posted window messages, so there is no other quiet route.
- **Watching a log:** only `python -I tools/watchlog.py LOG --match RE --until RE --max 1790`, which ends by itself;
  never `tail -f | grep`, which never does (KB #155). The close-out ends with `tools/offcheck.py` reporting nothing left.
- **Installing the mod:** the user's one-time setup (`C:\Work\config\elin-autoplay\apply.sh`,
  user-run) turns `Elin\Package\ElinBridge` into a junction to `mod\dist\ElinBridge`, and adds
  the allow rules and the dev-loop section below. Until that has run, a rebuild loads only
  after the user copies the folder in. Check the loaded version with `bridge.py ping`; load
  errors go to `Player.log`.

## Rules of play

- Play honestly: no debug mode, cheats, console commands, save editing or save-scumming
  unless the user asks for it. Learning to play is the point.
- Captures stay in `runs/captures/` (gitignored). Never put a capture in a commit, a report or
  an artifact. Run logs are text. Ylvapedia's copyright page: "The distribution of in-game media
  (image, animation) is prohibited by Noa(Lafrontier)", so `docs/samples/` holds pictures of the
  project's own pages only.
- No PII in anything kept: the user is "the user". Character and NPC names are game content
  and fine to use. No claude.ai links in a tracked file (they go in `runs/pages/links.csv`), and
  no note of where the user is or when they sleep: a log says "unattended" or "the user watching".
  `tools/publishcheck.py` checks all of it.

## How a session runs

The first owner's corrections over 40 runs; most were broken at least once before they were written down. They're defaults:
the current player can change any of them in `player.md`.

- **Decide for yourself.** Gear, feats, spending, routes and risk calls are yours, by the existing rules; write each outcome
  into a rule. Ask only on major goals (a new goal, tabling one, a big change of strategy). The point is to watch Claude
  learn, not to approve each step.
- **Tips arrive mid-turn.** A player who is watching sees what the bridge can't. Answer in a line, act on it now, then record
  it with credit (a fact, a lesson or a skill rule): a tip left in chat is lost next session. When a tip and a rule conflict,
  the player's call wins and the rule is rewritten.
- **A run lasts its full window.** Set it at once with `tools/session_end.py`. A supply problem (no food, a full pack) is
  solved inside the window (go home, restock, cook), never by quitting, and a relaunch splits one session's records. Start the
  close-out only when the player says so or the window is nearly up. The measure is growth per hour of play.
- **Never wait.** Idle hours cost food, money and training for nothing. A shop closed or a tick not due: leave, do something
  else, come back on the way. `tools/wait.py` refuses without `--user-ok`, which needs the player's yes to that wait.
- **New skills before upgrades.** At a trainer, list the "(Not Learned)" skills first, and save for a new one (5 platinum)
  rather than spend on upgrades (1) while a useful skill is unlearned: it levels cheaply and adds an ability.
- **A full set of gear.** Every slot holds the best piece in hand, checked at session start and after acid, curses, deaths or
  swaps. The one exception: beside a lone melee weapon the second hand stays empty, which keeps the two-hand style.
- **Cap the stock.** About 100 casts of a spell (then sell its books), one or two rods of a kind, and limits on potions and
  scrolls by kind, counting the pack, the bags and the home boxes. The excess ships or sells.
- **Every unattended loop** has a hunger stop and an eat step tested by hand on the food actually in the pack (run 18 starved
  in a loop with food in the bag, because the name match missed it).
- **Read before claiming.** Never say a piece isn't better unless its lines were read against the worn one's (`gearcheck.py`
  before `shipstar.py`, its whole output). Tally the home boxes by kind at session start, before planning or buying.
- **The latest note wins.** Before saying how something stands in the game, search `runs/*.md`, `knowledge/lessons.md` and the
  facts for the newest mention, not the first hit, and read a tool before quoting what it computes. When a fact is corrected,
  supersede the old one in the same commit.
- **Plans stay small.** At most three goal items plus upkeep a session. A random-drop item names its expected attempts; a stale
  item gets do, park or drop.

## Staying in bounds

- Writes stay inside this repo. No registry, services, scheduled tasks, firewall, installs or anything elevated: hand such a
  step to the player as a command to run themselves.
- Never end a process by hand (`Stop-Process`, `taskkill`, `kill`): only the entry points in the dev loop below.
- Don't run an unfamiliar third-party program, even with `--help` (some update themselves on it): check for it without running
  it, or ask.
- Write anything holding backslashes with the file tools: they die in shell heredocs (`hygiene.py` catches what's left).
- A missing log line proves nothing: log the skip and nil cases too.
- Ask before any push or other outward-facing step.

## The learning loop

The user's aim (2026-10-15): see how good Claude can get at Elin. Improvement has to show in
the numbers below, not just in the prose.

1. **Before playing**, read the Live section of `knowledge/lessons.md`, the last run's summary in `runs/`,
   the goal register's Next and Active, and `elin-play`; load the other skills when their task comes up
   (`elin-delve` before any nefia, `elin-travel`, `elin-guilds`, `elin-home`, `elin-pack`, `elin-gear`).
   `knowledge/wiki-primer.md`, `knowledge/tool-notes.md` and the lessons' Promoted section are reference:
   search them, don't read them through (the review of 2026-11-11: 19k of 48k tokens at session start). During play, ask the knowledge graph (`tools/kb.py`: the game's
   own data tables joined with observed facts) before guessing or reading game code.
2. **Play** in cycles: read the state, decide, act once, then read again to check the action
   did what was intended. When the state is unclear, open the relevant menu before acting.
   Never guess on a dialog you can't read.
3. **Log** each session in `runs/YYYY-MM-DD-NN.md`: goal, notable events, deaths and their
   causes, what worked, what failed, and open questions. Append a metrics row to
   `runs/metrics.csv`: date, run, minutes, char level, gold, deaths, furthest goal.
   Append a row to `runs/milestones.csv` each time a milestone is reached: minutes since the
   session started, game errors (an outcome the game can't undo), tool fixes, skills in use.
4. **Distill** at session end. A specific observation (a price, a place, what a food or monster
   did) goes in the graph with `kb.py add` (`knowledge/facts.jsonl`). A one-off mistake or
   insight goes in `knowledge/lessons.md` (one line, with the run it came from). A procedure that recurs (two or more runs) becomes a skill
   at `.claude/skills/<name>/SKILL.md`, or updates the skill that covers it. Each skill is
   judged on numbers: repeats in its domain in `runs/errors.csv`, and the exp and orens per real
   hour in `runs/stats.csv` for the runs it was used in (the review of 2026-10-23: the owner's
   measure is growth per play hour); say in the run log what it changed. A game error that broke
   a rule already written down ends the same session with a tool enforcing the rule.
5. **Commit** the lessons, facts, skills and tools. The repo is scripts and rules: a game's logs and records (`runs/`, the goal
   register, `fights.csv`, `travel.csv`) are gitignored and stay on this PC. Any push needs the user's yes and a clean
   `python -I tools/publishcheck.py --history`, and sends `main` only.

## Dev loop (added by the user)

- **Launch Elin (with autoload):** run these three commands, each on its own:
  
  1. `printf world_4 > mod/dist/ElinBridge/autoload.txt`
  2. `explorer.exe steam://rungameid/2135150` (it exits 1; that's normal)
  3. `python -I tools/wait_ingame.py`
  
  Steam starts the game. Once the title screen settles, the bridge loads the save named in
  `autoload.txt` and deletes the file, so it fires only once. Without the file the game stays
  on the title screen: load the save with `bridge.py load world_4` (local saves only).
  (Updated by Claude on 2026-10-15, with the user's yes in that session.)

- **Quit Elin:** `python -I tools/bridge.py quit` and nothing else. It saves first, refuses if
  the save fails, and exits through the game's own Quit. Never use Stop-Process, taskkill or kill.

- **Stop Claude's own runaway loop:** `python -I tools/stopjob.py springday` and nothing else,
  only for a loop Claude started in this session. It asks first (a stop file the loop checks
  between steps) and waits up to 10 minutes; only then does it end the one process the loop
  registered in `runs/jobs/`, re-checked by command line and start time, with
  `taskkill /PID N /T /F`. Never Elin (quit through the bridge), Ollama or any other process.
  (Added by the user on 2026-10-19.)

- **Reload the mod:** `Package\ElinBridge` in the game folder is a junction (made by the user)
  to `mod\dist\ElinBridge`, so a reload is: quit, `bash mod/build.sh`, launch. The build
  fails while Elin is running because the loaded DLL is locked.

- **Stop the repo-local Ollama:** `python -I tools/ollama_stop.py` and nothing else. It ends only what listens on
  127.0.0.1:11435, after checking that it is the installed ollama.exe running `serve` and not the user's own
  server on 11434, with `taskkill /PID N /T /F` so its runner goes too. It runs as the close-out's last step, after
  the embed. `tools/ollama_serve.sh` also starts the server under `timeout 12h` in case a session dies first.
  (Added by the user on 2026-11-03.)

- These are live only in sessions launched from `C:\GIT\elin-autoplay`, under the allow rules
  in `.claude/settings.local.json`.

**Ollama (repo-local):** `bash tools/ollama_serve.sh` in the background (it reuses a server
    already answering on 127.0.0.1:11435), then `python -I tools/kb.py embed`. Models stay in
    `.ollama/` (gitignored). The server outlives its task: the close-out's last step ends it (below).
