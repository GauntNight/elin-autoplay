"""Render a run summary (runs/<run>-summary.md) as the page published with the Artifact tool.

The user's request (2026-10-17): every close-out gets the rendered page, with the Mermaid
diagrams drawn. The summary file stays the source; this reads the subset of Markdown the
summaries use (headings, paragraphs, tables, lists, code fences) and fills summary_page.html.

- The first "# Run NN summary: ..." heading names the page; the paragraph after it is the lede.
  A paragraph holding a claude.ai/artifact link (the page's own link) is left out.
- A table before the first "##" heading goes under "Results".
- A table whose header has "Goal" and "Status" becomes goal rows with a status pill: a status
  starting "**done...**" is done, "open..." is open, otherwise its first bold phrase is the pill.
- A ```mermaid block becomes a diagram. Comment lines in it make the legend under it:
  "%% legend: done=done; todo=binding" (class names from its classDef lines) and "%% note: TEXT".
- A table column whose separator is "---:" is right-aligned as numbers.

usage: python -I tools/summary_page.py runs/2026-10-16-05-summary.md [OUT.html] [--standalone]
       (default OUT: runs/pages/<same name>.html, gitignored)
  --standalone  a page that needs no Artifact host, for any browser and any LLM: a complete document with the diagrams drawn as
                plain SVG (flowsvg.py), no script. Without it the diagrams are Mermaid source, for a host that draws them.
"""
import html
import re
import sys
from datetime import date
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import flowsvg  # noqa: E402

STANDALONE = False
drawn = {"ok": 0, "left": 0}


def inline(text):
    out = []
    for part in re.split(r"(`[^`]+`)", text):
        if len(part) > 1 and part.startswith("`") and part.endswith("`"):
            out.append("<code>" + html.escape(part[1:-1], quote=False) + "</code>")
            continue
        s = html.escape(part, quote=False)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', s)
        s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r"\1", s)  # repo-relative: the page can't follow it
        s = re.sub(r'(?<![\w"/>])(https?://[^\s<)]+)', r'<a href="\1">\1</a>', s)
        s = s.replace("-&gt;", "→").replace("&lt;=", "≤").replace("&gt;=", "≥")
        out.append(s)
    return "".join(out)


def blocks(md):
    lines = md.splitlines()
    i = 0
    starts = re.compile(r"(#{1,3} |```|\||[-*] |\d+\. )")
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("```"):
            lang, body = line[3:].strip(), []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1
            yield "code", lang, "\n".join(body)
        elif m := re.match(r"(#{1,3}) (.*)", line):
            yield "h", len(m.group(1)), m.group(2).strip()
            i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            yield "table", rows
        elif m := re.match(r"([-*]|\d+\.) ", line):
            ordered, items = m.group(1)[0].isdigit(), []
            while i < len(lines):
                l = lines[i]
                if m2 := re.match(r"(?:[-*]|\d+\.) (.*)", l):
                    items.append(m2.group(1))
                elif l.startswith(" ") and l.strip() and items:
                    items[-1] += " " + l.strip()
                else:
                    break
                i += 1
            yield "list", ordered, items
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not starts.match(lines[i]):
                para.append(lines[i].strip())
                i += 1
            yield "p", " ".join(para)


def cells(row):
    return [c.strip() for c in re.split(r"(?<!\\)\|", row.strip().strip("|"))]


