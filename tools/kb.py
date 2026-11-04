"""Knowledge graph for Elin: the game's own data tables (exported through the bridge) joined
with what was observed in play (knowledge/facts.jsonl). Answers "how do I make X", "what uses
X", "what does station S make", "what do I know about X" without re-reading game code.

usage: python -I tools/kb.py build                  export the game tables (game running), build graph
       python -I tools/kb.py find TEXT [N]          nodes whose id or name matches, best first
       python -I tools/kb.py show TEXT|KEY          one node: fields, edges in and out, observed facts
       python -I tools/kb.py make TEXT              how to make it: station and ingredients
       python -I tools/kb.py uses TEXT              what needs it as an ingredient
       python -I tools/kb.py station TEXT           what a crafting station makes
       python -I tools/kb.py facts [TEXT] [--all]   observed facts (matching TEXT; --all: superseded too)
       python -I tools/kb.py add S P O --run 03 [--where W] [--note N] [--supersedes N,M]
                                                    record an observed fact; --supersedes hides the
                                                    older facts (by line number) from facts, ask, show
       python -I tools/kb.py embed                  (re)build the semantic index (repo-local Ollama)
       python -I tools/kb.py ask TEXT [N] [--notes|--game]   plain-language search, best first
       python -I tools/kb.py stats                  counts for a session summary: nodes, edges, facts
       python -I tools/kb.py bench [--log RUN]      size and speed of the graph and the semantic index
                                                    (--log: a row in runs/index.csv for the run tracker)

Keys look like thing:roasted_fruit's id (thing:103), chara:chicken, element:10, category:fruit.
The exported tables and graph live in knowledge/game/ (gitignored: game data, rebuilt per game
version); observed facts live in knowledge/facts.jsonl (committed).
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "knowledge" / "game"
FACTS = ROOT / "knowledge" / "facts.jsonl"
VEC = ROOT / "knowledge" / "vectors"
# The repo-local Ollama (tools/ollama_serve.sh): models live in .ollama/ inside this repo.
OLLAMA = os.environ.get("ELIN_OLLAMA", "http://127.0.0.1:11435")
EMBED_MODEL = "nomic-embed-text"
INSTALL_VERSION = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Elin\version.json")

# Table -> node kind. Language tables, render-only tables and `backers` (real people) are left out.
TABLES = {
    "things": "thing", "charas": "chara", "elements": "element", "objs": "obj", "zones": "zone",
    "categories": "category", "recipes": "recipe", "races": "race", "jobs": "job",
    "materials": "material", "blocks": "block", "floors": "floor", "quests": "quest",
    "persons": "person", "religions": "religion", "factions": "faction", "hobbies": "hobby",
    "homeResources": "homeres", "researches": "research", "collectibles": "collectible",
    "keyItems": "keyitem", "stats": "stat", "spawnLists": "spawnlist", "zoneAffixes": "affix",
    "areas": "area", "tactics": "tactics",
}
NO_STATION = {"", "-", "x"}


# ---------- build ----------

def export():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from bridge import call  # noqa: E402
    GAME.mkdir(parents=True, exist_ok=True)
    counts = call("sources")["data"]["tables"]
    for table in TABLES:
        rows, off = [], 0
        while off < counts.get(table, 0):
            d = call("sources", table=table, offset=off, limit=400)["data"]
            rows += d["rows"]
            off += 400
        (GAME / f"{table}.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        print(f"  {table}: {len(rows)}")
    ver = {}
    try:
        ver = json.loads(INSTALL_VERSION.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        pass
    bridge = call("ping")["data"]["version"]
    manifest = {"exported": time.strftime("%Y-%m-%d %H:%M"), "game": ver, "bridge": bridge,
                "counts": {t: counts.get(t, 0) for t in TABLES}}
    (GAME / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")


def node_id(row):
    return str(row.get("id", row.get("_index", "")))


def parse_ingredient(text):
    """'ingot/2' -> count 2; '+#seasoning' -> optional category; 'potato|784' -> alternatives;
    'grass/5|pasture' -> 5 grass or pasture (RecipeSource.cs: split on '|' first, then the
    first alternative's '/count')."""
    alts_raw = text.split("|")
    first = alts_raw[0]
    optional = False
    cat = False
    while first[:1] in ("+", "#", "$"):
        optional |= first[0] == "+"
        cat |= first[0] == "#"
        first = first[1:]
    count = 1
    if "/" in first:
        first, n = first.split("/", 1)
        count = int(n) if n.isdigit() else 1
    first = first.split("@")[0]
    # A leading '#' makes the whole ingredient category-based, alternatives included:
    # "#meat|bodyparts|mushroom" = any meat, body part or mushroom.
    alts = [("category" if cat else "id", a) for a in [first] + alts_raw[1:]]
    return alts, count, optional


def build_graph():
    rows = {t: json.loads((GAME / f"{t}.json").read_text(encoding="utf-8"))
            for t in TABLES if (GAME / f"{t}.json").exists()}
    nodes, edges = {}, []
    by_thing, by_trait = {}, {}
    for table, kind in TABLES.items():
        for r in rows.get(table, []):
            key = f"{kind}:{node_id(r)}"
            nodes[key] = {"name": r.get("name") or r.get("alias") or node_id(r), "table": table,
                          "alias": r.get("alias")}
            if kind == "thing":
                by_thing[node_id(r)] = key
                if r.get("trait"):  # recipe stations are named by trait: Mill, Fortune (RollingFortune)
                    by_trait.setdefault(r["trait"][0].lower(), key)
    for r in rows.get("elements", []):  # elements are also known by alias (nutrition, STR, ...)
        if r.get("alias"):
            by_thing.setdefault("el:" + r["alias"], f"element:{node_id(r)}")

    def resolve(kind_hint, ident):
        if kind_hint == "category" and f"category:{ident}" in nodes:
            return f"category:{ident}"
        for k in (by_thing.get(ident), f"category:{ident}", f"obj:{ident}", f"block:{ident}",
                  f"floor:{ident}", f"chara:{ident}"):
            if k and k in nodes:
                return k
        return f"raw:{ident}"

    def station(f):
        k = by_thing.get(f) or by_thing.get(f.lower()) or by_trait.get(f.lower())             or next((v for t, v in sorted(by_trait.items()) if t.endswith(f.lower())), None)
        if k:
            return k
        key = f"station:{f}"
        nodes.setdefault(key, {"name": f, "table": "-"})
        return key

    for table, kind in TABLES.items():
        for r in rows.get(table, []):
            key = f"{kind}:{node_id(r)}"
            fac = r.get("factory")
            facs = fac if isinstance(fac, list) else ([fac] if fac else [])
            for f in facs:
                if f in NO_STATION:
                    continue
                edges.append([key, "made_at", "station:by hand" if f == "self" else station(f), {}])
                nodes.setdefault("station:by hand", {"name": "by hand (Quick Craft)", "table": "-"})
            comps = r.get("components") or []
            if table == "recipes":
                comps = [i for part in ("ing1", "ing2", "ing3") for i in (r.get(part) or [])]
                if r.get("thing"):
                    edges.append([key, "makes", resolve("id", r["thing"]), {"num": r.get("num")}])
            pred = "made_of" if kind in ("obj",) else "needs"
            for slot, comp in enumerate(c for c in comps if c and c != "-"):
                alts, count, optional = parse_ingredient(comp)
                for kh, ident in alts:
                    edges.append([key, pred, resolve(kh, ident),
                                  {"count": count, "optional": optional, "slot": slot, "alts": len(alts)}])
            if kind == "thing" and r.get("_origin"):
                # Recipes match an ingredient id against an item's id OR its origin (Recipe.cs):
                # "fruit" accepts a blueberry because its origin is fruit.
                edges.append([key, "variant_of", resolve("id", r["_origin"]), {}])
            if r.get("category") and kind in ("thing", "obj", "block", "floor"):
                edges.append([key, "is_a", resolve("category", r["category"]), {}])
            if kind == "category" and r.get("parent"):
                edges.append([key, "is_a", f"category:{r['parent']}", {}])
            if kind == "zone" and r.get("parent"):
                edges.append([key, "in", f"zone:{r['parent']}", {}])
            if kind == "chara":
                for p in ("race", "job"):
                    if r.get(p) and not str(r[p]).startswith("*"):
                        edges.append([key, p, f"{p}:{r[p]}", {}])
            el = r.get("elements") or []
            if kind in ("thing", "chara") and len(el) % 2 == 0:
                for i in range(0, len(el), 2):
                    edges.append([key, "has", f"element:{el[i]}", {"value": el[i + 1]}])
    (GAME / "graph.json").write_text(json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False),
                                     encoding="utf-8")
    print(f"graph: {len(nodes)} nodes, {len(edges)} edges")


