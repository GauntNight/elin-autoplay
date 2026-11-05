"""The opening as one tool (run 41: done by hand it took 15 real minutes, nearly all of it turns between steps; the elin-opening skill is the
reasoning, this is its fast path). From a new game's first dialog to a claimed home, Aliby-style pet, boards, Loytel, the Defense Training kit and
Way of Crafter's training dummy placed beside a bed. Each stage checks its result and stops (exit 3) naming the stage, so a stop is finished by
hand and the rest picked up with --from STAGE. Sets the game's speed to x5 at once (fights set x1 themselves).

usage: python -I tools/opening.py [--from STAGE] [--to STAGE]
stages: intro deed rewards pet box inspector punk boar logs workbench torch house dummy
Writes runs/earlybase.json (the stand, the bed and the bonfire) for earlyday.py and marks each stage on the trial clock when one runs.
Exit 0 done, 3 stopped for a decision, 2 the bridge.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402
from common import data, pc, run, state, stop, top, wait_idle, walk, walk_beside  # noqa: E402

STAGES = "intro deed rewards pet box inspector punk boar logs workbench torch house dummy".split()
BASE = Path(__file__).resolve().parent.parent / "runs" / "earlybase.json"


def say(*a):
    print(*a, flush=True)


def talk(n=12):
    return run("talk.py", n, timeout=120)


def settle():
    """Read through whatever opened (tips arrive after most steps)."""
    for _ in range(5):
        s = state()
        if not (s.get("drama") or (s.get("layers") or {}).get("top")):
            return
        talk(12)
        if top() and not state().get("drama"):
            run("close.py", timeout=20)
        time.sleep(0.1)


def choose(text):
    """Click the dialog choice starting with text. True when it was there."""
    bs = [b for b in call("buttons")["data"]["buttons"] if (b.get("text") or "").startswith(text)]
    if not bs:
        return False
    call("click", i=bs[0]["i"])
    time.sleep(0.25)
    return True


def bye():
    choose("Bye")
    settle()


def talkto(name):
    for _ in range(3):
        settle()
        out = run("talkto.py", name, timeout=60)
        if "not in view" in out or "could not get" in out:
            hits = [c for c in state().get("nearby") or [] if name.lower() in (c.get("name") or "").lower()]
            walk(55, 49, r=0, hp=1, timeout=15000)
            if hits:
                walk_beside(hits[0]["x"] if "x" in hits[0] else 55, hits[0]["z"] if "z" in hits[0] else 49)
            continue
        return out
    stop(f"can't reach {name}")


def here(text):
    """Do the act on my own cell that starts with text. True when it was there."""
    acts = call("acts", dx=0, dz=0, mode="all")["data"]["acts"]
    hit = [a for a in acts if a["text"].startswith(text)]
    if hit:
        call("do", i=hit[0]["i"])
        wait_idle(timeout=4000)
    return bool(hit)


def on_my_cell(text, r=2):
    """Pick up a dropped reward near me by name of the act (rewards land on or beside my cell)."""
    if here(text):
        return True
    p = pc()
    for h in call("find", name=text.split("(")[-1].rstrip(")").strip() or text, r=r, n=4)["data"]["hits"]:
        walk(h["x"], h["z"], r=0, hp=1, timeout=6000)
        if here(text):
            return True
    walk(p["x"], p["z"], r=0, hp=1, timeout=4000)
    return False


def board_job(name, choice=None, optional=False):
    settle()
    hits = [h for h in call("find", name="quest board", r=30, n=2)["data"]["hits"]]
    if not hits:
        stop("no quest board found")
    b = hits[0]
    p = pc()
    if max(abs(p["x"] - b["x"]), abs(p["z"] - b["z"])) > 1:
        walk_beside(b["x"], b["z"])
        p = pc()
    acts = call("acts", dx=b["x"] - p["x"], dz=b["z"] - p["z"], mode="all")["data"]["acts"]
    view = [a for a in acts if a["text"].startswith("View Works")]
    if not view:
        stop(f"the board offers: {[a['text'] for a in acts]}")
    call("do", i=view[0]["i"])
    time.sleep(0.5)
    rows = [r for r in call("buttons")["data"]["buttons"] if "item quest" in r.get("name", "") and name in r.get("text", "")]
    if not rows and optional:  # run 44: --from logs asked for a job already held and stopped there
        call("closetop")
        return
    if not rows:
        stop(f"no {name} on the board")
    call("click", i=rows[0]["i"], expect=name)
    time.sleep(0.3)
    talk(16)
    if choice and not choose(choice):
        stop(f"{name}: no choice {choice!r}")
    talk(16)
    settle()


def have(item_id):
    return sum((i.get("num") or 1) for i in data("inv")["items"] if i.get("id") == item_id)


def gather(obj, item, n, min_sp=3, r=30):
    out = run("gather.py", obj, item, n, min_sp, r, timeout=240)
    settle()
    return out


def rest_if_low(need=7):
    """SP is what runs out in the opening (run 42 stopped twice): a low bar sleeps where I stand: no bed needed under 20%, fact #1197."""
    p = pc()
    if p["sp"] >= need:
        return
    if p["sp"] * 5 > p.get("maxSp", 34):  # Rest only sleeps under 20%: spend down a little on nothing here, the craft will refuse: say so
        say(f"  SP {p['sp']}: over 20%, Rest would only meditate")
    run("ability.py", "Rest", timeout=20)
    for _ in range(40):
        time.sleep(0.25)
        settle()
        q = pc()
        if q["sp"] > p["sp"] + 5 and "ConSleep" not in str(q.get("conditions") or ""):
            break
    settle()


