"""Mine a way through when a floor looks closed (the user, run 42: "looks like you may be stuck in the dirt, may need to mine to get a path"; one soil block at 14,15 of Boring Cave B4
held 17 real minutes and a game day and a half of "delve: step limit"). Reads the explored cells, floods from me over open ground, and finds the cheapest run of walls to open ground I
can't reach (the magic map shows plenty); with none known, to the nearest unexplored cell. Then it holds the pickaxe and mines that run, nearest wall first.

usage: python -I tools/tunnel.py [--max N=6] [--dry]    at most N walls; --dry prints the plan
       python -I tools/tunnel.py --to X,Z [--max N=8]   dig the cheapest way to that cell, through unexplored cells too (run 43: Traditional Cave B4's stairs lay
                                                        magic-mapped in a closed room, one soil block and a dark cell from the corridor, and stopped a circuit)
Exit 0 dug (or "nothing to dig": no wall leads anywhere), 1 refused (no pickaxe, a window), 3 stopped (a hostile, a wall too hard, SP).
"""
import heapq
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import cells, grab, pc, ready, refuse, run, setup, state, stop, top, walk, walk_beside  # noqa: E402

NEAR = ((1, 0), (-1, 0), (0, 1), (0, -1))


def read_floor():
    z = state().get("zone") or {}
    b = z.get("bounds")
    if not b:
        refuse("this map has no bounds to read")
    x0, z0, x1, z1 = (int(v) for v in b.split(","))
    pts = [(x, y) for y in range(z0, z1 + 1) for x in range(x0, x1 + 1)]
    return cells(pts), (x0, z0, x1, z1)


def is_open(c):
    return bool(c) and not c.get("blocked") and not c.get("suffocate")


def mineable(c):
    return bool(c) and c.get("block") and str(c.get("blockReq") or "").startswith("mining")


def plan(info, bounds, me):
    x0, z0, x1, z1 = bounds
    seen, todo = {me}, [me]
    while todo:
        x, y = todo.pop()
        for dx, dy in NEAR:
            n = (x + dx, y + dy)
            if n not in seen and is_open(info.get(n)):
                seen.add(n)
                todo.append(n)
    # the open ground I can't reach, by connected piece: a lone cell behind a wall is rarely the way on
    pieces, part = {}, 0
    for n, c in info.items():
        if is_open(c) and n not in seen and n not in pieces:
            part += 1
            pieces[n] = part
            stack = [n]
            while stack:
                a, b_ = stack.pop()
                for dx, dy in NEAR:
                    m = (a + dx, b_ + dy)
                    if m not in pieces and m not in seen and is_open(info.get(m)):
                        pieces[m] = part
                        stack.append(m)
    size = {}
    for p_ in pieces.values():
        size[p_] = size.get(p_, 0) + 1
    # Dijkstra over walls from everything I can reach: a wall costs 1, soft ones a little less; open ground beyond ends it
    best, heap, prev = {}, [], {}
    for n in seen:
        best[n] = 0
        heap.append((0, n))
    heapq.heapify(heap)
    target = None
    frontier = None
    while heap:
        cost, n = heapq.heappop(heap)
        if cost > best.get(n, 1e9):
            continue
        if n in pieces and size[pieces[n]] >= 2:
            target = n
            break
        for dx, dy in NEAR:
            m = (n[0] + dx, n[1] + dy)
            if not (x0 < m[0] < x1 and z0 < m[1] < z1):
                continue
            c = info.get(m)
            if c is None:
                # unexplored: the fallback. Run 43 (Bewitching Cave B2): "the nearest" dug along the map's edge three times with the
                # dark middle of the floor unread: walls count against a cell, the unexplored cells around it for it, and never by the edge
                if x0 + 2 < m[0] < x1 - 2 and z0 + 2 < m[1] < z1 - 2:
                    dark = sum(1 for ax in range(m[0] - 5, m[0] + 6) for ay in range(m[1] - 5, m[1] + 6) if info.get((ax, ay)) is None)
                    score = cost - dark * 0.1
                    if frontier is None or score < frontier[0]:
                        frontier = (score, m, n)
                continue
            if is_open(c):
                step = 0
            elif mineable(c):
                step = 1 + min(int(c.get("blockHard") or 0), 100) / 1000
            else:
                continue
            if cost + step < best.get(m, 1e9):
                best[m] = cost + step
                prev[m] = n
                heapq.heappush(heap, (cost + step, m))
    end = target
    if end is None and frontier is not None and best.get(frontier[2], 0) > 0:
        end = frontier[2]  # the last wall before the dark
    if end is None:
        return [], len(seen), None
    walls, n = [], end
    while n in prev:
        if mineable(info.get(n)):
            walls.append(n)
        n = prev[n]
    walls.reverse()
    return walls, len(seen), (size[pieces[target]] if target else 0)


def reach(info, me):
    seen, todo = {me}, [me]
    while todo:
        x, y = todo.pop()
        for dx, dy in NEAR:
            n = (x + dx, y + dy)
            if n not in seen and is_open(info.get(n)):
                seen.add(n)
                todo.append(n)
    return seen


