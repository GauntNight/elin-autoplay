"""Draw a run summary's Mermaid flowcharts as plain SVG, with nothing external and no script: so a page can be made and read on any
PC, with any LLM, and no Claude Artifact to draw them (the user, 2026-11-04). summary_page.py --standalone calls it. It covers the
subset the summaries use (elin-summary lists it); anything else raises Unsupported, and the page shows that diagram's source.

usage: python -I tools/flowsvg.py FILE.md ...     check every diagram in the files: exit 0 if all can be drawn, 1 if not
"""
import html
import re
import sys
from pathlib import Path


class Unsupported(ValueError):
    pass


SHAPES = (
    (r'\[\("(.*?)"\)\]', "cylinder"),
    (r'\{\{"(.*?)"\}\}', "hexagon"),
    (r'\("(.*?)"\)', "round"),
    (r'\["(.*?)"\]', "rect"),
)
NODE = r"\w+(?:" + "|".join(s for s, _ in SHAPES) + r")?"
NODE_RX = re.compile(NODE)
LINK_RX = re.compile(r'\s*(-->|-\.->|~~~|-\.\s*"[^"]*"\s*\.->|--\s*"[^"]*"\s*-->|--\s*[^-"\s][^-"]*?\s*-->)\s*')
_count = 0


def text_lines(label):
    label = label.replace("#quot;", '"').replace("#39;", "'")
    return [re.sub(r"<[^>]+>", "", p).strip() for p in re.split(r"<br\s*/?>", label)]


def parse(src):
    direction, nodes, edges, defs, cls = None, {}, [], {}, {}

    def node(tok):
        m = re.match(r"\w+", tok)
        nid = m.group(0)
        rest = tok[m.end():]
        if nid not in nodes:
            nodes[nid] = {"id": nid, "lines": [nid], "shape": "rect"}
        for pat, shape in SHAPES:
            d = re.fullmatch(pat, rest)
            if d:
                nodes[nid].update(lines=text_lines(d.group(1)), shape=shape)
        return nid

    for raw in src.splitlines():
        line = raw.strip()
        if not line or line.startswith("%%"):
            continue
        m = re.fullmatch(r"(?:flowchart|graph)\s+(TB|TD|BT|LR|RL)", line)
        if m:
            direction = "TB" if m.group(1) == "TD" else m.group(1)
            continue
        m = re.match(r"classDef\s+(\w+)\s+(.+)", line)
        if m:
            props = dict(p.split(":", 1) for p in m.group(2).split(",") if ":" in p)
            defs[m.group(1)] = props
            continue
        m = re.fullmatch(r"class\s+([\w,]+)\s+(\w+)", line)
        if m:
            for nid in m.group(1).split(","):
                cls[nid] = m.group(2)
            continue
        pos, prev = 0, None
        while True:
            m = NODE_RX.match(line, pos)
            if not m:
                raise Unsupported(line)
            nid = node(m.group(0))
            pos = m.end()
            if prev:
                edges.append({"a": prev[0], "b": nid, **prev[1]})
            if pos == len(line):
                break
            lk = LINK_RX.match(line, pos)
            if not lk:
                raise Unsupported(line)
            token = lk.group(1)
            label = re.search(r'"([^"]*)"', token)
            word = re.fullmatch(r"--\s*([^-\"]+?)\s*-->", token)
            prev = (nid, {"dotted": token.startswith("-."), "hidden": token == "~~~",
                          "label": label.group(1) if label else (word.group(1) if word else "")})
            pos = lk.end()
    if direction is None:
        raise Unsupported("no flowchart line")
    return direction, nodes, edges, defs, cls


def ranks_of(nodes, edges):
    """Longest path from the sources; an edge that would close a loop doesn't count."""
    out = {n: [] for n in nodes}
    for e in edges:
        out[e["a"]].append(e)
    state, back = {}, set()

    def visit(n):
        state[n] = 1
        for e in out[n]:
            if state.get(e["b"]) == 1:
                back.add(id(e))
            elif e["b"] not in state:
                visit(e["b"])
        state[n] = 2

    for n in nodes:
        if n not in state:
            visit(n)
    rank = {n: 0 for n in nodes}
    for _ in nodes:
        for e in edges:
            if id(e) not in back and rank[e["b"]] < rank[e["a"]] + 1:
                rank[e["b"]] = rank[e["a"]] + 1
    return rank


def width_of(s):
    return sum(13 if ord(c) > 0x2E7F else 7.1 for c in s)


