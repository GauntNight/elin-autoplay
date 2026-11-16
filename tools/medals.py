"""Small Medals hidden on a town or named map, and picking them up (the user, 2026-10-29: "that may need an
update so you are looking for those in game next time").

The wiki (ylvapedia Elin:Small_Medal, read 2026-10-29) lists 141 medals hidden at fixed spots on 33 towns and
named places (knowledge/medals.md); none in nefias or random fields. A hidden medal is an installed thing:
stepping on its cell says *twinkle* and turns it loose (TraitCurrencyMedal.OnStepped, "spotMedalStep"), and it
is then picked up like any item. A few lie under furniture, behind a wall or a bridge, or in deep water: a
hammer, a shovel or a rod of teleport reaches them, and in a town the first two are crimes, so this tool only
reports those (a deliberate step, sneakmine.py's rules).

The bridge's find op sees a hidden medal on any explored cell, which the player can't. So this tool works only
on a map the wiki lists, where the spots are public knowledge, and refuses anywhere else (play honestly).

usage: python -I tools/medals.py          the medals on this map's explored cells: where, and reachable or why not
       python -I tools/medals.py --take   walk onto each reachable one, nearest first, and pick it up
Exit codes (common.py): 0 done, 1 refused (not a wiki map), 2 bridge, 3 stopped (a hostile, HP, a window).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import THRESHOLDS, cells, data, ready, refuse, setup, state, stop, walk  # noqa: E402

# The wiki's maps and the medals each hides (knowledge/medals.md has the spots and the hard ones).
WIKI_MAPS = {
    "Port Kapul": 8, "Quiet Beach": 2, "Cursed Manor": 2, "Derphy": 10, "Tinker's Camp": 3,
    "Little Garden": 2, "Olvina": 4, "Old Keep": 4, "Orphanage": 2, "Mysilia": 9, "Merchant Guild": 3,
    "Willow": 3, "Hill Cave": 1, "Vernis": 1, "Aquli Teola": 4, "Yowyn": 8, "Palmia": 7,
    "Fortune Bell": 9, "Embassy": 2, "Truce Ground": 3, "Specwing": 5, "Doga Ruins Camp": 3,
    "Nefu Village": 4, "Graveyard": 2, "Lumiest": 11, "Mifu Village": 5, "Where Winds Rest": 1,
    "Village of Atonement": 4, "Miral and Garokk's Workshop": 3, "Noyel": 5,
    "Mansion of Younger Sister": 3, "Seeker's Keep": 5, "Garden of Eternity": 3,
}


def wiki_map(zone):
    """The wiki map this zone is, or None: never a nefia, the world map, or Lumiest Crater (none listed)."""
    zone = zone or {}
    name = (zone.get("name") or "").lower()
    if zone.get("nefia") or zone.get("region") or "crater" in name:
        return None
    return next((m for m in WIKI_MAPS if m.lower() in name), None)


def find_medals():
    """Every Small Medal on an explored cell of this map, hidden (installed) or loose."""
    hits = data("find", name="small medal", r=999, n=300)["hits"]
    return [h for h in hits if h["kind"] == "thing"]


def why_not(h, ci):
    """None when a walk can reach the medal's cell, else the reason."""
    if ci.get("suffocate"):
        return "deep water (walkto refuses it: a rod of teleport or water breathing)"
    if ci.get("blocked"):
        return "blocked: furniture, a wall or a bridge over it (a hammer, shovel or rod of teleport: a crime in a town)"
    if not ci.get("floor"):
        return "no floor"
    if any(t.get("npcProperty") for t in ci.get("thingInfo") or [] if "medal" in (t.get("name") or "").lower()):
        return "someone's property"
    return None


def medal_count():
    # run 50: the pack grid only (`inv`) missed the stack in the backpack, so 7 taken in Yowyn read "picked up 0";
    # items.py reads every depth by kind
    import items
    return items.count(kind="medal", usable_only=False)


def pick_here():
    """Pick up a loose medal underfoot; True when one came into the pack."""
    for mode in ("all", "right"):  # loot.py, run 10: some cells offer only the right-click Grab
        acts = data("acts", dx=0, dz=0, mode=mode)["acts"]
        picks = [a for a in acts if a["text"].startswith(("Pick", "Grab (")) and "medal" in a["text"].lower()]
        if picks:
            call("do", i=picks[0]["i"])
            time.sleep(1.0)
            return True
    # run 31 (bridge 0.35.0): a twinkled medal is roaming but keeps the map editor's hidden bit, so no act
    # list shows it and the step doesn't auto-pick it: take it with the game's own Chara.Pick by uid
    info = data("cell", dx=0, dz=0).get("thingInfo") or []
    for t in info:
        if "medal" in (t.get("name") or "").lower() and t.get("placeState") == "roaming" and not t.get("npcProperty"):
            if call("pick", uid=t["uid"]).get("ok"):
                time.sleep(0.5)
                return True
    return False


def main():
    setup()
    s = state()
    m = wiki_map(s.get("zone"))
    if not m:
        refuse(f"{(s.get('zone') or {}).get('name')} isn't a map the wiki lists medals for: the bridge would show "
               "hidden things the player can't see")
    hits = find_medals()
    info = cells([(h["x"], h["z"]) for h in hits]) if hits else {}
    print(f"{m}: the wiki lists {WIKI_MAPS[m]}; {len(hits)} on explored cells here "
          f"({sum(1 for h in hits if h['installed'])} hidden, {sum(1 for h in hits if not h['installed'])} loose)")
    todo = []
    for h in hits:
        why = why_not(h, info.get((h["x"], h["z"])) or {})
        state_txt = "hidden" if h["installed"] else "loose"
        print(f"  {h['x']},{h['z']} d{h['dist']} {state_txt}: " + (why or "reachable"))
        if not why:
            todo.append(h)
    if "--take" not in sys.argv or not todo:
        if WIKI_MAPS[m] > len(hits):
            print(f"  ({WIKI_MAPS[m] - len(hits)} not on explored cells: taken already, or unexplored; "
                  "knowledge/medals.md says where)")
        return
    start, got = medal_count(), []
    for h in sorted(todo, key=lambda h: h["dist"]):
        why = ready(hp=THRESHOLDS["walk_hp"])
        if why:
            print("picked up:", ", ".join(got) or "none")
            stop(why)
        w = walk(h["x"], h["z"], r=4, hp=THRESHOLDS["walk_hp"], timeout=60000)
        if w.get("why") != "arrived":
            if w.get("why") in ("hostile", "hp", "window", "zone"):
                print("picked up:", ", ".join(got) or "none")
                stop(f"the walk to {h['x']},{h['z']} stopped: {w.get('why')}")
            print(f"  can't reach {h['x']},{h['z']}: {w.get('why')}")
            continue
        time.sleep(0.5)  # the step turns it loose (OnStepped)
        log = [ln for ln in (state().get("log") or [])[-4:] if "twinkl" in ln.lower()]
        if pick_here():
            got.append(f"{h['x']},{h['z']}")
            print(f"  took {h['x']},{h['z']}" + (f" ({log[-1]})" if log else ""))
        else:
            print(f"  nothing to pick up at {h['x']},{h['z']} (still hidden, or not mine)")
    n = medal_count() - start
    print(f"picked up {n} Small Medal(s) at: " + (", ".join(got) or "none"))


if __name__ == "__main__":
    main()