def table(rows):
    head = cells(rows[0])
    sep = cells(rows[1]) if len(rows) > 1 and re.fullmatch(r"[\s|:\-]+", rows[1]) else None
    body = rows[2:] if sep else rows[1:]
    num = [bool(sep) and k < len(sep) and sep[k].endswith(":") for k in range(len(head))]
    if any(re.match(r"goal\b", h, re.I) for h in head) and any(h.lower() == "status" for h in head):
        return goals(head, body)

    def td(tag, k, c):
        cls = ' class="num"' if num[k] else ""
        return f"<{tag}{cls}>{inline(c)}</{tag}>"

    out = ['<div class="tablewrap"><table>', "<thead><tr>"]
    out += [td("th", k, c) for k, c in enumerate(head)]
    out.append("</tr></thead><tbody>")
    for r in body:
        out.append("<tr>" + "".join(td("td", k, c) for k, c in enumerate(cells(r)[: len(head)])) + "</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def goals(head, body):
    col = {h.lower(): k for k, h in enumerate(head)}
    gk = next(k for h, k in col.items() if h.startswith("goal"))
    out = ['<div class="goals">']
    for r in body:
        c = cells(r)
        goal, status = c[gk], c[col["status"]]
        by = c[col["set by"]] if "set by" in col else ""
        m = re.match(r"(G\d+)\s+(.*)", goal)
        gid, name = (m.group(1), m.group(2)) if m else ("", goal)
        lead = re.match(r"\*\*(.+?)\*\*:?\s*(.*)", status)
        if lead and lead.group(1).lower().startswith("done"):
            kind, pill = "done", "done"
            when = lead.group(1)[4:].strip()
            detail = f"{when}: {lead.group(2)}" if when else lead.group(2)
        elif status.lower().startswith("open"):
            kind, pill, detail = "open", "open", re.sub(r"^open:?\s*", "", status, flags=re.I)
        elif lead:
            kind, pill, detail = "going", lead.group(1), lead.group(2)
        else:
            bold = re.search(r"\*\*(.+?)\*\*", status)
            kind, pill, detail = "going", bold.group(1) if bold else "active", status
        detail = detail[:1].upper() + detail[1:]
        by_html = f' <span class="by">· set by {inline(by)}</span>' if by else ""
        out.append(f'<div class="goal"><span class="id">{html.escape(gid)}</span>'
                   f'<span class="name">{inline(name[:1].upper() + name[1:])}</span>'
                   f'<span class="pill {kind}">{inline(pill)}</span>'
                   f'<span class="detail">{inline(detail)}{by_html}</span></div>')
    out.append("</div>")
    return "\n".join(out)


# run 46 (the user: "open goal chains doesn't render"): a node named `call` broke the whole diagram; these are words the
# flowchart grammar reads as keywords, so none may be a node id
MERMAID_RESERVED = {"call", "end", "click", "class", "classDef", "style", "linkStyle", "subgraph", "graph", "flowchart",
                    "direction", "href", "callback", "default", "interpolate"}


def mermaid(src):
    bad = sorted({m for m in re.findall(r"^\s*(\w+)\s*[\[\(\{>]", src, re.M) if m in MERMAID_RESERVED}
                 | {w for line in re.findall(r"^\s*(\w+\s*-->.*)$", src, re.M)
                    for w in re.findall(r"\b(\w+)\b", line) if w in MERMAID_RESERVED})
    if bad:
        sys.exit(f"refused: a Mermaid keyword used as a node id ({', '.join(bad)}): rename the node (run 46)")
    fills = {n: (f, s) for n, f, s in re.findall(r"classDef (\w+) fill:(#[0-9a-fA-F]+),stroke:(#[0-9a-fA-F]+)", src)}
    keys = []
    for line in re.findall(r"^\s*%%\s*legend:\s*(.+)$", src, re.M):
        for part in line.split(";"):
            name, _, label = part.strip().partition("=")
            if name.strip() in fills:
                f, s = fills[name.strip()]
                keys.append(f'<span class="key"><span class="sw" style="background:{f};border-color:{s}"></span>'
                            f"{inline(label.strip())}</span>")
    keys += [f"<span>{inline(n.strip())}</span>" for n in re.findall(r"^\s*%%\s*note:\s*(.+)$", src, re.M)]
    cap = f"\n<figcaption>{''.join(keys)}</figcaption>" if keys else ""
    if STANDALONE:  # no Artifact host to draw it: plain SVG, or the source and a warning if it can't be drawn
        try:
            drawn["ok"] += 1
            return f'<figure><div class="diagram">{flowsvg.to_svg(src)}</div>{cap}</figure>'
        except flowsvg.Unsupported as e:
            drawn["ok"] -= 1
            drawn["left"] += 1
            print(f"can't draw a diagram, showing its source instead: {e}")
            return f'<figure><div class="diagram"><pre>{html.escape(src, quote=False)}</pre></div>{cap}</figure>'
    # run 15: the host renders the diagrams with its own Mermaid, which measures a label in one
    # font and draws it in a wider one, so the last character of the widest line was clipped
    # ("(M6", "speed 11:"). Let label text overflow its box instead of being cut off.
    if "%%{init" not in src:
        src = '%%{init: {"themeCSS": "foreignObject { overflow: visible; }"}}%%\n' + src
    return (f'<figure><div class="diagram"><pre class="mermaid">{html.escape(src, quote=False)}</pre></div>'
            f"{cap}</figure>")


def render(md, source_name):
    title = h1 = eyebrow = "Run summary"
    lede, sections, cur = [], [], None
    for b in blocks(md):
        if b[0] == "h" and b[1] == 1:
            text = b[2]
            m = re.match(r"(Start Runs? [\d-]+|Run \d+)\s*(?:summary)?:?\s*(.*)", text, re.I)
            h1, rest = (m.group(1), m.group(2)) if m else (text, "")
            title, eyebrow = f"Elin {h1}", "Elin · " + rest if rest else "Elin"
            continue
        if b[0] == "h":
            cur = [f"<h2>{inline(b[2])}</h2>"]
            sections.append(cur)
            continue
        if b[0] == "p" and "claude.ai/artifact" in b[1]:
            continue  # the page's own link
        if cur is None and b[0] == "p":
            lede.append(f'<p class="lede">{inline(b[1])}</p>' if not lede else f"<p>{inline(b[1])}</p>")
            continue
        if cur is None:
            cur = ["<h2>Results</h2>"]
            sections.append(cur)
        if b[0] == "p":
            cur.append(f"<p>{inline(b[1])}</p>")
        elif b[0] == "table":
            cur.append(table(b[1]))
        elif b[0] == "list":
            tag = "ol" if b[1] else "ul"
            cur.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in b[2]) + f"</{tag}>")
        elif b[0] == "code" and b[1] == "mermaid":
            cur.append(mermaid(b[2]))
        elif b[0] == "code":
            cur.append(f'<pre class="code">{html.escape(b[2], quote=False)}</pre>')
    body = "\n".join("  <section>\n" + "\n".join(s) + "\n  </section>" for s in sections)
    footer = (f"Source: <code>{html.escape(source_name)}</code> in the elin-autoplay repo, rendered by "
              f"<code>tools/summary_page.py</code> on {date.today().isoformat()}. The diagrams are drawn "
              f"from its Mermaid source.")
    page = (TOOLS / "summary_page.html").read_text(encoding="utf-8")
    for k, v in {"TITLE": html.escape(title), "EYEBROW": inline(eyebrow), "H1": inline(h1),
                 "LEDE": "\n".join(lede), "BODY": body, "FOOTER": footer}.items():
        page = page.replace("{{" + k + "}}", v)
    return page


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    global STANDALONE
    STANDALONE = "--standalone" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    src = Path(args[0]).resolve()
    out = Path(args[1]) if len(args) > 1 else ROOT / "runs" / "pages" / (src.stem + ".html")
    page = render(src.read_text(encoding="utf-8"), src.relative_to(ROOT).as_posix())
    if STANDALONE:
        page = ('<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1">\n') + page
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    if STANDALONE:
        print(f"{out} ({len(page):,} bytes, {drawn['ok']} diagrams drawn, {drawn['left']} left as source)")
        return
    n = page.count('<pre class="mermaid">')
    print(f"{out} ({len(page):,} bytes, {n} diagram{'s' if n != 1 else ''})")


if __name__ == "__main__":
    main()
