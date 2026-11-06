"""Mine a way through when a floor looks closed (the user, run 42: "looks like you may be stuck in the dirt, may need to mine to get a path"; one soil block at 14,15 of Boring Cave B4
held 17 real minutes and a game day and a half of "delve: step limit"). Reads the explored cells, floods from me over open ground, and finds the cheapest run of walls to open ground I
can't reach (the magic map shows plenty); with none known, to the nearest unexplored cell. Then it holds the pickaxe and mines that run, nearest wall first.

usage: python -I tools/tunnel.py [--max N=6] [--dry]    at most N walls; --dry prints the plan
Exit 0 dug (or "nothing to dig": no wall leads anywhere), 1 refused (no pickaxe, a window), 3 stopped (a hostile, a wall too hard, SP).
"""
import heapq
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import cells, grab, pc, ready, refuse, run, setup, state, stop, top, walk_beside  # noqa: E402

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
                # unexplored: remember the nearest as the fallback
                if frontier is None or cost < frontier[0]:
                    frontier = (cost, m, n)
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
    if end is None and frontier is not None and frontier[0] > 0:
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


def main():
    setup()
    args = sys.argv[1:]
    most = int(args[args.index("--max") + 1]) if "--max" in args else 6
    if top():
        refuse(f"{top()} is open")
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
