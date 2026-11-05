"""Advance an open dialog with Confirm, printing each new line, until it offers
choices, closes, or `max` steps pass. Never picks a choice itself.

Choices are listed as the dialog's own buttons with their `click` index. The
bridge's drama choice list can be stale (run 02); the buttons are what's on screen.

usage: python -I tools/talk.py [max_steps]
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402

NOT_CHOICES = {"ScreenlockDefault(Clone)", "Portrait"}


def drama():
    d = call("state")["data"]
    return d.get("drama"), (d.get("layers") or {}).get("top")


def choice_buttons():
    r = call("buttons", all=False)
    if not r.get("ok") or r["data"]["scope"] != "LayerDrama":
        return []
    return [b for b in r["data"]["buttons"] if b["name"] not in NOT_CHOICES and b["text"]]


def main():
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    last = None
    z0 = call("state")["data"].get("zone")  # Start Run 1: a new game's intro plays before there's a map, so no zone yet
    zone0 = z0["full"] if isinstance(z0, dict) else z0
    for _ in range(steps):
        dr, top = drama()
        if not dr and top == "LayerDrama":
            # Tutorial pop-ups (Nerun), and some choice screens, keep LayerDrama on top
            # without an active drama.
            texts = call("texts", all=False)["data"]["texts"]
            choices = choice_buttons()
            labels = {c["text"].split(" | ")[0] for c in choices}
            text = " / ".join(t for t in texts if t not in labels and not t.rstrip(".").isdigit())
            if text != last:
                print("»", text)
                last = text
            if choices:
                for c in choices:
                    print(f"  click {c['i']}: {c['text'].split(' | ')[0]}")
                return
            call("act", action="Confirm")
            time.sleep(1.0)
            continue
        if not dr:
            time.sleep(1.0)  # a quest dialog can move you to another map as it ends
            z = call("state")["data"].get("zone")
            zone = z["full"] if isinstance(z, dict) else z
            print(f"[dialog closed; top layer: {top}; zone: {zone}]")
            if zone != zone0:
                print(f"!! ZONE CHANGED: {zone0} -> {zone} (danger {z.get('danger') if isinstance(z, dict) else '?'})"
                      " - the dialog moved you; run look.py before anything else")
            return
        choices = choice_buttons()
        # The dialog's text block repeats the choice labels; print only the speech.
        labels = {c["text"].split(" | ")[0] for c in choices}
        text = " / ".join(t for t in dr["text"] if t not in labels and not t.rstrip(".").isdigit())
        if text != last:
            print("»", text)
            last = text
        if choices:
            for c in choices:
                print(f"  click {c['i']}: {c['text'].split(' | ')[0]}")
            return
        call("act", action="Confirm")
        time.sleep(1.0)
    print("[stopped: step limit]")


if __name__ == "__main__":
    main()
