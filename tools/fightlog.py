"""The fight log (the user, run 29: "per monster in the graph is perfect", with a column for specials such as
"destroys equipment with fire", "weakens stats (slime)", "invisible", "runs away").

Every fight fight.py runs appends a row to knowledge/fights.csv: the foe's kind (the game's chara name, so threat.py
and power.py key it the same way), its id and level, how many hostiles were in view, my allies present, the game
turns it took, the HP I lost (start minus the lowest point), the result, and **special**: the tricks the game's log
showed during the fight (SPECIALS below: fire, acid on gear, drains, poison, paralysis, blindness, theft, teleports,
an unseen attacker, a foe that kept away...). Until run 29 rows were written by hand with `power.py fight` (132 rows
in 29 runs, mostly the memorable ones); the new columns go at the end, so old rows and old readers still line up.

The tags come from log lines seen while fighting one target, so in a crowd a tag may belong to another foe: the
summary counts each tag in solo fights and in group fights apart.

usage: python -I tools/fightlog.py [KIND]     the per-kind summary (all kinds, or one)
"""
import csv
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIGHTS = ROOT / "knowledge" / "fights.csv"
HEADER = ["run", "game_date", "my_lv", "my_pv", "my_maxhp", "foe", "foe_lv", "n_foes", "turns", "hp_lost", "result",
          "note", "foe_id", "allies", "special", "source"]

# (tag, pattern on a log line). Elin's own wording, as seen in runs 03-29; a tag only says the trick happened.
SPECIALS = [
    ("burns (fire: can burn gear and scrolls)", r"\bis burnt\b|\bburns? up\b|\bburnt to\b|catches fire|\bin flames\b"),
    ("acid (corrodes gear)", r"exposed to acid|\brusts\b|\bcorrode"),
    ("cold (can shatter potions)", r"\bis chilled\b|\bfrozen\b|\bshatters?\b"),
    ("drains stats", r"\b(weaken|drain|sap)s?\b|\bis weakened\b|\bfeels? weak"),
    ("poisons", r"\bpoison"),
    ("paralyses", r"\bparaly"),
    ("blinds", r"\bblind"),
    ("confuses", r"\bconfus"),
    ("puts to sleep", r"falls? asleep|\bsleepy\b"),
    ("terrifies", r"\bterror\b|\bafraid\b|\bfear\b"),
    ("steals", r"\bsteals?\b|\bstole\b|\bpickpocket"),
    ("teleports", r"teleport|disappears suddenly"),
    ("unseen attacker (invisible or dark)", r"^Something \w+ (you|kaberg)\b"),
    ("floats away from melee", r"\*float\*"),
    ("explodes", r"\bexplode"),
    ("summons", r"\bsummon"),
    ("breath attack", r"\bbreath\b"),
    ("casts spells", r"\bcasts?\b"),
]


# My own actions ("You cast magic arrow", "You read a scroll of teleport") are never the foe's trick
MINE = re.compile(r"^You (slash|smash|miss|miserably|throw|cast|evade|push|pick|displace|open|shoot|kick|punch|stab|"
                  r"hit|zap|read|drink|dump|drop|begin|have|gain|learn|feel good|protect|capture|leave|enter|wake)", re.I)


def tags_from_log(lines, allies=()):
    """The SPECIALS tags whose pattern appears in these log lines, in table order. Lines of my own actions and
    lines that start with an ally's name (their casts and swings) don't count."""
    # an ally's own action ("Kaberg the little girl casts ...", "A stalker slashes ...") is dropped; what happens
    # to an ally ("Kaberg the little girl is exposed to acid", "...'s hemp gloves rusts", "A stalker is chilled")
    # is the foe's trick and counts
    act = re.compile(r"^(?:\S+(?: the [\w ]+?)?) (casts?|slash|smash|miss|evade|kick|punch|shoot|throw|bite|stab|"
                     r"hit|claw|touch|attack|reads?|drinks?)\w*\b", re.I)
    keep = [ln for ln in lines if not MINE.match(ln)
            and not (any(ln.lower().startswith(a.lower()) for a in allies if a) and act.match(ln))]
    found = []
    for tag, pat in SPECIALS:
        if any(re.search(pat, ln, re.I) for ln in keep):
            found.append(tag)
    return found


