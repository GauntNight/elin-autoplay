# Dungeon risk: what is acceptable (run 16, 2026-10-20)

The user, run 16: "I'd like you to spend a little time today thinking about 'risk' in dungeons and
what level of risk is acceptable and what is not. My feeling is you may be teleporting out too early
- but since not dying is priority 1 that seems reasonable, maybe there are some other ways to do it.
For example maybe travel with different followers from town... if they die they just come back in a
week so they are expendable." And later: "Threat models are not linear. Different mob types pose
different kind of offensive or defensive capabilities... high damage enemies and casters need to be
killed first. High defense enemies should be avoided and killed last."

Not dying stays rule zero. What changes is how I keep it: more layers between a bad turn and death,
so a floor isn't abandoned at the first scare. Sources: the game's code (research report, run 16,
cited by class and line in the run log), `knowledge/fights.csv` (110 fights, runs 03-16).

## 1. What a death actually costs (Chara.ApplyDeathPenalty, Card.SpawnLoot)

| Lost | How much |
|---|---|
| Orens carried | a uniform 33-67%, **dropped on the death tile** (pick them up again if the floor still exists); boxed or banked gold is safe |
| Attributes | each of 8 has a 1-in-5 chance to lose 500 exp; about half of those lose a point |
| Items, equipment, levels, skills, karma | **nothing** (the PC faction's inventory never drops) |
| The trip | wake at home (or the last town) at 1/3 HP, 0 MP/SP; an instance quest fails (its karma) |

So a death is bounded: carried gold and a stat point or two. It stays the thing to avoid, but leaving
a floor costs something real too, and the two have to be weighed.

## 2. What leaving early costs

The rest of the floor and the boss: a conquered nefia's chest held 379-761 orens and platinum in runs
05-11, and a nefia is 1-3 game days of travel each way. fights.csv records 11 fights that ended in an
escape (teleport, evacuation, leaving); in only two was I near death when I left (run 11 at 8 HP,
run 12 at 9 HP), and run 15's Yeek Cave teleport came at 54 of 109. Several nefias were left
unconquered after the first such fight (Misty Ruin, Mystical Cave, Ancient Ruin, Forbidden
Machinarium: facts #304, #385, #562, #563).

## 3. Where the danger really came from (fights.csv)

26 of 110 fights cost 40%+ of max HP. **The foe's kind decides, not its level:**

| Kind | Fights at 40%+ | Why (game data, threat.py) |
|---|---:|---|
| yeek warrior | 7 | fast (yeek speed 130) and armed (warrior job): offense 1.44, defense 0.96 |
| drone | 5 | ranged (gunner), shoots from out of view |
| kamikaze yeek, hot guy | 5 | ActSuicide: one blast, 36-91 HP |
| goblin warrior / wizard, apprentice mage, kobold | 6 | armed or casting (paralysis, lightning) |

power.py's line (a level-L foe hits for 2.2 L) predicts the median fight **50 times too high**
(observed / predicted median 0.02) and still missed the blasts. It made every floor look deadly and
the specials look ordinary. **tools/threat.py** replaces it for decisions: a profile per kind from
the game's race, job and spell tables, checked against the fights we recorded.

## 4. The layers, in the order they act

1. **Threat order** (the user's rule, threat.py, delve.py): exploders never adjacent; then "kill first"
   (high offense and low defense, or a caster, summoner, blinder, paralyser, healer) from range with
   the Putit; "normal"; "kill last" (high defense, low offense) at the end. An **"avoid"** kind (high
   offense and high defense) within 8 levels of mine (4 until run 17) stops the delve: range it or go around.
2. **The auto-combat net** (bridge 0.26.0, fight.py): fights run in the game's own GoalAutoCombat. A
   lethal hit on me or a party member who was healthy when it started leaves us at **0 HP instead of
   dead**, once per start (Card.DamageHP), and the combat aborts. That turn is the teleport.
3. **An expendable ally** (the user's idea): a resident or pet along as a shield. A dead member comes
   back home free within 0-7 days (Zone.Revive), at -10 affinity; a bartender revives at once for
   (LV+5)^2 x 3 orens. "Always stay by you while in combat" (the Strategy tab) keeps her from running
   into the dark (runs 04-05). She costs Lonely Soul's 3% HP and speed per filled slot (two slots at CHA 19 with Party Animal; CHA 20 opens a third), and a
   scroll of teleport leaves her behind. First result: Kaberg took a kamikaze yeek's blast at Yeek
   Cave B1 that would have hit me, and the floor was cleared with no drink.
4. **Heal and go on, instead of leaving:** after a teleport, heal to 80%+ with no foe in view (the rod
   of cure critical, potions, bandages), then finish the floor while the **escape reserve** holds:
   2 teleports + 3 heals untouched. Leave when going on would spend the reserve.
5. **Stairs** are a one-action exit (monsters never follow, nefia floors persist): on a hard floor,
   fight near them.
6. **Gold:** box picked-up coins at home before a nefia; carry little currency (a death drops 33-67%).

## 5. What is acceptable

Acceptable: a floor within the gate (danger 8 at Lv16) with the kit and the reserve; fights that drop
me to 50-70% when the next action can heal; losing an ally; a teleport followed by healing and going
on. Not acceptable: a melee trade with an "avoid" kind near my level; any suicide attacker adjacent;
a turn costing over 15% twice in a row with no escape read; reading evacuation with a foe in view;
going on with the reserve spent; carrying a month's gold into a nefia.

Unattended: the gate minus 1 (was minus 2), since the net, the reserve and boxed gold
now stand between a bad turn and death. Still no client-based instance jobs.

## 6. Since run 16 (updated after run 55)

The frame above still holds. Deaths since (runs/metrics.csv): 18 (starved), 19 (drowned), 25 (overwork), 33 and 37 (named
exploders), 41 (two at home, a walk with no stops); none in runs 42-55. Most were tools, not fights (elin-play). The numbers
moved: the gate is **29 at Lv47** (28 unattended), raised one step at a time on a floor at the limit cleared with no drink
and lowered one after a near-death at or under the limit (elin-delve 5; the steps and their floors are facts #1047 onward).
Run 55 reached 30, then went back to 29 for the Minotaur's Nest near-death below. The risks the later runs added, each with its counter:

| Risk | Seen | Counter |
|---|---|---|
| A named exploder: the blast is past any HP | deaths, runs 33 and 37 | `common.named`; kill from 5+ cells at x1 or leave the floor (elin-delve 6) |
| A mine-layer's buried mines | 354 -> 42, run 46 | Levitate (`delve.py` casts it), walk only crossed cells under Gravity (elin-delve 6) |
| A neutral Evolved creature near my level | 57%, run 48; 41% in a round, run 49 | leave it alone, take the stairs on (elin-delve 4) |
| **Gravity: no teleport moves you** | 453 -> 113, run 55 (two minotaur mages, Minotaur's Nest B4) | `emergency_teleport` returns at once under it; drink, kill the wounded caster, evacuate; leave such floors early (fact #1555) |
| Thorned kinds reflect melee | ~100 HP an iron maiden, run 55 | threat.py's `thorns` flag: ranged rounds; a thorned master that out-trades the arrows is a reason to leave (fact #1552) |
| Thieving monsters (gnomes take items, fairies orens) | four tools and ~1,200-2,240 orens a theft, runs 51-55 | kill them first; every theft line ledgered whole (`note_thefts`); thief protection is weighed before shipping (fact #1558) |
| Suffocation underwater | 112 -> 20, run 17 | refused without `--breathe`; with water breathing worn it does no harm (fact #1544) |
