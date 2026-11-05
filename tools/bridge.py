"""Client for the ElinBridge mod (127.0.0.1:47323). One JSON line out, one back.

usage: python -I tools/bridge.py <op> [args]
  ping                      bridge version and frame counter
  state                     player, zone, visible creatures, message log, open layers, dialog
  buttons [--all] [text=T] [name=N] [card=C]
                            clickable buttons in the top UI layer (or everywhere); the filters
                            are substrings and keep the full listing's indices (0.23.0)
  closetop                  close the top UI layer as its own close button does
  shiftclick N              the game's quick move of inventory slot N into the open container
  drag I J [N]              drag slot I onto slot J (a hotbar slot, a picker's ing1, a crafter)
  altitude [D]              the placement height for the next Place (wall-mounted items)
  speed [1|2|3]             the game's own speed control (a hotbar's changeSpeed shortcut): x1, x2, x5; no index reads it (0.38.0)
  places [R]                world map: known places within R with distance and danger
  power                     my attacks, defense and resists as the game computes them
  actions                   every EAction name the input layer knows
  boxcfg [priority=N] [allow=food,weapon|all] [norotten=1] ["name=X"] [bag=CARRIED]
                            an open container's distribution settings (shared-box routing)
  cells DX,DZ ...           several `cell` reads in one call (0.23.0)
  wait [until=idle|zone|layer|moved|frames] [n=N] [timeout=MS]
                            the reply comes when the condition holds (ok, done=true) or at the
                            timeout (done=false): no sleep-and-poll loops (0.23.0)
  walkto X Z [r=4] [hp=60] [timeout=MS] [stairs=1] [weakok=1]
                            goto with the reply on arrival, or when the walk stops short, a
                            hostile comes within r (the walk is cancelled), HP falls under hp%,
                            a window opens or the zone changes; a stairway target needs stairs=1
  texts [--all] [--full]    visible text in the top UI layer (or everywhere); --full: no
                            200-character cut (letters, books)
  cancel                    stop my running task (training, fishing) as a click/Wait does
  find NAME [R] [N]         things, objects and visible creatures by name on the explored map
  sources [TABLE [OFF [N]]] the game's data tables (no TABLE: names and sizes); kb.py uses it
  click N [expect=T]        click button N from the last `buttons` listing; with expect=, refused
                            unless button N's text (or card) still contains T (0.25.0: any tool's
                            `buttons` call replaces the listing, run 14's Policy tab)
  rclick N [expect=T]       right-click button N (abilities: use); `buttons` marks these [R]
  hover N                   show button N's tooltip as a mouse hover would; then `tip`
  tip                       the text of the tooltip(s) on screen
  cell DX DZ                what an explored cell holds: floor, wall, object, things; the floor's and
                            block's material, hardness and reqHarvest (0.31.0)
  skills                    every skill on the sheet with its level (0.31.0)
  witness [R]               who could witness a hostile act (mining in a town): the creatures I see
                            within R (default 6) and the cells in line of sight I can't see (0.31.0)
  choose N                  pick dialog choice N
  act ACTION [frames]       inject a game action: Wait Interact Search Pick Fire Use Confirm
                            Cancel MenuInventory MenuChara MenuJournal MenuAbility GetAll ...
  move DIR [frames]         step by SCREEN direction: n s e w ne nw se sw
  step DX DZ                step by MAP delta (each -1..1); +x = screen SE, +z = screen NE
  goto X Z                  auto-walk to an explored map cell (the game's own pathing)
  map [R]                   ASCII map of explored cells within R (default 8)
  inv                       the player's inventory (top level)
  terrain [R] [WANT] [N]    world map: tile counts by biome/alias within R, and the N nearest
                            tiles matching WANT ("beach", "Sand", "Forest") with road distance and
                            the danger a field there gets (0.20.0)
  acts DX DZ [all|left|key] the game's own action list for the cell at map delta DX,DZ, as
                            the context menu (all, default), a left click or a keypress sees it
  do N                      perform act N from the last `acts` (as the context menu does)
                            mode `right` lists what the held item / hotbar tool does there
  invacts N                 right-click menu of inventory slot N (open the inventory with
                            `act MenuInventory`, then `buttons`; slots show [item name])
  invdo K                   perform entry K of the last `invacts`
  winbtn [NAME]             an open inventory window's header buttons (shown only on hover):
                            no NAME lists them; buttonShared toggles a container's share lock
  anykey                    "press any key" (intros, waits)
  load ID                   from the title screen, load the LOCAL save ID (e.g. world_2).
                            Never loads a cloud save and never changes the cloud setting.
  autocombat UID            fight that creature through the game's own auto-combat (0.26.0):
                            a lethal hit on anyone healthy at its start leaves them at 0 HP once
  abortcombat               stop the auto-combat
  quit                      save, then exit Elin through the game's own Quit (refuses if the
                            save fails). Runs only under the user's allow rule (see CLAUDE.md).
Exit code 1 when the bridge answers ok=false, 2 when it is not reachable.
World ops (goto, move, step, do, walkto) are refused by the bridge while a dialog or pop-up is
open ("window open: LayerX"); read it with talk.py, or read.py then close.py.
"""
import json
import re
import socket
import sys