# ---------- query ----------

class KB:
    def __init__(self):
        path = GAME / "graph.json"
        if not path.exists():
            sys.exit("no graph yet: run `kb.py build` with the game running")
        g = json.loads(path.read_text(encoding="utf-8"))
        self.nodes, self.edges = g["nodes"], g["edges"]
        self.out, self.inn = defaultdict(list), defaultdict(list)
        for e in self.edges:
            self.out[e[0]].append(e)
            self.inn[e[2]].append(e)
        self._rows = {}

    def row(self, key):
        n = self.nodes.get(key)
        if not n or n["table"] == "-":
            return {}
        t = n["table"]
        if t not in self._rows:
            self._rows[t] = {f"{TABLES[t]}:{node_id(r)}": r
                             for r in json.loads((GAME / f"{t}.json").read_text(encoding="utf-8"))}
        return self._rows[t].get(key, {})

    def label(self, key):
        n = self.nodes.get(key)
        return f"{n['name']} [{key}]" if n else f"[{key}]"

    def find(self, text, n=10, kinds=None):
        t = text.lower().strip()
        if t in self.nodes:
            return [t]
        scored = []
        for key, nd in self.nodes.items():
            if kinds and key.split(":")[0] not in kinds:
                continue
            name = str(nd["name"]).lower()
            ident = key.split(":", 1)[1].lower()
            alias = str(nd.get("alias") or "").lower()
            if t in (name, ident, alias):
                s = 0
            elif name.startswith(t):
                s = 1
            elif t in name or t in alias:
                s = 2
            elif t in ident:
                s = 3
            else:
                continue
            kind_rank = ["thing", "chara", "obj", "category", "element", "zone"].index(key.split(":")[0]) \
                if key.split(":")[0] in ["thing", "chara", "obj", "category", "element", "zone"] else 9
            scored.append((s, kind_rank, len(name), key))
        return [k for *_, k in sorted(scored)][:n]

    def one(self, text, kinds=None):
        hits = self.find(text, 1, kinds)
        if not hits:
            sys.exit(f"nothing matches {text!r}")
        return hits[0]

    def element_text(self, key):
        parts = []
        for _, _, el, meta in (e for e in self.out[key] if e[1] == "has"):
            parts.append(f"{self.nodes.get(el, {}).get('name', el)} {meta.get('value')}")
        return ", ".join(parts)


