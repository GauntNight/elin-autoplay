"""Fireproof blankets from the home's own stock (G65, run 54; the user: "a Goal on how to keep Fireproof Blankets in
stock (either through stores or creation, it's clearly a frequent issue)"). Runs 42-53 left home on 0-1 blankets with
160 waivers in 12 days while 145 skins and 55 hide fibers sat in the boxes: the minimum counted only finished textures.

The chain, run from whatever stage the stock is at, last stage first (fact #1421):
  skins --the butcher's tool (~1 SP a skin)--> 2-3 hide fibers each --the spinner (1 SP)--> hide thread
  2 hide threads --the loom (2 SP)--> a texture;  5 textures + 4 carbon logs --the loom (5 SP)--> a fireproof blanket
  a log --the kiln (1 SP)--> a carbon log (only carbon logs fill the blanket's log slot, fact #862)
About 33 SP a blanket from skins, 29 from fiber. The converters (butcher's tool, spinner, kiln) take only pack stacks,
so each stage carries its input from the box and packcheck.py --move puts the rest back at the end.

usage: python -I tools/blanket.py [--target N=6] [--max N] [--floor SP=40] [--dry]
  --target  charged fireproof blankets wanted across the pack and the home boxes; makes the difference
  --max     at most N this call
  --floor   SP left at the end, at least (the trip after; no stage starts that would cross it)
  --dry     print the stock, the plan and its SP, and act on nothing
Exit 0 made (or none needed), 1 refused, 2 the bridge, 3 stopped (a hostile, a window, a stage short of SP or stock).
"""
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data, pc, ready, refuse, run, setup, stop, walk_beside  # noqa: E402
from home import BOX_STR, STATIONS  # noqa: E402

LOOM, SPINNER, KILN = STATIONS["loom"], STATIONS["spinner"], STATIONS["kiln"]
TEXTURES, LOGS = 5, 4          # a blanket's recipe (kb.py make "fireproof blanket")
SP_SKIN, SP_SPIN, SP_TEX, SP_BLANKET, SP_BAKE = 1, 1, 2, 5, 1  # measured in run 48 (fact #1421)
FIBER_PER_SKIN = 2             # the game's minimum (2-3 a skin); run 48 averaged 2.5, run 54's 4 skins gave 9 fibers, one texture short
CHARGES = re.compile(r"\((\d+) charges?\)", re.I)
TOOL = "butcher's tool"


def charged(name):
    m = CHARGES.search(name or "")
    return m is None or int(m.group(1)) > 0


def material(name):
    """'a hide thread' -> 'hide'; '55 pieces of hide fiber' -> 'hide'; 'a carbon log' -> 'carbon'."""
    n = re.sub(r"^(\d[\d,]*|an?)\s+(pieces? of\s+)?", "", (name or "").lower())
    return n.split()[0] if n.split() else ""


def stock():
    """Every stack of the chain's kinds, carried or boxed: {key: [(place, item)]}. Keys: blanket (charged fireproof),
    texture, thread (hide), fiber (hide), skin, carbon (logs), log (plain logs fit for the kiln)."""
    s = data("stock")

    def flat(items, place):  # the pack is a tree: a stack in a bag counts but isn't in the grid ("bag")
        for it in items:
            yield place, it
            yield from flat(it.get("items") or [], "bag")
    places = [("pack", s.get("pack") or [])] + [((b["x"], b["z"]), b.get("items") or []) for b in s.get("boxes") or []]
    out = {k: [] for k in ("blanket", "texture", "thread", "fiber", "skin", "carbon", "log")}
    rows = [r for place, items in places[:1] for r in flat(items, place)]
    rows += [(place, it) for place, items in places[1:] for it in items]
    by_place = {}
    for place, it in rows:
        by_place.setdefault(place, []).append(it)
    for place, items in by_place.items():
        for it in items:
            i, nm = it.get("id"), it.get("name") or ""
            if i == "blanket_fire" and charged(nm):
                out["blanket"].append((place, it))
            elif i == "texture" and material(nm) == "hide":  # a slot takes one stack: a paper texture can't join hide ones
                out["texture"].append((place, it))
            elif i == "thread" and material(nm) == "hide":
                out["thread"].append((place, it))
            elif i == "fiber" and material(nm) == "hide":
                out["fiber"].append((place, it))
            elif i == "skin":
                out["skin"].append((place, it))
            elif i == "log" and material(nm) == "carbon":
                out["carbon"].append((place, it))
            elif i == "log" and material(nm) in ("oak", "pine", "fir", "birch", "poplar", "cedar", "acacia", "palulu"):
                out["log"].append((place, it))  # common woods only: feywood, coralwood and the rest stay for crafts
    return out


