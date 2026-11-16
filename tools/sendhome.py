"""Send every party member home: walk beside it, Talk, "Wait at your home", close (fact #1435).

Solo is the rule since run 38, and Lonely Soul pays +3% max HP and speed per empty party slot. The snow putits join
the party at home on their own (run 48: max HP 358 -> 342; run 49: 396 -> 363 with two of them, unseen through four
conquests). leave.py calls this at home before it lets me go (--party-ok keeps a member on purpose).

usage: python -I tools/sendhome.py [--dry]
Exit 0 the party is empty, 1 refused (a member not in view, no Talk, no "Wait at your home"), 2 the bridge.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, refuse, run, setup, walk_beside  # noqa: E402


def main():
    setup()
    dry = "--dry" in sys.argv
    for _ in range(6):
        s = call("state")["data"]
        party = s.get("party") or []
        if not party:
            print(f"party empty; max HP {s['pc']['maxHp']}")
            return 0
        if dry:
            print("party: " + ", ".join(f"{p['name']} Lv{p['lv']}" for p in party))
            return 0
        seen = {x.get("uid"): x for x in s.get("nearby") or []}
        pick = next((p for p in party if p["uid"] in seen), None)  # the one in view first
        if pick is None:
            refuse("party members not in view: " + ", ".join(f"{p['name']} at {p.get('dist')}" for p in party))
        me, c = s["pc"], seen[pick["uid"]]
        walk_beside(me["x"] + c["dx"], me["z"] + c["dz"], weak_ok=True)
        s = call("state")["data"]
        c = next((x for x in s.get("nearby") or [] if x.get("uid") == pick["uid"]), None)
        if c is None:
            refuse(f"{pick['name']} walked out of view")
        acts = call("acts", dx=c["dx"], dz=c["dz"], mode="all")["data"]["acts"]
        talk = [a for a in acts if a["text"].startswith("Talk")]
        if not talk:
            refuse(f"no Talk act on {pick['name']}: {[a['text'] for a in acts]}")
        call("do", i=talk[0]["i"])
        time.sleep(0.8)
        out = run("talk.py", "5", timeout=60)
        home = next((b for b in call("buttons")["data"]["buttons"] if "Wait at your home" in (b.get("text") or "")), None)
        if not home:
            run("close.py", timeout=30)
            refuse(f"{pick['name']} offers no 'Wait at your home': {str(out)[-200:]}")
        call("click", i=home["i"], expect="Wait at your home")
        time.sleep(0.6)
        run("talk.py", "5", timeout=60)
        run("close.py", timeout=30)
        print(f"{pick['name']} Lv{pick['lv']}: sent home")
    refuse("the party didn't empty in six tries")


if __name__ == "__main__":
    sys.exit(main())