def craft(dx, dz, name, n=1):
    rest_if_low()
    call("act", action="EmptyHand")
    out = run("craft.py", dx, dz, name, n, "--force", timeout=60)
    settle()
    acts = call("acts", dx=0, dz=0, mode="all")["data"]["acts"]
    put = [a for a in acts if a["text"].startswith("Put away")]
    if put:
        call("do", i=put[0]["i"])
        time.sleep(0.15)
    return out


def sleep_now(bed):
    p = pc()
    run("act.py", bed[0] - p["x"], bed[1] - p["z"], "Sleep", timeout=20)
    for _ in range(50):
        time.sleep(0.25)
        settle()
        q = pc()
        if q["sp"] > p["sp"] + 3 and "ConSleep" not in str(q.get("conditions") or ""):
            return True
    return False


def st_intro():
    for _ in range(60):
        s = state()
        if s.get("inGame") and not s.get("drama") and not (s.get("layers") or {}).get("top"):
            break
        talk(40)
        time.sleep(0.2)
    call("speed", i=3)
    h = call("find", name="vegetable soup", r=8, n=1)["data"]["hits"]
    if h:
        walk(h[0]["x"], h[0]["z"], r=0, hp=1, timeout=6000)
        here("Pick")


def st_deed():
    talkto("Ashland")
    bye()
    if not on_my_cell("Pick (★Land Deed", r=3):
        stop("no land deed at my feet")
    run("item.py", "Land Deed", "Read", timeout=20)
    time.sleep(0.4)
    if not choose("a | Yes") and not choose("Yes"):
        bs = [b for b in call("buttons")["data"]["buttons"] if (b.get("text") or "").endswith("Yes.")]
        if not bs:
            stop("the deed asked nothing")
        call("click", i=bs[0]["i"])
    settle()
    call("act", action="QuickSave")


def st_rewards():
    talkto("Ashland")
    bye()
    p = pc()
    if not here("Pick all"):
        stop(f"no rewards on my cell {p['x']},{p['z']}")
    settle()


def buy(card):
    b = [x for x in call("buttons")["data"]["buttons"] if card in (x.get("card") or "") and "grid" in x.get("name", "")]
    if not b:
        stop(f"the shop has no {card}")
    acts = call("invacts", i=b[0]["i"])["data"]["acts"]
    call("invdo", i=[a["i"] for a in acts if a["text"].startswith("Buy 1")][0])
    time.sleep(0.25)


def st_pet():
    settle()
    talkto("Fiama")
    talk(4)
    if not choose("A little girl"):
        stop("no pet choice")
    talk(12)
    if not choose("Let me see your home equipment"):
        stop("no home equipment choice")
    time.sleep(0.5)
    buy("resident board")
    buy("home board")
    call("act", action="Cancel")
    time.sleep(0.4)
    settle()