def path_to(info, bounds, me, goal):
    """The cheapest way from what I can reach to a cell beside `goal`, walls and dark cells at 1 each: [(cell, the cell before it), ...], the cells to open."""
    x0, z0, x1, z1 = bounds
    seen = reach(info, me)
    best = {n: 0 for n in seen}
    heap = [(0, n) for n in seen]
    heapq.heapify(heap)
    prev = {}
    while heap:
        cost, n = heapq.heappop(heap)
        if cost > best.get(n, 1e9):
            continue
        if max(abs(n[0] - goal[0]), abs(n[1] - goal[1])) <= 1:
            out = []
            while n in prev:
                out.append((n, prev[n]))
                n = prev[n]
            return list(reversed(out)), len(seen)
        for dx, dy in NEAR:
            m = (n[0] + dx, n[1] + dy)
            if not (x0 < m[0] < x1 and z0 < m[1] < z1):
                continue
            c = info.get(m)
            step = 1 if c is None else 0 if is_open(c) else 1 + min(int(c.get("blockHard") or 0), 100) / 1000 if mineable(c) else None
            if step is None or cost + step >= best.get(m, 1e9):
                continue
            best[m] = cost + step
            prev[m] = n
            heapq.heappush(heap, (cost + step, m))
    return None, len(seen)


def dig_to(goal, most, dry):
    p = pc()
    info, bounds = read_floor()
    path, reached = path_to(info, bounds, (p["x"], p["z"]), goal)
    if path is None:
        print(f"nothing to dig: {reached} cells in reach and no way to {goal[0]},{goal[1]}")
        return 1
    print(f"{reached} cells in reach; {len(path)} cell(s) to {goal[0]},{goal[1]}: " + " ".join(f"{x},{z}" for (x, z), _ in path))
    if dry:
        return 0
    if len(path) > most:
        print(f"over --max {most}: not digging")
        return 1
    for (x, z), (bx, bz) in path:
        why = ready(hp=60, hunger=None, burden=None)
        if why and "held" not in why:
            stop(f"not mining: {why}")
        w = walk(bx, bz, r=0, weak_ok=True)
        q = pc()
        if (q["x"], q["z"]) != (bx, bz):
            stop(f"the walk to {bx},{bz} ended: {w.get('why')}")
        c = cells([(x, z)]).get((x, z)) or {}
        if is_open(c):
            continue
        if not grab("pickaxe", prefer=None):
            run("hotbar.py", "--deselect", timeout=30)
            refuse("no pickaxe in the pack")
        out = run("harvest.py", str(x - bx), str(z - bz), timeout=120)
        print(f"  {x},{z}: " + (re.sub(r"\s+", " ", str(out))[-90:]))
        if out.rc:
            run("hotbar.py", "--deselect", timeout=30)
            stop(f"harvest.py at {x},{z}: rc {out.rc}")
    run("hotbar.py", "--deselect", timeout=30)
    return 0


def main():
    setup()
    args = sys.argv[1:]
    most = int(args[args.index("--max") + 1]) if "--max" in args else (8 if "--to" in args else 6)
    if top():
        refuse(f"{top()} is open")
    if "--to" in args:
        gx, gz = args[args.index("--to") + 1].split(",")
        return dig_to((int(gx), int(gz)), most, "--dry" in args)
    p = pc()
    info, bounds = read_floor()
    walls, reached, beyond = plan(info, bounds, (p["x"], p["z"]))
    if not walls:
        print(f"nothing to dig: {reached} cells in reach and no wall leads to open ground or the dark")
        return 0
    print(f"{reached} cells in reach; {len(walls)} wall(s) to " + (f"{beyond} open cells beyond: " if beyond else "the unexplored dark: ") + " ".join(f"{x},{z}" for x, z in walls))
    if "--dry" in args:
        return 0
    if len(walls) > most:
        print(f"over --max {most}: mining the first {most}")
        walls = walls[:most]
    for x, z in walls:
        why = ready(hp=60, hunger=None, burden=None)
        if why and "held" not in why:
            stop(f"not mining: {why}")
        w = walk_beside(x, z, weak_ok=True)
        if not w.get("done"):
            stop(f"the walk to {x},{z} ended: {w.get('why')}")
        if not grab("pickaxe", prefer=None):
            run("hotbar.py", "--deselect", timeout=30)
            refuse("no pickaxe in the pack")
        q = pc()
        out = run("harvest.py", str(x - q["x"]), str(z - q["z"]), timeout=120)
        print(f"  {x},{z}: " + (re.sub(r"\s+", " ", str(out))[-90:]))
        if out.rc:
            run("hotbar.py", "--deselect", timeout=30)
            stop(f"harvest.py at {x},{z}: rc {out.rc}")
    run("hotbar.py", "--deselect", timeout=30)
    return 0


if __name__ == "__main__":
    sys.exit(main())
