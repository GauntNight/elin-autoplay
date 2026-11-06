"""Pick up every loose item (not installed furniture) within a radius after a fight: walk to
each cell and take everything there (the user's rule: collect all loot, especially from
special mobs). Stops if a hostile shows up. Skips cells it can't reach.
Skips junk (vomit, rubble, garbage, cones...: run 07 filled the pack and re-looted my own drops) and
anything that is someone's property (picking it up is theft: Karma -1 and a witness check, G8).
By default only things worth a pack slot (run 07: the pack filled a dozen times with common gear,
food scraps and festival decor): money, potions, scrolls, books, recipes, rods, gems, ores of value,
artifacts (☆ ★, a capitalised Miracle/Godly name), special-mob drops (『』, cards, figures), medals,
lockpicks. --all takes everything that isn't junk: a new character's default, when materials are what it's short of.

usage: python -I tools/loot.py [radius] [--all] [--no-butcher]   (default 20)
With the butcher's tool in the pack, corpses are picked up one at a time and butchered at once
(run 14: a skin 20% of the time, for bag 3).
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import THRESHOLDS, pack_full, stop, walk  # noqa: E402

JUNK = ("vomit", "of curse", "summon monster", "rubble", "garbage", "a cone", " cones", "empty bottle", "cobweb", "stain",
        "scrap of", "offal", "rotten", "grave of",  # run 13: a boss grave matched the 『 keep rule
        "putitification", "stone circle", "paper war",  # run 12: fragments make glass, hearts feed jobs
        "bottle of liquid", "holy sock", "holy wreath", "holy garland", "gift box", "santa hat", "snow globe",
        # run 27: ~15 real minutes went to dropping these from full packs and bags (KEEP's "potion", "scroll" and
        # "book" took them): debuff potions nobody uses, cursed consumables, book piles and diaries
        "potion of slow", "potions of slow", "potion of paralysis", "potions of paralysis", "potion of confusion",
        "potions of confusion", "ultravision", "infravision", "potion of telepathy", "potions of telepathy",
        "salt water", "potion of weakness", "potions of weakness", "potion of strip blessing", "potions of strip",
        "weaken resistance", "catification", "cursed potion", "cursed scroll", "doomed potion", "doomed scroll",
        "book pile", "strange diary",
        # run 27: a figure weighs 8.5 (five were 40 of a 105 burden: phase 2, speed 121 -> 87) and sells for 34-40
        "figure of")


KEEP = ("oren", "platinum", "gold bar", "potion", "scroll", "book", "tome", "recipe", "rod of", "gem",
        "ruby", "emerald", "sapphire", "diamond", "onyx", "lapis", "cobalt", "garnet", "topaz", "medal",
        "card of", "figure of", "lockpick", "『", "☆", "★", "(miracle)", "(godly)", "ticket", "gene",
        "coin", "map", " rod", "amulet", "necklace", "decorative ring", "bejeweled",  # run 10: unidentified rods and jewelry
        "skin")  # the new-game test: a sleeping bag takes 2 and a backpack 4, and they drop 1 kill in 10


PACK_MAX = THRESHOLDS["pack_max"]  # the main pack refuses the 44th stack (run 09); leave a slot for a boss chest's loot


def at_home(s):
    """The home map (Zone_startSite...): its walks need no hostile radius or HP floor."""
    return str((s.get("zone") or {}).get("full") or "").startswith("Zone_startSite")


def room():
    """True while the pack has room for a pick-up; a full pack is first relieved into the loot
    bags (run 12: a skin picked up into a full pack vanished, "You can't put that in your backpack!")."""
    if pack_full(PACK_MAX):
        bag_haul()
    return not pack_full(PACK_MAX)


def bag_haul():
    """Run 14: move the pack's stacks that are neither trip kit nor food (packcheck's lists) into
    the loot bag (bag 2), so a full pack no longer ends the looting. Unidentified items stay in
    the pack for Appraising. Returns the number of stacks moved."""
    import re
    from common import run
    from packcheck import KIT, has_word, is_food, norm_name
    items = [i for i in call("inv")["data"]["items"] if not i.get("equipped")]
    if not any("loot bag" in i["name"] for i in items):
        return 0
    haul = [re.sub(r"^(an?|\d+)\s+", "", i["name"]) for i in items
            if i.get("id") != "unidentified" and not has_word(norm_name(i["name"]), KIT) and not is_food(norm_name(i["name"]))]
    if not haul:
        return 0
    moved = 0
    for bag in ("loot bag", "spoils bag", "haul bag"):  # run 14: bag 3 takes what the full loot bag refuses; run 41: bag 4
        if not haul or not any(bag in i["name"] for i in items):
            continue
        out = run("bag.py", bag, *haul)
        run("close.py")
        print(f"  to the {bag}: " + "; ".join(ln.strip() for ln in out.splitlines() if ln.strip()))
        done = [ln.split(":")[0].strip() for ln in out.splitlines() if ": moved " in ln]
        moved += len(done)
        haul = [h for h in haul if h not in done]
    return moved


def junk(name):
    n = name.lower()
    return any(j in n for j in JUNK)


def worth(name):
    """Worth a pack slot: valuables, consumables, artifacts. An unidentified Miracle or Godly item
    starts with a capital article ("A Sand Long Sword")."""
    from common import hammer_scrap
    if "shrine" in name.lower():  # run 40: "★" read as an artifact; a grabbed ★Shrine (weight 1,000) Squashed me: use it where it stands
        return False
    if hammer_scrap(name):  # run 13: cans, toasters, lucky cats... a hammer makes them scrap
        return True
    if junk(name):
        return False
    if CORPSES and "corpse" in name.lower():  # run 14: picked up one at a time; run 15: butchered
        return True                            # only when safe, so they can wait in the pack
    if "--all" in sys.argv:
        return True
    n = name.strip()
    if n[:2] in ("A ", "An") and n[2:3].isupper() or n.startswith("An ") and n[3:4].isupper():
        return True
    return any(k in n.lower() for k in KEEP)


BUTCHER = False  # set in main(): the butcher's tool is in the pack and --no-butcher wasn't given
CORPSES = False  # set in main(): pick corpses up (the tool is carried; fewer than 5 already wait)


def butcher_pack():
    """Butcher every corpse now in the pack (a corpse can come in with a 'Pick all' on a cell whose
    first item was something else: run 14's home hunt left six unbutchered)."""
    if not BUTCHER or not any("corpse" in i["name"].lower() for i in call("inv")["data"]["items"]):
        return
    from common import run
    out = run("butcher.py")
    print("  butchered: " + " / ".join(ln.strip() for ln in out.splitlines() if "->" in ln))


def main():
    global BUTCHER, CORPSES
    # run 14: ~40 kills in Ancient Ruin left their corpses; each one through the butcher's tool is
    # a skin 20% of the time (bag 3 needs 4). Corpses are heavy: one at a time, butchered at once.
    items = call("inv")["data"]["items"]
    tool = any("butcher's tool" in i["name"] for i in items)
    # the user, run 15: "you left all the meat on the ground": with --no-butcher the corpses were
    # skipped too; now they are picked up (one at a time: they're heavy, so at most 5 wait) and
    # butchered later, when it's safe
    waiting = sum(1 for i in items if "corpse" in i["name"].lower())
    CORPSES = tool and waiting < 5
    BUTCHER = "--no-butcher" not in sys.argv and tool
    # the user, run 15: butcher only after combat or when safe (a butchering task with a foe just
    # out of sight got me stuck and hit): with a hostile in view, corpses wait
    if BUTCHER and any(x.get("hostile") for x in call("state")["data"].get("nearby") or []):
        BUTCHER = False
        print("  (a hostile in view: corpses left for later, no butchering now)")
    nums = [a for a in sys.argv[1:] if a.isdigit()]
    r = int(nums[0]) if nums else 20
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    done, got = set(), []
    for _ in range(40):
        s = call("state")["data"]
        foes = [c for c in s.get("nearby") or [] if c["hostile"]]
        if foes:
            print("picked up at:", "; ".join(got) if got else "nothing")
            stop("hostile in view: " + ", ".join(f"{c['name']} Lv{c.get('lv')} d{c.get('dist')}" for c in foes[:3]))
        if not room():
            print("picked up at:", "; ".join(got) if got else "nothing")
            stop(f"the pack holds {PACK_MAX}+ stacks: drop or bag something before looting (the 44th is refused)")
        if (s["pc"].get("burdenPhase") or 0) >= 2:
            # run 21: loot.py picked 25 dropped granite stones (2.2 each) back up and the walk home
            # ran Overweight (160 -> 24 HP): the pack's weight is a limit too, not only its stacks
            print("picked up at:", "; ".join(got) if got else "nothing")
            stop(f"burden phase {s['pc']['burdenPhase']}: drop or store weight before looting more")
        home = at_home(s)
        hits = [h for h in call("find", name="", r=r, n=500)["data"]["hits"]
                if h["kind"] == "thing" and not h["installed"] and worth(h["name"])
                # run 21: a loose ★Shrine 《Strife》 on the Ruined Cave's B1 was picked up and carried
                # down: Squashed (1000/1000); shrines, altars and traps are used or left, never carried
                and not re.search(r"shrine|altar|trap", h["name"], re.I)
                and (h["x"], h["z"]) not in done]
        if not hits:
            break
        # run 33 (the user, P18): genes first, so a nearly full pack takes an Evolved creature's gene before the junk
        hits.sort(key=lambda x: 0 if "gene" in x["name"].lower() else 1)
        h = hits[0]
        done.add((h["x"], h["z"]))
        # run 26: junk dropped on a Machinarium's entrance stairway pulled the loot walk back there
        # twice, and an act on that cell took the stairs out of the nefia: items on stairs stay
        me = call("state")["data"]["pc"]
        on = (call("cell", dx=h["x"] - me["x"], dz=h["z"] - me["z"]).get("data") or {}).get("thingInfo") or []
        if any(re.search(r"stair", t.get("name", ""), re.I) for t in on):
            print(f"  skipped {h['x']},{h['z']}: on a stairway ({h['name']})")
            continue
        if h["dist"] > 0:
            # off the home map the walk keeps walkto's stops (the review of 2026-10-23: r=0, hp=0
            # let a loot walk carry on through a new arrival on a dungeon floor)
            rad, floor = (0, 0) if home else (4, THRESHOLDS["walk_hp"])
            w = walk(h["x"], h["z"], r=rad, hp=floor, timeout=20000)
            if w.get("why") != "arrived":
                print(f"  can't reach {h['x']},{h['z']} ({h['name']}): {w.get('why')}")
                continue
        info = (call("cell", dx=0, dz=0).get("data") or {}).get("thingInfo") or []
        if any(t.get("npcProperty") for t in info):
            print(f"  skipped {h['x']},{h['z']}: someone's property ({h['name']})")
            continue
        mixed = any(not worth(t.get("name", "")) for t in info)
        took = False
        for _ in range(8):  # one pick at a time when junk shares the cell; indices shift after each
            acts = call("acts", dx=0, dz=0, mode="all")["data"]["acts"]
            picks = [a for a in acts if a["text"].startswith("Pick") and (a["text"].startswith("Pick all") or worth(a["text"][5:].strip("() ")))]
            if mixed:
                picks = [a for a in picks if not a["text"].startswith("Pick all")]
            else:
                picks = [a for a in picks if a["text"].startswith("Pick all")] or picks
            if not picks:
                # Run 10: on some cells the only pick-up act is the right-click "Grab (item)"
                # (mode "all" offered Drink/Blend/Drop for a potion underfoot, no "Pick up").
                acts = call("acts", dx=0, dz=0, mode="right")["data"]["acts"]
                picks = [a for a in acts if a["text"].startswith("Grab (") and worth(a["text"][6:].rstrip(")"))]
                mixed = True  # one Grab takes one stack: keep going while the cell has more
            if not picks:
                break
            if not room():  # before every Pick: a cell can hold more stacks than the pack has room for
                print("picked up at:", "; ".join(got + ([h["name"]] if took else [])) or "nothing")
                stop(f"the pack holds {PACK_MAX}+ stacks: drop or bag something before looting (the 44th is refused)")
            call("do", i=picks[0]["i"])
            time.sleep(1.0)
            took = True
            if not mixed:
                break
        if not took:
            continue
        got.append(h["name"])
        butcher_pack()
    butcher_pack()
    print("picked up at:", "; ".join(got) if got else "nothing")
    log = call("state")["data"].get("log") or []
    print("log:", " / ".join(l for l in log[-8:] if "pick up" in l.lower()))


if __name__ == "__main__":
    main()
