"""The run score (the user, 2026-10-26: "a rating system to create a score ... This may help make
decisions"; tracked from run 26 on). Every outcome of a run is worth points; a run's rating is its
points per real hour, with points per game day beside it.

The user's order: a goal finished is worth the most; then gold, exp and nefias per hour played and per
game time; one death outweighs a few goals. Settled with the user the same day:
  - no points for a level: its exp already counts it (a level costs 50 + 30 x level exp, so a late
    level is worth more points than an early one, as it is harder to get);
  - gold is counted in days of rent: orens / (the month's tax bill / 30) x RENT_DAY. The bill is set by
    the game (500 + 500 a game year + a fame part, fact #368) and has grown about as fast as gold got
    easy, so late gold counts for less; never deflate by our own rates, which would cancel the
    improvement the score is there to show;
  - a game day costs RENT_DAY (one day of rent), so gold and game time share a unit;
  - gold is the run's gross income (stats.py's `income`: jobs, chests, shipping, Treasure Hunt, salaries,
    sales), so spending costs no points: shop investments, purchases, fees (the user, 2026-11-01:
    "spending money on boosting shops should no longer count against us"); bills are priced by the
    game days instead;
  - a near death costs nothing: survival is binary ("if you manage a strategy that you survive with
    1 HP left I'm not scoring it down").

Sources: runs/stats.csv (stats.py writes the points columns with parts() below; `bill` is the monthly
bill in force over the run's game days, from runs/bills.csv) and runs/activity_rates.csv.

usage: python -I tools/score.py [N]          the last N runs (default 10): points by component and rates
       python -I tools/score.py --activities the marked loops (activity_rates.csv) by points an hour
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"

SCORE = {
    "goal": 300,       # a goal finished (goals.md marks it done): the biggest single event
    "goal_step": 25,   # a goal milestone reached
    "nefia": 60,       # a nefia conquered, on top of its loot and exp
    "exp": 1,          # an exp point (a level at Lv25 is 800)
    "rent_day": 13,    # a day of rent: what a game day costs and what gold is counted in
    "death": -1000,    # more than three goals
}


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def parts(r):
    """A stats row -> its points by component. Gold is None when the income or the bill is unknown."""
    def n(k):
        return num(r.get(k)) or 0
    bill, income = num(r.get("bill")), num(r.get("income"))
    return {
        "goals": SCORE["goal"] * n("goals_done") + SCORE["goal_step"] * n("goal_steps"),
        "nefias": SCORE["nefia"] * n("nefias"),
        "exp": SCORE["exp"] * n("exp_gained"),
        "gold": income / (bill / 30) * SCORE["rent_day"] if income is not None and bill else None,
        "days": -SCORE["rent_day"] * n("game_days"),
        "deaths": SCORE["death"] * n("deaths"),
    }


def total(p):
    return sum(v for v in p.values() if v is not None)


def rows(name):
    with (RUNS / name).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def show_runs(last):
    runs = [r for r in rows("stats.csv") if r["kind"] == "run" and num(r["minutes"])][-last:]
    hdr = (f"{'run':>4} {'hrs':>5} {'days':>4} {'rent/d':>6} | {'goals':>6} {'nefias':>6} {'exp':>6} {'gold':>6} "
           f"{'days':>6} {'deaths':>6} | {'points':>6} {'/hour':>6} {'/day':>6}")
    print(hdr)
    print("-" * len(hdr))
    for r in runs:
        p = parts(r)
        rent = f"{num(r['bill']) / 30:.0f}" if num(r.get("bill")) else "?"
        gold = "?" if p["gold"] is None else f"{p['gold']:.0f}"
        print(f"{r['point']:>4} {num(r['minutes']) / 60:5.1f} {num(r['game_days']) or 0:4.0f} {rent:>6} | "
              f"{p['goals']:6.0f} {p['nefias']:6.0f} {p['exp']:6.0f} {gold:>6} {p['days']:6.0f} {p['deaths']:6.0f} | "
              f"{r['points']:>6} {r['points_per_hour']:>6} {r['points_per_game_day']:>6}"
              + ("  (gold unknown: counted as 0)" if p["gold"] is None else ""))
    print("\npoints: " + ", ".join(f"{k} {v:g}" for k, v in SCORE.items())
          + "; gold = orens / (bill / 30) x rent_day; a game day = -rent_day")


def show_activities():
    bill = {r["point"]: num(r.get("bill")) for r in rows("stats.csv")}
    print(f"{'run':>4} {'tag':<7} {'min':>4} {'days/h':>6} | {'exp/h':>6} {'gold/h':>6} {'days/h':>7} | {'pts/h':>6}")
    for a in rows("activity_rates.csv"):
        hrs = (num(a["minutes"]) or 0) / 60
        if not hrs or not bill.get(a["run"]):
            continue
        exp = num(a["exp_gained"]) * SCORE["exp"] / hrs
        gold = num(a["gold_delta"]) / (bill[a["run"]] / 30) * SCORE["rent_day"] / hrs
        days = -num(a["game_days"]) * SCORE["rent_day"] / hrs
        print(f"{a['run']:>4} {a['tag']:<7} {num(a['minutes']):4.0f} {num(a['game_days']) / hrs:6.1f} | "
              f"{exp:6.0f} {gold:6.0f} {days:7.0f} | {exp + gold + days:6.0f}")
    print("\ngold here is the carried-gold change: a bill paid inside a loop counts against it (and its days too)")


def main():
    if not (RUNS / "metrics.csv").exists():  # logs are gitignored: a fresh clone has none
        print("no records yet on this PC: a new player starts with the elin-setup skill (tools/newgame.py --yes)")
        return
    if "--activities" in sys.argv:
        show_activities()
        return
    show_runs(int(sys.argv[1]) if len(sys.argv) > 1 else 10)


if __name__ == "__main__":
    main()
