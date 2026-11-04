"""Zap a carried rod on myself N times (run 14: Magic Device, a new skill, levels with every zap).
Only rods that are harmless on oneself: holy shield, holy light, cure ..., keeping KEEP charges.

usage: python -I tools/zap.py "rod of holy shield" [N=5] [--keep K=3]
Opens the backpack (where the rods ride), holds the fullest stack of the rod (common.grab, a
whole-word match), right-click Zap on my own cell, repeats; stops (exit 3) on a hostile in view or
a window; ends (exit 0) with the rod down to K charges. Prints skill-up lines.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, grab, matches, ready, refuse, run, setup, stop, wait_idle  # noqa: E402

SAFE = ("holy shield", "holy light", "cure", "heal", "hero", "magic map")  # run 34: magic map shows the floor (no stairs found)


def charges(name):
    """The most-charged stack of this rod in the pack or an open bag (`inv` lists the top level only)."""
    best = None
    slots = [b for b in call("buttons", all=True)["data"]["buttons"] if "ButtonGrid inventory" in b["name"] and b.get("card")]
    for b in matches(name, slots):
        m = re.search(r"\((\d+) Charges?\)", b["card"])
        best = max(best or 0, int(m.group(1)) if m else 0)
    return best


def main():
    setup()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    rod = args[0]
    n = int(args[1]) if len(args) > 1 else 5
    keep = int(sys.argv[sys.argv.index("--keep") + 1]) if "--keep" in sys.argv else 3
    if not any(s in rod for s in SAFE):
        refuse(f"{rod!r} isn't on the self-safe list {SAFE}")
    run("bag.py", "backpack")  # the rods ride in the backpack; item lookups see into an open bag
    done = 0
    stopped = None
    for _ in range(n):
        # run 17: threat()'s HP floor refused to zap a cure rod exactly when HP was low (71/129):
        # only hostiles, windows other than the open bag, busy and bad conditions stop a zap
        # run 24: a Lv3 goblin in view stopped a heal at 79/177 on a danger-9 floor: a cure rod heals
        # with hostiles in view (that is when it is needed); the other rods still wait for none
        why = ready(hp=None, hunger=None, burden=None, world_ok=True, hostiles="cure" not in rod)
        if why:
            stopped = why
            break
        left = charges(rod)
        if left is None:
            refuse(f"no {rod} in the pack or the open backpack")
        if left <= keep:
            print(f"stopped: {rod} down to {left} charges (keeping {keep})")
            break
        if not grab(rod, prefer="charges", what="rod"):
            refuse(f"could not take {rod} in hand")
        acts = call("acts", dx=0, dz=0, mode="right")["data"]["acts"]
        z = [a for a in acts if a["text"].startswith("Zap")]
        if not z:
            refuse("no Zap act on my cell: " + ", ".join(a["text"] for a in acts))
        call("do", i=z[0]["i"])
        wait_idle()
        done += 1
    log = call("state")["data"].get("log") or []
    print(f"zapped {done}x; {rod}: {charges(rod)} charges left")
    for ln in log[-12:]:
        if "skill" in ln.lower() or "increase" in ln.lower():
            print("  " + ln)
    run("close.py")
    if stopped:
        stop(stopped)


if __name__ == "__main__":
    main()