def total(rows):
    return sum(it.get("num") or 1 for _, it in rows)


def plan(st, n):
    """What making n blankets takes from this stock: per-stage counts and the SP."""
    tex = max(0, TEXTURES * n - total(st["texture"]))
    thr = max(0, 2 * tex - total(st["thread"]))
    fib = max(0, thr - total(st["fiber"]))
    skins = math.ceil(fib / FIBER_PER_SKIN)
    bake = max(0, LOGS * n - total(st["carbon"]))
    sp = skins * SP_SKIN + thr * SP_SPIN + tex * SP_TEX + n * SP_BLANKET + bake * SP_BAKE
    short = []
    if skins > total(st["skin"]):
        short.append(f"skins {skins} > {total(st['skin'])}")
    if bake > total(st["log"]):
        short.append(f"logs {bake} > {total(st['log'])}")
    return {"n": n, "skins": skins, "fiber": thr, "textures": tex, "bake": bake, "sp": sp, "short": short}


def beside(xy):
    w = walk_beside(xy[0], xy[1], weak_ok=True)
    if not w.get("done"):
        stop(f"the walk to {xy} ended: {w.get('why')}")
    p = pc()
    return xy[0] - p["x"], xy[1] - p["z"]


def must(out, what):
    print("\n".join("  | " + ln for ln in str(out).splitlines()[-6:]))
    if out.rc:
        (stop if out.rc == 3 else refuse)(f"{what}: rc {out.rc}")


def carried(key):
    """The pack's stacks of one kind (convert.py drags pack stacks only)."""
    return [it for place, it in stock()[key] if place == "pack"]


def fetch(key, want):
    """Carry boxed stacks of one kind to the pack until it holds `want` or more."""
    have = total([("pack", it) for it in carried(key)])
    # run 54: the largest stack first took 56 oak logs for 12 carbon logs and box.py put them back at burden phase 3: the
    # smallest stack that covers the need first, then the largest ones
    need = want - have

    def order(r):
        n = r[1].get("num") or 1
        return (0, n) if n >= need else (1, -n)
    for place, it in sorted(stock()[key], key=order):
        if have >= want:
            break
        if place in ("pack", "bag"):
            continue
        must(run("box.py", BOX_STR(place), "--take", it["name"], timeout=180), f"box.py {place} --take {it['name']}")
        have += it.get("num") or 1
    return have


def feed(xy, act, key, pieces):
    """Feed `pieces` of one pack stack into a converter (at xy, or the carried butcher's tool when xy is None)."""
    stacks = sorted(carried(key), key=lambda it: -(it.get("num") or 1))
    if not stacks:
        stop(f"no {key} in the pack to {act}")
    name, num = stacks[0]["name"], stacks[0].get("num") or 1
    k = min(pieces, num)
    if xy is None:
        # run 54: purge's unclutter tucks the butcher's tool into a bag (kit rides where it is), and item.py Uses only what
        # the pack's grid holds: bring it out first
        import items as _items
        tools = [it for it in _items.inventory() if TOOL in (it.get("name") or "").lower()]
        if not tools:
            stop(f"no {TOOL} carried: make one at the tinker's table (3 barks + a dagger-class blade, fact #531)")
        if tools[0].get("parent"):
            must(run("bag.py", _items.where(tools[0], _items.inventory()).split(" > ")[-1], "--take",
                     f"uid:{tools[0]['uid']}", timeout=120), f"the {TOOL} out of its bag")
        args = ["convert.py", "--tool", TOOL]
    else:
        dx, dz = beside(xy)
        args = ["convert.py", str(dx), str(dz), act]
    if num > k:
        args += ["--max", str(k)]
    must(run(*args, name, timeout=600), f"{act} {k} of {name}")
    return k


