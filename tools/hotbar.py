"""The toolbelt hotbar as storage: its slots are pack items on grid row 1 (WidgetCurrentTool
reads pc.things with invY == 1), so they don't use the backpack grid's slots (the user's tip,
run 04). Moves go through the bridge's `drag` op, the game's own drop transaction.

usage: python -I tools/hotbar.py                 list the slots on this page
       python -I tools/hotbar.py ITEM [ITEM ...]  put each item on an empty slot
       python -I tools/hotbar.py --take ITEM      move it back into the backpack grid
       python -I tools/hotbar.py --deselect       empty the hands: a selected slot is the held item
                                                  (right-click then means Place/Throw, not Collect)
Good hotbar residents: the Putit In Amber, the bow, potions, teleport scrolls, the pickaxe,
the Cooler Box: things used often or carried always. Bridge 0.14.1+.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call, norm  # noqa: E402


def buttons():
    from common import open_inventory
    return open_inventory()  # run 17: the injected key stopped working; the hotbar button opens it


def hot(bs):
    return [b for b in bs if "WidgetCurrentTool/Slots" in (b.get("path") or "")]


def grid(bs):
    return [b for b in bs if "UIInventory/List" in (b.get("path") or "") and b["name"].startswith("ButtonGrid")]


def held():
    return call("state")["data"]["pc"]["held"]


def deselect():
    """Empty the hands of a hotbar item. A bridge click on the selected slot picks the item up
    (a drag; LayerRegisterHotbar opens), and Cancel drops it back into its slot unselected
    (run 05: the only way found; the widget's SubButton didn't do it)."""
    h = held()
    if not h:
        return True
    # The game's own EmptyHand action (an EAction) does it in one step (run 05)
    call("act", action="EmptyHand")
    time.sleep(0.4)
    if held() is None:
        return True
    slot = [b for b in hot(call("buttons", all=True)["data"]["buttons"]) if b.get("card") == h]
    if not slot:
        return False
    call("click", i=slot[0]["i"])
    time.sleep(0.6)
    call("act", action="Cancel")
    time.sleep(0.8)
    return held() is None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--deselect" in sys.argv:
        h = held()
        print(f"held {h!r} -> " + ("hands empty" if deselect() else f"still {held()!r}"))
        return
    take = "--take" in sys.argv
    items = [a for a in sys.argv[1:] if a != "--take"]
    bs = buttons()
    if not items:
        # the widget lists slots right to left: the last button is slot 1
        print(" | ".join(f"{n}:{b.get('card') or '-'}" for n, b in enumerate(reversed(hot(bs)), 1)))
        return
    for it in items:
        bs = buttons()
        if take:
            src = [b for b in hot(bs) if norm(it) in norm(b.get("card"))]
            dst = [b for b in grid(bs) if not b.get("card")]
        else:
            src = [b for b in grid(bs) if norm(it) in norm(b.get("card")) and b.get("in") == "pack"]
            dst = [b for b in reversed(hot(bs)) if not b.get("card")]
        if not src:
            print(f"{it}: not {'on the hotbar' if take else 'in the backpack'}")
            continue
        if not dst:
            print(f"{it}: no empty {'backpack' if take else 'hotbar'} slot")
            continue
        r = call("drag", i=src[0]["i"], j=dst[0]["i"])
        print(f"{it}: " + (f"moved {r['data']['dragged']}" if r.get("ok") and r["data"].get("accepted") else str(r.get("error") or r)))
        time.sleep(0.5)
    print(" | ".join(f"{n}:{b.get('card') or '-'}" for n, b in enumerate(reversed(hot(buttons())), 1)))


if __name__ == "__main__":
    main()
