"""List the furniture installed on this map with its base value and weight, most valuable first
(the user, run 08: dungeon wall lights are worth money). Dungeon and nefia furniture belongs to
nobody: take it with a right-click Grab (`act.py DX DZ "Grab (a wall light" right`; pick up what
lies on top first), then `hotbar.py --deselect` to put it in the pack. In towns it is someone's
property (theft: Karma -1): this tool says so and lists nothing there.

usage: python -I tools/valuables.py [min_value=500] [max_weight=15]
       python -I tools/valuables.py --take NAME [MAX=14]   grab every installed NAME on this map
  (run 16: 15 wall lights in a nefia shipped for 67 each). Stops (exit 3) on a hostile in view
  (fight, then run it again) and when the pack gets heavy (speed matters: drop heavy loot by the
  stairs, finish the floor, pick it up after).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import pack_full, refuse  # noqa: E402
from kb import KB  # noqa: E402

QUALITY = r"^(an? |\d+ )?(magnificent|superior|great|good|bad|miracle|godly|fine|cursed|blessed|exquisite|royal|maniac|stupid|esteemed)?\s*"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    nums = [float(a) for a in sys.argv[1:] if a.replace(".", "").isdigit()]
    min_value = nums[0] if nums else 500
    max_weight = nums[1] if len(nums) > 1 else 15
    s = call("state")["data"]
    if s["zone"].get("town"):
        refuse(f"{s['zone']['full']} is a town: its furniture is someone's property (theft is Karma -1)")
    kb = KB()
    hits = [h for h in call("find", name="", r=999, n=2000)["data"]["hits"] if h["kind"] == "thing" and h["installed"]]
    rows, seen = [], {}
    for h in hits:
        base = re.sub(QUALITY, "", h["name"].lower()).strip()
        if base not in seen:
            keys = kb.find(base, 1, ["thing"])
            r = kb.row(keys[0]) if keys else {}
            seen[base] = (int(r.get("value") or 0), int(r.get("weight") or 0) / 100, keys[0] if keys else "?")
        value, weight, key = seen[base]
        # run 16 (fact #619): a cobweb lists base value 976 but offers only "Collect", which destroys it
        if value >= min_value and weight <= max_weight and "cobweb" not in h["name"].lower():
            rows.append((value, weight, h, key))
    for value, weight, h, key in sorted(rows, key=lambda t: (-t[0], t[2]["dist"])):
        print(f"{value:>7} Wt{weight:>5.1f}  ({h['dx']:+d},{h['dz']:+d}) d{h['dist']:<3} {h['name']}  [{key}]")
    if not rows:
        print(f"nothing installed worth {min_value:.0f}+ under weight {max_weight:.0f}")


def take(name, most):
    import time
    from common import pc, put_away, state, stop, walk_beside
    if (state().get("zone") or {}).get("town"):
        stop("a town: its furniture is someone's property (theft)")
    put_away()
    # run 17: a selected hotbar slot (the Putit) stays "held" after put_away and turns the
    # right-click into Throw: deselect it too, or no light offers Grab
    from common import run
    run("hotbar.py", "--deselect")
    me = [m for m in call("power")["data"]["party"] if m.get("pc")]
    speed0, got = (me[0]["speed"] if me else None), 0
    for _ in range(most):
        s = state()
        foes = [c["name"] for c in s.get("nearby") or [] if c.get("hostile")]
        if foes:
            stop(f"grabbed {got}; a hostile in view ({', '.join(foes[:3])}): fight, then run again")
        if pack_full(s=s):  # run 12 (errors row 5): a pick-up into a full pack vanished
            stop(f"grabbed {got}; the pack is full: store or drop something, then run again")
        hits = [h for h in call("find", name=name, r=99, n=3)["data"]["hits"] if h["kind"] == "thing" and h["installed"]]
        if not hits:
            break
        p = pc()
        x, z = p["x"] + hits[0]["dx"], p["z"] + hits[0]["dz"]
        walk_beside(x, z, r=1)
        p = pc()
        acts = call("acts", dx=x - p["x"], dz=z - p["z"], mode="right")["data"]["acts"]
        g = [a for a in acts if a["text"].startswith("Grab")]
        if not g:
            stop(f"grabbed {got}; no Grab at {x},{z}: " + " | ".join(a["text"] for a in acts))
        call("do", i=g[0]["i"])
        time.sleep(1.2)
        put_away()  # Grab leaves it in hand; the next acts would offer only Throw
        got += 1
        me = [m for m in call("power")["data"]["party"] if m.get("pc")]
        speed = me[0]["speed"] if me else None
        if speed and speed0 and speed < speed0 * 0.92:
            stop(f"grabbed {got}; speed {speed0} -> {speed}: the pack is heavy")
    print(f"grabbed {got} {name}")


if __name__ == "__main__":
    if "--take" in sys.argv:
        i = sys.argv.index("--take")
        rest = sys.argv[i + 1:]
        take(rest[0], int(rest[1]) if len(rest) > 1 else 14)
    else:
        main()
