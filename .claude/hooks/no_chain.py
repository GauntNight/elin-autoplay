"""PreToolUse hook (Bash, PowerShell): refuse a shell line that chains two or more of this repo's game tools, or runs one
in a shell loop.

Draft for the user to install (the review of 2026-11-11). The rule: several tool calls in one line go through
`python -I tools/seq.py "TOOL ARGS" "TOOL ARGS"`, which ends at the first refusal; a `;`, `&&`, `||` or newline
chain walked on after a refusal in runs 21, 28, 29, 42, 43 and 45.

Reads the hook's JSON on stdin; exit 2 with a message on stderr blocks the call and shows Claude the message.
Read-only tools (look, state, items, kb, hygiene, score and the like) may be chained freely.

Since run 46 (the user's yes, 2026-11-13): a tool counts only when python RUNS it (`python [-flags] tools/NAME.py`). In run 46 the hook
blocked about fifteen read-only lines that merely named two tool files: `python -I -m py_compile tools/a.py && grep ...
tools/b.py`, `sed -n ... tools/x.py`, `git show ...:tools/fence.py`, a script whose comment named two tools.

Since run 51 (proposed 2026-11-17): a loop around one game tool is the same chain written once. Run 51 ran
`for ...; do python -I tools/fight.py ...; done` over six foes on a nefia floor: each pass ran whatever the last one
returned, and the old check saw one tool in the line and let it through. A shell loop (bash for/while/until, PowerShell
foreach/ForEach-Object/for/while/do, xargs) holding an acting tool is refused. The matcher should read "Bash|PowerShell":
the PowerShell tool takes the same `command` field and was never checked.
"""
import json
import re
import sys

READ_ONLY = {"look", "items", "kb", "hygiene", "publishcheck", "score", "stats", "toolindex", "offcheck", "pulse",
             "watchlog", "elin_eye", "journal", "threat", "power", "boxcount", "gearcheck", "whereis", "view", "find",
             "seq", "wait_ingame", "session_end", "activity"}

# `python -I tools/x.py`, `python3 -u tools/x.py`, `C:/Python314/python.exe -I tools/x.py`: the interpreter, its own
# flags (each a dash word: -I, -u, -B), then the tool. `python -m py_compile tools/x.py` doesn't match: after `-m` comes
# a module name, not a dash word.
RUNS_TOOL = re.compile(r"python[\w.]*\"?\s+(?:-[A-Za-z]+\s+)*\"?(?:\./)?tools[/\\](\w+)\.py")

# A shell loop: bash `for|while|until ... do` (one line or several), PowerShell `foreach (...) {`, `| ForEach-Object {`,
# `| % {`, `for (...)`, `while (...)`, `do {`, and xargs (it runs its command once per input line).
LOOP = re.compile(r"\b(?:for|while|until)\b.*?\bdo\b"
                  r"|\bforeach\b|\bForEach-Object\b|\|\s*%\s*\{"
                  r"|\bfor\s*\(|\bwhile\s*\(|\bdo\s*\{"
                  r"|\bxargs\b", re.I | re.S)


def main():
    try:
        cmd = (json.load(sys.stdin).get("tool_input") or {}).get("command") or ""
    except Exception:  # noqa: BLE001 (never block on a parse problem)
        return 0
    parts = re.split(r";|&&|\|\||\n", cmd)
    acting = []
    for part in parts:
        for m in RUNS_TOOL.finditer(part):
            if m.group(1) not in READ_ONLY:
                acting.append(m.group(1))
                break
    if len(acting) >= 2:
        print("Two or more game tools chained in one shell line (" + ", ".join(acting) + "). A refusal by one would "
              "not stop the next. Use: python -I tools/seq.py \"TOOL ARGS\" \"TOOL ARGS\" (it ends at the first "
              "non-zero exit), or run them one call at a time.", file=sys.stderr)
        return 2
    if acting and LOOP.search(cmd):
        print("A game tool (" + acting[0] + ") inside a shell loop: every pass runs whatever the last one returned, "
              "a refusal or a stop included. Run it one call at a time and read each result, or list the calls in "
              "python -I tools/seq.py \"TOOL ARGS\" \"TOOL ARGS\" (it ends at the first non-zero exit).", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
