"""Have a mage's artifact service identify the carried Godly (and Special) pieces, one per conversation (run 58; by hand in runs 11,
16, 44 and 49: a talk, the service's line, a Yes, a drag onto the grid under the drama, a close, a Bye, fourteen times over).
"Identify all" (identifyall.py) doesn't cover them. The grid lists the pack's own cards, so each piece is moved out of its bag
first. Fact #1450: 377 orens a piece at shop level 15, and a second drag in the same conversation is refused.

usage: python -I tools/identifyartifact.py [NAME=Aliyun] [MAX=700] [--match TEXT] [--dry]   beside NAME
  MAX     the most orens a piece: a dearer price is answered No and the run ends
  --match only the pieces whose name holds TEXT (default "(Godly)")
Exit 0 done (or nothing to identify), 1 refused (not in view, no such service), 3 a dialog or grid that didn't read as expected.
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, data, refuse, run, setup, state, stop, txlog, wait_until  # noqa: E402
from identifyall import bye, click  # noqa: E402
import items as inv  # noqa: E402


def pieces(text):
    return [it for it in inv.inventory() if not it.get("identified", True) and text.lower() in it["name"].lower()]


def one(name, it, most):
    """Identify one piece in one conversation: True, or the reason it stopped."""
    out = run("talkto.py", name, timeout=120)
    if out.rc:
        return f"talkto {name}: {str(out)[-120:]}"
    g0 = state()["pc"].get("gold") or 0
    if not click("identify an artifact"):
        bye()
        return f"{name} offers no artifact service"
    said = str(run("talk.py", timeout=60))
    m = re.search(r"([\d,]+) Orens", said, re.I)
    price = int(m.group(1).replace(",", "")) if m else 0
    if price > most:
        click("No.")
        run("talk.py", timeout=60)
        bye()
        return f"{price} orens is over {most}: declined"
    click("Yes.")
    time.sleep(0.5)
    slot = src = None
    for _ in range(8):
        btns = data("buttons", all=True)["buttons"]
        slot = next((b["i"] for b in btns if (b.get("name") or "").startswith("ing1")), None)
        src = next((b["i"] for b in btns if b.get("uid") == it["uid"] and "inventory" in (b.get("name") or "").lower()), None)
        if src is None:
            src = next((b["i"] for b in btns if b.get("card") == it["name"] and "inventory" in (b.get("name") or "").lower()), None)
        if slot is not None and src is not None:
            break
        wait_until("frames", n=10, timeout=2000)
    if slot is None or src is None:
        print(f"  the dialog: {said[-300:]}")
        return f"no grid or the piece isn't on it (slot {slot}, piece {src}): look.py, buttons --all"
    r = call("drag", i=src, j=slot, force=1)
    wait_until("frames", n=30, timeout=3000)
    run("close.py", timeout=60)
    run("talk.py", timeout=60)
    bye()
    run("close.py", timeout=60)
    now = next((x for x in inv.inventory() if x["uid"] == it["uid"]), None)
    paid = g0 - (state()["pc"].get("gold") or 0)
    if now is None or not now.get("identified", True):
        return f"{it['name']} is still unidentified (drag: {r.get('error') or r.get('data')}; paid {paid})"
    txlog("identified", now["name"], "pack", name, f"{paid} orens")
    print(f"  {it['name']} -> {now['name']} ({paid} orens)", flush=True)
    return True


def main():
    setup()
    args = [a for a in sys.argv[1:]]
    dry = "--dry" in args
    text = args[args.index("--match") + 1] if "--match" in args else "(Godly)"
    plain = [a for i, a in enumerate(args) if not a.startswith("--") and not (i and args[i - 1] == "--match")]
    name = plain[0] if plain else "Aliyun"
    most = int(plain[1]) if len(plain) > 1 else 700
    todo = pieces(text)
    if not todo:
        print(f"nothing unidentified holds {text!r}")
        return 0
    print(f"{len(todo)} to identify: " + "; ".join(it["name"] for it in todo))
    if dry:
        return 0
    if not any(name.lower() in (c.get("name") or "").lower() for c in state().get("nearby") or []):
        refuse(f"{name} isn't in view")
    done = 0
    for it in todo:
        if it.get("path"):
            ok, why = inv.to_pack(it, inv.inventory())
            if not ok:
                stop(f"{it['name']} won't come out of its bag: {why} ({done} done)")
        r = one(name, it, most)
        if r is not True:
            stop(f"{r} ({done} of {len(todo)} done)")
        done += 1
    print(f"done: {done} identified; next: gearcheck.py, then shipstar.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
