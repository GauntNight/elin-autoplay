"""Print the full visible text of the top window (quest boards, letters, books, shop info),
one text per line, without the 200-character cut, with colour tags removed.

usage: python -I tools/read.py [--all]
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import call  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    d = call("texts", all="--all" in sys.argv, max=100000)["data"]
    print(f"[{d['scope']}]")
    for t in d["texts"]:
        print(re.sub(r"</?color[^>]*>|</?size[^>]*>", "", t))


if __name__ == "__main__":
    main()
