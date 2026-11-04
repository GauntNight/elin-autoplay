"""World map: a grid of the danger an ambush or a field map would have on each tile around me, to
plan a route before travelling (run 09). A roads-and-shore route matters: each step rolls an
ambush 1 in 12 off-road, 1 in 22 on a road, never on a shore tile (Chara.cs), and the ambush's
foes come from the tile's danger.

Run 19 (the code): an ambush or field map gets max(0, road distance - 4) + min(home distance / 4,
10) (+ road distance past 20), capped at 100 (Player.EnterLocalZone: an ambush at road 3, home 6
was danger 1, as the map showed). The bridge's `terrain` adds 5: that is RegionPoint.dangerLv,
the level of the mobs that wander the world map itself (Region: CreateFromFilter(regionPoint.dangerLv),
the Lv9 bee that trailed me). This grid prints the ambush level (terrain - 5); until run 19 it
printed terrain's number, 5 too high, and routes west of home were refused on it.

usage: python -I tools/dangergrid.py [R=20] [X0 X1 Z0 Z1]   deltas from me; # blocked, R road
  e.g. python -I tools/dangergrid.py 14 -12 1 -1 10          west and north of home
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    r = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    x0, x1, z0, z1 = (int(v) for v in sys.argv[2:6]) if len(sys.argv) > 5 else (-r, r, -r, r)
    cells = {}
    # terrain lists the tiles whose biome or alias contains WANT: a few letters cover every biome.
    for want in ("a", "e", "i", "o", "u", "y", "r", "n", "s", "l"):
        d = call("terrain", r=r, want=want, n=20000)["data"]
        for h in d["hits"]:
            cells[(h["dx"], h["dz"])] = h
    for h in cells.values():
        h["danger"] = max(0, h["danger"] - 5)  # the ambush map's level, not the world-map wanderers'
    here = dict(d["here"], danger=max(0, d["here"]["danger"] - 5))
    print(f"me {d['me']}  here {here}  ({len(cells)} tiles; ambush level: world-map wanderers are +5)")
    print("     " + "".join(f"{dx:>3}" for dx in range(x0, x1 + 1)))
    for dz in range(z1, z0 - 1, -1):
        row = []
        for dx in range(x0, x1 + 1):
            h = cells.get((dx, dz))
            if not h:
                row.append("  ?")
            elif h["blocked"]:
                row.append("  #")
            elif h["isRoad"]:
                row.append(f" R{h['danger']}" if h["danger"] < 10 else f"R{h['danger']}")
            else:
                row.append(f"{h['danger']:>3}")
        print(f"{dz:>4} " + "".join(row))


if __name__ == "__main__":
    main()