# One name per place in `where` (run 12 review: "Meadow (home)", "home (Meadow)", "home" and
# "Meadow" were four names for one zone, so stats and searches split it). Coordinates go in
# the fact's `at` or its text, not in `where`.
WHERE_ALIASES = {
    "meadow": "Meadow", "home": "Meadow", "meadow (home)": "Meadow", "home (meadow)": "Meadow",
    "home board": "Meadow", "tinker's camp": "Tinker's Camp", "tinkers camp": "Tinker's Camp",
    "north tyris": "North Tyris", "world map": "North Tyris",
}
# One subject per NPC or thing that the facts named several ways; the right side should be a
# graph node's name when one exists (kb.py find NAME).
SUBJECT_ALIASES = {
    "aliyun the mage": "Aliyun", "aliyun the mage (tinker's camp)": "Aliyun", "aliyun (tinker's camp)": "Aliyun",
    "aliyun's identification": "Aliyun", "aliyun (identify)": "Aliyun",
    "nino the caravan master": "Nino", "casaneck the scholar": "Casaneck", "pery the trainer": "Pery",
    "fiama (home)": "Fiama", "fiama (home resident)": "Fiama", "minron the healer": "Minron",
    "nazs the secretary": "Nazs", "gizbird the goods shopkeeper": "Gizbird", "ilass the blacksmith": "Ilass",
    "kaberg the little girl": "Kaberg", "shared sturdy box 56,51": "shared sturdy box",
    "olvina board": "Olvina quest board", "world-map ambush": "world map step", "world-map ambushes": "world map step",
    "world map travel": "world map step", "world map movement": "world map step",
}


def canon_where(w):
    if not w:
        return w
    key = w.strip().lower()
    key = key.split(" (")[0] if key.split(" (")[0] in WHERE_ALIASES else key
    return WHERE_ALIASES.get(key, w.strip())


def canon_subject(subj):
    return SUBJECT_ALIASES.get((subj or "").strip().lower(), subj)


