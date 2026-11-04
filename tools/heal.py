"""Heal a party member by throwing a healing potion at them (ActThrow, ThrowType.Potion: the
potion's drink effect lands on whoever it hits, FoodEffect.ProcDrink; a healing potion is not a
hostile act, and potions are exempt from the throw-at-party guard). Kaberg shields me and takes
the hits; run 04 lost her at 51% because nothing healed her. Adjacent, right-click offers Gift
instead: she drinks a gifted potion at once (ActPlan actGive: one from the stack, SplitHeld(1)),
even at full HP (run 04 wasted two that way), so only heal when she's hurt.

usage: python -I tools/heal.py [NAME=Kaberg] [POTION=any cure potion, strongest first] [--force]
Prints the target's HP before and after. Within throwing range only (walks closer if needed).
Run 32 (Kaberg's death on Tragedic Forest B2): delve called this every turn, the default potion (cure minor)
was none of the 12 cure major in the backpack, so each call recast Nature's Embrace (heal over time, ~12 MP)
until MP was 4 and she died. Now every cure potion kind is tried, in the pack and then in the carried bags,
and Nature's Embrace is cast at most once per member per HOT_TURNS game turns (runs/jobs/heal_hot.json).
The review of 2026-10-23: the rod and the potion are held through common.grab (whole words, never
a cursed or doomed stack: run 17's loss from the sibling tool), a rod only with charges left, the
member by common.pick (two names fitting NAME refuse), and common.ready first (a window, a dialog,
a task running: exit 3).
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import grab, grid_slots, matches, pick, ready, refuse, run, state, stop, wait_until  # noqa: E402
from unpack import put_away_held  # noqa: E402  (the inventory "Put away"; common.put_away is the hotbar deselect)

POTIONS = ("potion of cure critical wound", "potion of cure major wound", "potion of cure serious wound",
           "potion of cure minor wound")
BAGS = ("backpack", "spoils bag", "loot bag")
HOT_TURNS = 30  # Nature's Embrace heals over time: one cast a member until this many game turns have passed
HOT_FILE = Path(__file__).resolve().parent.parent / "runs" / "jobs" / "heal_hot.json"


def hold_potion(names):
    """A cure potion in hand: each name in the pack, then in each carried bag (opened by bag.py: a bag's
    slots are listed only while it is open). Returns the name held, or None."""
    for n in names:
        if grab(n, what="potion"):
            return n
    for bag in BAGS:
        run("bag.py", bag)
        for n in names:
            if grab(n, what="potion"):
                return n
    return None


def hot_allowed(uid, turn):
    """True when Nature's Embrace wasn't cast at this member within HOT_TURNS; records the cast if so."""
    try:
        last = json.loads(HOT_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        last = {}
    if 0 <= turn - last.get(str(uid), -10**9) < HOT_TURNS:
        return False
    last[str(uid)] = turn
    HOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    HOT_FILE.write_text(json.dumps(last), encoding="utf-8")
    return True


def members():
    """The party without me: state.party (bridge 0.30.0), else power's list minus its pc flag."""
    s = call("state")["data"]
    if isinstance(s.get("party"), list):
        return s["party"]
    return [m for m in call("power")["data"]["party"] if not m.get("pc")]


def party_hp(name):
    m = pick(name, members(), what="party member", key="name")
    return (m["hp"], m["maxHp"]) if m else None


def where(name):
    s = call("state")["data"]
    return pick(name, [c for c in s.get("nearby") or [] if not c.get("hostile")], what="creature in view", key="name")


def charges(card):
    m = re.search(r"\((\d+) charges?\)", (card or "").lower())
    return int(m.group(1)) if m else -1  # -1: the name doesn't say


