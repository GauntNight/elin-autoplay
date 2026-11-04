# Power model (a hypothesis, started 2026-10-16)

The user's framing (end of run 03): what matters is the party's overall offense and defense,
and how many kinds of damage it can deal, more than whether every equipment slot is filled.
`tools/power.py` measures that; `runs/power.csv` tracks it over time; `knowledge/fights.csv`
calibrates it.

## What is measured, and where it comes from

| Part | Source |
|---|---|
| My and Kaberg's DV, PV, attributes, combat skills, resistances, spells and stock | bridge `power` (the character sheet) |
| Each attack: dice, multiplier, to-hit, penetration, attack type, weapon elements | bridge `power`, through the game's own `AttackProcess.Prepare`: the same evaluation item tooltips show. Equipped weapons, martial arts, and the bow, sling and throwables in the pack |
| Hit chance | `AttackProcess.CalcHit`: 5% always hit, 5% always miss, otherwise a miss when rnd(to-hit) < rnd(evasion x 1.25, or x 1.5 at range) |
| Armour | `Card.ApplyProtection`: protection P = PV + armour skill + DEX/10; the part that doesn't penetrate is cut to 100/(100+P), then a roll of (P/40+1) dice of about P/4 total is taken off every hit. **The flat roll is why weak foes do nothing** (at P 20 a 5-point hit becomes 0.7) |
| A foe's evasion and protection | not on screen, so priors: non-allies have PV and DV = level + equipment (`Chara.PV/DV`); evasion about 28 + 2.5 L, protection 2 + 1.5 L, HP 8 + 7 L |
| A foe's hit | non-allies get +250 to-hit on martial attacks: prior to-hit 200 + 5 L (they rarely miss) |
| A foe's damage | fitted: a level-L foe hits for a + b L before armour, least squares over `fights.csv` |

Honest play: the bridge reports only numbers the game shows the player. Foe numbers are priors
and fits from fights, never read from the game.

## The numbers it gives

- **Offense:** expected damage per turn for each option against a foe of my level, with speed.
  Party melee (me and Kaberg) and the bow are tracked separately.
- **Defense:** HP, protection, evasion, effective HP (HP x (100+P)/100), and the threat fit.
- **Variety:** physical types (Slash, Blunt, Pierce, Kick...), elements (weapon enchants, spells
  with stock, a natural element) and status throwables. More kinds means fewer foes that shrug
  everything off (run 03: the hermit crab's shell stopped the sword; Putit In Amber's lightning
  worked).
- **Escape kit:** scrolls of teleport (instant), short teleport, return (about 18 turns), cure
  potions, bandages.
- **Danger table:** for foes from my level -3 to +5, turns for the party to kill one, and the HP
  I lose fighting 1, 3 or 6 at once (they die one at a time; all engage at once). Past 40% of
  my HP is past the 60% floor.

## Baseline, 485-08-17 (end of run 03)

Rolord Lv5: HP 41, PV 18, DV 16, protection 20, evasion 50, effective HP 49. Wooden katana 4d2
x1.50 (to-hit 73, penetration 35), about 4.3 a turn against a Lv5; Putit In Amber (cold and
lightning) 6.4; bow with grass arrows 2.8. Spells: fire bolt (10), cold arrow (15), fire hand
(10), cold hand (8). Kaberg Lv7: HP 52, martial 2d6+2 x1.69, about 9.1 a turn: **the pet is
two-thirds of the party's melee damage.** Nine damage types (Blunt, Bow, Kick, Slash; cold,
fire, impact, lightning; a confusion potion). Escape kit: 2 teleport, 1 short teleport, 4 cure
potions, 11 bandages.

Threat fit (10 seed fights): a level-L foe hits for 4.8 + 0.55 L before armour. The table:

| Foe level | Turns to kill one | Lose: 1 foe | 3 at once | 6 at once |
|---|---|---|---|---|
| 2 | 1.4 | 4% | 23% | 80% past the floor |
| 4 | 2.6 | 12% | 71% past the floor | past |
| 5 | 3.2 | 18% | past | past |
| 7 | 4.8 | 36% | past | past |
| 8 | 5.7 | 48% past the floor | past | past |

Reading: a single foe up to about Lv7 is a fair fight; three at once at Lv4 or above is not, so
in a dungeon fight in corridors (one at a time), shoot and throw first, and teleport out when
three or more close in. This matches the swarm rule and the run 03 death.

## How it gets better over time

1. **Every fight:** `power.py fight FOE LV N TURNS HP_LOST RESULT RUN [NOTE]` (N foes at once,
   HP I lost, turns it took). This includes the fights that cost nothing, because a log of only
   the painful fights overstates danger (the first fit did). The fit re-runs on every call.
2. **Every session start and end:** `power.py --log RUN` appends the card to `runs/power.csv`:
   level, HP, PV, DV, protection, evasion, effective HP, damage per turn, damage types, escape
   kit, Kaberg, and the threat fit in use.
3. **Check the predictions:** when a fight's turns-to-kill or HP lost is far from the table,
   note it in the run log. Turns to kill off by 2x means the foe HP prior is wrong; HP lost off
   means the threat fit or the foe hit prior is.
4. **Known gaps:** spell damage isn't modelled yet (listed as damage types only); crits; Kaberg
   drawing attacks off me (it's in the fit, since he was there in most fights); ranged foes;
   foe speed (taken as 100); race matters more than level for some foes (dodo, bears), so a
   per-race fit is the next step once fights.csv has enough rows.

## Seed data

`knowledge/fights.csv` started with 10 fights rebuilt from run 03's notes (PV and turns
approximate where marked). From run 04 on, rows are logged when the fight happens.
