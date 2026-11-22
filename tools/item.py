"""Use an inventory item by name: find its slot, read its right-click menu, and
perform the entry whose text starts with ACTION. Never picks by index, because
the menu order differs per item (run 02: index 0 was "Split" on a stack).

usage: python -I tools/item.py NAME            (list the item's menu)
       python -I tools/item.py NAME ACTION     (e.g. Grab, Equip, Read, Eat, Use)
       python -I tools/item.py NAME Transfer --take   (from the open container to my pack)
With a container or shop open, my pack's slot is used unless --take is given.
Refusals (exit 1), each with the flag that overrides it (the review of 2026-10-23):
  --cursed-ok    Equip, Read, Use, Drink or Eat of a stack named cursed or doomed
  --teleport-ok  Equip of gear whose tooltip says it prevents teleportation (lessons: it switches
                 off every escape scroll)
  --main         Equip of a weapon when both hands are taken, so it would replace the main hand
                 (run 20: the axe came off for a grass sword); with a free hand the worn list is
                 printed afterwards instead, since the slot the game picks can't be told beforehand
  --offhand-ok   Equip of a shield or a second weapon beside a lone weapon: it switches off the
                 two-hand style (run 37's close: the axe 22.8 a turn alone, 9.5 with a shield)
  (no override) Read of a scroll of return or evacuation while one is counting down (pc.return)
  --force        a food listed as harmful, with a harmful trait in its tooltip, or rotten (run 27)
Before a Buy with a shop open it prints what is carried already (the pack, and each open bag).
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call, norm  # noqa: E402

WEAPON = re.compile(r"\(\d+d\d+")  # "(3d5+3, 2)": a weapon's dice (packcheck.GEAR)
HAND = re.compile(r"\b(shield|buckler)\b", re.I)  # the other thing a hand holds


def qty(card):
    m = re.match(r"(\d+) ", card or "")
    return int(m.group(1)) if m else 1


def worn_hands():
    """The equipped weapons and shields, in `inv` order (the main hand is the first weapon slot)."""
    items = call("inv")["data"]["items"]
    return [i["name"] for i in items if i.get("equipped") and (WEAPON.search(i["name"]) or HAND.search(i["name"]))]


def harmful_foods():
    """Food names listed under '## Harmful' in knowledge/foods.md (first table column)."""
    path = Path(__file__).resolve().parent.parent / "knowledge" / "foods.md"
    names, on = [], False
    for line in path.read_text(encoding="utf-8").splitlines() if path.exists() else []:
        if line.startswith("## "):
            on = line.strip().lower() == "## harmful"
            continue
        if on and line.startswith("|") and not line.startswith("|---") and not line.startswith("| Food"):
            names.append(line.split("|")[1].split("(")[0].strip().lower())
    return [n for n in names if n]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    take = "--take" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    name = args[0].lower()
    action = args[1].lower() if len(args) > 1 else None
    from common import matches, refuse, stack_hits
    def find_slots():
        bs = call("buttons", all=True)["data"]["buttons"]
        grid = [b for b in bs if b.get("card") and "ButtonGrid inventory" in b["name"]]
        # exact, then whole word, then a word start (run 12: "(1" picked "(11 Charges)"); two
        # different names at the best level is an error, not a guess
        hits, ambiguous = stack_hits(name, grid)  # run 13: stacks differing only in count are one item
        if ambiguous:
            refuse(f"{name!r} matches several items: " + " | ".join(sorted({b["card"] for b in hits})[:8]) + " (give the full name)")
        # With a shop or chest open, the same item can sit in its grid too: my pack first
        # (bridge 0.9.2 marks my own items "mine"), or theirs first with --take.
        def order(b):
            mine = b["mine"] if "mine" in b else "UIInventory/List" in (b.get("path") or "")
            return 0 if mine != take else 1
        return sorted(hits, key=order)

    slots = find_slots()
    if action == "transfer":
        # Transfer only from the side asked for: without --take, never pull the container's copy
        # back into the pack once mine are gone (run 03: garbage went back and forth).
        slots = [s for s in slots if s.get("mine", True) != take]
        if not slots:
            sys.exit(f"no {'container' if take else 'pack'} slot holding {name!r}")
    if not slots:
        from common import open_inventory
        open_inventory()  # the inventory panel is closed: open it (run 17: by the hotbar button)
        slots = find_slots()
    if not slots:
        sys.exit(f"no inventory slot holding {name!r}")
    # A shop's grid can hold the same item ("Buy" instead of "Sell"): use the first slot that
    # offers the requested action, else the first slot.
    rep = None
    for s in slots:
        r = call("invacts", i=s["i"])
        if not r.get("ok"):
            continue
        if rep is None:
            rep, chosen = r, s
        if action and any(a["text"].lower().startswith(action) for a in r["data"]["acts"]):
            rep, chosen = r, s
            break
    if action and action.startswith("buy") and (rep is None or not any(a["text"].lower().startswith("buy") for a in rep["data"]["acts"])):
        # run 51: "travel ration" matched my own "a travel ration" at the exact level and never reached the shop's
        # "2 travel rations" (a plural one level down), so Buy was refused three times: for a Buy, look at the shop's side
        # of the grid with the plural too
        bs = call("buttons", all=True)["data"]["buttons"]
        theirs = [b for b in bs if b.get("card") and "ButtonGrid inventory" in b["name"]
                  and not (b["mine"] if "mine" in b else "UIInventory/List" in (b.get("path") or ""))]
        for b in matches(name, theirs) or matches(name + "s", theirs):
            r = call("invacts", i=b["i"])
            if r.get("ok") and any(a["text"].lower().startswith("buy") for a in r["data"]["acts"]):
                rep, chosen = r, b
                break
    if rep is None:
        sys.exit("no usable slot")
    slots = [chosen]
    rep = call("invacts", i=chosen["i"])  # re-list: invdo acts on the latest listing
    acts = rep["data"]["acts"]
    if action is None:
        print(rep["data"]["item"] + ":", " | ".join(a["text"] for a in acts))
        return
    if action in ("info", "?"):
        tip = call("hover", i=slots[0]["i"])
        print("\n".join(tip["data"]["texts"]) if tip.get("ok") else tip.get("error"))
        return
    card = (chosen.get("card") or rep["data"]["item"] or "").lower()
    if action == "drop" and "--full-ok" not in sys.argv:
        # run 57: six "empty" mystic chests were dropped on a far field after a chests.py --field pass; they still held
        # the junk it leaves behind, and most likely the pine shovel (it was never seen again): a container that holds
        # anything is not dropped without --full-ok
        try:
            import items as _inv
            uid = chosen.get("uid")
            hit = [i for i in _inv.inventory() if i.get("uid") == uid] if uid else []
            if hit and hit[0].get("container") and (hit[0].get("count") or 0) > 0:
                refuse(f"{rep['data']['item']} still holds {hit[0]['count']} things: empty it first (--full-ok to drop it anyway)")
        except SystemExit:
            raise
        except Exception:  # noqa: BLE001 - the check never blocks a plain drop
            pass
    if action in ("equip", "read", "use", "drink", "eat") and re.search(r"\b(cursed|doomed)\b", card) \
            and "--cursed-ok" not in sys.argv:
        refuse(f"{rep['data']['item']} is cursed or doomed: not {action}ing it (--cursed-ok to insist)")
    if action == "read" and re.search(r"\bof (return|evacuation)\b", card):
        # run 20 (errors.csv row 43): a second scroll of return read while the first counted down
        # spent both ("The air relaxes"); the bridge refuses the read too (0.30.0): belt and braces
        ret = (call("state")["data"].get("pc") or {}).get("return")
        if ret:
            refuse(f"a {'evacuation' if ret.get('evac') else 'return'} is counting down ({ret.get('turns')} turns left): "
                   "never read another; wait for the zone change")
    if action == "equip":
        tip = call("hover", i=slots[0]["i"])
        texts = (tip.get("data") or {}).get("texts") or []
        if any("prevents teleport" in t.lower() for t in texts) and "--teleport-ok" not in sys.argv:
            refuse(f"{rep['data']['item']} prevents teleportation: every escape scroll stops working while it is worn "
                   "(lessons, run 13); --teleport-ok to insist")
        # run 30: a shield has no dice, and its Equip with both hands taken replaced the main-hand axe: any
        # hand item (a weapon or a shield) gets the same guard
        # (run 37's close: the regex held backspaces, not word edges, and the slot's card can be empty: the shield was
        # equipped past this test; now the card text with the item's name as its fallback, as for the cursed check)
        if WEAPON.search(card) or HAND.search(card):
            hands = worn_hands()
            if len(hands) >= 2 and "--main" not in sys.argv:
                # run 20: the Rigid Hand Axe came off for a grass sword. With no free hand the game
                # equips into the first weapon slot, the main hand (Body.GetSlot: a free slot first,
                # else the first slot of the kind)
                refuse(f"equipping {rep['data']['item']} would replace the main hand ({hands[0]}); worn: "
                       + " | ".join(hands) + " (--main to do it, or Put away the one to drop first)")
            # run 37's close: the shield had been worn since run 30 for PV +6, while the axe alone deals 2.4x the
            # damage (x4.85 against x2.92, hit 142% against 111%): a second hand item needs a deliberate flag
            if len(hands) == 1 and WEAPON.search(hands[0]) and "--offhand-ok" not in sys.argv:
                refuse(f"equipping {rep['data']['item']} beside {hands[0]} switches off the two-hand style (x1.5 "
                       "damage, +25 to-hit: 22.8 a turn alone against 9.5 with a shield); Unequip the weapon first "
                       "to replace it, or --offhand-ok to wear both")
            print(f"  hands before: {' | '.join(hands) or 'nothing'}")
        # run 29: an Unequip of the Mass Ring failed on a full pack, and the stone ring's Equip then replaced the
        # copper ring instead (PV 54 -> 44): with both fingers taken the game swaps the first ring, so it's refused
        # unless --finger-ok (take the one to replace off first, and gate that step on its exit code)
        card0 = (chosen.get("card") or "").lower()
        # run 50: "Ring Mail" is body armour (gearcheck had the same gap in run 48): a ring is "ring" not followed by "mail"
        if re.search(r"\bring\b(?! mail)", card0) and "--finger-ok" not in sys.argv:
            rings = [i["name"] for i in call("inv")["data"]["items"]
                     if i.get("equipped") and re.search(r"\bring\b(?! mail)", i["name"].lower())]
            if len(rings) >= 2:
                refuse(f"both fingers are taken ({' | '.join(rings)}): the game would replace the first ring; "
                       "Unequip the one to replace first (gate on its exit code), or --finger-ok")
    if action == "buy":
        # the review of 2026-10-23 (errors.csv row 44): 2 evacuation scrolls bought with 14 in the
        # backpack. What is carried already, by the grids on screen: the pack, and each open bag
        bs = call("buttons", all=True)["data"]["buttons"]
        grid = [b for b in bs if b.get("card") and "ButtonGrid inventory" in b["name"]
                and (b["mine"] if "mine" in b else "UIInventory/List" in (b.get("path") or ""))]
        have = {}
        for b in matches(name, grid):
            have[b.get("in") or "pack"] = have.get(b.get("in") or "pack", 0) + qty(b["card"])
        parts = [f"{have.get('pack', 0)} in the pack"]
        bags = sorted({b.get("in") for b in grid if b.get("in") and b["in"] != "pack"})
        parts += [f"{have.get(bag, 0)} in the {bag}" for bag in bags]
        if not any("backpack" in bag.lower() for bag in bags):
            parts.append("backpack not open (bag.py backpack first to count it)")
        print("  carried: " + ", ".join(parts))
    if action in ("eat", "drink"):
        # Pros and cons first (the user's rule): show the tooltip, refuse known-harmful food.
        tip = call("hover", i=slots[0]["i"])
        print("  " + " | ".join(tip["data"]["texts"]) if tip.get("ok") else "")
        harmful = harmful_foods()
        item = rep["data"]["item"].lower()
        bad = [h for h in harmful if h in item]
        if bad and "--force" not in sys.argv:
            sys.exit(f"refusing: {bad[0]!r} is listed as harmful in knowledge/foods.md")
        # run 27 (errors.csv): a meal kept in the pack rotted and I ate "a rotten goblin warrior on the bone"
        # by hand (the rule "food rots loose: keep it in the Cooler Box" was only text); rotten food can sicken
        if action == "eat" and re.search(r"\brotten\b", item) and "--force" not in sys.argv:
            sys.exit(f"refusing: {rep['data']['item']} is rotten (--force to eat it anyway)")
        # Run 06: a scorpion on the bone poisoned me; the food's own traits (【...】 lines) say
        # what it does, and a cure trait ("Cure Poison", the blue herb: the user's tip) is fine.
        traits = [t for t in (tip.get("data") or {}).get("texts", []) if "【" in t]
        risky = [t for t in traits if re.search(r"(?<!cure )(poison|paraly|confus|blind|hallucin|insan|fear|nause|sleep)", t, re.I)]
        # run 46: 【Waking】 Anti Sleep keeps me awake; it harms only a loop that sleeps next (trainday, music, a road nap),
        # and a nefia floor is never slept on: there it's food (a Hungry stop on Capricious Ruin with nine such dishes)
        zone = (call("state").get("data") or {}).get("zone") or {}
        # run 51: circuit.fed_nap eats on a nefia's B1 and naps outside right after: ELIN_NAP_NEXT keeps Waking refused
        # run 52: Hungry (76) on a road with three coffee bean pies the only meal left: the refusal stopped wgo, which won't
        # walk Hungry, and the pie went down by hand (--force). At Hungry and not Sleepy, the hunger outweighs a nap's delay
        pc = (call("state").get("data") or {}).get("pc") or {}
        hungry_awake = (pc.get("hunger") or 0) >= 70 and not (pc.get("sleepPhase") or 0)
        if ((zone.get("nefia") or str(zone.get("full") or "").startswith("Zone_dungeon")) or hungry_awake) and not os.environ.get("ELIN_NAP_NEXT"):
            risky = [t for t in risky if not re.search(r"anti sleep|waking", t, re.I)]
        if risky and "--force" not in sys.argv:
            sys.exit(f"refusing: a harmful trait in the tooltip: {risky}")
    # An exact name wins over a longer one: "Grab" must not pick "Grab as furniture", which holds
    # a tool to be placed (run 05: the pickaxe then offered only "Place" on a crop)
    hit = [a for a in acts if a["text"].lower() == action] or \
          [a for a in acts if a["text"].lower().startswith(action)]
    # run 08: with the axe already held its menu has no plain "Grab", and the prefix match took
    # "Grab as furniture" (placement mode) twice
    if action == "grab" and not any(a["text"].lower() == "grab" for a in acts):
        held = (call("state")["data"]["pc"].get("held") or "")
        sys.exit(f"no plain Grab for {rep['data']['item']} (held now: {held or 'nothing'}); not taking 'Grab as furniture'")
    if not hit:
        sys.exit(f"{rep['data']['item']} has no {action!r}: " + " | ".join(a["text"] for a in acts))
    def mine_count():
        # How many of the item sit on the side it moves from (my pack, or the box with --take).
        # Count quantity, not stacks: a stack that merges into one on the other side leaves the
        # stack count unchanged (run 04: a false "did not move it").
        def qty(card):
            m = re.match(r"(\d+) ", card)
            return int(m.group(1)) if m else 1
        grid = [b for b in call("buttons", all=True)["data"]["buttons"] if b.get("card") and "ButtonGrid inventory" in b["name"]]
        return sum(qty(b["card"]) for b in matches(name, grid) if bool(b.get("mine")) != take)
    before = mine_count() if action == "transfer" else None
    r = call("invdo", i=hit[0]["i"])
    print(r["data"]["did"] if r.get("ok") else r.get("error"), "-", rep["data"]["item"])
    from common import txlog, wait_until
    if r.get("ok"):  # run 49: every act on a carried thing goes in the run's item ledger (common.txlog)
        txlog(hit[0]["text"].split(" (")[0].lower(), rep["data"]["item"], "a shop or box" if take else "pack",
              "", " ".join(sys.argv[1:])[:120])
    if action == "transfer":
        # A full box or pack refuses silently (run 03): check that something actually moved.
        wait_until("frames", n=8, timeout=1000)
        if mine_count() == before:
            sys.exit("!! transfer did not move it: the container or the pack is probably full")
    if action == "equip" and r.get("ok") and WEAPON.search(card):
        wait_until("frames", n=8, timeout=1000)
        hands = worn_hands()
        print(f"  hands after: {' | '.join(hands) or 'nothing'} (the first weapon is the main hand: check it)")
    if action == "unequip" and r.get("ok"):
        # run 21: "Unequip - ☆The Practice Scimitar" printed and the scimitar stayed worn (the pack's
        # grid was full: the game had nowhere to put it); check it left the hands
        wait_until("frames", n=8, timeout=1000)
        card = chosen.get("card") or rep["data"]["item"]
        still = [i for i in call("inv")["data"]["items"] if i.get("equipped") and i["name"] == card]
        if still:
            sys.exit("!! still worn: the pack's grid is probably full (put a stack in a bag first)")


if __name__ == "__main__":
    main()
