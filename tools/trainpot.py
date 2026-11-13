"""Buy temporary potential from a trainer (run 42, G48 M0; the user, 2026-11-06: "if you have platinum coins you should enhance the skills so they level easier"). With a trainer's
"Choose a skill to train" list open, click a skill until its potential reads the target. CostTrain (fact #1296): under skill 10, 1 platinum each to +100, 2 each to +200, 3 each to +300.
Each level-up of the skill takes temp/4 + 5-9 off it, so buy it just before a push on that skill.

usage: python -I tools/trainpot.py NAME=POT [NAME=POT ...] [--floor N]   NAME as the list shows it ("Carpentry", "Crafting"); POT the potential to reach; --floor: platinum to keep (0)
       python -I tools/trainpot.py carpentry=300 blacksmith=300 --floor 60
Open the list first (talkto.py TRAINER, then click "Train me."). The list stays open at the end. Exit 0 done, 1 refused (no list, no such skill), 3 stopped (the platinum floor).
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, data, refuse, setup, stop, top  # noqa: E402

SKILL_ID = {"crafting": "handicraft", "sculpting": "sculpture"}


def pot_of(name):
    want = SKILL_ID.get(name.lower(), name.lower())
    skills = data("skills").get("skills") or {}
    # run 46: weapon skills are keyed weaponPolearm, weaponBlunt...: match the display name ("Polearm", "Mace") too
    row = skills.get(want) or next((r for r in skills.values() if (r.get("name") or "").lower() == name.lower()), None)
    return row.get("potential") if row else None


def platinum():
    for b in data("buttons").get("buttons") or []:
        m = re.match(r"([\d,]+) \(tip: Platinum", b.get("text") or "")
        if m:
            return int(m.group(1).replace(",", ""))
    return None


def main():
    setup()
    args = sys.argv[1:]
    floor = int(args[args.index("--floor") + 1]) if "--floor" in args else 0
    wants = [a.split("=") for a in args if "=" in a]
    if not wants:
        refuse(__doc__.splitlines()[3])
    if top() != "LayerList":
        refuse(f"the trainer's list isn't open (top layer {top()})")
    for name, pot in wants:
        pot = int(pot)
        for _ in range(60):
            now = pot_of(name)
            if now is None:
                refuse(f"no skill '{name}' in the skills list")
            if now >= pot:
                break
            have = platinum()
            if have is not None and have <= floor:
                stop(f"{name}: potential {now}, platinum {have} at the floor {floor}")
            rows = [b for b in data("buttons").get("buttons") or [] if (b.get("text") or "").lower().startswith(name.lower() + " |")]
            if not rows:
                refuse(f"{name} isn't on this trainer's list")
            r = call("click", i=rows[0]["i"], expect=name)
            if not r.get("ok"):
                refuse(f"click: {r}")
            time.sleep(0.15)
        print(f"{name}: potential {pot_of(name)}, platinum {platinum()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