def hold_rod(rod):
    """Hold a rod of this name that still has charges, else None (the review of 2026-10-23: the old
    hold_rod checked that some rod had charges and then grabbed the first name match, maybe the
    "(0 Charges)" one)."""
    if not any(charges(b["card"]) > 0 for b in matches(rod, grid_slots(mine=True))):
        return None
    held = grab(rod, prefer="charges")
    if held and charges(held) == 0:
        put_away_held()
        return None
    return held


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    name = args[0] if args else "Kaberg"
    # run 29: the bare "cure minor wound" also named the rod of cure minor wound, and grab refused it as
    # ambiguous with Kaberg at 36%: the default names the potion ("potion of" matches one or several)
    potions = (args[1].lower(),) if len(args) > 1 else POTIONS
    why = ready(hp=None, hunger=None, hostile_r=-1, burden=None)
    if why:
        stop(why)
    hp = party_hp(name)
    if not hp:
        refuse(f"{name} is not in the party")
    if hp[0] * 3 > hp[1] * 2 and "--force" not in sys.argv:
        refuse(f"{name} HP {hp[0]}/{hp[1]}: not hurt enough to spend a potion (--force)")
    c = where(name)
    if not c:
        # run 37: the stalker (invisible) at 100/224 after a bomb rock: "not in view" until See Invisible was cast
        r = call("cast", spell="SpSeeInvisible")
        if r.get("ok") and (r.get("data") or {}).get("cast"):
            time.sleep(1)
            c = where(name)
    if not c:
        refuse(f"{name} is not in view")
    print(f"{name} HP {hp[0]}/{hp[1]} at d{c['dist']}")
    # run 28 (bridge 0.33.0 cast): Cure Minor Wound cast at her (46% -> 80% in four casts, ~6 MP each) costs no
    # charge or potion: the spell first, to 80% or the MP floor of 20
    for _ in range(8):
        hp = party_hp(name)
        if not hp or hp[0] * 5 >= hp[1] * 4 or state()["pc"]["mp"] < 20:
            break
        r = call("cast", spell="SpHealLight", uid=c["uid"])
        if not r.get("ok") or not r["data"].get("cast"):
            break
        wait_until("idle", timeout=5000)
    hp = party_hp(name)
    if hp and hp[0] * 5 >= hp[1] * 4:
        print(f"{name} HP {hp[0]}/{hp[1]} after the spell")
        return
    put_away_held()
    # run 29 (twice on Spiritual Ruin): with the pack's grid full the held Putit couldn't be put away ("no
    # usable slot"), so the rod's Grab failed and the tool fell through to potions there were none of: free a
    # card first (purge.unclutter moves non-kit stacks into the bags), then hold the rod
    if state()["pc"].get("held"):
        try:
            from purge import unclutter
            unclutter()
        except Exception as e:  # noqa: BLE001 (a heal is never worth a crash)
            print(f"  unclutter failed: {e}")
        put_away_held()
    # run 20: a rod of cure critical wound zapped at Kaberg took her from 1% to 43% (potions of cure
    # minor had run out, and a thrown one can miss): a healing rod with charges goes first
    rod = next((r for r in ("rod of cure critical wound", "rod of cure serious wound", "rod of cure minor wound")
                if hold_rod(r)), None)
    if rod:
        c = where(name)
        acts = call("acts", dx=c["dx"], dz=c["dz"], mode="right")["data"]["acts"]
        zap = [a for a in acts if a["text"].startswith("Zap")]
        if zap:
            call("do", i=zap[0]["i"])
            time.sleep(1.5)
            after = party_hp(name)
            print(f"{name} HP {hp[0]} -> {after[0]}/{after[1]} ({rod})" if after else f"{name} left the party?")
            put_away_held()
            return
        print(f"  no Zap offered at {name} (d{c['dist']}): " + " | ".join(a["text"] for a in acts))
        put_away_held()
    # run 34: twelve cure potions bought at Koflord went to the crew in two nefias (Kaberg, the mercenary under 50%)
    # and the ladder then found none for me: an ally gets a potion only while I keep more than the escape reserve
    from common import THRESHOLDS
    mine = sum(i.get("num") or 1 for i in call("inv")["data"]["items"]
               if re.search(r"potions? of cure (minor|major|critical)", i["name"], re.I) and "cursed" not in i["name"])
    if mine <= THRESHOLDS["escape_heals"] + 2:
        refuse(f"keeping my {mine} cure potions (the reserve is {THRESHOLDS['escape_heals']} + 2): no potion for {name}")
    potion = hold_potion(potions)
    if not potion:
        # run 29: no rod in hand and no potion: Nature's Embrace (heal over time, 12 MP) before refusing
        if hot_allowed(c["uid"], state()["pc"]["turn"]):
            r = call("cast", spell="SpHOT", uid=c["uid"])
            if r.get("ok") and r["data"].get("cast"):
                time.sleep(1.5)
                after = party_hp(name)
                print(f"{name} HP {hp[0]} -> {after[0] if after else '?'}/{hp[1]} (Nature's Embrace, heals over time)")
                return
        refuse(f"no uncursed cure potion ({', '.join(potions)}) to hold, and Nature's Embrace is cast or out of MP")
    c = where(name)
    acts = call("acts", dx=c["dx"], dz=c["dz"], mode="right")["data"]["acts"]
    th = [a for a in acts if a["text"].startswith(("Throw", "Gift"))]
    if not th:
        put_away_held()
        refuse(f"no Throw offered at {name}: " + " | ".join(a["text"] for a in acts))
    call("do", i=th[0]["i"])
    time.sleep(1.5)
    after = party_hp(name)
    print(f"{name} HP {hp[0]} -> {after[0]}/{after[1]}" if after else f"{name} left the party?")
    put_away_held()


if __name__ == "__main__":
    main()