def craft(recipe, n, use):
    dx, dz = beside(LOOM)
    must(run("craft.py", str(dx), str(dz), recipe, str(n), "--use", use, timeout=600), f"craft {n} {recipe}")
    run("close.py", timeout=30)


def main():
    setup()
    a = sys.argv[1:]

    def opt(flag, default):
        return int(a[a.index(flag) + 1]) if flag in a else default
    target, most, floor, dry = opt("--target", 6), opt("--max", 99), opt("--floor", 40), "--dry" in a
    st = stock()
    have = total(st["blanket"])
    sp = pc()["sp"]
    print(f"stock: {have} charged blankets; textures {total(st['texture'])}, hide threads {total(st['thread'])}, "
          f"hide fiber {total(st['fiber'])}, skins {total(st['skin'])}, carbon logs {total(st['carbon'])}, "
          f"kiln logs {total(st['log'])}; SP {sp}, floor {floor}")
    want = min(max(0, target - have), most)
    if want == 0:
        print(f"no blankets needed: {have} of the target {target}")
        return
    n, best = want, None
    while n > 0:  # the most the SP and the stock allow
        p = plan(st, n)
        if not p["short"] and sp - p["sp"] >= floor:
            best = p
            break
        n -= 1
    if best is None:
        p = plan(st, 1)
        stop(f"not even one blanket: {p['sp']} SP against SP {sp} - floor {floor}"
             + (f"; short: {', '.join(p['short'])}" if p["short"] else "") + " (sleep, then again)")
    print(f"plan: {best['n']} of {want} wanted; skins {best['skins']} -> fiber, spin {best['fiber']}, "
          f"weave {best['textures']} textures, bake {best['bake']} carbon logs; ~{best['sp']} SP")
    if dry:
        return
    why = ready(hp=None, hunger=70, burden=None)
    if why:
        stop(why)
    if best["bake"]:
        fetch("log", best["bake"])
        feed(KILN, "Bake", "log", best["bake"])
    if best["skins"]:
        fetch("skin", best["skins"])
        feed(None, "Butcher", "skin", best["skins"])
    if best["fiber"]:
        fetch("fiber", best["fiber"])
        feed(SPINNER, "Spin", "fiber", best["fiber"])
    if best["textures"]:
        craft("texture", best["textures"], "hide")
    fetch("carbon", 10 ** 6)  # every carbon log into the pack, one stack: the log slot takes a single stack of 4
    for i in range(best["n"]):  # one a call: a second stack of textures or logs can't top up a slot mid-batch
        before = total(stock()["blanket"])
        craft("fireproof blanket", 1, "hide,carbon")
        if total(stock()["blanket"]) <= before:
            stop(f"blanket {i + 1} of {best['n']}: the count didn't rise")
    st = stock()
    print(f"made: {total(st['blanket']) - have} blankets; now {total(st['blanket'])} charged "
          f"({', '.join(it['name'] for _, it in st['blanket'])}); SP {pc()['sp']}")
    out = run("packcheck.py", "--move", timeout=600)
    print("\n".join("  | " + ln for ln in str(out).splitlines()[-4:]))
    spares()


def spares():
    """Three blankets ride in the pack's grid (CORE_KIT, leave.py's minimum); the rest ride in the spoils bag, where
    packcheck keeps kit and a charge still guards the pack (fact #1071: a breath drained one in the backpack too), so a
    bad fire mid-run doesn't leave the second half on none (run 53)."""
    import items as _items
    its = _items.inventory()
    grid = sorted((it for it in its if not it.get("parent") and it.get("id") == "blanket_fire" and charged(it["name"])),
                  key=lambda it: -(int(CHARGES.search(it["name"]).group(1)) if CHARGES.search(it["name"]) else 99))
    for it in grid[3:]:
        out = run("bag.py", "spoils bag", f"uid:{it['uid']}", timeout=120)
        print(f"  spare to the spoils bag: {it['name']} (rc {out.rc})")


if __name__ == "__main__":
    main()
