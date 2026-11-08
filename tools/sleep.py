"""Sleep anywhere with the bed in the pack (the sleeping bag): the F-key hotbar's "Use bed in
inventory" slot (HotItemActionSleep). The game installs the bag on my cell, sleeps, and picks
it up again. Needs: sleepy (the game refuses otherwise), a bed item in the pack, not in a quest
instance. Never in a dungeon (the user's rule): monsters keep coming while you sleep.
G2 (run 05): on the world map by home, SP 17 -> 58 in 10 hours, nothing woke me.

usage: python -I tools/sleep.py [--home-ok] [--user-ok]
  --home-ok  allow a sleep on the home map (elin-home: time at home costs the residents' food, so
             the loops that sleep at home on purpose say so; a traveller sleeps on the world map)
  --user-ok  allow a sleep in a nefia (the user's yes in this session; the rule says never)
Refuses (exit 1): a nefia without --user-ok, the home map without --home-ok, a window open, hunger
at or over THRESHOLDS["sleep_hunger"] (50: eat first). Exit 3 when the click didn't put me to sleep (run 40).
Bridge 0.16.0+ (`buttons` names the slot's hot item; `click` runs it).
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from close import close_all  # noqa: E402
from common import THRESHOLDS, refuse, run, setup, wait_until  # noqa: E402


def main():
    setup()
    s = call("state")["data"]
    p0 = s["pc"]
    z = s.get("zone") or {}
    if (s.get("layers") or {}).get("top"):
        refuse(f"a window is open ({s['layers']['top']}): close it first")
    # the review of 2026-10-23: the docstring and elin-play said "never in a dungeon" and nothing
    # enforced it (ladder.py only printed the rule)
    if z.get("nefia") and "--user-ok" not in sys.argv:
        refuse("in a nefia: never sleep here (monsters keep coming); --user-ok only with the user's yes")
    if "startsite" in (z.get("full") or "").lower() and "--home-ok" not in sys.argv:
        refuse("on the home map: a night here costs the residents' food (elin-home); sleep on the world map, "
               "or --home-ok from a loop that means to stay")
    # A sleep costs about 20-30 hunger: going to sleep Hungry woke me Very Hungry (run 05: 60 -> 81
    # in 9 hours on the road, when the meal before it had failed). Eat first.
    if p0["hunger"] >= THRESHOLDS["sleep_hunger"]:
        refuse(f"hunger {p0['hunger']}: eat first (a sleep adds 20-30; 80+ is Very Hungry, no healing)")
    hostile = [c for c in s.get("nearby") or [] if c.get("hostile")]
    if hostile and not z.get("region"):  # run 26: slept on an ambush field beside Lv3-4 hostiles
        refuse("hostiles in view (" + ", ".join(f"{c.get('name')} Lv{c.get('lv')}" for c in hostile[:3])
               + "): kill them or leave to the world map first")
    if hostile:
        print("note: a hostile is in view; sleeping now risks waking to a fight")
    slot = [b for b in call("buttons", all=True)["data"]["buttons"] if b.get("hot") == "HotItemActionSleep"]
    if not slot:
        refuse("no 'Use bed in inventory' slot on the F-key hotbar")
    slept = False
    # run 44: the sleeping bag was gone and the hotbar's sleep said "There's no bed in your backpack. You can use Rest
    # Ability to sleep but..."; the ability bar's Rest (card 'Rest', no text: pick it by card) slept me in Mifu Village
    beds = [i for i in call("inv")["data"]["items"]
            if re.search(r"sleeping bag|makeshift bed|\bbed\b", i["name"].lower()) and "recipe" not in i["name"].lower()]
    # run 40: right after a walk (three times at a nefia's door) the click starts nothing, no message, and the same click
    # works a moment later; the failed door nap cost Tainted Forest, which expired during the nap from B1
    for attempt in range(3):
        btns = call("buttons", all=True)["data"]["buttons"]
        rest = [b for b in btns if "ButtonAbility" in (b.get("name") or "") and b.get("card") == "Rest"]
        slot = [b for b in btns if b.get("hot") == "HotItemActionSleep"]
        if not beds and rest:
            if attempt == 0:
                print("no bed carried: the Rest ability", flush=True)
            call("rclick", i=rest[0]["i"])
        elif not slot:
            refuse("no 'Use bed in inventory' slot on the F-key hotbar")
        else:
            call("click", i=slot[0]["i"])
        wait_until("layer", timeout=3000)  # the sleep layer comes up a moment after the click
        for _ in range(150):
            s = call("state")["data"]
            p = s["pc"]
            # run 40: a sleep across 05:00 opens the shipping report, which holds ConSleep until it is closed: this loop
            # then waited out its whole 5 real minutes
            if (s.get("layers") or {}).get("top") == "LayerShippingResult":
                close_all()
                time.sleep(1)
                continue
            # the new-game test: a dream's dialog at waking ("You look tired") holds the same way until it's read
            if (s.get("layers") or {}).get("top") == "LayerDrama":
                print(run("talk.py", "20").strip()[-200:], flush=True)
                time.sleep(1)
                continue
            asleep = "ConSleep" in p["conditions"] or (p["ai"] or "").startswith("AI_Sleep")
            slept = slept or asleep
            if not asleep and (slept or _ > 3):
                break
            time.sleep(2)
        if slept:
            break
        print(f"try {attempt + 1}: the click started no sleep", flush=True)
    log = [l for l in s.get("log") or [] if "sleep" in l.lower() or "wake" in l.lower() or "bed" in l.lower()
           or "sleepy" in l.lower() or "bad idea" in l.lower()]
    print(f"SP {p0['sp']} -> {p['sp']}/{p['maxSp']}  {p0['date']} -> {p['date']}  hunger {p['hunger']}")
    print("log: " + " / ".join(log[-4:]))
    if not slept:  # run 40: Boring Ruin's door printed rc 0 with no sleep, and the ladder then stopped Sleepy on B1
        print("did not sleep: the game's last lines: " + " / ".join((s.get("log") or [])[-4:]))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
