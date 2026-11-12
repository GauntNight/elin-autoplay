"""Fast Travel from the world map (run 25: the current tile's own act "Fast Travel" opens LayerTravel,
a button per visited place with its ration cost and days; one click travels at once, no confirmation,
autosaved on arrival). The fare is travel rations (1 + hours/24); the list shows the exact count.
usage: python -I tools/fasttravel.py            list the places with their ration cost and days
       python -I tools/fasttravel.py NAME       travel to NAME (whole-word match; refuses two candidates,
                                                a cost over the rations carried, or a non-world-map zone)
Exit 0 travelled (or listed), 1 refused, 2 bridge error, 3 stopped (the list did not open).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import call, data, matches, refuse, run, setup, state, stop, wait_until  # noqa: E402


def rations():
    n = 0
    for i in call("inv")["data"]["items"]:
        if "travel ration" in i["name"].lower():
            n += int(i.get("num") or 1)
    return n


def open_list():
    acts = data("acts", dx=0, dz=0, mode="all").get("acts") or []
    ft = [a for a in acts if a["text"].startswith("Fast Travel")]
    if not ft:
        refuse("no 'Fast Travel' act on this tile (be on the world map, on your own tile): " + ", ".join(a["text"] for a in acts))
    call("do", i=ft[0]["i"])
    wait_until("layer", timeout=4000)
    bs = call("buttons")["data"]["buttons"]
    rows = []
    for b in bs:
        t = b.get("text") or ""
        m = re.match(r"^(.*?)\s*\|\s*(\d+)\s*\|\s*(\S+)$", t)
        if m:
            rows.append({"i": b["i"], "name": m.group(1).strip(), "rations": int(m.group(2)), "time": m.group(3), "text": t})
        elif b.get("card"):
            rows.append({"i": b["i"], "name": b["card"], "rations": None, "time": "", "text": t})
    if not rows:
        stop("the travel list did not open (top layer " + str(state().get("layers", {}).get("top")) + ")")
    return rows


def main():
    setup()
    z = state().get("zone") or {}
    zid = z.get("full") or z.get("id") or ""
    if "ntyris" not in zid:
        refuse(f"not on the world map ({zid}): leave.py first")
    have = rations()
    rows = open_list()
    if len(sys.argv) < 2:
        print(f"travel rations carried: {have}")
        for r in rows:
            print(f"  {r['name']:<32} {r['rations']!s:>3} rations  {r['time']}")
        call("closetop")
        return
    name = sys.argv[1]
    hits = [r for r in rows if r["name"].lower().replace("(home)", "") == name.lower()] or \
           [r for r in rows if re.search(r"\b" + re.escape(name.lower()) + r"\b", r["name"].lower())]
    if len(hits) != 1:
        call("closetop")
        refuse(f"{name!r} fits {len(hits)} places: " + ", ".join(h["name"] for h in hits))
    h = hits[0]
    if h["rations"] is not None and h["rations"] > have:
        call("closetop")
        refuse(f"{h['name']} costs {h['rations']} rations and I carry {have}")
    before = state().get("zone", {}).get("full")
    call("click", i=h["i"], expect=h["name"])
    for _ in range(15):  # run 26: the trip takes a few seconds; the first read still showed the world map
        wait_until("frames", n=60, timeout=8000)
        after = state()
        if after.get("zone", {}).get("full") != before:
            break
    zone = after.get("zone", {}).get("full")
    pc = after.get("pc", {})
    print(f"travelled to {h['name']} for {h['rations']} rations ({h['time']}): {before} -> {zone}; {pc.get('date')}; rations left {rations()}")
    if zone == before:
        stop("the zone did not change: read the log (look.py) before trying again")
    # run 45: a trip passes the 05:00 shipping pickup, and its report sat open over Olvina twice: every walk and talk after it
    # was refused ("no guard found", "Gizon is not in view") until close.py ran
    wait_until("frames", n=30, timeout=3000)
    if (state().get("layers") or {}).get("top") == "LayerShippingResult":
        run("close.py", timeout=60)
        print("  closed the shipping report the trip brought")


if __name__ == "__main__":
    main()
