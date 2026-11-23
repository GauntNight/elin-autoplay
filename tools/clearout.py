"""The clear-out of home storage by the keep rules (G70 Smart Storage M4, run 57): every stack keep.py calls "sell" or
"trash" is taken from its box into the pack's own grid, a batch at a time, then sold to the home shopkeeper (sell.py, the
resident board's Find walks me to her) or dropped in the trash can (trash.py dump). The approved calls are in
knowledge/storage-audit.md (the user, 2026-11-21); gear ("gear") waits for gearcheck.py, unidentified things for Aliyun.

A batch is as many stacks as the pack's grid has free (packcheck.GRID_CARDS, 35, less the loose stacks, less one spare); a
shop lists only that grid (fence.py's lesson, run 43). Boxes with the most candidates go first, so each walk moves the most.
Never touched: the shipping chest, the trash can, the mail post, the Dishes box, the Maps box (Poppy's), Fiama's quest
chest and the practice chest. Every batch runs farmday.home_guard first (run 41: a box walk with no stops ended in two
deaths), and the run stops at the first batch whose sale moved no gold (the buyer out of money).

usage: python -I tools/clearout.py [--calls sell,trash] [--batches N] [--buyer NAME] [--chest] [--dry]
  --calls    which of keep.py's calls to clear (default sell,trash)
  --batches  stop after N batches (default 99)
  --buyer    the shopkeeper (default "Samata": the name talkto sees)
  --chest    the "sell" stacks go to the shipping chest instead of the shopkeeper (when her shop won't take more)
  --dry      print the plan (boxes and stacks per call) and move nothing
  To end a run between batches: create runs/jobs/clearout.stop (it is removed when read).
Exit 0 done (nothing left, or N batches), 1 refused (the grid has no room), 3 stopped (home_guard, a take or sale failed,
the buyer out of money).
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data, last, refuse, run, setup, stop  # noqa: E402
import farmday  # noqa: E402
import home  # noqa: E402
from keep import category, verdict  # noqa: E402

SKIP_NAMES = ("shipping chest", "trash can", "mail post", "Dishes", "Maps", "practice chest", "package labelled")


def skip(box):
    if not box.get("installed"):
        return True
    if (box["x"], box["z"]) == tuple(home.FIAMA_CHEST):
        return True
    return any(n.lower() in (box.get("name") or "").lower() for n in SKIP_NAMES)


def plan(calls, held=(), no_junk=False):
    """{(x, z, name): {call: [item]}} of the candidates, boxes with the most first."""
    out = defaultdict(lambda: defaultdict(list))
    for box in data("stock")["boxes"]:
        if skip(box):
            continue
        for it in box.get("items") or []:
            c, _why = verdict(it)
            # box.py refuses junk for the shipping chest (the user, run 08: junk to the trash can, never the chest)
            if no_junk and category(it)[0] == "junk":
                continue
            if c in calls and it.get("uid") not in held:
                out[(box["x"], box["z"], box["name"])][c].append(it)
    return sorted(out.items(), key=lambda kv: -sum(len(v) for v in kv[1].values()))


def free_grid():
    """packcheck's count (run 25): the grid holds 35 cards; the inv entries not worn take one each (pc.stacks counts the
    toolbelt's stacks too). One slot stays spare for whatever a walk picks up."""
    from bridge import call
    from packcheck import GRID_CARDS
    return GRID_CARDS - sum(1 for i in call("inv")["data"]["items"] if not i.get("equipped")) - 1


