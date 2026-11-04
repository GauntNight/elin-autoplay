"""Is this repo fit to publish? (2026-11-04, before the first push.) Scans what a push would send for what must
never leave this PC: names and account details, private claude.ai links, real-life schedule notes, network ids,
secrets, and files that aren't ours to share. It prints where each hit is, with the value masked, and exits 1 on any.

The account name comes from the environment and any other words from `.publish-terms` (gitignored, one a line: a
real name, a handle), so this file never holds the things it looks for. Text is checked with line breaks collapsed:
a phrase split over two lines in a run log counts. Images can't be read by a script: only docs/samples/ may hold any,
so look at each one before adding it.

usage: python -I tools/publishcheck.py             the working tree: tracked files plus new ones not ignored
       python -I tools/publishcheck.py --history   also every commit reachable from HEAD: its messages,
                                                   the lines it added, and its author and committer
Exit: 0 clean, 1 something found.
"""
import getpass
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TERMS = ROOT / ".publish-terms"

PATTERNS = {
    "claude.ai link": r"claude\.ai/(?:code/)?(?:artifact/|session_)[A-Za-z0-9]",
    "home folder": r"[A-Za-z]:[\\/]+Users[\\/]+(?!Public\b|<|%)[A-Za-z0-9._-]+|/c/Users/(?!Public\b|<)[A-Za-z0-9._-]+",
    "private address": r"\b(?:192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b",
    "MAC address": r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b",
    "Windows SID": r"\bS-1-5-21-\d+",
    "Steam id": r"\b7656119\d{10}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@(?!anthropic\.com\b|users\.noreply\.github\.com\b)[A-Za-z0-9-]+\.[A-Za-z]{2,}\b",
    "secret": r"\bgh[pousr]_[A-Za-z0-9]{20,}|\bsk-[A-Za-z0-9_-]{20,}|BEGIN [A-Z ]*PRIVATE KEY",
    "real-life schedule": r"\b(?:the|The) user(?: is| was|, who was)? (?:asleep|awake|at work|away\b|went to b[e]d|going to b[e]d)"
                          r"|\bgoing to b[e]d\b|\bI'll be (?:asleep|at work)\b|\bwhile (?:I|they) work\b"
                          r"|see you in the m[o]rning"
                          # the cold read before the first push found these, which the phrases above had missed
                          r"|\b(?:the|The) user (?:went to sl[e]ep|sl[e]pt|left for the n[i]ght)\b|\bwhile the user sl[e]pt\b"
                          r"|\b(?:I am|I'm) w[o]rking\b|\bthe user's n[i]ght(?:ly)?\b|\b(?:our|your|the) n[i]ghtly\b|\bn[i]ght run\b"
                          r"|\buntil m[i]dnight\b|\b[0-9]+:[0-9]+ AM ET\b",
}
PATTERNS = {k: re.compile(v) for k, v in PATTERNS.items()}

# Never tracked, whatever .gitignore says at the time.
BAD_PATH = re.compile(r"^(?:runs/|archive/|knowledge/goals\.md$|knowledge/goals-done\.md$|knowledge/milestones\.csv$|knowledge/fights\.csv$"
                      r"|knowledge/travel\.csv$|knowledge/game/|knowledge/vectors/|mod/dist/|\.ollama/|\.cache/"
                      r"|\.claude/settings[^/]*\.json$|CLAUDE\.local\.md$|\.publish-terms$|player\.md$)")
BINARY = re.compile(r"\.(?:png|jpe?g|gif|bmp|webp|mp4|dll|exe|pdb|so|zip|7z|rar|gz|tar|bin|gguf|db|sqlite)$", re.I)
SAMPLES = "docs/samples/"


def git(*args):
    p = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode:
        sys.exit(f"git {args[0]}: {p.stderr.strip()}")
    return p.stdout


