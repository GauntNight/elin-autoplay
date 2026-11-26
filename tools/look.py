"""A compact summary of the bridge's `state`: player, zone, layers, dialog, creatures in
view, items here and nearby, and the newest log lines.

usage: python -I tools/look.py [log_lines]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402


def main():
    n_log = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        r = call("state")
    except OSError as e:
        sys.exit(f"bridge not reachable: {e}")
    if not r.get("ok"):
        sys.exit(f"bridge error: {r.get('error')}")
    d = r["data"]
    lay = d.get("layers") or {}
    print(f"frame {d['frame']}  top layer: {lay.get('top')}  open: {', '.join(lay.get('open') or [])}")
    # Some windows (the morning shipping report) aren't in the layer list but still block input:
    # any visible "button close" under a Layer means a window is open.
    try:
        bs = call("buttons", all=True)["data"]["buttons"]
        wins = sorted({b["path"].split("/")[0] for b in bs if b["name"] == "button close" and b.get("path", "").startswith("Layer")})
        if wins:
            print("!! WINDOW OPEN (blocks input): " + ", ".join(wins) + "  -> read it, then click its 'button close'")
    except (OSError, KeyError):
        pass
    dr = d.get("drama")
    if dr:
        print("DIALOG:", " / ".join(dr["text"]))
        for c in dr["choices"]:
            print(f"  [{c['i']}] {c['text']}")
    if not d.get("inGame"):
        print("(not in game)")
        return
    p, z = d["pc"], d["zone"]
    if isinstance(p, dict):
        cond = ",".join(p["conditions"]) or "-"
        print(f"{p['name']} Lv{p['lv']} ({p['exp']}/{p['expNext']})  HP {p['hp']}/{p['maxHp']}  "
              f"MP {p['mp']}/{p['maxMp']}  SP {p['sp']}/{p['maxSp']}  hunger {p['hunger']}  "
              f"@ {p['x']},{p['z']}  turn {p['turn']}  cond {cond}")
        print(f"gold {p.get('gold')}  gold bars {p.get('goldBars')}  date {p.get('date')}  held {p.get('held')}")
        print(f"hunger '{p.get('hungerText')}'  stamina '{p.get('staminaText')}'  ai {p.get('ai')}  actCount {p.get('actCount')}")
        # bridge 0.30.0 (the review of 2026-10-23): one line each when the field exists
        if p.get("burdenPhase") is not None:
            print(f"burden '{p.get('burdenText')}' (phase {p.get('burdenPhase')}, {p.get('burden')}/{p.get('burdenMax')})"
                  f"  sleep '{p.get('sleepText')}' (phase {p.get('sleepPhase')})  stacks {p.get('stacks')}")
        if p.get("return"):
            ret = p["return"]
            print(f"!! {'EVACUATION' if ret.get('evac') else 'RETURN'} counting down: {ret.get('turns')} turns left"
                  f"{' to ' + str(ret.get('dest')) if ret.get('dest') else ''} (never read another scroll)")
        if d.get("party"):
            print("party: " + "; ".join(f"{m.get('name')} Lv{m.get('lv')} {m.get('hp')}/{m.get('maxHp')}"
                                        + ("" if m.get("here") else " (not here)") for m in d["party"]))
        if d.get("allyDead"):
            print("!! ALLY DEAD on this map: " + ", ".join(d["allyDead"]))
    else:
        print("pc:", p)
    if isinstance(z, dict):
        print(f"zone: {z['full']} (danger {z['danger']}{', town' if z['town'] else ''}{', nefia' if z['nefia'] else ''})")
    # Survival first: say every threat out loud.
    if isinstance(p, dict):
        warn = []
        if p["hp"] * 100 < 60 * p["maxHp"]:
            warn.append(f"HP {p['hp']}/{p['maxHp']}")
        if p["sp"] < 5:
            warn.append(f"SP {p['sp']}")
        if p.get("hungerText") and p["hungerText"] not in ("", "Normal", "Filled"):
            warn.append(p["hungerText"])
        for c in d.get("nearby") or []:
            if c["hostile"] and (c["lv"] > p["lv"] + 2 or c["dist"] <= 2):
                warn.append(f"hostile {c['name']} Lv{c['lv']} at {c['dist']}")
        benign = ("ConSleep", "ConWet", "ConBandage", "ConRest", "ConMeditate")
        bad = [x for x in p["conditions"] if x not in benign]
        for c in d.get("nearby") or []:
            if c["party"] and c["hpPct"] < 40:
                warn.append(f"{c['name']} at {c['hpPct']}% HP")
        if bad:
            warn.append("conditions " + ",".join(bad))
        # run 11: an overloaded pack bled me 75 -> 30 HP in an afternoon unnoticed. Burden isn't a
        # condition; the HUD shows its label. At phase 3+ each turn has a 1 in 30 chance (1 in 100
        # on the world map) of MaxHP x weight% / 1000 + 1 damage (Chara.TickConditions): unload now
        if p.get("burdenPhase") is not None:  # bridge 0.30.0
            if p["burdenPhase"] >= 1:
                warn.append(f"weight: {p.get('burdenText')} (phase {p['burdenPhase']}; 3+ costs HP: stash or drop heavy items)")
        else:
            try:
                hud = call("texts", all=True)["data"]["texts"]
                heavy = [t for t in hud if t.strip().rstrip("!") in ("Burden", "Heavy Burden", "Overweight",
                                                                      "Very Overweight", "Squashed")]
                if heavy:
                    warn.append(f"weight: {heavy[0].strip()} (phase 3+ costs HP: stash or drop heavy items)")
            except Exception:
                pass
        # run 35 (fact #1093): over the ally cap, the whole party loses 20% speed
        try:
            from common import party_cap
            allies, cap, cha = party_cap(d)
            if allies > cap:
                warn.append(f"party {allies} over the ally cap {cap} (CHA {cha}): -20% speed for all")
        except Exception:  # noqa: BLE001 (a look must not fail on a side check)
            pass
        # run 35 (facts #1098-#1099): a CHA drain and a twisted-legs mutation went unseen for a run (bridge 0.36.0)
        try:
            sk = call("skills").get("data") or {}
            if sk.get("drains"):
                warn.append("drained " + ", ".join(f"{k} {v}" for k, v in sk["drains"].items())
                            + " (restore body: STR DEX END CHA; restore mind: PER LER WIL MAG)")
            from common import mutation_split
            bad, good = mutation_split(sk)
            if bad:
                warn.append("harmful mutation: " + ", ".join(m["name"] for m in bad.values()) + " (a potion of cure mutation"
                            + (f"; a plain one may take {', '.join(m['name'] for m in good.values())} instead" if good else "")
                            + ")")
            # run 57: Weakening (max HP -20%, melee halved) rode through a dig tour unseen: look.py named drains and
            # mutations but no ether disease. ladder.ether_check's allowed list says which ones are kept on purpose
            try:
                from ladder import ETHER_OK
            except Exception:  # noqa: BLE001
                ETHER_OK = ()
            eth = [e["name"] for e in (sk.get("ether") or {}).values()
                   if e.get("id") not in ETHER_OK and e.get("name") not in ETHER_OK]
            if eth:
                warn.append("ether disease: " + ", ".join(eth) + f" (corruption {sk.get('corruption')}: an ether antibody)")
        except Exception:  # noqa: BLE001
            pass
        # run 36: the Ocean Bucket and the Practice Ring were worn cursed from run 35 or earlier and the axe was hexed
        # in run 36 (Hit and damage down): one scroll of uncurse cleared all four; a worn cursed piece is named here
        try:
            cursed = [i["name"] for i in call("inv").get("data", {}).get("items") or []
                      if i.get("equipped") and ("cursed" in i["name"].lower() or "doomed" in i["name"].lower())]
            if cursed:
                warn.append("cursed gear worn: " + ", ".join(cursed) + " (read a scroll of uncurse)")
        except Exception:  # noqa: BLE001
            pass
        if warn:
            print("!! DANGER: " + "; ".join(warn))
    for c in d.get("nearby") or []:
        tag = "HOSTILE" if c["hostile"] else ("party" if c["party"] else "")
        print(f"  creature {c['name']} ({c['id']}) Lv{c['lv']} d=({c['dx']},{c['dz']}) hp {c['hpPct']}% {tag}")
    here = d.get("here") or []
    if here:
        print("here:", "; ".join(f"{t['name']} x{t['num']}" for t in here))
    things = [t for t in d.get("things") or [] if (t["dx"], t["dz"]) != (0, 0)]
    if things:
        print("nearby things:", "; ".join(f"{t['name']} ({t['dx']},{t['dz']}){'' if not t['installed'] else ' inst'}" for t in things[:15]))
    # Worth a detour on any map, seen or not from here (the user, run 05: an armour shrine's
    # glowing shield on an ambush map went unnoticed; run 04: chests and wrecks). Shrines:
    # armor = +1 armour enchant, replenish = full heal, knowledge = a book, invention = a recipe,
    # strife = a boss and 3-4 monsters (avoid unless strong).
    if not d.get("zone", {}).get("town"):
        notable = []
        for word in ("shrine", "treasure", "chest", "wreck", "altar"):
            rep = call("find", name=word, r=99, n=4)
            for h in (rep.get("data") or {}).get("hits") or []:
                if h["kind"] != "chara" and not (word == "chest" and any(w in h["name"] for w in ("shipping", "tax", "box"))):
                    notable.append(f"{h['name']} ({h['dx']},{h['dz']})")
        if notable:
            print("!! NOTABLE on this map:", "; ".join(dict.fromkeys(notable)))
    # the user, 2026-10-29: Small Medals lie hidden at the wiki's fixed spots on towns and named places
    # (knowledge/medals.md); only on those maps, where the spots are public (medals.py's honesty rule)
    from medals import WIKI_MAPS, find_medals, wiki_map
    m = wiki_map(d.get("zone"))
    if m:
        here_now = find_medals()
        if here_now:
            print(f"!! MEDALS: {len(here_now)} Small Medal(s) on explored cells of {m} (the wiki lists "
                  f"{WIKI_MAPS[m]}): medals.py --take")
    log = d.get("log") or []
    if log and n_log:
        print("log:")
        for line in log[-n_log:]:
            print("  " + line)


if __name__ == "__main__":
    main()
