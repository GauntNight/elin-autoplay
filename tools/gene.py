"""The Gene Machine (G38, run 36): the gene plan, a gene into a member, a finished gene applied.

usage: python -I tools/gene.py plan [MEMBER]     each member's feat points and slots, and every gene that would take
       python -I tools/gene.py start MEMBER GENE  walk to the machine, Use, pick MEMBER, Use, drag GENE onto ing1
       python -I tools/gene.py finish             Use the machine when the incubation is done: the gene applies
The member list and the checks are bridge 0.37.0's `genes` op (InvOwnerGene's own: gene slots, a feat at its max, an
action already known, plus the feat points to pay). GENE must be carried in the pack itself, not in a bag (the drag
grid shows the pack): take it out of its box first (box.py X,Z --take NAME). Incubation takes cost^2/2 game hours
(fact #1049); one member at a time; the machine offers no Use until it's done (fact #1105).
Exit 0 done, 1 refused (no machine, the member or gene not found, a gene that won't take, someone already inside),
2 the bridge, 3 stopped (a window that didn't open, a drag the grid didn't accept, the incubation not done).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import data, pc, pick, refuse, run, stop, top, walk_beside  # noqa: E402


def members():
    return data("genes")["members"]


def machine():
    hits = data("find", name="Gene Machine", r=999, n=1)["hits"]
    if not hits:
        refuse("no Gene Machine on this map")
    return hits[0]["x"], hits[0]["z"]


def use(x, z):
    p = pc()
    out = run("act.py", x - p["x"], z - p["z"], "Use")
    if out.rc != 0:
        stop(f"the machine offers no Use ({out.strip()}): the incubation isn't done yet, or it has no power")


def wait_layer(name, timeout=5.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if top() == name:
            return True
        time.sleep(0.25)
    return False


def plan(who=None):
    ms = members()
    want = pick(who, ms, "member", key="name") if who else None
    if who and not want:
        refuse(f"no member named {who!r}")
    for m in ms:
        if who and m is not want:
            continue
        ok = [f for f in m["fits"] if f["ok"]]
        print(f"{m['name']} Lv{m['lv']} ({m['race']}{', party' if m['party'] else ''}"
              f"{', IN THE MACHINE' if m['incubating'] else ''}): FP {m['feat']}, gene slots {m['slotsUsed']}/{m['slotsMax']}, "
              f"{len(m['genes'])} genes: " + ("; ".join(
                  "+".join(f"{v['name']} {v['v']}" for v in g["vals"]) or g["from"] for g in m["genes"]) or "none"))
        if who:
            for f in sorted(ok, key=lambda f: f["fp"]):
                print(f"   ok  {f['fp']:>2} FP {f['slots']} slot  {f['name']}")
            no = [f for f in m["fits"] if not f["ok"]]
            if no:
                print(f"   ({len(no)} won't take: " + ", ".join(sorted({f['why'] for f in no})) + ")")


def start(who, gene):
    ms = members()
    if any(m["incubating"] for m in ms):
        refuse("someone is already in the machine: " + ", ".join(m["name"] for m in ms if m["incubating"])
               + " (gene.py finish when it's done)")
    m = pick(who, ms, "member", key="name")
    if not m:
        refuse(f"no member named {who!r}: " + ", ".join(x["name"] for x in ms))
    f = pick(gene, m["fits"], "gene", key="name")
    if not f:
        refuse(f"no gene {gene!r} carried or boxed on this map")
    if not f["ok"]:
        refuse(f"{f['name']} won't take in {m['name']}: {f['why']}")
    pack = [i for i in data("stock", r=0)["pack"] if i.get("uid") == f["uid"]]
    if not pack:
        refuse(f"{f['name']} isn't in the pack itself (box.py X,Z --take, or bag.py --take, first)")
    x, z = machine()
    walk_beside(x, z)
    use(x, z)
    if not wait_layer("LayerPeople"):
        stop(f"the people picker didn't open (top: {top()})")
    rows = [b for b in data("buttons")["buttons"] if b.get("name") == "ButtonGeneral"]
    row = pick(m["name"], rows, "picker row", key="text")
    if not row:
        run("close.py")
        stop(f"{m['name']} isn't in the picker")
    r = call("click", i=row["i"], expect=m["name"])
    if not r.get("ok"):
        run("close.py")
        stop(f"the click on {m['name']}'s row failed: {r.get('error')}")
    time.sleep(0.8)
    use(x, z)
    if not wait_layer("LayerDragGrid"):
        stop(f"the Modify Genes grid didn't open (top: {top()}); {m['name']} is in the machine: gene.py start again")
    btns = data("buttons", all=True)["buttons"]
    slot = next((b["i"] for b in btns if b["name"].startswith("ing1")), None)
    src = [b for b in btns if b.get("in") == "pack" and b.get("card") == f["name"]]
    if slot is None or len(src) != 1:
        run("close.py")
        stop(f"the grid shows ing1 {slot} and {len(src)} slots holding {f['name']}")
    r = data("drag", i=src[0]["i"], j=slot)
    if not r.get("accepted"):
        stop(f"the grid didn't take {f['name']}: {r}")
    time.sleep(0.5)
    hours = f["fp"] * f["fp"] // 2 if f["fp"] else 0
    log = (data("state").get("log") or [])[-3:]
    print(f"{m['name']} takes in {f['name']} ({f['fp']} FP, {f['slots']} slot; ~{hours} game hours): {' / '.join(log)}")


def finish():
    ms = members()
    inside = [m for m in ms if m["incubating"]]
    if not inside:
        refuse("nobody is in the machine")
    x, z = machine()
    walk_beside(x, z)
    use(x, z)
    time.sleep(0.8)
    if top() == "LayerDragGrid":  # a member inside with no gene yet: the grid asks for one
        run("close.py")
        stop(f"{inside[0]['name']} is in the machine without a gene: gene.py start {inside[0]['name']!r} GENE")
    log = (data("state").get("log") or [])[-3:]
    after = pick(inside[0]["name"], members(), "member", key="name")
    print(f"{after['name']}: FP {after['feat']}, gene slots {after['slotsUsed']}/{after['slotsMax']}, "
          f"in the machine {after['incubating']}: {' / '.join(log)}")
    if after["incubating"]:
        stop("still in the machine")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    if not a or a[0] not in ("plan", "start", "finish"):
        refuse(__doc__.strip().splitlines()[2])
    if a[0] == "plan":
        plan(a[1] if len(a) > 1 else None)
    elif a[0] == "start":
        if len(a) < 3:
            refuse("start MEMBER GENE")
        start(a[1], a[2])
    else:
        finish()


if __name__ == "__main__":
    main()