def personal_terms():
    """Words that are personal on this PC; `.publish-terms` adds the ones the environment can't know."""
    out = set()
    for name in (os.environ.get("USERNAME"), os.environ.get("USER")):
        if name:
            out.add(name)
    try:
        out.add(getpass.getuser())
    except (OSError, KeyError):
        pass
    if TERMS.exists():
        out |= {t.strip() for t in TERMS.read_text(encoding="utf-8").splitlines() if t.strip() and not t.startswith("#")}
    return [re.compile(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", re.I) for t in sorted(out, key=len) if len(t) >= 3]


def mask(s):
    return s[:3] + "..." if len(s) > 3 else "..."


def scan_text(text, terms):
    """Yields (line number, kind, masked value). Line breaks count as spaces, so a wrapped phrase still matches."""
    for kind, rx in PATTERNS.items():
        for line, value in _wrapped(rx, text):
            yield line, kind, mask(value)
    for rx in terms:
        for m in rx.finditer(text):
            yield text.count("\n", 0, m.start()) + 1, "personal term", mask(m.group())


def _wrapped(rx, text):
    """Matches of rx over text with runs of whitespace collapsed; each with the line it starts on in text."""
    keep, lines, line = [], [], 1
    prev_space = False
    for ch in text:
        if ch.isspace():
            if not prev_space:
                keep.append(" ")
                lines.append(line)
            prev_space = True
            if ch == "\n":
                line += 1
        else:
            keep.append(ch)
            lines.append(line)
            prev_space = False
    flat = "".join(keep)
    for m in rx.finditer(flat):
        yield lines[m.start()], m.group()


def check_tree(terms):
    hits = []
    files = [f for f in git("ls-files", "-co", "--exclude-standard").splitlines() if f]
    for f in files:
        if BAD_PATH.match(f):
            hits.append(f"{f}: never tracked")
        if BINARY.search(f):
            if not f.startswith(SAMPLES):
                hits.append(f"{f}: a binary outside {SAMPLES}")
            continue
        path = ROOT / f
        if not path.is_file():
            continue
        text = path.read_bytes().decode("utf-8", errors="replace")
        for line, kind, val in scan_text(text, terms):
            hits.append(f"{f}:{line}: {kind}: {val}")
    return len(files), hits


def check_history(terms):
    hits = []
    commits = 0
    # identities: only a no-reply address is fit to publish
    for row in sorted(set(git("log", "--format=%ae%n%ce").split())):
        if not row.endswith(("@users.noreply.github.com", "noreply@anthropic.com")):
            hits.append(f"commit identity: {mask(row)}")
    # messages
    log = git("log", "--format=%x00%h%x01%B")
    for entry in log.split("\0"):
        if not entry.strip():
            continue
        commits += 1
        sha, _, body = entry.partition("\x01")
        for _, kind, val in scan_text(body, terms):
            hits.append(f"commit {sha.strip()} message: {kind}: {val}")
    # every line a commit added; a removed line was added by an earlier commit
    sha = "?"
    path = "?"
    for line in git("log", "-p", "--no-color", "--format=%x00%h").splitlines():
        if line.startswith("\0"):
            sha = line[1:]
        elif line.startswith("+++ b/"):
            path = line[6:]
            if BAD_PATH.match(path) or (BINARY.search(path) and not path.startswith(SAMPLES)):
                hits.append(f"commit {sha}: added {path}")
        elif line.startswith("+") and not line.startswith("+++"):
            for _, kind, val in scan_text(line[1:], terms):
                hits.append(f"commit {sha} {path}: {kind}: {val}")
    return commits, hits


def main():
    terms = personal_terms()
    n, hits = check_tree(terms)
    report = f"{n} files"
    if "--history" in sys.argv[1:]:
        c, more = check_history(terms)
        hits += more
        report += f", {c} commits"
    for h in hits[:200]:
        print(h)
    if len(hits) > 200:
        print(f"... and {len(hits) - 200} more")
    if hits:
        print(f"publishcheck: {len(hits)} found ({report}): not fit to push")
        return 1
    print(f"publishcheck: clean ({report}; {len(terms)} personal terms checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
