"""PreToolUse hook (Bash): refuse a shell line that chains two or more of this repo's game tools.

Draft for the user to install (the review of 2026-11-11). The rule: several tool calls in one line go through
`python -I tools/seq.py "TOOL ARGS" "TOOL ARGS"`, which ends at the first refusal; a `;`, `&&`, `||` or newline
chain walked on after a refusal in runs 21, 28, 29, 42, 43 and 45.

Reads the hook's JSON on stdin; exit 2 with a message on stderr blocks the call and shows Claude the message.
Read-only tools (look, state, items, kb, hygiene, score and the like) may be chained freely.

Since run 46 (the user's yes, 2026-11-13): a tool counts only when python RUNS it (`python [-flags] tools/NAME.py`). In run 46 the hook
blocked about fifteen read-only lines that merely named two tool files: `python -I -m py_compile tools/a.py && grep ...
tools/b.py`, `sed -n ... tools/x.py`, `git show ...:tools/fence.py`, a script whose comment named two tools.
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
