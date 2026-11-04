"""Hunt a wild map for kills (Defense Training, Regular patrol) and loot, with the survival
rules built in: shoot floating eyes and anything above my level, melee the rest with a 60%
HP floor, drink a potion below 70%, and leave on anything 3+ levels above me, 2+ above my
level at once (the user's run 04 rule: HP decides, not the count), or a swarm (delve.swarm:
the thresholds table's 6+ in view, or 4+ with one at or above my level). Sweeps the map in
legs inside `zone.bounds`; every leg starts with common.ready (HP 70, Hungry, a window, a task
running, Overweight: exit 3).

usage: python -I tools/hunt.py [KILLS=5] [MAX_LEGS=12] [--animals] [--danger N]
  --animals   also hunt neutral animals (race or creature tagged "animal" in the game's tables):
              skins drop 1 in 10, fangs 1 in 15 (G2, run 05). Never targets neutral people.
  --danger N  the highest map danger to hunt on (default DEFAULT_DANGER = 2: elin-play's
              "danger 1-2 only"; an explicit N may raise it)
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import THRESHOLDS, last, put_away, ready, refuse, run, state, stop  # noqa: E402
from delve import swarm  # noqa: E402

TOOLS = Path(__file__).resolve().parent
GAME = TOOLS.parent / "knowledge" / "game"
DEFAULT_DANGER = 2  # elin-play: hunts on danger 1-2 maps only
# shot, never meleed: whole words (the review of 2026-10-23: "bee" fitted "beetle", "eye" "eyeball")
RANGED = re.compile(r"(?<![a-z])(floating eye|eye|bee|wasp)(?![a-z])")


def cat_ids():
    """Creatures of race 'cat': killing one with original hostility Neutral or better costs Karma -1."""
    import json
    return {c["id"] for c in json.load(open(GAME / "charas.json", encoding="utf-8")) if c.get("race") == "cat"}


CATS = cat_ids()


def dog_ids():
    """Run 14: dogs are spared too: the residents keep them (Poppy, Kaberg's dog), and the Meadow's
    puppies are theirs to cuddle; a skin hunt at home takes the sheep, goats and fowl instead."""
    import json
    return {c["id"] for c in json.load(open(GAME / "charas.json", encoding="utf-8")) if c.get("race") == "dog"}


DOGS = dog_ids()


def animal_ids():
    """Creature ids the game counts as animals (Chara.IsAnimal: race tag or own tag 'animal')."""
    import json
    races = {r["id"]: str(r.get("tag") or "") for r in json.load(open(GAME / "races.json", encoding="utf-8"))}
    out = set()
    for c in json.load(open(GAME / "charas.json", encoding="utf-8")):
        if "animal" in races.get(c.get("race"), "") or "animal" in str(c.get("tag") or ""):
            out.add(c["id"])
    return out


def tend(p):
    """Drink under the dungeon floor; under the teleport floor after drinking, teleport and
    leave. True when a potion was drunk (the round is spent)."""
    if p["hp"] * 100 >= THRESHOLDS["dungeon_hp"] * p["maxHp"]:
        return False
    print("  " + last(run("item.py", "cure minor wound", "Drink")))
    if state()["pc"]["hp"] * 100 < THRESHOLDS["teleport_hp"] * p["maxHp"]:
        print(f"  still under {THRESHOLDS['teleport_hp']}% after drinking: teleport, then leave")
        print("  " + last(run("item.py", "scroll of teleport", "Read")))
        print(last(run("leave.py", "--force")))
        stop("teleported out under the HP floor: heal before the next hunt")
    return True


def main():
    a = sys.argv[1:]
    animals = animal_ids() if "--animals" in a else set()
    cap = int(a[a.index("--danger") + 1]) if "--danger" in a else None
    nums = [int(x) for i, x in enumerate(a) if x.isdigit() and (i == 0 or a[i - 1] != "--danger")]
    want = nums[0] if nums else 5
    legs = nums[1] if len(nums) > 1 else 12
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    s = state()
    cap = cap if cap is not None else DEFAULT_DANGER
    if s["zone"]["danger"] > cap:
        refuse(f"danger {s['zone']['danger']}: above the cap {cap} (--danger N to raise it)")
    x0, z0, x1, z1 = (int(v) for v in s["zone"]["bounds"].split(","))
    kills, lv = 0, s["pc"]["lv"]
    dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    for leg in range(legs):
        # the leg's precondition: HP 70, Hungry, a window, a task running, Overweight; the hostiles
        # in view are the hunt's business (hostile_r=-1 switches that check off)
        tend(state()["pc"])
        why = ready(hp=THRESHOLDS["dungeon_hp"], hostile_r=-1)
        if why:
            stop(f"{why} (kills so far: {kills})")
        dx, dz = dirs[leg % 4]
        for _ in range(6 * (leg // 2 + 1)):  # an outward spiral, not a square back to the start
            p = state()["pc"]
            # Check only the axis we move on (you often start on a boundary row).
            nx, nz = p["x"] + dx, p["z"] + dz
            if (dx and not x0 + 2 <= nx <= x1 - 2) or (dz and not z0 + 2 <= nz <= z1 - 2):
                break
            call("step", dx=dx, dz=dz)
            time.sleep(0.35)
        for _round in range(8):
            s = state()
            p = s["pc"]
            hostile = [c for c in s.get("nearby") or [] if c["hostile"]]
            # run 11: never cats (Karma -1 each, Chara.Die) nor anyone Ally/Friend (the home's
            # livestock putit, residents' pets): only neutral wild animals
            prey = [c for c in s.get("nearby") or []
                    if not c["hostile"] and not c["party"] and c["id"] in animals and c["lv"] <= lv
                    and c["id"] not in CATS and c["id"] not in DOGS and c.get("hostility") not in ("Ally", "Friend")]
            foes = hostile or prey
            if not foes:
                break
            sw = swarm(hostile, lv, (s.get("threat") or {}).get("hostiles"))
            if sw or any(c["lv"] >= lv + 3 for c in hostile) or sum(c["lv"] > lv for c in hostile) >= 2:
                print((sw or "too dangerous here") + ": " + ", ".join(f"{c['name']} Lv{c['lv']}" for c in hostile))
                print(last(run("leave.py", "--force")))
                stop(f"left the map: {sw or 'hostiles above my level'} (kills so far: {kills})")
            if tend(p):
                continue
            t = min(foes, key=lambda c: c["dist"])
            name = re.sub(r"^(an?|the) ", "", t["name"])
            if RANGED.search(t["name"].lower()) or t["lv"] > lv:
                out = run("shoot.py", name, "60", "12")
                if "no ammo" in out:  # run 12: the bow had no arrows
                    out = run("throw.py", name, "Putit In Amber", "10", "60")
                put_away()  # the bow (short or long: whichever the kit carries) goes back in the pack
            else:
                # a neutral animal needs --force (fight.py skips non-hostiles since run 07; run 12:
                # --animals never killed one without it); --force still spares party and Allies
                out = run("fight.py", name, "60", "15", *([] if t["hostile"] else ["--force"]))
            gone = "target gone" in out or "dead" in out or "no target" in out
            kills += 1 if gone else 0
            print(f"  {t['name']} Lv{t['lv']}{'' if t['hostile'] else ' (animal)'}: "
                  f"{'down' if gone else 'not finished'}  HP {state()['pc']['hp']}")
            if gone:
                got = run("loot.py", "6", "--no-butcher")  # the user, run 15
                if got and "nothing" not in got.splitlines()[0]:
                    print("    " + last(got))
            if out.rc == 3:  # the fight tool stopped for a decision (HP, a big hit, a window): no more rounds here
                print("  " + last(out))
                break
        if kills >= want:
            break
    run("loot.py", "20")
    p = state()["pc"]
    print(f"hunt done: {kills} kills  HP {p['hp']}/{p['maxHp']}  SP {p['sp']}  {p['date']}")


if __name__ == "__main__":
    main()
