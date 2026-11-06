---
name: elin-gear
description: Judging equipment in Elin (run 42, the user's request) - comparing a weapon or armour piece against what's worn by wearing it and reading the game's own numbers, what penetration, flurry, crits, to-hit, weight and armour are really worth from the game's code, the foe panel, the trial in play and how to judge it, and what no number settles (immunities, resistances). Use whenever a new piece turns up, before shipping or selling any ☆ or ★ gear, when damage or HP feel off, and when deciding what to wear or which artifact to buy.
---

# Judging gear: wear it, read it, then fight with it

Why this exists: the character sheet's damage line and a tooltip read from the pack both undersell some gear. A sword stayed in a bag through a whole run because its dice looked small next to 3d14+23; its 50% penetration, flurry and crits weren't in the number being compared. The user, who spotted it: "It is worth it... make a skill/method to validate equipment cleanly between worn/wielded. Pen% value is huge on armored opponents."

**Three steps. Don't skip to the third, and don't stop at the second.**

## 1. Read both pieces whole

`python -I tools/gearcheck.py [SLOT]` prints every ☆ and ★ piece in the pack and bags beside what's worn in that slot, line by line. It's the read-before-claiming step: `shipstar.py` ships only what it has shown. Armor numbers can't settle a choice alone; immunities and resistances are lines of text.

## 2. Wear it and compute

`python -I tools/gearcompare.py NAME [--against WORN] [--level L] [--foe KIND ...]` swaps the piece on, reads the game's own numbers, swaps back and checks every worn piece is where it was. Nothing stays changed. Use it with no hostile in view; it refuses a window, and `item.py`'s own refusals still hold (cursed gear, gear that prevents teleportation), so it can't leave a sticky curse on you.

Wearing it matters because a piece's other lines feed the attack: a weapon's STR and PER change the multiplier, Mind's Eye changes crits, and its PV and DV change the armour. `gearcompare.py --worn` prints the same panel for what's on now, and needs no swap.

**Run it at several levels.** `--level` is the foe's level. Run your own level, about 15 below (most of a floor), and 5 above (the masters). A weapon can lose at your level and win where you actually spend your fights.

**Read the three columns:**

| Column | What it says | Trap |
|---|---|---|
| damage a turn | hit chance x a landed swing x swings x speed | counts overkill: on small foes it flatters big dice |
| turns to kill | whole landed swings needed, at the rate they land | the fairest offence number: a foe dying to one hit from either weapon comes down to to-hit and flurry |
| HP lost a kill | turns to kill x what a foe does to you a turn | the one number with weapon, armour, speed and max HP together; it reads near 0 well under your level, so judge it at your level and above |

**The panel's foes are priors, not facts.** A foe's armour and evasion aren't shown in play, so `soft`, `normal`, `armoured` (armour x2), `plated` (x4) and `evasive` (evasion x2) show how a choice depends on armour. `--foe KIND` scales them by that kind's race in the game's tables. Physical reduction is real and large on a few races (armor 80%, ghost 75%, wisp 50%, alien 30%).

## 3. Fight with it, then judge

A computed win earns a trial, not a verdict. Wear the candidate for 20+ fights, note the game date, then:

`python -I tools/gearcompare.py --judge DATE [--before DATE0]`

It reads `knowledge/fights.csv` and sets turns and HP lost by foe level against the fights before that date. Fights differ in crowd and kind, so read it alongside the run log: also count stops, near-deaths and potions, which the table doesn't. Spend what can't be taken back (enchant scrolls, a sale) only after the trial.

## What each number is worth (from the game's code)

| Line | What it does | Source |
|---|---|---|
| **Penetration** | that share of the damage skips armour entirely; the rest is cut to 100/(100+P), less a flat roll averaging about P/7. At high armour it decides everything: the same character did 22.9 a turn with Pen 0% and 54.4 with Pen 50% against P x4, level for level even on normal armour | AttackProcess.Perform, Card.ApplyProtection |
| **To-hit** | a miss when rnd(toHit) < rnd(evasion x 1.25, x 1.5 at range), with 5% always and 5% never. Raising it pays most when it's near the foe's evasion | AttackProcess.CalcHit |
| **Flurry** | each further swing at flurry / (25 + 5^(i+2)): flurry 12 is 1.26 swings; each swing rolls to hit again. The two-hand style adds up to 50% to the enchant | ActMelee.AttackWithFlurry, GetWeaponEnc |
| **Critical** | (critical + sqrt(Mind's Eye)) / 200, plus (PER + 50) / 5000: the dice's maximum at x1.25 | CalcHit, GetRawDamage |
| **Vorpal** | that % of hits at 100% penetration | Perform |
| **Attack element** | 25% a hit for a roll up to raw x (100 + 10 x value) / 500 + 5, before the foe's resistance | Perform |
| **Two-hand style** | a lone weapon, the other hand empty: x1.5 damage and +25 to-hit. Anything else in a hand switches it off. Compare a shield against the empty hand too | AttackProcess.Prepare, run 37 |
| **PV** | your armour at the same formula: near a foe's hit size the flat roll eats most of it, so a few points of PV count double at your own level and little far below it | ApplyProtection |
| **DV** | your evasion. Foes get a large to-hit bonus on martial attacks, so DV shows little in the model; **that's a prior, not a measurement**: let the trial say | Prepare |
| **Weight** | not in any damage number: Burden is -10%, -20%, -30% speed, and speed is damage and escape. Look at the weight line | Chara.RefreshSpeed |

## What no number settles

Immunities and resistances (`gearcompare.py` prints the key lines only one piece has). Decide these by what has actually hurt: read the run logs and errors, not a list of what might.

- **See Invisible:** an unseen foe stops walks and looks like an empty screen, so it costs real time; a weapon carrying it saves a spell a floor.
- **Paralysis, sleep, confusion, fear, blindness:** check who else in your gear gives each immunity before taking one off. Two pieces giving the same one means one is spare.
- **Prevents teleportation:** never, it switches off every escape.
- Keep the loser if it does something the winner can't; ship it if not. A resident can take gear from a shared box.

## Judging a whole set

A rule per slot beats a sum: every slot filled with the best piece in hand, except the second hand beside a lone melee weapon. Re-check after a level-up, a cure (an ether disease can pull a neck or back piece off: run 42's Thick Neck left a necklace in a bag until `gear slots` was read by hand), acid, a curse or a death.

## For other players

Nothing here is specific to one character: the tools read your own sheet, and the formulas are the game's. Without this repo, the same comparison works by hand: wear each piece in a safe place, note the Attack Evaluation line (dice, multiplier, Hit, Pen) and PV, DV, speed from the sheet, then work the penetration line above for armour 50, 100 and 200.

## What this skill changed

New in run 42. Measure: a piece kept or shipped against its numbers, stops for unseen foes, and turns and HP per fight by foe level (`--judge`). First result: the Sword of Forget-me-not, unread for a run, came level with Dragon Slayer on normal foes and 2.4x on plated ones, at 1 weight against 28.