ADDR = ("127.0.0.1", 47323)


# One connection per process: a socket per call ran out of local ports (run 03). Since bridge
# 0.23.0 the mod serves each client on its own thread, so a held connection no longer blocks the
# tools this process launches; close() before a subprocess is still the polite default
# (common.run does it), and a request the client stopped waiting for is dropped, never run late.
_conn = None


def norm(s):
    """An item name for matching: lower case, with a stack's plural read as the singular ("3 scrolls of
    teleport" -> "3 scroll of teleport"). Run 08: item.py "scroll of teleport" missed the stack of 3 in
    an ambush. Apply it to both the wanted name and the card."""
    return re.sub(r"(\w)s of ", r"\1 of ", (s or "").lower())


def close():
    global _conn
    if _conn is not None:
        try:
            _conn[0].close()
        except OSError:
            pass
        _conn = None


# World actions do nothing while a dialog or pop-up is open, and that fails silently (run 04:
# a tutorial dialog swallowed several gotos and talks; the user asked for an alert). The bridge
# refuses them itself since 0.23.0 ("window open: LayerX"); until then this client sent a
# `state` before each one, which doubled the round trips. The alert is kept here.
QUIET_LAYERS = {None, "LayerInventory"}


def blocking_window():
    st = _send("state", {})
    top = ((st.get("data") or {}).get("layers") or {}).get("top")
    return None if top in QUIET_LAYERS else top


GUARD_PREFIXES = ("window open", "context menu open", "drama open", "a return is pending", "Squashed")


def call(op, **kw):
    reply = _send(op, kw)
    err = reply.get("error") or ""
    if not reply.get("ok") and err.startswith("window open"):
        print(f"!! {err[len('window open: '):]} is open: the game ignores '{op}' until it's read and "
              f"closed (talk.py for dialogs, read.py then close.py for reports)", file=sys.stderr)
    elif not reply.get("ok") and err.startswith(GUARD_PREFIXES):
        # bridge 0.30.0's guard (the review of 2026-10-23): the op was refused, nothing ran
        print(f"!! '{op}' refused by the bridge: {err}", file=sys.stderr)
    return reply


def _send(op, kw):
    """One request. Reconnects and resends once only when the message could not be delivered
    (the connection was dead); a request that was delivered is never resent (run 12 review: a
    click resent after a slow frame fired twice). Deferred ops wait for their own timeout."""
    global _conn
    msg = (json.dumps({"op": op, **kw}) + "\n").encode("utf-8")
    wait_s = (min(max(int(kw.get("timeout") or 15000), 1000), 180000) + 1000) / 1000 + 5
    for attempt in (0, 1):
        try:
            if _conn is None:
                s = socket.create_connection(ADDR, timeout=20)
                _conn = (s, s.makefile("r", encoding="utf-8"))
            _conn[0].settimeout(wait_s)
            _conn[0].sendall(msg)
        except OSError:
            close()
            if attempt:
                raise
            continue
        try:
            line = _conn[1].readline()
        except OSError as e:
            close()
            raise OSError(f"no answer from the bridge within {wait_s:.0f}s ({e}); the request was "
                          "not resent") from e
        if line:
            return json.loads(line)
        # the server closed the socket before answering (a game crash or a dead client thread):
        # nothing ran, so one fresh attempt is safe
        close()
        if attempt:
            raise OSError("bridge closed the connection")


