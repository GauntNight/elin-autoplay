"""Solo against crew (the user, run 31: "could be you are still better alone"; run 35: "are groups better than solo
at this point?"): fights.csv rows from my level band, grouped by how many allies were with me, as HP lost per fight (in
% of my max HP) and game turns per fight; then (run 35 on) each nefia and circuit start/end pair in runs/activity.csv,
grouped by the "[party N]" its start mark carries, as real minutes, exp and orens an hour, and minutes a conquest.

usage: python -I tools/crewcheck.py [MIN_LV=26] [--foe-min N] [--run NN]
  --run NN  only fights.csv rows and activity marks from run NN (the A/B blocks of one session)
"""
import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    min_lv = int(args[0]) if args else 26
    foe_min = int(sys.argv[sys.argv.index("--foe-min") + 1]) if "--foe-min" in sys.argv else 0
    only = sys.argv[sys.argv.index("--run") + 1] if "--run" in sys.argv else None
    rows = list(csv.DictReader(open(ROOT / "knowledge" / "fights.csv", encoding="utf-8")))
    groups = {}
    for r in rows:
        try:
            lv, flv, hp, turns, mx = int(r["my_lv"]), int(r["foe_lv"] or 0), int(r["hp_lost"] or 0), int(r["turns"] or 0), int(r["my_maxhp"] or 0)
            allies = int(r.get("allies") or 0)
        except ValueError:
            continue
        if lv < min_lv or flv < foe_min or not mx or (only and r["run"] != only):
            continue
        key = "solo" if allies == 0 else ("1 ally" if allies == 1 else f"{allies} allies")
        groups.setdefault(key, []).append((100 * hp / mx, turns, flv, r["result"], r["run"]))
    print(f"fights at my Lv{min_lv}+ (foes Lv{foe_min}+), by allies present")
    print(f"{'party':<10} {'fights':>6} {'HP lost/fight':>14} {'worst':>6} {'turns/fight':>12} {'foe lv':>7} {'killed':>7}")
    for key in sorted(groups, key=lambda k: (k != "solo", k)):
        g = groups[key]
        hp = [x[0] for x in g]
        print(f"{key:<10} {len(g):>6} {statistics.mean(hp):>13.1f}% {max(hp):>5.0f}% {statistics.mean(x[1] for x in g):>12.1f}"
              f" {statistics.median(x[2] for x in g):>7} {sum(1 for x in g if x[3] == 'killed') / len(g):>6.0%}")
    runs = sorted({x[4] for g in groups.values() for x in g})
    print("runs:", ", ".join(runs))
    activities(only)


def activities(only):
    """The loops' own marks paired start -> end per tag, split by the party size of the start mark."""
    import datetime as dt
    import re
    rows = list(csv.DictReader(open(ROOT / "runs" / "activity.csv", encoding="utf-8")))
    open_ = {}
    out = {}
    for r in rows:
        if r["tag"] not in ("nefia", "circuit"):
            continue
        m = re.search(r"\[party (\d+)\]", r.get("note") or "")
        if r["phase"] == "start":
            open_[r["tag"]] = (r, m)
            continue
        st, sm = open_.pop(r["tag"], (None, None))
        if not st or not sm:
            continue  # marks before run 35 carry no party size
        if only and not (st["logged_at"].startswith(only_date(only)) and st["logged_at"] >= only_start(only)):
            continue
        mins = (dt.datetime.fromisoformat(r["logged_at"]) - dt.datetime.fromisoformat(st["logged_at"])).total_seconds() / 60
        try:
            # the exp bar resets at a level-up: add each passed level's ExpToNext = 50 + 30 x LV (fact #481)
            exp = int(r["exp"]) - int(st["exp"]) + sum(50 + 30 * lv for lv in range(int(st["lv"]), int(r["lv"])))
        except ValueError:
            exp = None
        try:
            gold = int(r["gold"]) - int(st["gold"])
        except ValueError:
            gold = None
        # the ladder's end note counts floors; a conquest shows as the zone name gaining "*Conquered*"
        conq = 1 if r["tag"] == "nefia" and "Conquered" in r["zone"] and "Conquered" not in st["zone"] else 0
        if r["tag"] == "circuit":
            c = re.search(r"(\d+) conquered", r.get("note") or "")
            conq = int(c.group(1)) if c else 0
        key = (r["tag"], "solo" if sm.group(1) == "0" else f"crew {sm.group(1)}")
        o = out.setdefault(key, {"n": 0, "min": 0.0, "exp": 0, "exp_min": 0.0, "gold": 0, "conq": 0})
        o["n"] += 1
        o["min"] += mins
        if exp is not None:
            o["exp"] += exp
            o["exp_min"] += mins
        o["gold"] += gold or 0
        o["conq"] += conq
    if not out:
        print("\nno activity marks with a party size yet (run 35 on)")
        return
    print(f"\n{'activity':<9} {'party':<7} {'marks':>5} {'minutes':>8} {'exp/h':>6} {'orens/h':>8} {'conquests':>9} {'min/conq':>8}")
    for (tag, party), o in sorted(out.items()):
        eh = o["exp"] * 60 / o["exp_min"] if o["exp_min"] else 0
        gh = o["gold"] * 60 / o["min"] if o["min"] else 0
        mc = f"{o['min'] / o['conq']:.0f}" if o["conq"] else "-"
        print(f"{tag:<9} {party:<7} {o['n']:>5} {o['min']:>8.0f} {eh:>6.0f} {gh:>8.0f} {o['conq']:>9} {mc:>8}")
    print("(orens include bills paid inside a pair)")


def only_date(run):
    """The real date a run was played, from runs/metrics.csv or the run logs' names."""
    for f in sorted((ROOT / "runs").glob(f"*-{run}.md")):
        return f.name[:10]
    return "2026-10-31" if run == "35" else "9999"


def only_start(run):
    """The run's real start time, "YYYY-MM-DD HH:MM", from a "Start HH:MM" line near the top of its log; run 37: the
    date alone took run 36's after-midnight marks (a window past midnight) into the next run's A/B."""
    import re
    for f in sorted((ROOT / "runs").glob(f"*-{run}.md")):
        m = re.search(r"\bStart (\d\d:\d\d)", f.read_text(encoding="utf-8")[:2000])
        return f"{f.name[:10]} {m.group(1)}" if m else f.name[:10]
    return ""


if __name__ == "__main__":
    main()