def _ensure_header():
    """Create the file, or extend an old 12-column header with the new columns (old rows keep their values)."""
    if not FIGHTS.exists():
        with FIGHTS.open("w", encoding="utf-8", newline="") as fh:
            csv.writer(fh, lineterminator="\n").writerow(HEADER)
        return
    text = FIGHTS.read_text(encoding="utf-8")
    first, _, rest = text.partition("\n")
    if first.strip() != ",".join(HEADER):
        FIGHTS.write_text(",".join(HEADER) + "\n" + rest, encoding="utf-8")


def record(row):
    """Append one fight (a dict keyed by HEADER names; missing keys stay blank)."""
    _ensure_header()
    with FIGHTS.open("a", encoding="utf-8", newline="") as fh:
        csv.writer(fh, lineterminator="\n").writerow([row.get(k, "") for k in HEADER])


def rows():
    if not FIGHTS.exists():
        return []
    return list(csv.DictReader(FIGHTS.open(encoding="utf-8")))


def _int(v, default=None):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def summary():
    """{kind (lower case): {fights, solo, typical_pct, worst_pct, last_run, levels, specials: {tag: (solo, group)},
    results: Counter}} from every row; % is HP lost against my max HP at the time."""
    out = defaultdict(lambda: {"fights": 0, "solo": 0, "pcts": [], "worst_pct": 0, "last_run": "", "levels": set(),
                               "specials": defaultdict(lambda: [0, 0]), "results": Counter()})
    for r in rows():
        k = (r.get("foe") or "").strip().lower()
        if not k:
            continue
        s = out[k]
        s["fights"] += 1
        nf = _int(r.get("n_foes"), 1) or 1
        solo = nf <= 1
        s["solo"] += solo
        lost, mx = _int(r.get("hp_lost")), _int(r.get("my_maxhp"))
        if lost is not None and mx:
            pct = round(100 * lost / mx)
            s["pcts"].append(pct)
            s["worst_pct"] = max(s["worst_pct"], pct)
        s["last_run"] = max(s["last_run"], (r.get("run") or "").zfill(2))
        lv = _int(r.get("foe_lv"))
        if lv is not None:
            s["levels"].add(lv)
        for tag in filter(None, (r.get("special") or "").split(";")):
            s["specials"][tag.strip()][0 if solo else 1] += 1
        s["results"][(r.get("result") or "?").strip()] += 1
    # the tricks already documented in run logs and facts before fights were logged (knowledge/specials.csv:
    # kind, special, run, source), counted as notes so a summary shows them before the next fight
    notes = ROOT / "knowledge" / "specials.csv"
    if notes.exists():
        for r in csv.DictReader(notes.open(encoding="utf-8")):
            k = (r.get("kind") or "").strip().lower()
            if k:
                out[k]["specials"][(r.get("special") or "").strip()]
                out[k].setdefault("noted", set()).add((r.get("special") or "").strip())
    for s in out.values():
        s["typical_pct"] = round(statistics.median(s["pcts"])) if s["pcts"] else None
    return dict(out)


def line(kind, s=None):
    """One plain line for a kind (kb.py show and the semantic index)."""
    s = s or summary().get(kind.strip().lower())
    if not s:
        return ""
    lv = sorted(s["levels"])
    lvs = (f"Lv{lv[0]}" if len(lv) == 1 else f"Lv{lv[0]}-{lv[-1]}") if lv else "Lv?"
    hp = (f"HP lost typically {s['typical_pct']}% of my max, worst {s['worst_pct']}%" if s["typical_pct"] is not None
          else "HP lost not recorded")
    noted = s.get("noted", set())

    def how(t, a, b):
        seen = (f"{a} solo, {b} in a group" if b else f"{a} solo") if a + b else ""
        return f"{t} ({', '.join(x for x in (seen, 'noted in run logs' if t in noted else '') if x)})"
    sp = "; ".join(how(t, a, b) for t, (a, b) in sorted(s["specials"].items(), key=lambda x: -(x[1][0] + x[1][1])))
    res = ", ".join(f"{k} {v}" for k, v in s["results"].most_common())
    if not s["fights"]:
        return f"{kind}: no fights recorded" + (f". Seen to: {sp}" if sp else "")
    return (f"{kind}: {s['fights']} fights recorded ({s['solo']} solo), {lvs}, {hp}; results: {res}; last run "
            f"{s['last_run']}" + (f". Seen to: {sp}" if sp else ""))


