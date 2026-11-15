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

G56, a town that looks good and works (the user, 2026-11-14; M0, run 48): four checks read from the game, and a map.
A house is a lot (the rooms op); its wall outline is the rooms' bounding box grown by one cell.
       python -I tools/town.py --walls    every outline cell a wall or a door (a gap otherwise), no wall cell just
                                          outside the outline that isn't another house's (a bit sticking out), every
                                          cell inside the box in a room or an inner wall (else the house isn't a
                                          rectangle), one wall material a house and that material wood or rock
                                          (materials.json's category: no grass or straw)
       python -I tools/town.py --storage  no empty container and none off the routes (packcheck's ROUTES and the boxes
                                          the home tools use by name), and every big container (60+ slots, read from
                                          the game, not a name) inside home.STORAGE_QUARTER once the plan sets it
       python -I tools/town.py --inputs   each crafting station in the same house as the box that holds its main
                                          input (STATION_INPUT below)
       python -I tools/town.py --field    the tilled cells one rectangle, every cell within a farm sign's reach
                                          (TraitSpotFarm, radius 2: a 5x5 square), then --garden's planted check
       python -I tools/town.py --map      a text map of the town as it stands (walls by material, doors, boxes,
                                          stations, lights, the field, signs): the plan map starts from it
       python -I tools/town.py --survey   the five G56 checks in a row (walls, storage, inputs, field, lights), one
                                          PASS or FAIL line each at the end. Exit 1 if any fail.
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
BOX_HOUSE = {home.WOOD_BOX: "Workshop", home.STONE_BOX: "Forge", home.STONE_BOX_2: "Workshop",
             home.FARM_BOX: "Farmhouse", home.HARVEST_BOX: "Farmhouse", home.HARVEST_FRIDGE: "Farmhouse", home.FODDER_BOX: "Farmhouse",
             home.PANTRY: "Kitchen", home.PANTRY_2: "Kitchen", home.PANTRY_3: "Kitchen", home.DISH_BOX: "Kitchen",
             home.PARTS_BOX: "Workshop", home.MAPS_BOX: "Workshop", home.SPARES: "Storehouse", home.SPARES2: "Storehouse",
             home.ARMORY: "Residence", home.BOOKSHELF: "Storehouse",  # run 18: the armory arms the residents
             home.COLLECTIBLES: "Storehouse", home.FARM_BOX2: "Farmhouse", home.SPARE_BOX: "Storehouse"}
for xy in home.BAG_PARTS:
    BOX_HOUSE[xy] = "Workshop"
for xy in home.VALUABLES + home.LIBRARY:
    if xy not in home.WAGONS:  # run 42 (G47): the wagons stand in the east yard, like the office
        BOX_HOUSE[xy] = "Storehouse"
BOX_HOUSE[home.OVERFLOW2] = "Workshop"  # run 22: the mystic treasure chest beside it
for xy in (home.ARMORY2, home.SPARES3, (48, 58)):  # run 23: three wooden boxes beside them (Armory 2, Spares 3, Library 2)
    BOX_HOUSE[xy] = "Workshop"
for xy in (home.FARM_BOX, home.SPARES2, home.LIBRARY[1], home.VALUABLES[-1], home.ARMORY3, home.PANTRY_2):
    BOX_HOUSE[xy] = "Depot"  # run 30 (G28): the six sturdy boxes of the new Depot
BOX_HOUSE[home.OVERFLOW3] = "Depot"  # run 31: a mystic treasure chest beside it
for xy in home.OVERFLOW4:
    BOX_HOUSE[xy] = "Depot"  # run 31: two more, installed for G30 M4
# run 42 (G47): the yard's big containers belong to no house; G56 M1 (run 48): the two ★Storage Chests joined them in the quarter
YARD = set(home.WAGONS) | {tuple(home.STORAGE_CHEST), tuple(home.STORAGE_CHEST_2)}
for xy in YARD:
    BOX_HOUSE.pop(xy, None)
OFFICE = {home.MAIL_POST, home.TAX_CHEST, home.SHIPPING, home.TRASH_CAN, home.PRACTICE_CHEST, home.FIAMA_CHEST, home.MAIL_PACKAGE, *home.MAIL_SPOTS, *YARD}
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


# G56 (run 48): the box that holds each station's main input, by home.py's name for it. A station not listed here is
# reported, never guessed. The wall workshop takes planks (or cut stone, if the town goes stone: change it with the plan).
STATION_INPUT = {
    "loom": "BAG_PARTS", "spinner": "BAG_PARTS",
    "sawmill": "WOOD_BOX", "carpenter's table": "WOOD_BOX", "workbench": "WOOD_BOX", "drafting table": "WOOD_BOX",
    "signboard workshop": "WOOD_BOX", "wall workshop": "WOOD_BOX",
    "mason's table": "STONE_BOX_2", "stonecutter": "STONE_BOX_2", "flooring workshop": "STONE_BOX_2",  # G56 M2 (run 48)
    "kiln": "STONE_BOX", "smelter": "STONE_BOX", "blacksmith's table": "STONE_BOX",
    "tinker's table": "PARTS_BOX",
    "bonfire": "PANTRY", "millstone": "HARVEST_BOX", "ration maker": "HARVEST_BOX",
    "cutting board": "PANTRY", "machine table": "PARTS_BOX",  # run 48: the first survey named both as unknown
}


def _rect(x0, z0, x1, z1):
    return [(x, z) for z in range(z0, z1 + 1) for x in range(x0, x1 + 1)]


def _outline(r):
    x0, z0, x1, z1 = r
    return {(x, z) for x, z in _rect(x0, z0, x1, z1) if x in (x0, x1) or z in (z0, z1)}


def houses_of(d):
    """{name: {"lot", "rect" (the wall outline's corners), "rooms", "cells"}} for every lot on the map."""
    lots = {}
    for r in d["rooms"]:
        lots.setdefault(r["lot"], []).append(r)
    out = {}
    for lot, rs in sorted(lots.items()):
        named = sorted({house_of(r["name"]) for r in rs if r["plate"] and house_of(r["name"])})
        name = named[0] if len(named) == 1 else f"lot {lot}" + (f" ({'/'.join(named)})" if named else "")
        # run 48 (the first survey): every house showed "gaps" along its south row and east column. Elin's walls are
        # panels (blockDir), and the cells of a room's east and south walls are room cells themselves, so the outline
        # is the rooms' box plus one column west and one row north: the Workshop's rooms 47-56 x 55-60 make the
        # outline 46-56 x 55-61, as home.py has it.
        rect = (min(r["x"] for r in rs) - 1, min(r["z"] for r in rs), max(r["mx"] for r in rs), max(r["mz"] for r in rs) + 1)
        out[name] = {"lot": lot, "rect": rect, "rooms": rs, "cells": sum(r["cells"] for r in rs)}
    return out


def _materials():
    game = Path(__file__).resolve().parent.parent / "knowledge/game/materials.json"
    return {m["alias"]: m.get("category") for m in json.loads(game.read_text(encoding="utf-8"))}


def walls_check(d):
    from collections import Counter
    from common import cells
    houses = houses_of(d)
    cat = _materials()
    doors = {(t["x"], t["z"]) for t in d["things"] if t["door"]}
    pts = set()
    for h in houses.values():
        x0, z0, x1, z1 = h["rect"]
        pts |= set(_rect(x0 - 1, z0 - 1, x1 + 1, z1 + 1))
    info = cells(sorted(pts))
    every_outline = set().union(*(_outline(h["rect"]) for h in houses.values())) if houses else set()

    def wall(c):
        return bool((info.get(c) or {}).get("wall"))

    fails = 0
    print(f"walls: {len(houses)} houses (outline = the rooms' box + 1)")
    for name, h in houses.items():
        x0, z0, x1, z1 = h["rect"]
        ol = _outline(h["rect"])
        gaps = sorted(c for c in ol if not wall(c) and c not in doors and not (info.get(c) or {}).get("door"))
        ring = _outline((x0 - 1, z0 - 1, x1 + 1, z1 + 1))
        bits = sorted(c for c in ring if wall(c) and c not in every_outline)
        inner = [c for c in _rect(x0 + 1, z0 + 1, x1 - 1, z1 - 1) if wall(c)]
        notch = (x1 - x0) * (z1 - z0) - h["cells"]  # the rooms' own box (the outline less its west column and north row)
        mats = Counter((info[c].get("blockMat") or "?") for c in ol if wall(c))
        bad_mat = [m for m in mats if cat.get(m) not in ("wood", "rock")]
        problems = []
        if gaps:
            problems.append(f"{len(gaps)} gaps " + " ".join(f"{x},{z}" for x, z in gaps[:12]))
        if bits:
            problems.append(f"{len(bits)} bits outside " + " ".join(f"{x},{z}" for x, z in bits[:12]))
        if notch > 0:
            problems.append(f"not a rectangle: {notch} cells in the box are in no room")
        if len(mats) > 1:
            problems.append("mixed materials")
        if bad_mat:
            problems.append("not wood or stone: " + ", ".join(bad_mat))
        mat_txt = ", ".join(f"{m} ({cat.get(m) or '?'}) {n}" for m, n in mats.most_common())
        print(f"  {name}: {x0}-{x1} x {z0}-{z1}, {len(ol)} outline cells, {sum(mats.values())} walls: {mat_txt or 'none'}"
              + (f"; {len(inner)} inner walls" if inner else "")
              + (f"\n     FAIL: " + "; ".join(problems) if problems else "  ok"))
        fails += bool(problems)
    print(f"\n{'PASS' if not fails else f'{fails} of {len(houses)} houses fail the wall check'}")
    return 1 if fails else 0


def _box_cells(where):
    import re
    return {tuple(int(v) for v in c.split(",")) for c in where.split("|") if re.fullmatch(r"\d+,\d+", c)}


def storage_check(d):
    import packcheck  # noqa: E402 (its ROUTES are the routes the sort uses)
    boxes = [b for b in data("stock")["boxes"] if b.get("installed") and not b.get("property")]
    on_route = set().union(*(_box_cells(w) for _, w, _ in packcheck.ROUTES))
    on_route |= {tuple(home.DISH_BOX), tuple(home.HARVEST_FRIDGE), tuple(home.MAPS_BOX)}  # used by dishes.py, Delegated Farming, Poppy
    on_route |= _box_cells(packcheck.ARMORY[0]) | {tuple(home.STORAGE_CHEST_2)}  # gear goes by code (packcheck.ARMORY); rebalance.py
    office = (set(OFFICE) - YARD) | {tuple(home.MAPS_BOX)}  # run 48: G47 made the yard's boxes "office" for check 3
    fails = 0
    # run 48: a locked box counts (the mystic chest 65,40 relocked with 6 stacks in it); Fiama's and the practice chest are office
    mine = [b for b in boxes if (b["x"], b["z"]) not in office and b.get("trait") not in OFFICE_TRAITS]
    empty = [b for b in mine if not b.get("count")]
    print(f"storage: {len(mine)} containers (office and others' left out)")
    print(f"a. empty: {len(empty)}" + "".join(f"\n     {b['name']} ({b['x']},{b['z']}) {b.get('slots')} slots" for b in empty))
    fails += bool(empty)
    off = [b for b in mine if (b["x"], b["z"]) not in on_route]
    print(f"b. off the routes: {len(off)}" + "".join(f"\n     {b['name']} ({b['x']},{b['z']}) {b.get('count')}/{b.get('slots')}" for b in off))
    fails += bool(off)
    big = [b for b in mine if (b.get("slots") or 0) >= 60]
    q = getattr(home, "STORAGE_QUARTER", None)
    if big:
        bx = (min(b["x"] for b in big), min(b["z"] for b in big), max(b["x"] for b in big), max(b["z"] for b in big))
        print(f"c. big containers (60+ slots): {len(big)}, spread over {bx[0]}-{bx[2]} x {bx[1]}-{bx[3]}")
        for b in big:
            print(f"     {b['name']} ({b['x']},{b['z']}) {b.get('count')}/{b.get('slots')}")
    if q is None:
        print("   no storage quarter set yet (home.STORAGE_QUARTER: M0's plan names it)")
        fails += 1
    else:
        (qx0, qz0), (qx1, qz1) = q
        out = [b for b in big if not (qx0 <= b["x"] <= qx1 and qz0 <= b["z"] <= qz1)]
        print(f"   outside the quarter {qx0}-{qx1} x {qz0}-{qz1}: {len(out)}" + "".join(f"\n     {b['name']} ({b['x']},{b['z']})" for b in out))
        fails += bool(out)
    print(f"\n{'PASS' if not fails else f'{fails} of 3 storage checks fail'}")
    return 1 if fails else 0


def inputs_check(d):
    rooms = {r["uid"]: r for r in d["rooms"]}
    lot_at = {(t["x"], t["z"]): (rooms[t["room"]]["lot"] if t["room"] in rooms else None) for t in d["things"]}
    lot_name = {h["lot"]: n for n, h in houses_of(d).items()}
    fails, unknown = 0, []
    stations = [t for t in d["things"] if t["crafter"]]
    print(f"inputs: {len(stations)} stations")
    for t in sorted(stations, key=lambda t: (t["x"], t["z"])):
        key = next((k for k in STATION_INPUT if t["name"].lower().endswith(k)), None)
        if key is None:
            unknown.append(t)
            continue
        cell = getattr(home, STATION_INPUT[key])
        cell = tuple(cell[0] if isinstance(cell, list) else cell)
        here, there = lot_at.get((t["x"], t["z"])), lot_at.get(cell)
        ok = here is not None and here == there
        print(f"  {'ok  ' if ok else 'FAIL'} {t['name']} ({t['x']},{t['z']}) in {lot_name.get(here, 'the open')};"
              f" its input box {STATION_INPUT[key]} {cell[0]},{cell[1]} in {lot_name.get(there, 'the open')}")
        fails += not ok
    if unknown:
        print("  no main input known (STATION_INPUT): " + ", ".join(f"{t['name']} ({t['x']},{t['z']})" for t in unknown))
    print(f"\n{'PASS' if not fails else f'{fails} stations away from their input'}")
    return 1 if fails else 0


def field_check(d):
    from common import cells
    signs = [(t["x"], t["z"]) for t in d["things"] if t["trait"] == "TraitSpotFarm"]
    fx = [c[0] for c in home.FIELD]
    fz = [c[1] for c in home.FIELD]
    area = _rect(min(fx) - 8, min(fz) - 8, max(fx) + 8, max(fz) + 8)
    info = cells(area)
    tilled = sorted(c for c, i in info.items() if (i.get("floor") or "") == "field")
    reach = {(x, z) for sx, sz in signs for x in range(sx - 2, sx + 3) for z in range(sz - 2, sz + 3)}
    fails = 0
    if not tilled:
        print("field: no tilled cell near home.FIELD")
        return 1
    x0, z0 = min(c[0] for c in tilled), min(c[1] for c in tilled)
    x1, z1 = max(c[0] for c in tilled), max(c[1] for c in tilled)
    box = (x1 - x0 + 1) * (z1 - z0 + 1)
    print(f"field: {len(tilled)} tilled cells in the box {x0}-{x1} x {z0}-{z1} ({box} cells); farm signs at "
          + (", ".join(f"{x},{z}" for x, z in signs) or "none"))
    holes = sorted(set(_rect(x0, z0, x1, z1)) - set(tilled) - set(signs))  # a sign inside the field stands on its own cell
    print(f"a. one rectangle: {'yes' if not holes else 'no, ' + str(len(holes)) + ' untilled cells inside the box'}")
    fails += bool(holes)
    outside = [c for c in tilled if c not in reach]
    print(f"b. inside a sign's reach (5x5): {len(tilled) - len(outside)} of {len(tilled)}"
          + (" ; outside: " + " ".join(f"{x},{z}" for x, z in outside[:20]) if outside else ""))
    fails += bool(outside)
    print("c. planted (--garden a):")
    g = garden_check(d)
    fails += bool(g)
    print(f"\n{'PASS' if not fails else 'the field check fails'}")
    return 1 if fails else 0


def map_view(d, rect=None):
    """A text map: north (higher z) at the top, x rising to the right."""
    from common import cells
    houses = houses_of(d)
    if rect is None:
        xs = [h["rect"][0] for h in houses.values()] + [h["rect"][2] for h in houses.values()] + [c[0] for c in home.FIELD]
        zs = [h["rect"][1] for h in houses.values()] + [h["rect"][3] for h in houses.values()] + [c[1] for c in home.FIELD]
        xs += [w[0] for w in home.WAGONS]
        zs += [w[1] for w in home.WAGONS]
        rect = (min(xs) - 2, min(zs) - 2, max(xs) + 2, max(zs) + 2)
    x0, z0, x1, z1 = rect
    info = cells(_rect(x0, z0, x1, z1))
    cat = _materials()
    game = json.loads((Path(__file__).resolve().parent.parent / "knowledge/game/things.json").read_text(encoding="utf-8"))
    light_ids = {r["id"] for r in game if r.get("category") == "light"}
    big = {(b["x"], b["z"]): b.get("slots") or 0 for b in data("stock")["boxes"]}
    over = {}
    for t in d["things"]:
        c = (t["x"], t["z"])
        if t["door"]:
            over[c] = "+"
        elif t["crafter"]:
            over[c] = "S"
        elif t["container"] and not t["bed"]:
            over.setdefault(c, "W" if big.get(c, 0) >= 60 else "c")
        elif t["bed"]:
            over.setdefault(c, "B")
        elif t["trait"] == "TraitSpotFarm":
            over[c] = "F"
        elif t["id"] in light_ids:
            over.setdefault(c, "L")
    print(f"map {x0}-{x1} x {z0}-{z1}: # wood wall, % stone wall, g grass or straw wall, ? other wall, + door,"
          " S station, W big box (60+), c box, B bed, L light, F farm sign, f tilled, ~ water, . floor")
    print("     " + "".join(str(x % 10) for x in range(x0, x1 + 1)))
    for z in range(z1, z0 - 1, -1):
        row = []
        for x in range(x0, x1 + 1):
            i = info.get((x, z)) or {}
            ch = " "
            if i.get("wall"):
                m = cat.get(i.get("blockMat"))
                ch = "#" if m == "wood" else "%" if m == "rock" else "g" if m == "grass" else "?"
            elif i.get("water"):
                ch = "~"
            elif (i.get("floor") or "") == "field":
                ch = "f"
            elif i.get("floor"):
                ch = "."
            ch = over.get((x, z), ch)
            row.append(ch)
        print(f"{z:4d} " + "".join(row))
    for name, h in houses.items():
        x0_, z0_, x1_, z1_ = h["rect"]
        print(f"  {name}: {x0_}-{x1_} x {z0_}-{z1_}")
    return 0


def main(argv):
    setup()
    d = data("rooms")
    if "--garden" in argv:
        return garden_check(d)
    if "--walls" in argv:
        return walls_check(d)
    if "--storage" in argv:
        return storage_check(d)
    if "--inputs" in argv:
        return inputs_check(d)
    if "--field" in argv:
        return field_check(d)
    if "--map" in argv:
        return map_view(d)
    if "--survey" in argv:
        results = {}
        for name, fn in (("walls", walls_check), ("storage", storage_check), ("stations", inputs_check),
                         ("field", field_check), ("lights", lights_check)):
            print(f"\n===== {name} =====")
            results[name] = fn(d)
        print("\n===== G56 survey =====")
        for name, rc in results.items():
            print(f"  {name}: {'PASS' if rc == 0 else 'FAIL'}")
        return 1 if any(results.values()) else 0
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