def layout(direction, nodes, edges):
    rank = ranks_of(nodes, edges)
    horizontal = direction in ("LR", "RL")
    for n in nodes.values():
        n["w"] = max(96, max(width_of(s) for s in n["lines"]) + (44 if n["shape"] == "hexagon" else 26))
        n["h"] = 17.5 * len(n["lines"]) + (28 if n["shape"] == "cylinder" else 16)
    rows = [[] for _ in range(max(rank.values(), default=0) + 1)]
    for nid in nodes:
        rows[rank[nid]].append(nid)
    across = {n: i for row in rows for i, n in enumerate(row)}
    near = {n: [] for n in nodes}
    for e in edges:
        near[e["a"]].append(e["b"])
        near[e["b"]].append(e["a"])
    for sweep in range(6):  # order each row by where its neighbours sit
        for row in rows if sweep % 2 == 0 else reversed(rows):
            key = {n: (sum(across[m] for m in near[n]) / len(near[n]) if near[n] else across[n]) for n in row}
            row.sort(key=lambda n: key[n])
            for i, n in enumerate(row):
                across[n] = i
    size = (lambda n: nodes[n]["h"]) if horizontal else (lambda n: nodes[n]["w"])
    gap = 22 if horizontal else 26
    pos = {}
    for row in rows:
        total = sum(size(n) for n in row) + gap * (len(row) - 1)
        x = -total / 2
        for n in row:
            pos[n] = x + size(n) / 2
            x += size(n) + gap
    for sweep in range(8):  # slide each row toward its neighbours, keeping the gaps
        for row in rows if sweep % 2 == 0 else reversed(rows):
            want = {n: (sum(pos[m] for m in near[n]) / len(near[n]) if near[n] else pos[n]) for n in row}
            placed, end = {}, None
            for n in row:
                p = want[n] if end is None else max(want[n], end + size(n) / 2)
                placed[n] = p
                end = p + size(n) / 2 + gap
            shift = sum(want[n] - placed[n] for n in row) / len(row)
            for n in row:
                pos[n] = placed[n] + shift
    depth = (lambda n: nodes[n]["w"]) if horizontal else (lambda n: nodes[n]["h"])
    labelled = {rank[e["a"]] for e in edges if e["label"]}
    main, cur = {}, 0.0
    for r, row in enumerate(rows):
        thick = max((depth(n) for n in row), default=0)
        for n in row:
            main[n] = cur + thick / 2
        cur += thick + ((118 if horizontal else 82) if r in labelled else (70 if horizontal else 58))
    low = min(pos[n] - size(n) / 2 for n in nodes)
    high = max(pos[n] + size(n) / 2 for n in nodes)
    end = max(main[n] + depth(n) / 2 for n in nodes)
    pad = 14
    for nid, n in nodes.items():
        c, m = pos[nid] - low + pad, main[nid] + pad
        if direction in ("RL",):
            m = end + 2 * pad - m
        if direction == "BT":
            m = end + 2 * pad - m
        n["x"], n["y"] = (m, c) if horizontal else (c, m)
    across_size = high - low + 2 * pad
    main_size = end + 2 * pad
    return (main_size, across_size) if horizontal else (across_size, main_size)


def edge_path(direction, a, b):
    """A cubic from the side of a to the facing side of b: its four points."""
    if direction in ("LR", "RL"):
        sign = 1 if b["x"] >= a["x"] else -1
        x1, y1, x2, y2 = a["x"] + sign * a["w"] / 2, a["y"], b["x"] - sign * b["w"] / 2, b["y"]
        mid = (x1 + x2) / 2
        return (x1, y1), (mid, y1), (mid, y2), (x2, y2)
    sign = 1 if b["y"] >= a["y"] else -1
    x1, y1, x2, y2 = a["x"], a["y"] + sign * a["h"] / 2, b["x"], b["y"] - sign * b["h"] / 2
    mid = (y1 + y2) / 2
    return (x1, y1), (x1, mid), (x2, mid), (x2, y2)


def on_curve(pts, t):
    u = 1 - t
    return tuple(u ** 3 * pts[0][i] + 3 * u * u * t * pts[1][i] + 3 * u * t * t * pts[2][i] + t ** 3 * pts[3][i] for i in (0, 1))


def label_spot(pts, text, nodes, taken):
    """The first spot along the edge where the label covers no node and no other label: a long edge can pass behind a node."""
    w, h = width_of(text) * 0.92 + 6, 16
    for t in (0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8, 0.12, 0.88):
        x, y = on_curve(pts, t)
        box = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
        solid = [(n["x"] - n["w"] / 2, n["y"] - n["h"] / 2, n["x"] + n["w"] / 2, n["y"] + n["h"] / 2) for n in nodes.values()]
        if not any(box[0] < o[2] and o[0] < box[2] and box[1] < o[3] and o[1] < box[3] for o in solid + taken):
            taken.append(box)
            return x, y
    return on_curve(pts, 0.5)