def make_room():
    """Run 57: every home stop's clear-out began with a full grid (the kit: rods, lockpicks, the pickaxe, ammo) and the
    same hand step, moving kit stacks into a bag. They go into the roomiest carried bag here; packcheck --move puts the kit
    back into the pack before leave.py lets me out."""
    import items as inv
    its = inv.inventory()
    bags = [b for b in its if b.get("container") and not b.get("path") and not b.get("equipped")
            and b.get("name") in ("a haul bag", "a backpack", "a loot bag", "a spoils bag", "a pouch")]
    if not bags:
        return
    bag = max(bags, key=lambda b: (b.get("slots") or 0) - (b.get("count") or 0))
    space = (bag.get("slots") or 0) - (bag.get("count") or 0)
    words = ("rod of", "lockpick", "pickaxe", "arrows",  # never the shovel: packcheck files it in the Farm box (run 57)
              "quarrels", "troll blood", "restore mind", "restore body")
    loose = [i for i in its if not i.get("path") and not i.get("equipped") and not i.get("container")
             and any(w in (i.get("name") or "") for w in words)]
    pick = loose[:max(0, min(space - 1, 12))]
    if pick:
        out = run("bag.py", bag["name"], *[f"uid:{i['uid']}" for i in pick], timeout=600)
        print(f"  room: {sum(1 for ln in out.splitlines() if ': moved' in ln)} kit stacks into {bag['name']}")
        MOVED.extend(i["uid"] for i in pick)


MOVED = []  # make_room's kit stacks, put back into the pack when the clear-out ends


def put_back():
    """Run 57: packcheck leaves kit inside a bag ("kit rides where it is"), so the pickaxe, a lockpick and the arrows
    make_room had bagged stayed there: the wrecks step found no pickaxe, unlock.py picked bare-handed, the bow had no arrows."""
    if not MOVED:
        return
    import items as inv
    its = inv.inventory()
    back = 0
    for i in its:
        if i.get("uid") in MOVED and i.get("path"):
            ok, _why = inv.to_pack(i, inv.inventory())
            back += ok
    print(f"  put back into the pack: {back} of {len(MOVED)} kit stacks")


def main():
    from job import register  # run 58: bridge.call refuses a second acting client while this runs
    register("clearout")
    try:
        _main()
    finally:
        put_back()


