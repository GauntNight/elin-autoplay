"""List the home's policies, or switch one on or off by its exact name, and check that only it
changed (run 15).

Why a tool: in run 14 the Policy tab's clicks hit the wrong rows. The game binds each row to its
own policy (ContentPolicy: the button's refObj and its onClick listener), so the rows were never
the problem: a `look.py` between `buttons` and `click` re-listed every button on screen
(`buttons --all`), and the next `click 16` / `click 8` pressed index 16 / 8 of that listing
instead of the Policy tab's. Tax Free Land went off twice that way. Here the listing and the
click come one right after the other, by name, and the tab is read again after the click.

The game's own checks still apply on the click (ContentPolicy.RefreshPolicyList): a policy
whose cost would pass the admin points, Tax Free Land at 3+ bases, and the excluding pairs
(2515/2516, 2814/2823) beep and do nothing.

usage: python -I tools/policy.py                    list: cost, on/off, admin points
       python -I tools/policy.py on "Border Watch"
       python -I tools/policy.py off "Growth Boost"
       python -I tools/policy.py ... --keep         leave the Home window open
Exit codes: 0 done, 1 refused (no such policy, the game beeped), 2 bridge, 3 another row changed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from close import close_all  # noqa: E402
from common import data, refuse, setup, stop, top, wait_until, walk_beside  # noqa: E402


def rows():
    """The Policy tab's rows as {name: (index, cost, on)} and the admin points text."""
    bs = data("buttons")["buttons"]
    out, ap = {}, None
    for b in bs:
        parts = [p.strip() for p in (b.get("text") or "").split("|")]
        if b["name"] == "ButtonGeneral(Clone)" and len(parts) == 2 and parts[0].isdigit():
            out[parts[1]] = (b["i"], int(parts[0]), bool(b.get("checked")))
        elif (b.get("tip") or "") == "Admin Points":
            ap = parts[0]
    return out, ap


def open_tab():
    if top() != "LayerHome":
        if top():
            refuse(f"{top()} is open: close it first")
        hits = data("find", name="home board", r=999, n=1)["hits"]
        if not hits:
            refuse("no home board on this map (the Home window opens from its Home Summary)")
        # A board 5 cells off lists no acts at all (run 15): stand beside it first.
        if hits[0]["dist"] > 1:
            w = walk_beside(hits[0]["x"], hits[0]["z"])
            if not w.get("done"):
                stop(f"the walk to the home board ended: {w.get('why')}")
            hits = data("find", name="home board", r=999, n=1)["hits"]
        acts = data("acts", dx=hits[0]["dx"], dz=hits[0]["dz"], mode="all")["acts"]
        summary = [a for a in acts if a["text"].startswith("Home Summary")]
        if not summary:
            refuse("the home board offers no Home Summary: " + " | ".join(a["text"] for a in acts))
        data("do", i=summary[0]["i"])
        wait_until("layer", timeout=5000)
        if top() != "LayerHome":
            refuse(f"the Home window didn't open (top: {top()})")
    tabs = [b for b in data("buttons")["buttons"] if b["name"].startswith("ButtonTab") and b["text"].strip() == "Policy"]
    if not tabs:
        refuse("no Policy tab in the Home window")
    data("click", i=tabs[0]["i"], expect="Policy")
    wait_until("frames", n=10, timeout=3000)
    found, ap = rows()
    if not found:
        refuse("the Policy tab shows no policy rows")
    return found, ap


def show(found, ap):
    for name, (_, cost, on) in found.items():
        print(f"  {'[x]' if on else '[ ]'} {name}  ({cost} AP)")
    print(f"admin points {ap}")


def main():
    setup()
    args = [a for a in sys.argv[1:] if a != "--keep"]
    keep = "--keep" in sys.argv
    if args and (args[0] not in ("on", "off") or len(args) != 2):
        refuse(__doc__.split("usage:")[1].split("Exit")[0].strip())
    found, ap = open_tab()
    if not args:
        show(found, ap)
    else:
        want_on, name = args[0] == "on", args[1]
        if name not in found:
            refuse(f"no policy named {name!r} (names are exact): " + ", ".join(found))
        i, cost, on = found[name]
        if on == want_on:
            print(f"{name} is already {'on' if on else 'off'}")
        else:
            # The click comes straight after the listing it indexes (no other bridge call between),
            # and bridge 0.25.0 refuses it if row i no longer shows this name.
            data("click", i=i, expect=name)
            wait_until("frames", n=10, timeout=3000)
            after, ap2 = rows()
            changed = [n for n in after if n in found and after[n][2] != found[n][2]]
            show(after, ap2)
            if changed == [name]:
                print(f"{name} switched {'on' if want_on else 'off'} (admin points {ap} -> {ap2})")
            elif not changed:
                refuse(f"{name} didn't change: the game refused it (admin points {ap}, cost {cost})")
            else:
                stop(f"other rows changed: {', '.join(changed)} (wanted only {name}); fix them by name")
    if not keep:
        close_all(lambda *_: None)


if __name__ == "__main__":
    main()