KILLED = re.compile(r"\bkills?\b|\bdestroys?\b|\bminces?\b|pieces of meat|\bdies\b|\bis dead\b|\bkilled\b", re.I)


def current_run():
    """The run number from the newest run log (runs/YYYY-MM-DD-NN.md), as fight.py doesn't know it."""
    logs = sorted(p.stem for p in (ROOT / "runs").glob("????-??-??-??.md"))
    return logs[-1][-2:] if logs else ""


class Tracker:
    """fight.py's bookkeeping: feed it every state snapshot (see), call engage(target, state) before each attack,
    and finish(result) once at the end; it writes one row per target attacked."""

    def __init__(self, pv=None, source="fight.py"):
        self.pv, self.source = pv, source
        self.lines, self.min_hp, self.max_foes = set(), None, 0
        self.allies, self.ally_names = 0, set()
        self.targets, self.last, self.base = {}, None, None

    def see(self, s):
        # the log ring's lines from before the fight are not this fight's
        if self.base is None:
            self.base = set(s.get("log") or [])
        self.last = s
        pc = s.get("pc") or {}
        if pc.get("hp") is not None:
            self.min_hp = pc["hp"] if self.min_hp is None else min(self.min_hp, pc["hp"])
        self.max_foes = max(self.max_foes, sum(1 for c in s.get("nearby") or [] if c.get("hostile")))
        here = [p for p in s.get("party") or [] if p.get("here")]
        self.allies = max(self.allies, len(here))
        self.ally_names.update(p.get("name", "") for p in here)
        self.lines.update(ln for ln in s.get("log") or [] if ln not in self.base)

    def engage(self, t, s):
        if t["uid"] in self.targets:
            return
        pc = s["pc"]
        kind = re.sub(r"^(an?|the) ", "", t["name"])
        try:
            import threat
            row = threat.find(t.get("id") or t["name"])
            if row and row.get("name") and not str(row["name"]).startswith("*"):
                kind = str(row["name"])
        except Exception:  # noqa: BLE001 (a log row is never worth a crash)
            pass
        pv = ""
        if self.pv:
            try:
                pv = self.pv()
            except Exception:  # noqa: BLE001
                pv = ""
        self.targets[t["uid"]] = {"kind": kind, "id": t.get("id", ""), "lv": t.get("lv", ""), "hp0": pc["hp"],
                                  "maxhp": pc["maxHp"], "lvme": pc.get("lv", ""), "turn0": pc.get("turn"),
                                  "date": str(pc.get("date", "")).split(" ")[0], "pv": pv, "flags": []}
        self.min_hp = pc["hp"] if self.min_hp is None else min(self.min_hp, pc["hp"])

    def flag(self, uid, tag):
        if uid in self.targets and tag not in self.targets[uid]["flags"]:
            self.targets[uid]["flags"].append(tag)

    def finish(self, result=None, note=""):
        if not self.targets:
            return
        s = self.last or {}
        pc = s.get("pc") or {}
        alive = {c["uid"] for c in s.get("nearby") or []}
        lines = sorted(self.lines)
        tags = tags_from_log(lines, sorted(self.ally_names))
        run = current_run()
        for uid, t in self.targets.items():
            res = result or ("killed" if uid not in alive and any(KILLED.search(ln) for ln in lines)
                             else "lost from view" if uid not in alive else "alive")
            turns = (pc.get("turn") - t["turn0"]) if pc.get("turn") is not None and t["turn0"] is not None else ""
            record({"run": run, "game_date": t["date"], "my_lv": t["lvme"], "my_pv": t["pv"], "my_maxhp": t["maxhp"],
                    "foe": t["kind"], "foe_lv": t["lv"], "n_foes": max(1, self.max_foes), "turns": turns,
                    "hp_lost": max(0, t["hp0"] - (self.min_hp if self.min_hp is not None else t["hp0"])),
                    "result": res, "note": note, "foe_id": t["id"], "allies": self.allies,
                    "special": ";".join(t["flags"] + [g for g in tags if g not in t["flags"]]), "source": self.source})


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    summ = summary()
    if a:
        print(line(" ".join(a), summ.get(" ".join(a).lower())) or f"no fights recorded with {' '.join(a)!r}")
        return
    for k, s in sorted(summ.items(), key=lambda x: -x[1]["fights"]):
        print(line(k, s))


if __name__ == "__main__":
    main()