def st_box():
    # run 43: "a royal sturdy box": a random quality word, so the name is matched by its last words; a resumed stage has the job already
    if not call("find", name="sturdy box", r=4, n=1)["data"]["hits"]:
        board_job("Essential Equipment")
    hit = call("find", name="sturdy box", r=4, n=1)["data"]["hits"]
    if not hit:
        stop("no sturdy box")
    walk(hit[0]["x"], hit[0]["z"], r=0, hp=1, timeout=4000)
    acts = call("acts", dx=0, dz=0, mode="all")["data"]["acts"]
    pick = [a for a in acts if a["text"].startswith("Pick") and "sturdy box" in a["text"]]
    if not pick:
        stop(f"no Pick for the box: {[a['text'] for a in acts]}")
    call("do", i=pick[0]["i"])
    wait_idle(timeout=3000)
    settle()
    run("item.py", "sturdy box", "Grab", timeout=20)
    p = pc()
    out = run("place.py", "sturdy box", f"{p['x'] + 1},{p['z'] + 1}", f"{p['x'] + 2},{p['z']}", f"{p['x']},{p['z'] + 2}", timeout=30)
    if "placed" not in out:
        stop("couldn't place the box: " + out[-120:])
    b = call("find", name="sturdy box", r=4, n=1)["data"]["hits"][0]
    q = pc()
    if max(abs(b["x"] - q["x"]), abs(b["z"] - q["z"])) > 1:
        walk_beside(b["x"], b["z"])
        q = pc()
    run("act.py", b["x"] - q["x"], b["z"] - q["z"], "Open", timeout=20)
    time.sleep(0.4)
    call("winbtn", name="buttonShared")
    time.sleep(0.2)
    run("close.py", timeout=10)
    settle()
    talkto("Ashland")
    settle()


def st_inspector():
    board_job("Frontier Inspector", "I want the help of a frontier inspector")
    if "Loytel" not in " ".join(c.get("name", "") for c in state().get("nearby") or []):
        say("  check: Loytel not in view yet")


def st_punk():
    board_job("Defense Training")
    g = call("find", name="gallows", r=25, n=1)["data"]["hits"]
    if not g:
        stop("no gallows")
    walk(g[0]["x"] + 4, g[0]["z"] - 3, r=0, hp=1, timeout=10000)
    out = run("fight.py", "punk", timeout=90)
    say("  " + out[-90:].replace("\n", " "))
    settle()
    walk(55, 49, r=0, hp=1, timeout=10000)
    talkto("Ashland")
    settle()
    if not here("Pick all"):
        h = call("find", name="granite pebble", r=3, n=1)["data"]["hits"]
        if h:
            walk(h[0]["x"], h[0]["z"], r=0, hp=1, timeout=4000)
            here("Pick all")
    settle()


def st_boar():
    g = call("find", name="gallows", r=25, n=1)["data"]["hits"]
    walk(g[0]["x"] + 4, g[0]["z"] - 3, r=0, hp=1, timeout=10000)
    out = run("throw.py", "boar", "granite pebble", 30, 50, timeout=240)
    say("  " + out[-80:].replace("\n", " "))
    settle()
    run("loot.py", 10, "--all", timeout=120)
    settle()
    walk(55, 49, r=0, hp=1, timeout=10000)
    talkto("Ashland")
    settle()


def st_logs():
    board_job("Way of Crafter", optional=True)
    gather("cedar tree", "log", 8, 3, 30)
    if have("log") < 3:
        gather("tree", "log", 5, 3, 30)
    if have("log") < 3:
        stop(f"only {have('log')} logs")


def st_workbench():
    run("craft.py", "quick", "Workbench", "--force", timeout=30)
    settle()
    walk(57, 49, r=0, hp=1, timeout=8000)
    out = run("place.py", "workbench", "58,49", "58,50", "58,48", timeout=30)
    if "placed" not in out:
        stop("couldn't place the workbench: " + out[-120:])
    settle()
    talkto("Ashland")
    settle()


def bench():
    p = pc()
    b = call("find", name="workbench", r=60, n=1)["data"]["hits"][0]
    if max(abs(p["x"] - b["x"]), abs(p["z"] - b["z"])) > 1:
        walk_beside(b["x"], b["z"])
        p = pc()
    return b["x"] - p["x"], b["z"] - p["z"]