def all_facts():
    """Every fact with its 1-based line number as `id`, superseded ones marked."""
    if not FACTS.exists():
        return []
    out = []
    for n, line in enumerate(FACTS.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        f = json.loads(line)
        f["id"] = n
        out.append(f)
    gone = {}
    for f in out:
        for old in (f.get("supersedes") or []):
            gone[int(old)] = f["id"]
    for f in out:
        if f["id"] in gone:
            f["superseded_by"] = gone[f["id"]]
    return out


def facts(match=None, include_superseded=False):
    """Facts matching TEXT (every word of each pattern must appear; the canonical subject and
    place count too). Superseded facts are left out unless asked for: a stale price or rule used
    to come back from `facts`, `show` and `ask` beside its correction (run 12 review)."""
    out = []
    pats = [m.lower() for m in (match if isinstance(match, list) else [match])] if match else []
    for f in all_facts():
        if f.get("superseded_by") and not include_superseded:
            continue
        blob = " ".join(str(v) for k, v in f.items() if k not in ("id", "supersedes", "superseded_by")).lower()
        blob += " " + str(canon_subject(f["s"])).lower() + " " + str(canon_where(f.get("where"))).lower()
        if not pats or any(all(w in blob for w in m.split()) for m in pats):
            out.append(f)
    return out


QUAL_RE = re.compile(r"\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*$")


def norm_pred(p):
    """The review of 2026-10-30: 584 distinct predicates among 1,045 facts, 472 of them used once, because dates and
    qualifiers rode inside the predicate ("stock (489-10-09)", "sold at (486-08-24)", "rule (code)"). The predicate
    keeps the relation; a trailing parenthetical becomes the fact's `qual`. Returns (predicate, qual or None)."""
    p = re.sub(r"\s+", " ", str(p).strip(" -"))
    m = QUAL_RE.search(p)
    if m and m.start() > 0:
        return p[:m.start()].rstrip(), m.group(1).strip()
    return p, None


def fact_line(f):
    where = f" @ {canon_where(f['where'])}" if f.get("where") else ""
    note = f" ({f['note']})" if f.get("note") else ""
    old = f"  (superseded by #{f['superseded_by']})" if f.get("superseded_by") else ""
    qual = f" ({f['qual']})" if f.get("qual") else ""
    return f"  [{f.get('run', '?')}] #{f.get('id', '?')} {f['s']} --{f['p']}{qual}--> {f['o']}{where}{note}{old}"


def ingredient_text(kb, e):
    meta = e[3]
    tgt = kb.label(e[2])
    extra = []
    if meta.get("count", 1) != 1:
        extra.append(f"x{meta['count']}")
    if meta.get("optional"):
        extra.append("optional")
    if meta.get("alts", 1) > 1:
        extra.append(f"or-group {meta.get('slot')}")
    return tgt + (" (" + ", ".join(extra) + ")" if extra else "")


def show(kb, key):
    r = kb.row(key)
    print(kb.label(key))
    keep = ["category", "value", "LV", "weight", "detail", "trait", "tag", "recipeKey", "hostility",
            "race", "job", "type", "parent", "reqHarvest", "objType", "offense", "defense", "HP"]
    for k in keep:
        if k in r:
            v = r[k]
            print(f"  {k}: {', '.join(map(str, v)) if isinstance(v, list) else v}")
    els = kb.element_text(key)
    if els:
        print(f"  elements: {els}")
    groups = defaultdict(list)
    for e in kb.out[key]:
        if e[1] != "has":
            groups[e[1]].append(ingredient_text(kb, e) if e[1] in ("needs", "made_of") else kb.label(e[2]))
    for p, items in groups.items():
        print(f"  {p}: " + "; ".join(items[:20]) + (f" ... +{len(items) - 20}" if len(items) > 20 else ""))
    back = defaultdict(list)
    for e in kb.inn[key]:
        back[e[1]].append(kb.label(e[0]))
    for p, items in back.items():
        print(f"  <-{p}: " + "; ".join(items[:12]) + (f" ... +{len(items) - 12}" if len(items) > 12 else ""))
    if key.startswith("chara:"):  # run 16 (the user): a threat profile per kind, not one line by level
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import threat
            tp = threat.profile(key.split(":", 1)[1])
            if tp:
                print("  threat: " + threat.card(tp).split(": ", 1)[1])
            # the user (run 29): every fight logged, summarised per monster in the graph (tools/fightlog.py)
            import fightlog
            fl = fightlog.line(str(kb.nodes[key]["name"]))
            if fl:
                print("  fights: " + fl.split(": ", 1)[1])
        except Exception as e:  # noqa: BLE001 - the profile is extra; show the node anyway
            print(f"  threat: unavailable ({e})")
    name = str(kb.nodes[key]["name"])
    # Match facts by a real name only: a numeric name ("58") would hit map cells like 58,50.
    fs = facts([key] + ([name] if len(name) >= 3 and not name.isdigit() else []))
    if fs:
        print("  observed:")
        for f in fs:
            print("  " + fact_line(f))


def make(kb, key):
    print(kb.label(key))
    sts = [kb.label(e[2]) for e in kb.out[key] if e[1] == "made_at"]
    print("  made at: " + ("; ".join(sts) if sts else "no station listed (found, bought or dropped)"))
    for e in kb.out[key]:
        if e[1] in ("needs", "made_of"):
            print("  needs: " + ingredient_text(kb, e))
            rel = "is_a" if e[2].startswith("category:") else "variant_of"
            members = [kb.nodes[x[0]]["name"] for x in kb.inn[e[2]] if x[1] == rel and x[0].startswith("thing:")]
            if members:
                print("     any of: " + ", ".join(sorted(set(map(str, members)))[:15])
                      + (f" ... +{len(set(members)) - 15}" if len(set(members)) > 15 else ""))
    for e in kb.inn[key]:
        if e[1] == "makes":
            print("  also made by " + kb.label(e[0]))


# ---------- semantic index (Ollama embeddings) ----------

def note_chunks(path, src):
    """Bullets, numbered items and table rows of a markdown file, wrapped lines joined, each
    prefixed by its heading."""
    out, cur, heading = [], None, ""

    def flush():
        nonlocal cur
        if cur and len(cur) > 12:
            out.append((src, (heading + ": " if heading else "") + cur.strip()))
        cur = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            flush()
            heading = line.strip("# ").strip()
        elif line.startswith("|---") or line.startswith("| Food") or line.startswith("| Need"):
            continue
        elif line.startswith(("- ", "| ")) or re.match(r"\d+\. ", line):
            flush()
            cur = line.strip("|- ").replace(" | ", "; ").strip()
        elif line.startswith("  ") and cur is not None:
            cur += " " + line.strip()
        elif not line.strip() or line.startswith("---") or line.startswith("```"):
            flush()
        elif not line.startswith(("name:", "description:")):
            cur = (cur + " " + line.strip()) if cur else line.strip()
    flush()
    return out


def corpus(kb):
    docs = [("fact", fact_line(f).strip()) for f in facts()]
    for path, src in [(ROOT / "knowledge" / "lessons.md", "lesson"), (ROOT / "knowledge" / "foods.md", "food"),
                      (ROOT / "knowledge" / "wiki-primer.md", "primer"),
                      (ROOT / "knowledge" / "power-model.md", "power"),
                      (ROOT / "knowledge" / "goals.md", "goals")]:  # long-term goals (run 04)
        if path.exists():
            docs += note_chunks(path, src)
    for path in sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md")):
        docs += note_chunks(path, "skill:" + path.parent.name)
    for path in sorted((ROOT / "runs").glob("*.md")):
        docs += note_chunks(path, "run:" + path.stem)
    # one line per monster kind from knowledge/fights.csv (the user, run 29: "per monster in graph is perfect")
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import fightlog
        docs += [("fights", fightlog.line(k, v)) for k, v in fightlog.summary().items()]
    except Exception as e:  # noqa: BLE001 - the index still builds without them
        print(f"fights not indexed: {e}")
    # The game's own text, with recipe and nutrition facts from the graph spelled out.
    for key, nd in kb.nodes.items():
        kind = key.split(":")[0]
        if kind not in ("thing", "chara", "quest", "element", "zone", "obj"):
            continue
        r = kb.row(key)
        name = str(nd["name"])
        if not name or name.startswith("*"):
            continue
        if kind == "element" and not r.get("detail"):
            continue
        bits = [f"{name} ({kind}" + (f", {r['category']}" if r.get("category") else "") + ")."]
        if r.get("detail"):
            bits.append(str(r["detail"]).replace("|", " "))
        st = [kb.nodes.get(e[2], {}).get("name") for e in kb.out[key] if e[1] == "made_at"]
        ings = [ingredient_text(kb, e).split(" [")[0] for e in kb.out[key] if e[1] in ("needs", "made_of")]
        if st:
            bits.append(f"Made at {', '.join(map(str, st))}" + (f" from {', '.join(ings)}." if ings else "."))
        elif ings and kind == "obj":
            bits.append(f"Gives {', '.join(ings)}.")
        els = kb.element_text(key)
        if els and kind == "thing":
            bits.append(f"Has {els}.")
        if kind == "chara":
            bits.append(f"Level {r.get('LV', 1)}, {r.get('hostility', '')}, race {r.get('race', '')}, job {r.get('job', '')}.")
        docs.append(("game:" + kind, " ".join(bits)))
    return docs


def ollama(path, payload, timeout=600):
    req = urllib.request.Request(OLLAMA + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def embed_texts(texts, kind):
    prefix = "search_query: " if kind == "query" else "search_document: "  # nomic-embed-text
    out = []
    for i in range(0, len(texts), 64):
        out += ollama("/api/embed", {"model": EMBED_MODEL,
                                     "input": [prefix + t[:2000] for t in texts[i:i + 64]]})["embeddings"]
    return out


def build_index(kb):
    import numpy as np
    VEC.mkdir(parents=True, exist_ok=True)
    old = {}
    if (VEC / "docs.json").exists() and (VEC / "vectors.npy").exists():
        od = json.loads((VEC / "docs.json").read_text(encoding="utf-8"))
        ov = np.load(VEC / "vectors.npy")
        old = {d["h"]: ov[i] for i, d in enumerate(od)}
    uniq, seen = [], set()
    for src, text in corpus(kb):
        h = hashlib.sha1((src + "\n" + text).encode("utf-8")).hexdigest()[:16]
        if h not in seen:
            seen.add(h)
            uniq.append({"src": src, "text": text, "h": h})
    todo = [r for r in uniq if r["h"] not in old]
    t0 = time.time()
    if todo:
        for r, v in zip(todo, embed_texts([r["text"] for r in todo], "doc")):
            old[r["h"]] = np.asarray(v, dtype=np.float32)
    mat = np.stack([old[r["h"]] for r in uniq]).astype(np.float32)
    mat /= np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9
    np.save(VEC / "vectors.npy", mat)
    (VEC / "docs.json").write_text(json.dumps(uniq, ensure_ascii=False), encoding="utf-8")
    print(f"index: {len(uniq)} entries ({len(todo)} embedded in {time.time() - t0:.0f}s, rest cached)")


def ask(text, n, only):
    if not (VEC / "docs.json").exists():
        sys.exit("no index yet: start tools/ollama_serve.sh, then kb.py embed")
    docs = json.loads((VEC / "docs.json").read_text(encoding="utf-8"))
    keep = [i for i, d in enumerate(docs)
            if only is None or (only == "notes") != d["src"].startswith("game:")]
    try:
        import numpy as np
        q = np.asarray(embed_texts([text], "query")[0], dtype=np.float32)
        q /= np.linalg.norm(q) + 1e-9
        scores = np.load(VEC / "vectors.npy")[keep] @ q
        hits = [(float(scores[j]), docs[keep[j]]) for j in np.argsort(-scores)[:n]]
        how = "semantic"
    except (OSError, ValueError) as e:  # server down: keyword overlap over the same entries
        words = set(re.findall(r"[a-z0-9]+", text.lower()))
        sc = [(len(words & set(re.findall(r"[a-z0-9]+", docs[i]["text"].lower()))) / (len(words) or 1), docs[i])
              for i in keep]
        hits = sorted(sc, key=lambda t: -t[0])[:n]
        how = f"keyword fallback ({e.__class__.__name__}: is tools/ollama_serve.sh running?)"
    print(f"[{how}]")
    for sc, d in hits:
        t = d["text"]
        print(f"{sc:.2f} {d['src']:14} {t[:240]}{'...' if len(t) > 240 else ''}")


def stats(kb):
    """The numbers a session summary quotes (runs/*-summary.md): graph size by node kind and by
    relation, the biggest kind-to-kind links, observed facts by run, predicate and place."""
    kinds = Counter(k.split(":")[0] for k in kb.nodes)
    print(f"graph: {len(kb.nodes):,} nodes, {len(kb.edges):,} edges, {len(kinds)} node kinds")
    print("nodes: " + ", ".join(f"{k} {n:,}" for k, n in kinds.most_common()))
    print("edges: " + ", ".join(f"{r} {n:,}" for r, n in Counter(e[1] for e in kb.edges).most_common()))
    links = Counter((e[0].split(":")[0], e[1], e[2].split(":")[0]) for e in kb.edges)
    print("links: " + ", ".join(f"{a}-{r}->{b} {n:,}" for (a, r, b), n in links.most_common(16)))
    fs = facts()
    names = {str(n.get("name", "")).lower() for n in kb.nodes.values()}
    print(f"facts: {len(fs)} live, {len(all_facts()) - len(fs)} superseded "
          f"({sum(canon_subject(f['s']).lower() in names for f in fs)} subjects name a node)")
    print("  by run: " + ", ".join(f"{r} {n}" for r, n in sorted(Counter(f["run"] for f in fs).items())))
    print("  by predicate: " + ", ".join(f"{p} {n}" for p, n in Counter(f["p"] for f in fs).most_common(8)))
    print("  by place: " + ", ".join(f"{w} {n}" for w, n in Counter(
        canon_where(f.get("where")) or "none" for f in fs).most_common(6)))
    if (VEC / "vectors.npy").exists():
        print(f"semantic index: {((VEC / 'vectors.npy').stat().st_size - 128) // (768 * 4):,} entries (approx)")


INDEX_LOG = ROOT / "runs" / "index.csv"
BENCH_QUERIES = ["what heals HP quickly", "where do I pay the tax bill", "how do I make a wooden box",
                 "what killed me in a nefia", "which foods are harmful to eat"]


def bench(log_run=None):
    """Size and speed of the knowledge base for the run tracker (the user, 2026-10-20: "track the
    size/speed of the Semantic Index"): graph nodes and edges, live facts, index entries and MB on
    disk, load times, and the median query split into the Ollama embedding and the search itself."""
    import numpy as np
    t0 = time.perf_counter()
    kb = KB()
    graph_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    docs = json.loads((VEC / "docs.json").read_text(encoding="utf-8"))
    mat = np.load(VEC / "vectors.npy")
    load_ms = (time.perf_counter() - t0) * 1000
    mb = sum((VEC / f).stat().st_size for f in ("docs.json", "vectors.npy")) / 1e6
    embed_ms, search_ms = [], []
    try:
        embed_texts(["warm-up"], "query")  # the first call after a quiet spell loads the model
        for q in BENCH_QUERIES:
            t0 = time.perf_counter()
            v = np.asarray(embed_texts([q], "query")[0], dtype=np.float32)
            t1 = time.perf_counter()
            v /= np.linalg.norm(v) + 1e-9
            np.argsort(-(mat @ v))[:8]
            search_ms.append((time.perf_counter() - t1) * 1000)
            embed_ms.append((t1 - t0) * 1000)
    except OSError as e:
        print(f"ollama not answering ({e.__class__.__name__}): query times left blank")
    med = lambda xs: round(sorted(xs)[len(xs) // 2], 1) if xs else ""  # noqa: E731
    row = {"run": log_run or "", "date": time.strftime("%Y-%m-%d %H:%M"), "nodes": len(kb.nodes),
           "edges": len(kb.edges), "facts_live": len(facts()), "index_entries": len(docs),
           "index_mb": round(mb, 1), "graph_load_s": round(graph_s, 2), "index_load_ms": round(load_ms),
           "query_embed_ms": med(embed_ms), "query_search_ms": med(search_ms), "embed_model": EMBED_MODEL}
    print(f"graph {row['nodes']:,} nodes, {row['edges']:,} edges, loads in {row['graph_load_s']} s; "
          f"{row['facts_live']} live facts")
    print(f"index {row['index_entries']:,} entries, {row['index_mb']} MB, loads in {row['index_load_ms']} ms; "
          f"a query: {row['query_embed_ms']} ms to embed + {row['query_search_ms']} ms to search "
          f"(median of {len(embed_ms)})")
    if log_run:
        import csv
        new = not INDEX_LOG.exists()
        with INDEX_LOG.open("a", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(row), lineterminator="\n")
            if new:
                w.writeheader()
            w.writerow(row)
        print(f"logged to {INDEX_LOG.relative_to(ROOT)}")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    op, args = sys.argv[1], sys.argv[2:]
    if op == "build":
        export()
        build_graph()
        return
    if op == "graph":  # rebuild the graph from already exported tables
        build_graph()
        return
    if op == "add":
        opts = {}
        pos = []
        i = 0
        while i < len(args):
            if args[i].startswith("--"):
                opts[args[i][2:]] = args[i + 1]
                i += 2
            else:
                pos.append(args[i])
                i += 1
        if len(pos) != 3 or "run" not in opts:
            sys.exit("usage: kb.py add SUBJECT PREDICATE OBJECT --run NN [--where W] [--note N] [--supersedes N,M]")
        p, qual = norm_pred(pos[1])
        f = {"s": canon_subject(pos[0]), "p": p, "o": pos[2], "run": opts["run"]}
        if qual:
            f["qual"] = qual
        for k in ("where", "note", "date", "at", "qual"):
            if k in opts:
                f[k] = canon_where(opts[k]) if k == "where" else opts[k]
        if "supersedes" in opts:
            ids = [int(x) for x in re.split(r"[ ,]+", opts["supersedes"].strip()) if x]
            known = {x["id"] for x in all_facts()}
            bad = [x for x in ids if x not in known]
            if bad:
                sys.exit(f"--supersedes names facts that don't exist: {bad} (facts are numbered by line: kb.py facts TEXT)")
            f["supersedes"] = ids
        # the subject should name a graph node where one exists, so `show` joins the fact to it
        kb = KB()
        names = {str(n.get("name", "")).lower() for n in kb.nodes.values()}
        if f["s"].lower() not in names:
            hits = [kb.label(k) for k in kb.find(f["s"], 3)]
            if hits:
                print(f"note: {f['s']!r} is not a node name; nearest nodes: {'; '.join(hits)} (use one of them as the subject when it is the same thing)")
        with FACTS.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(f, ensure_ascii=False) + "\n")
        f["id"] = len(all_facts())
        print("added" + fact_line(f))
        return
    if op == "facts":
        show_all = "--all" in args
        text = " ".join(a for a in args if not a.startswith("--"))
        for f in facts(text or None, include_superseded=show_all):
            print(fact_line(f))
        return
    if op == "bench":
        bench(args[args.index("--log") + 1] if "--log" in args else None)
        return
    if op == "ask":
        only = "notes" if "--notes" in args else ("game" if "--game" in args else None)
        rest = [a for a in args if not a.startswith("--")]
        n = 8
        if len(rest) > 1 and rest[-1].isdigit():
            n, rest = int(rest[-1]), rest[:-1]
        ask(" ".join(rest), n, only)
        return
    kb = KB()
    if op == "stats":
        stats(kb)
        return
    if op == "embed":
        build_index(kb)
        return
    text = " ".join(a for a in args if not a.isdigit() or op != "find")
    if op == "find":
        n = int(args[-1]) if args and args[-1].isdigit() else 10
        for k in kb.find(text, n):
            r = kb.row(k)
            extra = ", ".join(str(r[x]) for x in ("category", "LV") if x in r)
            print(f"{kb.label(k)}  {extra}")
        if facts(text):
            print(f"({len(facts(text))} observed facts mention it: kb.py facts {text})")
    elif op == "show":
        show(kb, kb.one(text))
    elif op == "make":
        make(kb, kb.one(text, ["thing", "obj", "block", "floor"]))
    elif op == "uses":
        key = kb.one(text)
        users = [e for e in kb.inn[key] if e[1] in ("needs", "made_of")]
        # also through the item's categories (recipes ask for "#fruit", "#meat" ...)
        for e in kb.out[key]:  # an item also counts as its origin ("fruit" for a blueberry)
            if e[1] == "variant_of":
                users += [x for x in kb.inn[e[2]] if x[1] in ("needs", "made_of")]
        cats = [e[2] for e in kb.out[key] if e[1] == "is_a"]
        while cats:
            c = cats.pop()
            users += [e for e in kb.inn[c] if e[1] == "needs"]
            cats += [e[2] for e in kb.out[c] if e[1] == "is_a"]
        print(kb.label(key) + f": needed by {len(users)}")
        for e in users[:40]:
            st = [kb.nodes.get(x[2], {}).get("name") for x in kb.out[e[0]] if x[1] == "made_at"]
            print(f"  {kb.label(e[0])}" + (f"  at {', '.join(map(str, st))}" if st else ""))
    elif op == "station":
        key = kb.one(text, ["thing", "station"])
        made = [e[0] for e in kb.inn[key] if e[1] == "made_at"]
        print(kb.label(key) + f": makes {len(made)}")
        for k in made:
            r = kb.row(k)
            keys = r.get("recipeKey") or []
            print(f"  {kb.label(k)}" + ("  (known from the start)" if "*" in keys else ""))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
