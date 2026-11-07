"""Steal NPC property with Sleight of Hand for the Thieves Guild (G27, run 30).

Only Sleight of Hand makes a thing stolen: a plain Grab of NPC property costs Karma -1 and clears the
property flag but never sets isStolen (Chara.HoldCard), and goods bought in the guild's own shops lose
the flag at the counter (ShopTransaction.OnEndTransaction). AI_Steal takes an NPC-property thing that
is unlocked and CanBeStolen, weighing at most Pickpocket x 200 + STR x 100 + 1000 (AI_Steal.IsValidTC,
Run): 20 turns beside it, 4 checks. At each check every witness within 4 with line of sight (humans,
fairies, gods, mutants; not blind, confused, paralysed or my party) rolls rnd(PER x 2.5, doubled for a
unique) against my Pickpocket + DEX (+30 when it can't see me); one hit cancels the theft and turns the
witness hostile (no guard in Derphy). Success: Karma -1, the thing isStolen, Pickpocket exp. Selling a
stolen unit to a black market pays the guild (int)sqrt(unit price) / 2 (ShopTransaction); below rank 4
only Derphy town, Port Kapul and my own land buy them (Siyun in Derphy, ~95,81).

usage: python -I tools/steal.py [R=20] [--all]     the marks in reach, best contribution first (liftable,
                                                   contribution 2+; --all lists everything)
       python -I tools/steal.py take UID [UID ...] [--max-lv 14] [--skip]
       python -I tools/steal.py auto TARGET [R=60] --bold    in Derphy only: the marks best first until their contribution adds up to TARGET (run 43, G32:
                                                   at DEX 61 a plain townsperson needs PER over 30 to notice at all, so the old levels and the sneak guard refused nearly every mark;
                                                   Derphy has no guards: a witness who does notice only turns hostile)
  take: walks beside each thing, refuses while an awake possible witness of level >= --max-lv stands
  within 4 (their PER is unknown to the bridge; a level stands in for it), casts Sleight of Hand on it
  through the bridge (0.34.0 `cast spell=AI_Steal uid=N` takes things), waits the task out and reports
  the log. Exit 0 done, 1 refused, 2 bridge, 3 stopped (a witness, the theft cancelled, a hostile).
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, data, ready, refuse, setup, stop, wait_idle, walk_beside  # noqa: E402

SKIP = False  # --skip: pass over a watched mark instead of stopping the batch
TAKEN = 0     # thefts this run (the activity mark, run 33)
STEEL_WORDS = ("alarm clock", "wall lamp", "pendant light", "monitor", "computer", "electronics", "training machine",
               "street lamp")  # steel by default (things.json defMat; fact #726): check the material once taken
UNIQUE_LV = 15  # a named NPC: PER x 2.5 x 2 against Pickpocket + DEX; 6 until the 2026-10-30 review (the user agreed: 60% of marks
                # were skipped, and the bridge sneak guard now cancels a theft the moment a witness comes within 5): run 34 tests 15


def props(r):
    return data("props", r=r)


def show(r, every, steel=False):
    d = props(r)
    rows = [p for p in d["props"] if every or (p["liftable"] and p["contribution"] >= 2)]
    if steel:  # run 32 (the user: "Can you steal steel in places?"): G18's hammer breaks these into a steel ingot
        rows = [p for p in d["props"] if p["liftable"] and any(w in p["name"] for w in STEEL_WORDS)]
    rows.sort(key=lambda p: (-p["contribution"], p["dist"]))
    print(f"steal limit {d['limit']} weight; Thieves rank {d['rank']} (member {d['member']}); "
          f"{len(rows)} marks within {r}")
    for p in (rows if steel else rows[:25]):
        print(f"  uid {p['uid']:>7}  {p['name'][:40]:<40} @{p['x']},{p['z']} d{p['dist']:<3} wt {p['weight']:>6}"
              f"  sell {p['sell']:>5} -> stolen {p['stolenSell']:>5}  +{p['contribution']}"
              + ("" if p["liftable"] else "  (too heavy)"))


def creatures():
    return {c["uid"]: c for c in data("state").get("creatures") or [] if c.get("uid")}


def witnesses(max_lv):
    """Awake possible witnesses within 4 who could notice (the witness op flags them; state.nearby gives
    levels, matched by position). Run 30: Vesyun the mayor (Lv8) saw the first try: a unique's PER counts
    double, so a named NPC (no article) blocks from UNIQUE_LV, anyone else from max_lv. A sleeper can't
    see me (+30 on my side) and is skipped."""
    w = data("witness", r=4)
    by_pos = {(c["dx"], c["dz"]): c for c in data("state").get("nearby") or []}
    bad = []
    for c in w.get("creatures") or []:
        if not c.get("witness") or c.get("sleeping"):
            continue
        n = by_pos.get((c["dx"], c["dz"])) or {}
        lv = n.get("lv") or 99  # unknown: assume the worst
        named = not re.match(r"^(an? |the )", (n.get("name") or c["name"]).lower())
        if lv >= (UNIQUE_LV if named else max_lv) or n.get("hostile"):
            bad.append(f"{c['name']} Lv{lv}{' (named)' if named else ''} d{c['dist']}")
    return bad


def log_tail(n=6):
    return [l for l in (data("state").get("log") or [])][-n:]


def take(uid, max_lv):
    d = props(99)  # run 30: 30 lost marks across Port Kapul once I'd walked off
    hit = [p for p in d["props"] if p["uid"] == uid]
    if not hit:
        if SKIP:
            print(f"uid {uid}: skipped, gone (taken, moved, or out of sight)")
            return 0
        return refuse(f"uid {uid}: no stealable NPC property by that id on a seen cell within 99")
    p = hit[0]
    if not p["liftable"]:
        return refuse(f"{p['name']} weighs {p['weight']}, over the steal limit {d['limit']}")
    why = ready()
    if why:
        stop(f"not now: {why}")
    walk_beside(p["x"], p["z"], r=0, timeout=60000)
    wait_idle(timeout=5000)  # the walk's AI_Goto is still ending: the cast refuses "busy"
    me = data("state")["pc"]
    if max(abs(me["x"] - p["x"]), abs(me["z"] - p["z"])) > 1:
        if SKIP:  # run 30: a mooring rope on Kapul's pier had no free cell beside it (water)
            print(f"{p['name']}: skipped, no free cell beside {p['x']},{p['z']} (at {me['x']},{me['z']})")
            return 0
        stop(f"couldn't stand beside {p['name']} at {p['x']},{p['z']} (at {me['x']},{me['z']})")
    bad = witnesses(max_lv)
    if bad:
        if SKIP:
            print(f"{p['name']}: skipped, a witness who could notice: {', '.join(bad)}")
            return 0
        stop(f"a witness who could notice: {', '.join(bad)}")
    r = call("cast", spell="AI_Steal", uid=uid)
    if not r.get("ok"):
        stop(f"cast refused: {r.get('error')}")
    for _ in range(90):  # 20 turns of the task
        time.sleep(0.7)
        ai = str(data("state")["pc"].get("ai"))
        if "Steal" not in ai:
            break
    lines = log_tail(8)
    print(f"{p['name']} (+{p['contribution']} if sold): " + " / ".join(lines[-4:]))
    got = [i for i in call("inv")["data"]["items"] if p["name"].split(" ", 1)[-1] in i["name"]]
    if any("you steal" in l.lower() for l in lines):
        global TAKEN
        TAKEN += 1
        # run 33: fence.py sells what this file lists (the pack's stolen flag isn't readable from the bridge)
        with (Path(__file__).resolve().parent.parent / "runs" / "stolen.txt").open("a", encoding="utf-8") as fh:
            fh.write((got[0]["name"] if got else p["name"]) + "\n")
    if not any("steal" in l.lower() and p["name"].split(" ", 1)[-1] in l for l in lines) and not got:
        sn = call("sneak").get("data") or {}
        if SKIP and sn.get("lastStop"):  # run 33: the sneak guard cancelled it (a possible witness came close): next mark
            print(f"{p['name']}: cancelled by the sneak guard ({sn['lastStop']})")
            call("sneak", r=5)  # resets lastStop
            return 0
        if SKIP:  # run 43: a bookshelf's contents came out instead of the shelf: a log with no line for the mark isn't a reason to end the batch
            print(f"{p['name']}: no theft in the log; next mark")
            return 0
        stop(f"no theft in the log for {p['name']}: check witnesses (cancelled?)")
    return 0


def auto(target, r):
    """Run 43: best contribution first, nearest among equals, until the sum reaches target. A named witness blocks from Lv15 as always (a unique's PER counts double: Monazess Lv26 caught
    the first theft beside her and turned hostile), anyone else from Lv45."""
    global SKIP
    SKIP = True
    z = (data("state").get("zone") or {}).get("full") or ""
    if "derphy" not in z:
        refuse("--bold only in Derphy: no guards there; anywhere else a witness calls one (run 33: Olno, Lv40)")
    call("sneak", r=0)
    from activity import mark
    mark("thief", "start", note=f"auto {target}")
    got, tried = 0, set()
    try:
        while got < target:
            before = TAKEN
            ps = [p for p in props(r)["props"] if p.get("liftable") and p.get("contribution", 0) >= 2 and p["uid"] not in tried]
            if not ps:
                print("no marks left in reach")
                break
            me = data("state")["pc"]
            p = max(ps, key=lambda q: (q["contribution"], -max(abs(q["x"] - me["x"]), abs(q["z"] - me["z"]))))
            tried.add(p["uid"])
            take(p["uid"], 45)
            if TAKEN > before:
                got += p["contribution"]
                print(f"  {got}/{target} from {TAKEN} thefts", flush=True)
    finally:
        mark("thief", "end", note=f"{TAKEN} stolen, +{got} when sold")
    print(f"auto: {TAKEN} thefts, +{got} when sold (fence.py SIYUN)")
    return 0


def main():
    setup()
    args = [a for a in sys.argv[1:]]
    if args and args[0] == "auto":
        if "--bold" not in args:
            refuse("auto needs --bold, for Derphy")
        nums = [int(a) for a in args[1:] if a.isdigit()]
        return auto(nums[0] if nums else 82, nums[1] if len(nums) > 1 else 60)
    max_lv = 14
    if "--max-lv" in args:
        i = args.index("--max-lv")
        max_lv = int(args[i + 1])
        del args[i:i + 2]
    global SKIP
    if "--skip" in args:
        SKIP = True
        args.remove("--skip")
    if args and args[0] == "take":
        # run 33: Olno the guard (Lv40) walked into range during a theft by Minwer's stall: "What is this? Guard!",
        # the guards hostile (teleport, then a return scroll). The witness check above runs once, before the cast;
        # the bridge's sneak guard cancels any hostile act (AI_Steal is one) the moment a possible witness stands
        # within r, every frame. The theft's own witness circle is 4 (AI_Steal ListWitnesses): r 5 is the margin.
        call("sneak", r=5)
        from activity import mark
        mark("thief", "start", note=f"{len(args) - 1} marks")  # run 33's review: ~90 unmarked real minutes of thefts
        try:
            for a in args[1:]:
                take(int(a), max_lv)
        finally:
            call("sneak", r=0)
            mark("thief", "end", note=f"{TAKEN} stolen")
        return 0
    every = "--all" in args
    nums = [int(a) for a in args if a.isdigit()]
    show(nums[0] if nums else 20, every, "--steel" in sys.argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
