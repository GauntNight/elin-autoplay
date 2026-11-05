"""Close the top window safely, the right way for its type, and never leave the System menu
open. A blind `act Cancel` is dangerous: when nothing (or only a container window) is open it
opens the System context menu (Save / Load / To Title / Quit), which stays open (run 03).

  LayerInventory (box, shop, package) -> the inventory key (MenuInventory) toggles them shut
  LayerPause, LayerRegisterHotbar     -> the bridge's closetop (no key reaches them)
  a window with a "button close"      -> click it
  dialogs, help, drag grids           -> Cancel
If the System menu appears, it is dismissed by clicking its harmless "Help" entry and then
closing the help page. Repeats until no window is open (at most 6 steps).

usage: python -I tools/close.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import top  # noqa: E402


def system_menu():
    return [b for b in call("buttons", all=True)["data"]["buttons"] if "ContextSystem" in (b.get("path") or "")]


def close_all(say=print):
    """Close windows until none is open; the System menu is dismissed through Help. Never the death prompt (Start Run 3): common.crawl_up answers that."""
    if call("state")["data"]["pc"]["hp"] <= 0:
        say("refused: HP under 0: a death prompt is answered by common.crawl_up, never closed")
        return False
    for i in range(6):
        sm = system_menu()
        if sm:
            help_ = [b for b in sm if b["text"].strip() == "Help"]
            call("click", i=help_[0]["i"])
            time.sleep(1.0)
            say("dismissed the System menu (via Help)")
            continue
        t = top()
        if not t:
            say("no window open")
            return True
        if t == "LayerInventory" and i > 0:
            # run 08: a shop's merchant chest stayed open through repeated MenuInventory toggles
            call("closetop")
        elif t == "LayerInventory":
            call("act", action="MenuInventory")
        elif t == "LayerRegisterHotbar" and i > 0:
            # It comes back while an item is still being dragged (run 05: a click on a hotbar slot
            # picked the item up, and closetop reopened it five times): Cancel ends the drag and
            # puts the item back
            call("act", action="Cancel")
        elif t in ("LayerRegisterHotbar", "LayerPause"):
            # Cancel doesn't close these (run 04); LayerPause waits for a real key press (run 05:
            # a quest instance's time limit pauses, then moves you back on close)
            call("closetop")
        else:
            close = [b for b in call("buttons")["data"]["buttons"] if b["name"] == "button close"]
            if close:
                call("click", i=close[0]["i"])
            else:
                call("act", action="Cancel")
        time.sleep(1.0)
        say(f"closed {t} -> now {top()}")
    return not system_menu() and not top()


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    close_all()
    if system_menu():
        sys.exit("the System menu is still open: dismiss it by hand")


if __name__ == "__main__":
    main()