def st_torch():
    if have("vine") < 2:
        gather("vine bush", "vine", 2, 0, 30)
    rest_if_low(6)
    if have("resin") < 2:
        gather("cedar tree", "resin", 2, 2, 40)
    if have("branch") < 1:  # run 44: the resin came without one and "no torch worn" was the first sign
        gather("tree", "branch", 1, 2, 40)
    craft(*bench(), "String")
    craft(*bench(), "Torch")
    run("item.py", "torch", "Equip", timeout=20)
    settle()
    if not any("torch" in i["name"] and i.get("equipped") for i in data("inv")["items"]):
        stop("no torch worn")
    talkto("Ashland")
    settle()


def ring(x, z):
    """A 3x3 ring round x,z with the door on its west side: 8 walls: a 1x1 room passes the house check (run 41)."""
    cells = [(x - 1, z - 1), (x, z - 1), (x + 1, z - 1), (x + 1, z), (x + 1, z + 1), (x, z + 1), (x - 1, z + 1), (x - 1, z)]
    return [f"{a},{b}" for a, b in cells], f"{x - 1},{z}"


def st_house():
    if have("leaf") < 12 or have("grass") < 11:
        gather("weed", "leaf", 13, 3, 40)
    if have("grass") < 11:
        gather("weed", "grass", 11, 3, 40)
    craft(*bench(), "Grass wall", 8)
    craft(*bench(), "Grass door", 1)
    walls, door = ring(61, 51)
    out = run("place.py", "grass wall", *walls, timeout=60)
    if out.count("placed") < 8:
        stop("the walls: " + out[-140:])
    door_name = [i["name"] for i in data("inv")["items"] if i.get("id") == "door_grass"]
    out = run("place.py", door_name[0], door, timeout=20)
    if "placed" not in out:
        stop("the door: " + out[-120:])
    walk(56, 48, r=0, hp=1, timeout=10000)
    talkto("Ashland")
    settle()
    if not here("Pick all"):
        walk(58, 47, r=0, hp=1, timeout=4000)  # run 41: the rewards landed two cells off
        here("Pick all")
    settle()
    if not have("432"):
        h = call("find", name="training dummy", r=4, n=1)["data"]["hits"]
        if h:
            walk(h[0]["x"], h[0]["z"], r=0, hp=1, timeout=4000)
            here("Pick all")
        settle()
    if not have("432"):
        stop("no training dummy in the pack after the house")


def st_dummy():
    rest_if_low(6)
    fire = call("find", name="bonfire", r=25, n=1)["data"]["hits"]
    fx, fz = (fire[0]["x"], fire[0]["z"]) if fire else (56, 47)
    dummy, stand, bed = (fx + 1, fz - 1), (fx + 1, fz), (fx + 2, fz - 1)
    out = run("place.py", "training dummy", f"{dummy[0]},{dummy[1]}", timeout=20)
    if "placed" not in out:
        stop("the dummy: " + out[-120:])
    if have("leaf") < 4 or have("grass") < 2:  # run 44: short of leaves the bed was skipped in silence, and earlyday stopped at "no Sleep" 15 minutes later
        gather("weed", "leaf", 4, 2, 40)
        gather("weed", "grass", 2, 2, 40)
    if have("leaf") >= 4 and have("grass") >= 2:
        craft(*bench(), "Makeshift bed", 1)
        out = run("place.py", "makeshift bed", f"{bed[0]},{bed[1]}", timeout=20)
        if "placed" not in out:
            stop("the bed: " + out[-120:])
    BASE.write_text(json.dumps({"stand": list(stand), "bed": list(bed), "fire": [fx, fz]}) + "\n", encoding="utf-8", newline="\n")
    walk(*stand, r=0, hp=1, timeout=8000)
    say(f"  base: stand {stand}, bed {bed}, bonfire {(fx, fz)}")


def main():
    a = sys.argv[1:]
    first = a[a.index("--from") + 1] if "--from" in a else STAGES[0]
    last_stage = a[a.index("--to") + 1] if "--to" in a else STAGES[-1]
    todo = STAGES[STAGES.index(first):STAGES.index(last_stage) + 1]
    t0 = time.time()
    for name in todo:
        globals()["st_" + name]()
        p = pc()
        say(f"{name}: done at {time.time() - t0:.0f}s  SP {p['sp']}/{p.get('maxSp')}  hunger {p['hunger']}  {p['date']}")
        run("trial.py", "mark", f"opening: {name}", timeout=10)
    return 0


if __name__ == "__main__":
    sys.exit(main())