def shape_svg(n, fill, stroke):
    x, y, w, h = n["x"] - n["w"] / 2, n["y"] - n["h"] / 2, n["w"], n["h"]
    style = f'fill="{fill}" stroke="{stroke}" stroke-width="1.3"'
    if n["shape"] == "cylinder":
        ry = 6
        return (f'<path {style} d="M{x:.1f},{y + ry:.1f} a{w / 2:.1f},{ry} 0 0 1 {w:.1f},0 V{y + h - ry:.1f} '
                f'a{w / 2:.1f},{ry} 0 0 1 -{w:.1f},0 Z"/>'
                f'<path fill="none" stroke="{stroke}" stroke-width="1.3" d="M{x:.1f},{y + ry:.1f} a{w / 2:.1f},{ry} 0 0 0 {w:.1f},0"/>')
    if n["shape"] == "hexagon":
        k = 12
        pts = [(x + k, y), (x + w - k, y), (x + w, y + h / 2), (x + w - k, y + h), (x + k, y + h), (x, y + h / 2)]
        return f'<polygon {style} points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in pts) + '"/>'
    rx = h / 2 if n["shape"] == "round" else 5
    return f'<rect {style} x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx:.1f}"/>'


def to_svg(src):
    """The SVG for one flowchart. Raises Unsupported on anything outside the subset."""
    global _count
    _count += 1
    direction, nodes, edges, defs, cls = parse(src)
    if not nodes:
        raise Unsupported("no nodes")
    width, height = layout(direction, nodes, edges)
    marker = f"flowsvg-arrow-{_count}"
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" role="img" '
             f'style="display:block;margin:auto;width:100%;max-width:{width:.0f}px;height:auto;color:var(--muted,#56635a);'
             f'font:500 13px var(--body,system-ui,sans-serif)">',
             f'<defs><marker id="{marker}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
             '<path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker></defs>']
    labels, taken = [], []
    for e in edges:
        if e["hidden"]:
            continue
        pts = edge_path(direction, nodes[e["a"]], nodes[e["b"]])
        d = "M{:.1f},{:.1f} C{:.1f},{:.1f} {:.1f},{:.1f} {:.1f},{:.1f}".format(*[v for p in pts for v in p])
        dash = ' stroke-dasharray="5 4"' if e["dotted"] else ""
        parts.append(f'<path d="{d}" fill="none" stroke="currentColor" stroke-width="1.4"{dash} marker-end="url(#{marker})"/>')
        if e["label"]:
            mx, my = label_spot(pts, e["label"], nodes, taken)
            labels.append(f'<text x="{mx:.1f}" y="{my + 4:.1f}" text-anchor="middle" fill="currentColor" stroke="var(--surface,#fff)" '
                          f'stroke-width="4" paint-order="stroke" style="font-size:12px">{html.escape(e["label"])}</text>')
    for nid, n in nodes.items():
        props = defs.get(cls.get(nid), {})
        fill = props.get("fill", "var(--accent-soft,#e0eddc)")
        stroke = props.get("stroke", "var(--accent,#33683a)")
        ink = props.get("color", "var(--fg,#1b221e)" if "fill" not in props else "#1f2937")
        parts.append(shape_svg(n, fill, stroke))
        drop = 5 if n["shape"] == "cylinder" else 0
        top = n["y"] + drop - 17.5 * (len(n["lines"]) - 1) / 2 + 4.5
        spans = "".join(f'<tspan x="{n["x"]:.1f}" y="{top + 17.5 * i:.1f}">{html.escape(s)}</tspan>' for i, s in enumerate(n["lines"]))
        parts.append(f'<text text-anchor="middle" fill="{ink}">{spans}</text>')
    parts.extend(labels)
    parts.append("</svg>")
    return "".join(parts)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    total, bad = 0, 0
    for name in sys.argv[1:]:
        for m in re.finditer(r"```mermaid\n(.*?)```", Path(name).read_text(encoding="utf-8"), re.S):
            total += 1
            try:
                to_svg(m.group(1))
            except Unsupported as e:
                bad += 1
                print(f"{name}: can't draw: {e}")
    print(f"{total} diagrams, {total - bad} can be drawn, {bad} can't")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
