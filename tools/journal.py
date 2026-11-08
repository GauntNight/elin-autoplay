"""Read the journal (run 33: opened by hand five times for the guild ranks and Gold Beneath's step). The
injected MenuJournal key does nothing after a restart (run 15); the hotbar's own Journal button (a
HotItemLayer whose hover tip reads "Journal") opens LayerJournal. The Quests tab lists the main quests and
the four guild entries; an entry's text shows under "Quests in progress".

usage: python -I tools/journal.py guilds          the four guilds: rank, contribution, salary
       python -I tools/journal.py list            every entry on the Quests tab (run 44: G52 needed the
                                                  story's open quests, and an entry's name had to be guessed)
       python -I tools/journal.py "Gold Beneath"  one entry's text
Exit 0, 1 refused (no Journal button), 3 stopped (a window already open).
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, data, ready, refuse, run, stop, wait_until  # noqa: E402
from job import JOBS  # noqa: E402

GUILDS = ("Fighters Guild", "Mages Guild", "Thieves Guild", "Merchants Guild")


def open_journal():
    for b in data("buttons", all=True).get("buttons") or []:
        if b.get("hot") == "HotItemLayer":
            tip = (call("hover", i=b["i"]).get("data") or {}).get("texts") or [""]
            if tip[0] == "Journal":
                data("buttons", all=True)  # the listing a click is checked against
                call("click", i=b["i"])
                wait_until("layer", timeout=3000)
                time.sleep(0.5)
                return True
    return False


def entry_text(label):
    """Click the Quests entry whose text holds `label`; the window's text after it."""
    bs = data("buttons").get("buttons") or []
    hit = [b for b in bs if "ButtonGeneral" in (b.get("name") or "") and label.lower() in (b.get("text") or "").lower()]
    if not hit:
        return None
    call("click", i=hit[0]["i"], expect=label)
    time.sleep(0.4)
    out = run("read.py")
    m = re.search(r"Quests in progress\n(.*)", out, re.S)
    return (m.group(1) if m else out).strip()


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    want = args[0] if args else "guilds"
    # run 42: read during a circuit, its window stopped the evacuation
    if (JOBS / "circuit.json").exists() and "--force" not in sys.argv:
        refuse("a circuit is running: this window would stop its next step. Read it when the circuit ends (--force if runs/jobs/circuit.json is left over)")
    why = ready(hp=None, hunger=None, hostiles=False)
    if why:
        stop(why)
    if not open_journal():
        refuse("no Journal button on the hotbar (buttons --all)")
    try:
        if want == "guilds":
            for g in GUILDS:
                t = entry_text(g) or ""
                rank = re.search(r"Rank \d+ \([^)]*\)", t)
                contrib = re.search(r"Contribution: [\d,]+ / [\d,]+", t)
                salary = re.search(r"Salary: [^\n]+", t)
                print(f"{g}: {rank.group(0) if rank else '?'}; {contrib.group(0) if contrib else '?'}; {salary.group(0) if salary else ''}")
        elif want == "list":
            bs = data("buttons").get("buttons") or []
            names = [(b.get("text") or "").strip() for b in bs if "ButtonGeneral" in (b.get("name") or "")]
            for n in names:
                if n:
                    print(n)
            if not any(names):
                print("(no entries listed: the Quests tab may not be the one open)")
        else:
            t = entry_text(want)
            if t is None:
                refuse(f"no journal entry matching {want!r}")
            print("\n".join(ln for ln in t.splitlines()[:12] if ln.strip()))
    finally:
        run("close.py")


if __name__ == "__main__":
    main()
