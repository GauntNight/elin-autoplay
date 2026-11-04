"""Stone paths from every house door to the office and the field (G30 M4, run 31): a breadth-first search over the
home map's walkable cells (no wall, not blocked, no water, never a tilled field cell), from each door's outside step
to the office hub and to the field's edge; the union of those shortest paths is the path network. Lays a floor item
(default "stepping stones": the flooring workshop, 1 stone and 1 SP a cell; stone floor costs 4 SP and
stone road needs a recipe) through place.py, or lists the cells.

usage: python -I tools/paths.py [--dry] [--item "stone roads"] [--mat granite]
  --dry   print the network (cells per door and in all) and stop
Doors and the hub are the ones in tools/home.py's comments (run 31): each entry is (door outside step, name).
Exit 0 laid or listed; 3 a place.py stop.
"""
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import cells, run, stop  # noqa: E402
import home  # noqa: E402

BOUNDS = (40, 36, 70, 62)  # x0, z0, x1, z1 of the town
HUB = (58, 50)             # the office: between the mail post (61,50), the trash can (58,51) and the shipping chest (56,52)
FIELD_EDGE = (55, 46)      # the tilled field's east edge (home.FIELD is 48-54 x 43-49)
DOORS = [((51, 54), "Workshop"), ((60, 54), "Forge"), ((66, 54), "Kitchen"), ((65, 48), "Residence"),
         ((60, 50), "my room"), ((56, 43), "Farmhouse"), ((66, 43), "Storehouse"), ((47, 49), "Depot")]


def walkable(c):
    return c and not c.get("wall") and not c.get("blocked") and not c.get("water") and c.get("floor") != "field"


def bfs(info, start, goal):
    q, prev = deque([start]), {start: None}
    while q:
        cur = q.popleft()
        if cur == goal:
            path = []
            while cur:
                path.append(cur)
                cur = prev[cur]
            return path[::-1]
        x, z = cur
        for nx, nz in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):  # 4-way: a path reads as a path
            if (nx, nz) not in prev and walkable(info.get((nx, nz))) or (nx, nz) == goal and (nx, nz) not in prev:
                prev[(nx, nz)] = cur
                q.append((nx, nz))
    return None


def network():
    x0, z0, x1, z1 = BOUNDS
    info = cells([(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)])
    net, per = set(), {}
    for start, name in DOORS + [(FIELD_EDGE, "the field")]:
        p = bfs(info, start, HUB)
        per[name] = len(p) if p else None
        if p:
            net.update(p)
    return net, per, info


def main():
    net, per, info = network()
    for name, n in per.items():
        print(f"  {name}: {n if n is not None else 'NO PATH'} cells to the office")
    def paved(c):  # run 31: stepping stones (an obj, 1 stone and 1 SP each) pave it as well as a stone floor or road
        return any(w in (c.get("floor") or "") + " " + str(c.get("obj") or "") for w in ("stone", "road"))
    todo = sorted((x, z) for x, z in net if not paved(info[(x, z)]))
    print(f"network: {len(net)} cells, {len(todo)} without a stone road yet")
    if "--dry" in sys.argv or not todo:
        print(" ".join(f"{x},{z}" for x, z in todo))
        return
    item = sys.argv[sys.argv.index("--item") + 1] if "--item" in sys.argv else "stepping stones"
    r = run("place.py", item, *[f"{x},{z}" for x, z in todo], timeout=3600)
    print("\n".join([ln for ln in str(r).splitlines() if "placed" not in ln][-6:]))
    if r.rc != 0:
        stop(f"place.py stopped (rc {r.rc})")


if __name__ == "__main__":
    main()
