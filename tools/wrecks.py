"""Mine every wreck on the explored map with the pickaxe and pick up what drops (run 06: five
wrecks on one floor of Spiritual Cave; wrecks give gems, scrap, fiber, bolts, logs).

Nearest wreck first. Holds the pickaxe for each wreck and puts it away before a fight. When a
hostile shows up: fights it with fight.py if it is at or below my level, else stops and hands
control back. Stops (exit 3) on a window, low SP, HP under the floor, a full pack, or fight.py
stopping or refusing; exit 0 when no wreck is left; exit 1 without a pickaxe.

usage: python -I tools/wrecks.py [R=60] [min_hp_pct=70] [min_sp=5]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import grab, last, pack_full, refuse, run, stop  # noqa: E402
from harvest import DONE, INTERRUPTED, harvest  # noqa: E402
from unpack import put_away_held  # noqa: E402  (the inventory "Put away"; common.put_away is the hotbar deselect)


def wrecks(r):
    hits = call("find", name="wreck", r=r, n=20)["data"]["hits"]
    return [h for h in hits if h.get("kind") == "obj" and "wreck" in (h.get("name") or "")]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    r = int(a[0]) if a else 60
    min_hp = int(a[1]) if len(a) > 1 else 70
    min_sp = int(a[2]) if len(a) > 2 else 5
    tried = set()
    for _ in range(20):
        s = call("state")["data"]
        pc = s["pc"]
        if pc["hp"] * 100 < pc["maxHp"] * min_hp:
            stop(f"HP {pc['hp']}/{pc['maxHp']} under {min_hp}%")
        if (s.get("layers") or {}).get("top"):
            stop(f"window open ({s['layers']['top']})")
        foes = [c for c in s.get("nearby") or [] if c["hostile"]]
        if foes:
            f = min(foes, key=lambda c: c["dist"])
            if any(c["lv"] > pc["lv"] for c in foes):
                put_away_held()
                stop(f"a hostile above my level in view: {[(c['name'], c['lv']) for c in foes]}")
            put_away_held()
            out = run("fight.py", f["name"].removeprefix("a ").removeprefix("an "), str(min_hp))
            print(f"fight {f['name']} Lv{f['lv']}: " + last(out))
            if out.rc in (1, 3):  # refused (a rule) or stopped (HP, a big hit, a window): mine to decide
                stop(f"fight.py {'refused' if out.rc == 1 else 'stopped'}: {last(out)[:120]}")
            continue
        if pack_full():  # run 12 (errors row 5): a pick-up into a full pack vanished
            put_away_held()
            stop("the pack is full: store or drop something before the next wreck")
        todo = [w for w in wrecks(r) if (w["x"], w["z"]) not in tried]
        if not todo:
            print("no wreck left")
            break
        w = min(todo, key=lambda h: max(abs(h["x"] - pc["x"]), abs(h["z"] - pc["z"])))
        tried.add((w["x"], w["z"]))
        if "pickaxe" not in (pc.get("held") or ""):
            # A selected hotbar slot (the Putit after a fight) is the held item and blocks the
            # Grab (run 06: two wrecks got "no harvest act"): empty the hands first.
            put_away_held()
            if not grab("pickaxe", what="tool"):
                refuse("couldn't take a pickaxe in hand (none in the pack?)")
        out = harvest(w["x"] - pc["x"], w["z"] - pc["z"], min_sp)
        if out == INTERRUPTED:
            tried.discard((w["x"], w["z"]))
        elif out != DONE:
            print(f"wreck at {w['x']},{w['z']}: {out}")
    put_away_held()
    print(" / ".join(call("state")["data"]["log"][-6:]))  # the last 6 lines (oldest first)


if __name__ == "__main__":
    main()
