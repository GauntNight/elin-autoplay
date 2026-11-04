"""Feed named stacks into an installed converter's drag grid (the kiln's Bake, the spinner's Spin; run 28).
A converter turns the WHOLE dragged stack, one piece per tick, as one AI_UseCrafter task (run 25: 124
fibers on the spinner ran SP 51 -> -19, the death by overwork): so each stack is checked against SP
first (SP_EACH a piece, plus the reserve), fed one at a time, and waited out before the next. The
bridge's stamina floor (0.32.0) still cancels the task at SP 3. The grid closes at the end.

usage: python -I tools/convert.py DX DZ ACT [--sp-each N] [--max N] STACK [STACK ...]
  --max N  feed a bigger stack but stop after about N pieces: the bridge's stamina floor (spguard) is set
           to SP - N x sp-each for the task and put back to 3 after (run 28: 10 threads from 73 fibers)
  e.g. python -I tools/convert.py -1 1 Bake "6 pine logs" "5 palulu logs"     (kiln: log -> carbon log)
       python -I tools/convert.py -1 1 Spin --sp-each 1 "8 pieces of hide fiber"
  STACK  the pack stack's full name (whole-word matching; two candidates is a refusal)
Exit 0 all fed, 1 refused (no such act, a stack missing or over the SP), 3 stopped (a hostile, a window).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import matches, pc, ready, refuse, run, setup, stop, top, wait_idle  # noqa: E402

RESERVE = 10  # SP left after a stack, at least


def count(card):
    m = re.match(r"(\d+) ", card or "")
    return int(m.group(1)) if m else 1


def open_grid(dx, dz, act):
    if top() == "LayerDragGrid":
        return
    acts = call("acts", dx=dx, dz=dz, mode="all")["data"]["acts"]
    hit = [a for a in acts if a["text"].startswith(act)]
    if not hit:
        refuse(f"no {act} act at {dx},{dz}: " + ", ".join(a["text"] for a in acts))
    call("do", i=hit[0]["i"])
    call("wait", until="layer", timeout=5000)
    if top() != "LayerDragGrid":
        refuse(f"the {act} grid did not open (top {top()})")


def slots():
    bs = call("buttons", all=True)["data"]["buttons"]
    ing = next((b["i"] for b in bs if b["name"].startswith("ing1")), None)
    inv = [b for b in bs if "ButtonGrid inventory" in b["name"] and b.get("card")]
    return ing, inv


def main():
    setup()
    args = sys.argv[1:]
    sp_each, most = 1, None
    if "--max" in args:
        i = args.index("--max")
        most = int(args[i + 1])
        del args[i:i + 2]
    if "--sp-each" in args:
        i = args.index("--sp-each")
        sp_each = int(args[i + 1])
        del args[i:i + 2]
    if len(args) < 4:
        refuse(__doc__.strip().splitlines()[-4])
    dx, dz, act, wanted = int(args[0]), int(args[1]), args[2], args[3:]
    why = ready(hp=None, hunger=None, burden=None, allow=("LayerInventory", "LayerDragGrid"))
    if why:
        stop(why)
    fed = []
    for want in wanted:
        open_grid(dx, dz, act)
        ing, inv = slots()
        hits = [h for h in inv if h.get("card") == want] or matches(want, inv)  # an exact name first
        if not hits:
            run("close.py")
            refuse(f"no pack stack named {want!r} in the grid")
        if len({h['card'] for h in hits}) > 1:
            run("close.py")
            refuse(f"{want!r} fits {', '.join(sorted({h['card'] for h in hits}))}: give the full name")
        src = hits[0]
        n, sp = count(src["card"]), pc()["sp"]
        if most is not None and n > most:
            floor = sp - most * sp_each
            if floor < 3:
                run("close.py")
                refuse(f"--max {most}: SP {sp} can't cover {most} pieces")
            import atexit
            atexit.register(lambda: call("spguard", floor=3))  # a refusal or crash never leaves the floor raised
            call("spguard", floor=floor)
            n = most
        if n * sp_each > sp - RESERVE:
            run("close.py")
            refuse(f"{src['card']}: {n} pieces x {sp_each} SP is over SP {sp} - {RESERVE}")
        foes = [x["name"] for x in call("state")["data"].get("nearby") or [] if x.get("hostile")]
        if foes:
            run("close.py")
            stop("hostile in view: " + ", ".join(foes[:3]))
        r = call("drag", i=src["i"], j=ing)
        if not r.get("ok"):
            run("close.py")
            refuse(f"drag of {src['card']} failed: {r.get('error')}")
        wait_idle(timeout=max(30000, n * 4000))
        if most is not None:
            run("close.py")  # the open grid restarts the crafter after each cancel (run 25)
            call("spguard", floor=3)
        print(f"  {src['card']} fed (SP {sp} -> {pc()['sp']})")
        fed.append(src["card"])
    run("close.py")
    print(f"fed {len(fed)} stacks")


if __name__ == "__main__":
    main()