def _main():
    setup()
    argv = sys.argv[1:]
    opt = {k: argv[argv.index(k) + 1] for k in ("--calls", "--batches", "--buyer") if k in argv}
    calls = set((opt.get("--calls") or "sell,trash").split(","))
    batches = int(opt.get("--batches") or 99)
    to_chest = "--chest" in argv
    buyer = opt.get("--buyer") or "Samata"  # the creature's name (talkto); the board row reads "Samata the healer"
    if "--dry" in argv:
        tot = defaultdict(int)
        for (x, z, name), by in plan(calls):
            print(f"  {x},{z} {name}: " + ", ".join(f"{c} {len(v)}" for c, v in by.items()))
            for c, v in by.items():
                tot[c] += len(v)
        print("total: " + ", ".join(f"{c} {n}" for c, n in tot.items()) + f"; the grid has {free_grid()} free")
        return
    done_sell = done_trash = 0
    held = set()  # uids items.protected() holds back: never planned again this run
    stopfile = Path(__file__).resolve().parent.parent / "runs" / "jobs" / "clearout.stop"
    for b in range(batches):
        # run 57: a 60-batch run (~2.5 real minutes a batch) had no way to end early but a kill, which the rules forbid
        if stopfile.exists():
            stopfile.unlink()
            print(f"stopped by {stopfile.name} before batch {b + 1}")
            break
        farmday.home_guard(f"the clear-out, batch {b + 1}")
        room = free_grid()
        if room < 3:
            make_room()
            room = free_grid()
        if room < 3:
            refuse(f"the pack's grid has {room} free: put kit stacks in a bag first (packcheck --move restores them)")
        todo = plan(calls, held, no_junk=to_chest)
        if not todo:
            print("nothing left to clear")
            break
        taken = {"sell": [], "trash": []}
        for (x, z, name), by in todo:
            if room <= 0:
                break
            batch = []
            for c in ("trash", "sell"):
                for it in by.get(c, []):
                    if room <= 0:
                        break
                    batch.append((c, it))
                    room -= 1
            if not batch:
                continue
            out = run("box.py", f"{x},{z}", "--take", *[f"uid:{it['uid']}" for _c, it in batch], timeout=600)
            moved = {m.group(1) for m in (re.match(r"(uid:\d+): moved", ln) for ln in out.splitlines()) if m}
            for c, it in batch:
                if f"uid:{it['uid']}" in moved:
                    taken[c].append(it)
            if out.rc != 0:
                print(f"  {x},{z} {name}: {last(out)}")
        if taken["trash"]:
            names = sorted({it["name"] for it in taken["trash"]})
            t = run("trash.py", "dump", *names, timeout=600)
            print(f"  trash: {last(t)}")
            done_trash += len(taken["trash"])
        if taken["sell"]:
            # run 57: "3 light stands" (junk to keep.py) read as kit (a light) to items.protected(), and sell.py refused
            # the whole batch: a protected stack stays in the pack (packcheck --move files it after) and is never planned again
            import items as inv
            carried = inv.inventory()
            by = {c["uid"]: c for c in carried}
            ok = []
            for it in taken["sell"]:
                why = inv.protected(by.get(it["uid"], it), carried)
                if why:
                    held.add(it["uid"])
                    print(f"  held back: {it['name']} ({why})")
                else:
                    ok.append(it)
            taken["sell"] = ok
        if taken["sell"] and to_chest:
            # run 57: Samata stopped taking anything after ~70,000 orens (the Restock did nothing: influence gone?);
            # the shipping chest pays 1.1x a shop and empties each morning, ~40 stacks a day (fact #1001)
            sx, sz = home.SHIPPING
            s = run("box.py", f"{sx},{sz}", *[f"uid:{it['uid']}" for it in taken["sell"]], timeout=900)
            moved = {m.group(1) for m in (re.match(r"(uid:\d+): moved", ln) for ln in s.splitlines()) if m}
            left = [it for it in taken["sell"] if f"uid:{it['uid']}" not in moved]
            print(f"  shipped {len(moved)}" + (f"; not taken: {', '.join(it['name'] for it in left)}" if left else ""))
            if left:
                back = run("box.py", f"{home.STORAGE_CHEST_2[0]},{home.STORAGE_CHEST_2[1]}",
                           *[f"uid:{it['uid']}" for it in left], timeout=600)
                print(f"  back to the Storage Chest ({last(back) or 'ok'})")
            done_sell += len(moved)
            if not moved:
                stop("clear-out: the shipping chest took nothing: full for today (or a refused kind: junk goes to Samata)")
            print(f"batch {b + 1}: shipped {len(moved)}")
            continue
        if taken["sell"]:
            s = run("sell.py", buyer, *[f"uid:{it['uid']}" for it in taken["sell"]], "--find", timeout=900)
            for ln in s.splitlines():
                if ln.startswith(("sold", "wouldn't", "still", "  left")):
                    print("  " + ln)
            # what didn't sell (a royal gift box, run 57) goes to the roomiest Storage Chest and is never planned again
            still = {c["uid"] for c in inv.inventory()}
            left = [it for it in taken["sell"] if it["uid"] in still]
            if left:
                held.update(it["uid"] for it in left)
                back = run("box.py", f"{home.STORAGE_CHEST_2[0]},{home.STORAGE_CHEST_2[1]}",
                           *[f"uid:{it['uid']}" for it in left], timeout=600)
                print(f"  unsold, to the Storage Chest: {', '.join(it['name'] for it in left)} ({last(back) or 'ok'})")
            if s.rc == 3:
                stop(f"clear-out: {last(s)}")
            if s.rc != 0:
                stop(f"clear-out: sell.py refused: {last(s)}")
            done_sell += len(taken["sell"]) - len(left)
        if not taken["sell"] and not taken["trash"]:
            stop("clear-out: a batch took nothing out of the boxes (full grid? locked box?)")
        print(f"batch {b + 1}: sold {len(taken['sell'])}, trashed {len(taken['trash'])}")
    print(f"clear-out: {done_sell} stacks sold, {done_trash} trashed")


if __name__ == "__main__":
    main()
