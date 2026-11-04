"""G12's done-when, read from the game's own rooms (bridge 0.27.0 `rooms`): the town checks.

The user (2026-10-21): "building a town (multiple houses, work benches in houses, boxes within the
relevet houses, etc)". A house is a game Lot: rooms within 1 cell in the same room-board group merge
into one (RoomManager.RebuildLots). A house counts as named when one of its rooms carries a room
board whose name starts with the house's theme (Workshop, Forge, ...).

The five checks (knowledge/goals.md, G12):
  1. six houses, each named by a room board: Workshop, Forge, Kitchen, Farmhouse, Storehouse, Residence
  2. every crafting station inside the house of its theme
  3. every storage box inside the house of its theme (office things and fields stay outside)
  4. every bed in a Residence
  5. upkeep: no garbage on the map (the resident-death half is read from the home log by hand)

usage: python -I tools/town.py           the checks, with every thing out of place (exit 1 if any fail)
       python -I tools/town.py --rooms   the rooms and lots only
       python -I tools/town.py --json    the raw `rooms` reply
       python -I tools/town.py --lights  G30 M5 (run 32): a light inside every room, a light within 2 of every door,
                                         no path cell (paths.py's network) over 4 from a light, and no electric light.
                                         A light is a thing of the game's 'light' category (things.json); a fire light
                                         draws no electricity. Distances are straight-line. Exit 1 if any fail.
       python -I tools/town.py --garden  G30 M3 (run 32): the field planted (a planted seed counts) with nothing ripe
                                         or withered left, no rotten food in the harvest box or a fridge, a flower
                                         within 3 of a door of every house. Exit 1 if any fail.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data, setup  # noqa: E402
import home  # noqa: E402

HOUSES = ("Workshop", "Forge", "Kitchen", "Farmhouse", "Storehouse", "Residence", "Depot")  # run 30 (G28): the Depot

# Stations by name (the game's names); anything else with a crafter trait is listed as unthemed.
STATION_HOUSE = {
    "workbench": "Workshop", "carpenter's table": "Workshop", "sawmill": "Workshop",
    "tinker's table": "Workshop", "stonecutter": "Workshop", "mason's table": "Workshop",
    "signboard workshop": "Workshop", "drafting table": "Workshop", "loom": "Workshop",
    "spinner": "Workshop", "wall workshop": "Workshop", "block workshop": "Workshop",
    "flooring workshop": "Workshop", "platform workshop": "Workshop",
    "kiln": "Forge", "smelter": "Forge", "blacksmith's table": "Forge",
    "bonfire": "Kitchen", "stove": "Kitchen", "millstone": "Kitchen", "ration maker": "Kitchen",
    "cooking pot": "Kitchen", "cutting board": "Kitchen", "oven": "Kitchen", "grill": "Kitchen", "fermentation barrel": "Kitchen",
}

# Boxes by their home.py cell (the themes of elin-home 2a and packcheck). OFFICE stays outside.
BOX_HOUSE = {home.WOOD_BOX: "Workshop", home.STONE_BOX: "Forge", home.STONE_BOX_2: "Forge",
             home.FARM_BOX: "Farmhouse", home.HARVEST_BOX: "Farmhouse", home.HARVEST_FRIDGE: "Farmhouse", home.FODDER_BOX: "Farmhouse",
             home.PANTRY: "Kitchen", home.PANTRY_2: "Kitchen", home.PANTRY_3: "Kitchen", home.DISH_BOX: "Kitchen",
             home.PARTS_BOX: "Workshop", home.MAPS_BOX: "Workshop", home.SPARES: "Storehouse", home.SPARES2: "Storehouse",
             home.ARMORY: "Residence", home.BOOKSHELF: "Storehouse",  # run 18: the armory arms the residents
             home.COLLECTIBLES: "Storehouse", home.FARM_BOX2: "Farmhouse", home.SPARE_BOX: "Storehouse"}
for xy in home.BAG_PARTS:
    BOX_HOUSE[xy] = "Workshop"
for xy in home.VALUABLES + home.LIBRARY:
    BOX_HOUSE[xy] = "Storehouse"
BOX_HOUSE[home.STORAGE_CHEST] = "Workshop"  # run 20: the library overflow sits in the Workshop
BOX_HOUSE[home.OVERFLOW2] = "Workshop"  # run 22: the mystic treasure chest beside it
for xy in (home.ARMORY2, home.SPARES3, (48, 58)):  # run 23: three wooden boxes beside them (Armory 2, Spares 3, Library 2)
    BOX_HOUSE[xy] = "Workshop"
for xy in (home.FARM_BOX, home.SPARES2, home.LIBRARY[1], home.VALUABLES[-1], home.ARMORY3, home.PANTRY_2):
    BOX_HOUSE[xy] = "Depot"  # run 30 (G28): the six sturdy boxes of the new Depot
BOX_HOUSE[home.STORAGE_CHEST_2] = "Depot"  # run 31 (G29 M1): the second ★Storage Chest, every box's overflow
BOX_HOUSE[home.OVERFLOW3] = "Depot"  # run 31: a mystic treasure chest beside it
for xy in home.OVERFLOW4:
    BOX_HOUSE[xy] = "Depot"  # run 31: two more, installed for G30 M4
OFFICE = {home.MAIL_POST, home.TAX_CHEST, home.SHIPPING, home.TRASH_CAN, home.PRACTICE_CHEST, home.FIAMA_CHEST, home.MAIL_PACKAGE, *home.MAIL_SPOTS}
OFFICE_TRAITS = ("TraitMailPost", "TraitShippingChest", "TraitChestPractice", "TraitTrashcan",
                 "TraitDeliveryChest", "TraitTaxChest")


def station_theme(name):
    n = name.lower()
    for key, house in STATION_HOUSE.items():
        if n.endswith(key):  # "a stupid ration maker" is still the ration maker
            return house
    return None


def house_of(theme_name):
    """The house theme a room board name stands for ("Residence 2" -> Residence), or None."""
    n = (theme_name or "").strip().lower()
    for h in HOUSES:
        if n.startswith(h.lower()):
            return h
    return None


def lights_check(d):
    """G30 M5's done-when, read from the same `rooms` reply plus paths.py's path network."""
    import paths  # noqa: E402 (its network() reads the map cells: only this check needs it)
    game = json.loads((Path(__file__).resolve().parent.parent / "knowledge/game/things.json").read_text(encoding="utf-8"))
    light_ids = {r["id"]: r.get("electricity") for r in game if r.get("category") == "light"}
    things = d["things"]
    lights = [t for t in things if t["id"] in light_ids]
    rooms = d["rooms"]
    fails = 0

    def near(x, z, r):
        return [t for t in lights if (t["x"] - x) ** 2 + (t["z"] - z) ** 2 <= r * r]

    print(f"lights on the map: {len(lights)}")
    electric = [t for t in lights if light_ids[t["id"]]]
    print(f"a. electric lights: {len(electric)}" + "".join(f"\n     {t['name']} ({t['x']},{t['z']})" for t in electric))
    fails += bool(electric)
    dark = [r for r in rooms if not any(t["room"] == r["uid"] for t in lights)]
    print(f"b. rooms with a light inside: {len(rooms) - len(dark)} of {len(rooms)}")
    for r in dark:
        print(f"     room {r['uid']} '{r['name']}' {r['x']}-{r['mx']} x {r['z']}-{r['mz']}")
    fails += bool(dark)
    doors = [t for t in things if t["door"]]
    unlit = [t for t in doors if not near(t["x"], t["z"], 2)]
    print(f"c. doors with a light within 2: {len(doors) - len(unlit)} of {len(doors)}")
    for t in unlit:
        print(f"     {t['name']} ({t['x']},{t['z']})")
    fails += bool(unlit)
    net, _, _ = paths.network()
    far = sorted(c for c in net if not near(c[0], c[1], 4))
    print(f"d. path cells within 4 of a light: {len(net) - len(far)} of {len(net)}")
    if far:
        print("     " + " ".join(f"{x},{z}" for x, z in far))
    fails += bool(far)
    print(f"\n{'PASS' if not fails else f'{fails} of 4 light checks fail'}")
    return 1 if fails else 0


def garden_check(d):
    """G30 M3 (run 32): every tilled field cell holds a plant or a planted seed (an installed TraitSeed thing: it
    sprouts at the next 06:00; Delegated Farming replants harvested cells that way), none ripe and left or
    withered; no rotten food in the harvest box or a fridge; a flower within 3 of a door of every house."""
    from common import cells
    info = cells(home.FIELD)
    tilled = [c for c, i in info.items() if (i.get("floor") or "") == "field"]
    seeded = [c for c in tilled if not info[c].get("obj")
              and any(t.get("trait") == "TraitSeed" for t in info[c].get("thingInfo") or [])]
    bare = [c for c in tilled if not info[c].get("obj") and c not in seeded]
    ripe = [c for c in tilled if info[c].get("ripe")]
    withered = [c for c in tilled if any(w in str(info[c].get("obj") or "").lower() for w in ("wither", "dead"))]
    fails = 0
    print(f"a. field cells: {len(tilled)} tilled, {len(tilled) - len(bare) - len(seeded)} growing, {len(seeded)} seeded,"
          f" bare {bare or 0}, ripe and left {ripe or 0}, withered {withered or 0}")
    fails += bool(bare or ripe or withered)
    rotten = []
    for b in data("stock")["boxes"]:
        if (b["x"], b["z"]) == tuple(home.HARVEST_BOX) or b.get("trait") == "TraitFridge":
            rotten += [f"{i['name']} ({b['name']} {b['x']},{b['z']})" for i in b["items"] if "rotten" in i["name"].lower()]
    print(f"b. rotten food in the harvest box and fridges: {len(rotten)}" + "".join(f"\n     {r}" for r in rotten))
    fails += bool(rotten)
    rooms = {r["uid"]: r for r in d["rooms"]}
    houses = {}
    for t in d["things"]:
        if t["door"]:
            near = [rooms[u] for u in rooms if rooms[u]["x"] - 1 <= t["x"] <= rooms[u]["mx"] + 1
                    and rooms[u]["z"] - 1 <= t["z"] <= rooms[u]["mz"] + 1]
            lots = {r["lot"] for r in near}  # a house is a lot: my room's door is the Residence's (run 32)
            house = next((house_of(r["name"]) for r in d["rooms"] if r["lot"] in lots and house_of(r["name"])), None)
            houses.setdefault(house or f"door {t['x']},{t['z']}", []).append((t["x"], t["z"]))
    pts = {(x, z) for ds in houses.values() for dx, dz in ds for x in range(dx - 3, dx + 4) for z in range(dz - 3, dz + 4)}
    around = cells(sorted(pts))
    flowers = {c for c, i in around.items() if "flower" in str(i.get("obj") or "").lower()}
    bedless = [h for h, ds in houses.items()
               if not any((fx - dx) ** 2 + (fz - dz) ** 2 <= 9 for dx, dz in ds for fx, fz in flowers)]
    print(f"c. houses with a flower bed by a door: {len(houses) - len(bedless)} of {len(houses)}"
          + (f"; none by {', '.join(bedless)}" if bedless else ""))
    fails += bool(bedless)
    print(f"\n{'PASS' if not fails else f'{fails} of 3 garden checks fail'}")
    return 1 if fails else 0


def main(argv):
    setup()
    d = data("rooms")
    if "--garden" in argv:
        return garden_check(d)
    if "--json" in argv:
        print(json.dumps(d, indent=1, ensure_ascii=False))
        return 0
    if "--lights" in argv:
        return lights_check(d)
    rooms = {r["uid"]: r for r in d["rooms"]}
    lots = {}
    for r in d["rooms"]:
        lots.setdefault(r["lot"], []).append(r)
    print(f"{d['zone']}: {len(rooms)} rooms in {d['lots']} houses"
          + (" (the game has a room refresh pending)" if d.get("dirtyRooms") or d.get("dirtyLots") else ""))
    lot_house = {}
    for lot, rs in sorted(lots.items()):
        names = [house_of(r["name"]) for r in rs if r["plate"]]
        named = sorted({n for n in names if n})
        lot_house[lot] = named[0] if len(named) == 1 else None
        clash = " (two themes: " + ", ".join(named) + ")" if len(named) > 1 else ""
        print(f"  house {lot}: {lot_house[lot] or 'unnamed'}{clash}")
        for r in rs:
            print(f"    room {r['uid']} '{r['name']}'{' [board]' if r['plate'] else ''} {r['access']}"
                  f" group {r['group']} {'roof' if r['roof'] else 'no roof'}"
                  f" {r['x']}-{r['mx']} x {r['z']}-{r['mz']} ({r['cells']} cells)")
    if "--rooms" in argv:
        return 0

    def where(t):
        r = rooms.get(t["room"])
        return lot_house.get(r["lot"]) if r else None

    def at(t):
        return f"{t['name']} ({t['x']},{t['z']})"

    things = d["things"]
    fails = 0
    # 1. houses
    have = sorted({h for h in lot_house.values() if h})
    missing = [h for h in HOUSES if h not in have]
    print(f"\n1. houses named: {len(have)} of {len(HOUSES)}" + (f"; missing {', '.join(missing)}" if missing else ""))
    fails += bool(missing)
    # 2. stations
    stations = [t for t in things if t["crafter"]]
    bad, unthemed = [], []
    for t in stations:
        theme = station_theme(t["name"])
        if theme is None:
            unthemed.append(t)
        elif where(t) != theme:
            bad.append((t, theme))
    print(f"2. stations housed: {len(stations) - len(bad) - len(unthemed)} of {len(stations)}")
    for t, theme in bad:
        print(f"     {at(t)} -> {theme} (now in {where(t) or 'the open'})")
    for t in unthemed:
        print(f"     {at(t)}: no theme for it in town.py (STATION_HOUSE)")
    fails += bool(bad or unthemed)
    # 3. boxes
    boxes = [t for t in things if t["container"] and not t["bed"]
             and (t["x"], t["z"]) not in OFFICE and t["trait"] not in OFFICE_TRAITS]
    bad, unthemed = [], []
    for t in boxes:
        theme = BOX_HOUSE.get((t["x"], t["z"]))
        if theme is None:
            unthemed.append(t)
        elif where(t) != theme:
            bad.append((t, theme))
    print(f"3. boxes housed: {len(boxes) - len(bad) - len(unthemed)} of {len(boxes)}")
    for t, theme in bad:
        print(f"     {at(t)} -> {theme} (now in {where(t) or 'the open'})")
    for t in unthemed:
        print(f"     {at(t)}: no theme (not in tools/home.py)")
    fails += bool(bad or unthemed)
    # 4. beds
    beds = [t for t in things if t["bed"]]
    bad = [t for t in beds if where(t) != "Residence"]
    print(f"4. beds in a Residence: {len(beds) - len(bad)} of {len(beds)}")
    for t in bad:
        print(f"     {at(t)} (now in {where(t) or 'the open'})")
    fails += bool(bad)
    # 5. garbage
    g = data("find", name="garbage", r=999, n=50)
    piles = [h for h in g["hits"] if h["kind"] == "thing" and not h.get("installed")]  # not the garbage dump sign
    print(f"5. garbage on the map: {len(piles)}" + (" (trash.py sweep)" if piles else ""))
    fails += bool(piles)
    print(f"\n{'PASS' if not fails else f'{fails} of 5 checks fail'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