def main(argv):
    if not argv:
        sys.exit(__doc__)
    op, rest = argv[0], argv[1:]
    kw = {}
    def keyed(names, ints=(), bools=()):
        """k=v arguments: ints parsed, bools true for 1/true/yes; unknown keys are an error."""
        for a in rest:
            if a.startswith("--") or "=" not in a:
                continue
            k, _, v = a.partition("=")
            if k not in names:
                sys.exit(f"unknown argument {k}= for {op}; expected " + ", ".join(names))
            kw[k] = int(v) if k in ints else (v.lower() in ("1", "true", "yes") if k in bools else v)

    if op == "spguard":  # the stamina guard: no argument reads it; floor=-1 turns it off, floor=3 is the default
        keyed(("floor",), ints=("floor",))
    elif op in ("buttons", "texts"):
        kw["all"] = "--all" in rest
        if "--full" in rest:
            kw["max"] = 100000
        keyed(("text", "name", "card"))
    elif op == "cells":
        kw["cells"] = [[int(v) for v in a.split(",")] for a in rest if "," in a]
    elif op == "wait":
        keyed(("until", "n", "timeout", "zone", "layer"), ints=("n", "timeout"))
    elif op == "cast":  # 0.33.0 (run 28): cast spell=arrow_Cold uid=N (no uid: myself)
        keyed(("spell", "uid"), ints=("uid",))
    elif op == "pick":  # 0.35.0 (run 31): pick uid=N, a loose thing on my own cell (twinkled medals)
        keyed(("uid",), ints=("uid",))
    elif op == "walkto":
        kw["x"], kw["z"] = int(rest[0]), int(rest[1])
        keyed(("r", "hp", "timeout", "stairs", "weakOk", "weakok"), ints=("r", "hp", "timeout"), bools=("stairs", "weakOk", "weakok"))
        if "weakok" in kw:
            kw["weakOk"] = kw.pop("weakok")
    elif op == "find":
        kw["name"] = rest[0]
        if len(rest) > 1:
            kw["r"] = int(rest[1])
        if len(rest) > 2:
            kw["n"] = int(rest[2])
    elif op in ("click", "rclick"):
        if not rest or not rest[0].lstrip("-").isdigit():
            sys.exit(f"{op} needs a button index first (got {rest[:1]}): list `buttons` again")
        kw["i"] = int(rest[0])
        rest = rest[1:]
        keyed(("expect",))
    elif op in ("shiftclick", "choose", "hover"):
        kw["i"] = int(rest[0])
    elif op == "altitude":
        kw["d"] = int(rest[0]) if rest else 0
    elif op == "speed":
        if rest:
            kw["i"] = int(rest[0])
    elif op == "boxcfg":  # boxcfg [priority=N] [allow=food,drink|all] [norotten=1|0] ["name=X"] (open box)
        keyed(("priority", "allow", "norotten", "name", "bag"), ints=("priority",), bools=("norotten",))
        if "norotten" in kw:
            kw["noRotten"] = kw.pop("norotten")
    elif op == "drag":
        kw["i"], kw["j"] = int(rest[0]), int(rest[1])
        if len(rest) > 2 and rest[2].lstrip("-").isdigit():  # run 25: `drag I J force=1` is not a count
            kw["n"] = int(rest[2])
    elif op == "act":
        kw["action"] = rest[0]
        if len(rest) > 1:
            kw["frames"] = int(rest[1])
    elif op == "move":
        kw["dir"] = rest[0]
        if len(rest) > 1:
            kw["frames"] = int(rest[1])
    elif op == "step":
        kw["dx"], kw["dz"] = int(rest[0]), int(rest[1])
    elif op == "goto":
        kw["x"], kw["z"] = int(rest[0]), int(rest[1])
    elif op == "map" and rest:
        kw["r"] = int(rest[0])
    elif op == "load":
        kw["id"] = rest[0]
    elif op == "quit":
        # run 22: run 21 quit at 00:55 although the user had said at 22:03 "keep at it for the next 5
        # hours" (a rule already in memory). `session_end.py` writes the window's end; quit waits for it
        # unless --early-ok (the user said stop, or a reload: rebuild the mod, a hang)
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent))  # python -I leaves tools/ off the path
        from session_end import ends_at
        end = ends_at()
        if end and "--early-ok" not in rest:
            sys.exit(f"refused: the user's play window runs until {end:%H:%M}; play on, or --early-ok "
                     "when the user said to stop or a reload needs it")
        # run 33: the close-out quit at 14:24 of a window to 16:10 on my own call (--early-ok, "food out, the crew worn"),
        # and the user asked why the game was restarted. --early-ok now names its reason: 'user: "QUOTE"' (their words in
        # chat) or 'reload: WHY' (a mod rebuild, a hang); anything else is refused, and the reason goes to activity.csv
        if end and "--early-ok" in rest:
            i = rest.index("--early-ok")
            why = rest[i + 1] if i + 1 < len(rest) else ""
            if not why.startswith(("user:", "reload:")):
                sys.exit(f"refused: --early-ok before {end:%H:%M} needs a reason: --early-ok 'user: \"their words\"' or "
                         "--early-ok 'reload: why' (run 33: an early close-out on my own call)")
            import datetime
            log = Path(__file__).resolve().parent.parent / "runs" / "early_quits.csv"
            new = not log.exists()
            with log.open("a", encoding="utf-8") as f:
                if new:
                    f.write("quit_at,window_end,reason\n")
                f.write(f'{datetime.datetime.now():%Y-%m-%d %H:%M},{end:%Y-%m-%d %H:%M},"{why.replace(chr(34), chr(39))}"\n')
    elif op == "cell":
        kw["dx"], kw["dz"] = int(rest[0]), int(rest[1])
    elif op == "witness" and rest:
        kw["r"] = int(rest[0])
    elif op == "places" and rest:
        kw["r"] = int(rest[0])
    elif op == "terrain":
        if rest:
            kw["r"] = int(rest[0])
        if len(rest) > 1:
            kw["want"] = rest[1]
        if len(rest) > 2:
            kw["n"] = int(rest[2])
    elif op == "acts":
        kw["dx"], kw["dz"] = int(rest[0]), int(rest[1])
        if len(rest) > 2:
            kw["mode"] = rest[2]
    elif op in ("do", "invacts", "invdo"):
        kw["i"] = int(rest[0])
    elif op == "ride":  # ride UID | ride off  (bridge 0.31.6: mount a party member beside me; home work only)
        if rest and rest[0] == "off":
            kw["off"] = True
        elif rest:
            kw["uid"] = int(rest[0])
    elif op == "autocombat":  # autocombat UID [TACTICS]  (warrior, archer, ...: the Strategy dropdown)
        kw["uid"] = int(rest[0])
        if len(rest) > 1:
            kw["tactics"] = rest[1]
    elif op == "sources" and rest:
        kw["table"] = rest[0]
        if len(rest) > 1:
            kw["offset"] = int(rest[1])
        if len(rest) > 2:
            kw["limit"] = int(rest[2])
    elif op == "input":  # input TEXT: the open text dialog (Change name), then click its OK
        kw["text"] = " ".join(rest)
    elif op == "winbtn":
        kw["name"] = rest[0] if rest else ""
    elif op == "menu":  # menu | menu N | menu text=Sleep | menu close=1  (the open context menu, bridge 0.30.0)
        if rest and rest[0].isdigit():
            kw["i"] = int(rest[0])
        keyed(("text", "close"), bools=("close",))
    if op == "load":
        kw.setdefault("timeout", 60000)  # Game.Load is synchronous: a slow load looked "dropped" at 15 s
    if any(a in ("force=1", "force=true", "--force") for a in rest):
        kw["force"] = True  # bridge 0.30.0: past the busy guard (a window, a menu, a pending return)
    try:
        reply = call(op, **kw)
    except OSError as e:
        why = "it did not answer in time" if "no answer" in str(e) else "is Elin running with the mod?"
        print(f"bridge not reachable at {ADDR[0]}:{ADDR[1]} ({why}): {e}", file=sys.stderr)
        sys.exit(2)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if op == "map" and reply.get("ok"):
        d = reply["data"]
        print(d["origin"], "|", d["screen"])
        print(d["legend"])
        print("\n".join("|" + row + "|" for row in d["rows"]))
    elif op == "buttons" and reply.get("ok"):
        d = reply["data"]
        print("scope:", d["scope"])
        for b in d["buttons"]:
            card = f" [{b['card']}]" if b.get("card") else ""
            tip = f" (tip: {b['tip']})" if b.get("tip") else ""
            path = f"  <{b['path']}>" if b.get("path") else ""
            rc = " [R]" if b.get("rclick") else ""
            ing = f" (needs {b['ing']})" if b.get("ing") else ""
            chk = " [x]" if b.get("checked") else ""
            print(f"{b['i']:3} {b['name']} | {b['text']}{chk}{card}{ing}{tip}{rc}{path}")
    elif op == "terrain" and reply.get("ok"):
        d = reply["data"]
        print("me", d["me"], "here:", d["here"])
        print("counts:", ", ".join(f"{k} {v}" for k, v in d["counts"].items()))
        for h in d["hits"]:
            flags = (" blocked" if h["blocked"] else "") + (" road" if h["isRoad"] else "")
            print(f"  ({h['dx']:+d},{h['dz']:+d}) d{h['dist']} {h['biome']}/{h['alias']} road {h['road']} danger {h['danger']}{flags}")
    elif op == "places" and reply.get("ok"):
        d = reply["data"]
        print("me", d["me"], "(map deltas: +x screen east, +z screen north on the world map; check)")
        for p in d["places"]:
            tag = (" town" if p["town"] else "") + (" known" if p["known"] else "")
            print(f"  ({p['dx']:+d},{p['dz']:+d}) d{p['dist']} {p['name']} [{p['id']}] danger {p['danger']}{tag}")
        for t in d.get("treasure") or []:
            print(f"  treasure ({t['dx']:+d},{t['dz']:+d}) d{t['dist']} {t['name']} Lv{t['lv']} {t['blessed']}: dig here with a shovel")
    elif op == "skills" and reply.get("ok"):
        for k, v in reply["data"]["skills"].items():
            exp = f"  exp {v['exp']}/{v['next']} pot {v['potential']}" if "exp" in v else ""
            print(f"  {k:18} {v['lv']:4} (base {v['base']})  {v['name']}{exp}")
    elif op == "witness" and reply.get("ok"):
        d = reply["data"]
        print(f"me {d['me']} r {d['r']} law {d['zoneLaw']}: {len(d['creatures'])} creatures seen, "
              f"{d['blindCells']} cells in sight but unseen {d['blindSample']}")
        for c in d["creatures"]:
            tags = [t for t in ("witness", "canWitness", "guard", "sleeping", "faction", "los") if c.get(t)]
            print(f"  {c['name']} [{c['id']}] d{c['dist']} ({c['dx']:+d},{c['dz']:+d}) {' '.join(tags)}")
    elif op == "inv" and reply.get("ok"):
        for i in reply["data"]["items"]:
            eq = " [worn]" if i["equipped"] else ""
            eq += " [lost property]" if i.get("lostProperty") else ""
            eq += f" [locked Lv{i['lockLv']}]" if i.get("lockLv") else ""
            print(f"{i['id']:16} {i['name']}{eq}")
    elif op == "hover" and reply.get("ok"):
        print("\n".join(reply["data"]["texts"]) or "(no tooltip text)")
    elif op == "acts" and reply.get("ok"):
        d = reply["data"]
        print("cell", d["cell"], "-", len(d["acts"]), "acts")
        for a in d["acts"]:
            print(f"{a['i']:3} {a['text']}  ({a['act']})")
    elif op == "invacts" and reply.get("ok"):
        d = reply["data"]
        print(d["item"], "-", len(d["acts"]), "acts")
        for a in d["acts"]:
            print(f"{a['i']:3} {a['text']}")
    elif op in ("wait", "walkto") and reply.get("ok"):
        d = reply["data"]
        extra = f" hostile {d['hostile']} Lv{d.get('hostileLv')} at {d.get('hostileDist')}" if d.get("hostile") else ""
        print(f"{d['why']}: at {d['x']},{d['z']} HP {d['hp']}/{d['maxHp']} after {d.get('frames')} frames; "
              f"zone {d['zone']}; top {d['top']}; ai {d['ai']}{extra}")
    elif op == "cells" and reply.get("ok"):
        for i, c in enumerate(reply["data"]["cells"]):
            if not c:  # run 14: absolute coordinates by mistake; the cell is off the map
                print(f"{','.join(map(str, kw['cells'][i])) if i < len(kw.get('cells') or []) else '?'}: off the map (cells takes DX,DZ deltas)")
                continue
            print(f"{c['cell']}: floor {c.get('floor')}, obj {c.get('obj')}, things {c.get('things')}"
                  + (" watered" if c.get("watered") else "") + (" blocked" if c.get("blocked") else ""))
    else:
        print(json.dumps(reply, indent=1, ensure_ascii=False))
    sys.exit(0 if reply.get("ok") else 1)


if __name__ == "__main__":
    main(sys.argv[1:])
