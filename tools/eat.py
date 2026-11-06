"""One or more meals by the same path the loops use (farmday.eat_one: the Cooler Box first, MEALS words), from the shell
(run 41: every hand-run stop at Hungry needed a one-line script). You can't eat on the world map: enter a local map first.

usage: python -I tools/eat.py [--until HUNGER=50] [--max N=4]
Exit 0 at or under HUNGER, 1 refused (the world map), 3 stopped (no meal found, a window, a hostile).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data, refuse, setup, stop  # noqa: E402
import farmday  # noqa: E402


def main():
    setup()
    args = sys.argv[1:]
    until = int(args[args.index("--until") + 1]) if "--until" in args else 50
    most = int(args[args.index("--max") + 1]) if "--max" in args else 4
    s = data("state")
    if (s.get("zone") or {}).get("region"):
        refuse("the world map: no eating here, enter a local map first")
    for _ in range(most):
        h = data("state")["pc"]["hunger"]
        if h < until:
            print(f"hunger {h}")
            return
        meal = farmday.eat_one()
        if not meal:
            stop(f"no meal eaten at hunger {h}")
        print(f"  ate: {meal}")
    print(f"hunger {data('state')['pc']['hunger']}")


if __name__ == "__main__":
    main()
