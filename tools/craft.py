"""Craft a recipe at a station next to the player (or with Quick Craft).

Opens the station through its own "Craft" act (or the Quick Craft ability), selects
the recipe by name, shows its ingredients and stamina cost, raises the count with
the window's own +1 button, then presses Craft. Prints the new log lines.

usage: python -I tools/craft.py STATION_DX STATION_DZ "Recipe name" [count] [--dry] [--use MATERIAL] [--force]
       python -I tools/craft.py quick "Recipe name" [count] [--dry] [--use MATERIAL] [--force]
  --use rosewood  pick the "rosewood ..." stack in every ingredient slot that offers one (the
                  screen picks a default; a slot takes a single stack, so mixed woods don't add up)
  --use rosewood,voynich  several materials: each slot takes the first one it offers (run 12:
                  a bookshelf's book slots took scrolls, which count as books)
  --force         craft although SP - Stamina Cost x count would end under SP_RESERVE (errors.csv
                  row 15: four arrow batches at SP 19 drove SP to -2)
Refuses (exit 1): a window open, no such recipe, --use matching nothing, the +1 or Craft button
not offered (ingredients short), the SP reserve. Stops (exit 3) mid-batch at Overweight (burden
phase 3: crafted furniture lands in the pack; run 14 ended Squashed).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import THRESHOLDS, refuse, stop, top, wait_idle, wait_until  # noqa: E402

SP_RESERVE = 5  # SP left after the batch, at least


def buttons(all_=False):
    return call("buttons", all=all_)["data"]["buttons"]


def close_window():
    """Leave nothing open: an open craft window interrupts the next task (run 03, twice)."""
    close = [b for b in buttons() if b["name"] == "button close"]
    if close:
        call("click", i=close[0]["i"])
    for _ in range(3):  # run 13: after a craft the button wasn't listed; close the layer itself
        if top() != "LayerCraft":
            break
        call("closetop")
        wait_until("frames", n=5, timeout=1000)


def plain(t):
    return re.sub(r"<[^>]+>", "", t or "").strip()


def ingredients():
    """Name the stack each slot will use: a slot takes one stack, and the default may not be the
    one meant (run 04: the hoe's stone slot)."""
    return "; ".join(f"{b['ing']} <- {b.get('card') or 'nothing'} ({plain(b['text'])})"
                     for b in buttons() if b.get("ing"))


def burden_phase():
    """pc.burdenPhase (bridge 0.30.0), else the HUD label (3 Overweight, 4 Squashed; look.py)."""
    p = call("state")["data"].get("pc") or {}
    if p.get("burdenPhase") is not None:
        return p["burdenPhase"]
    hud = call("texts", all=True)["data"]["texts"]
    labels = {"Burden": 1, "Heavy Burden": 2, "Overweight": 3, "Very Overweight": 3, "Squashed": 4}
    return max((labels[t.strip().rstrip("!")] for t in hud if t.strip().rstrip("!") in labels), default=0)


def main():
    argv = sys.argv[1:]
    use = None
    if "--use" in argv:
        k = argv.index("--use")
        use = [u.strip() for u in argv[k + 1].lower().split(",") if u.strip()]
        del argv[k:k + 2]
    args = [a for a in argv if a not in ("--dry", "--force", "--allow-default", "--burden-ok")]
    dry = "--dry" in sys.argv
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if top() not in (None, "LayerCraft"):
        sys.exit(f"a window or dialog is open ({top()}): run talk.py or close it first")
    if args[0] == "quick":
        name, rest = args[1], args[2:]
        if top() != "LayerCraft":
            ab = [b for b in buttons(True) if b.get("card") == "Quick Craft"]
            if not ab:
                call("act", action="MenuAbility")
                wait_until("layer", timeout=3000)
                ab = [b for b in buttons(True) if b.get("card") == "Quick Craft"]
            if not ab:
                # run 15: after a restart the injected MenuAbility/MenuChara/MenuJournal keys did
                # nothing; the hotbar's own "Ability" button (a HotItemLayer) opens the list
                for b in buttons(True):
                    if b.get("hot") == "HotItemLayer":
                        tip = (call("hover", i=b["i"]).get("data") or {}).get("texts") or [""]
                        if tip[0] == "Ability":
                            buttons(True)
                            call("click", i=b["i"])
                            wait_until("layer", timeout=3000)
                            break
                ab = [b for b in buttons(True) if b.get("card") == "Quick Craft"]
            if not ab:
                sys.exit("Quick Craft ability button not found")
            call("rclick", i=ab[0]["i"])
    else:
        dx, dz, name, rest = int(args[0]), int(args[1]), args[2], args[3:]
        if top() != "LayerCraft":
            acts = call("acts", dx=dx, dz=dz, mode="all")["data"]["acts"]
            # Stations name their act by trade: workbench "Craft", sawmill "Saw", ...
            verbs = ("Craft", "Saw", "Cook", "Smelt", "Process", "Carve", "Sew", "Tinker", "Blend", "Cut", "Spin", "Bake")  # run 15: the stonecutter "Cut"; run 23: the spinner "Spin"; run 28: the kiln "Bake"
            cr = [a for a in acts if a["text"].startswith(verbs)]
            if not cr:
                sys.exit("no Craft act there: " + ", ".join(a["text"] for a in acts))
            call("do", i=cr[0]["i"])
    count = int(rest[0]) if rest else 1
    if top() != "LayerCraft":
        wait_until("layer", timeout=5000)  # the craft window opens
    if top() != "LayerCraft" and args[0] == "quick":
        # run 16: inside trainday the Quick Craft click came while the player was still busy (after
        # the lockpick round) and nothing opened, two days running; wait for idle and click again
        wait_idle(timeout=10000)
        ab = [b for b in buttons(True) if b.get("card") == "Quick Craft"]
        if ab:
            call("rclick", i=ab[0]["i"])
            wait_until("layer", timeout=5000)
    if top() != "LayerCraft":
        sys.exit(f"craft window did not open (top layer {top()})")
    # Recipe names match case-insensitively (run 13: "workbench" missed the window's "Workbench").
    seen = set()

    def recipes():
        rs = [b for b in buttons() if b.get("card") and "drag text" in b["name"]]
        seen.update(b["card"] for b in rs)
        return [b for b in rs if b["card"].strip().lower() == name.strip().lower()]

    rec = recipes()
    if not rec:
        # run 11: the All tab shows one page only (the tinker's Pickaxe was off it); try each tab
        for tab in [b for b in buttons() if "ButtonTab Craft" in b["name"] and not (b.get("text") or "").startswith("All")]:
            call("click", i=tab["i"])
            wait_until("frames", n=5, timeout=1000)
            rec = recipes()
            if rec:
                break
    if not rec:
        names = sorted(seen)  # every tab's recipes, not just the last tab's (run 13)
        close_window()
        sys.exit(f"recipe {name!r} not here; recipes: {', '.join(names)}")
    call("click", i=rec[0]["i"])
    wait_until("frames", n=10, timeout=1500)  # the recipe card and its slots are rebuilt
    if use:
        # Clicking a slot opens a drop list outside the layer; pick the stack named MATERIAL.
        def stack(b):  # "6 granite stones" -> 6, "a granite stone" -> 1
            m = re.match(r"(\d+) ", b.get("card") or "")
            return int(m.group(1)) if m else 1
        from common import matches
        unsatisfied = []
        # Re-list the slots before each one (run 15): picking slot 1's material rebuilds the
        # window's buttons, so slot 2's index from a listing made before the loop was stale, its
        # click opened no drop list, and every second slot read "offered" empty (the millstone's
        # strings, the stone chest's nails).
        for k in range(len([b for b in buttons() if b.get("ing")])):
            slots = [b for b in buttons() if b.get("ing")]
            if k >= len(slots):
                break
            slot = slots[k]
            if "(Extra)" in (slot.get("text") or ""):
                continue  # optional slot (rune, scrubber): leave it empty
            call("click", i=slot["i"])
            wait_until("frames", n=5, timeout=1000)  # the drop list opens (no layer of its own)
            grid = [b for b in buttons(True) if "grid with bg" in b["name"]]
            opts = []
            for u in use:  # the first material named that this slot offers (whole-word match)
                opts = matches(u, grid)
                if opts:
                    break
            if opts:
                # the biggest matching stack: a slot takes one stack, and "a granite stone" in
                # the shared box beat the pack's 6 for a 2-stone recipe (run 04)
                call("click", i=max(opts, key=stack)["i"])
                wait_until("frames", n=5, timeout=1000)
            else:
                offered = sorted({b.get("card") for b in grid if b.get("card")})
                unsatisfied.append(f"{slot['ing']}: offered " + ", ".join(offered[:10]))
                close_drop = [b for b in buttons(True) if "grid with bg" in b["name"]]
                if close_drop:  # nothing matching: pick the current one again to close the list
                    cur = [b for b in close_drop if b.get("card") == slot.get("card")]
                    call("click", i=(cur or close_drop)[0]["i"])
                    wait_until("frames", n=5, timeout=1000)
        # Run 11 spent bag 2's threads and run 12 a carbon log because a slot nothing matched fell
        # back to the screen's default stack in silence: refuse instead (--allow-default keeps the
        # old behaviour for slots the named materials can't fill, e.g. a book slot with --use rosewood).
        if unsatisfied and "--allow-default" not in sys.argv:
            close_window()
            sys.exit(f"--use {','.join(use)} matched nothing in {len(unsatisfied)} slot(s), so the default stack "
                     "would be spent: " + " | ".join(unsatisfied) + " (name a material from the list, or --allow-default)")
    # run 23: read the cost at a count of 1, before +1 raises it: the window then shows the whole
    # batch (string x1 read 2, x6 read 12), and the old read-after-raise times the count refused a
    # 12-SP batch of six strings as 72
    texts1 = call("texts", all=False)["data"]["texts"]
    st1 = texts1[texts1.index("Stamina Cost") - 1] if "Stamina Cost" in texts1 else "?"
    for _ in range(count - 1):
        plus = [b for b in buttons() if b["text"] == "+1"]
        if not plus:  # the review of 2026-10-23: an IndexError here when the count can't be raised
            ings = ingredients()
            close_window()
            refuse(f"{name}: no +1 button (the ingredients cover fewer than {count}, or the recipe doesn't batch); needs {ings}")
        call("click", i=plus[0]["i"])
        wait_until("frames", n=3, timeout=500)
    texts = call("texts", all=False)["data"]["texts"]
    ings = ingredients()
    st = texts[texts.index("Stamina Cost") - 1] if "Stamina Cost" in texts else "?"
    print(f"{name} x{count}: needs {ings}; stamina {st}")
    # errors.csv row 15 (run 16): four arrow batches at SP 19 drove SP to -2 ("You suffer a minor
    # injury"); the cost of one craft (read at x1 above) times the count
    m = re.search(r"\d+", plain(st1)) or re.search(r"\d+", plain(st))
    sp = call("state")["data"]["pc"]["sp"]
    if m and sp - int(m.group()) * count < SP_RESERVE and "--force" not in sys.argv and not dry:
        close_window()
        refuse(f"{name} x{count} costs {int(m.group()) * count} SP and I have {sp}: under the reserve of {SP_RESERVE} "
               f"(a smaller count, rest first, or --force)")
    if dry:
        close_window()
        return
    main_btn = [b for b in buttons() if b["name"] == "ButtonMain" and b["text"] == "Craft"]
    if not main_btn:  # the review of 2026-10-23: an IndexError when the Craft button isn't offered
        close_window()
        refuse(f"{name}: no Craft button (ingredients short?); needs {ings}")
    call("click", i=main_btn[0]["i"])
    wait_until("frames", n=20, timeout=3000)  # the task starts
    # crafting runs as a task: wait for it, looking at the burden between items (run 14: crafted
    # furniture lands in the pack, and the batch ended Squashed); a cut-short batch stops (exit 3)
    deadline = (3 + count) * 4
    cut = None
    for _ in range(max(1, deadline // 3)):
        w = wait_until("idle", timeout=3000)
        if w.get("done"):
            break
        phase = burden_phase()
        # run 21: --burden-ok for a batch that lowers the weight (25 stones at 2.2 each into flams)
        if phase >= THRESHOLDS["burden_stop"] and "--burden-ok" not in sys.argv:
            call("cancel")
            wait_idle(timeout=5000)
            cut = f"burden phase {phase} (Overweight or worse): the batch was cut short; store weight first"
            break
    log = call("state")["data"].get("log") or []
    print("log:", " / ".join(log[-6:]))
    # run 13: the game keeps the craft window open after crafting, and the next tool's walk was
    # refused ("window open: LayerCraft") twice; close it here
    close_window()
    if cut:
        stop(cut)


if __name__ == "__main__":
    main()
