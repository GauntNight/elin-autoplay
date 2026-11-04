"""The Dishes box's share lock (run 19, the user's rule after run 18; facts #685-#686).

Residents eat prepared food from shared boxes. While I'm on the home map there is no free meal, so
the Dishes box must be shared. While I'm away the game feeds them free only if no shared box holds
prepared food; a stocked box just gets eaten down. So leave.py unshares the box on the way out, and
arrive.py shares it again on the way in.

usage: python -I tools/dishes.py [share|unshare|status]
  status (the default) prints the lock and what the box holds; share/unshare set it, read it back
  from the game (Thing.IsSharedContainer, through boxcfg) and close the window.
Exit: 0 done (the box is as asked), 1 refused (not at home, bad argument), 2 the bridge,
3 stopped (the box couldn't be opened or the lock didn't change).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from box import open_at  # noqa: E402
from close import close_all  # noqa: E402
from common import contents, data, refuse, setup, stop  # noqa: E402
import home  # noqa: E402


def shared():
    return bool(data("boxcfg")["shared"])


def main():
    setup()
    want = (sys.argv[1:] or ["status"])[0]
    if want not in ("share", "unshare", "status"):
        refuse("usage: dishes.py [share|unshare|status]")
    if not data("state")["zone"]["full"].startswith("Zone_startSite"):
        refuse("not at home: the Dishes box is in the Kitchen")
    x, z = home.DISH_BOX
    why = open_at(x, z)
    if why:
        stop(f"Dishes box: {why}")
    try:
        was = shared()
        held = contents()
        if want != "status" and was != (want == "share"):
            data("winbtn", name="buttonShared")
            if shared() != (want == "share"):
                stop(f"Dishes box: the share lock didn't change (still {'shared' if was else 'private'})")
        now = shared()
    finally:
        close_all(lambda *_: None)
    change = "" if want == "status" or was == now else f" (was {'shared' if was else 'private'})"
    print(f"Dishes box {x},{z}: {'shared' if now else 'private'}{change}; holds "
          + (", ".join(held) or "nothing"))


if __name__ == "__main__":
    main()
