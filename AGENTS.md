# For an LLM other than Claude Code

This repo was built on Claude Code and hasn't been run on anything else, but its rules are plain files. Your tool may need pointing at them:

- **Rules:** read `CLAUDE.md` first and treat it as your rulebook. Read `player.md` next; if there isn't one, this is a first run.
- **Skills:** each is a Markdown file at `.claude/skills/<name>/SKILL.md`, and its first lines say when it applies. Claude Code loads them
  by itself; you read the one that fits. Start with `elin-setup` on a first run, and `elin-play` for every session.
- **Run pages:** use `elin-summary`, which makes them with a script and a browser.
- **Claude-only tools:** where a skill names the Artifact tool, ArtifactData, the Chrome extension, Monitor or TaskStop, use your own equivalent
  or skip that step. The game itself is driven by plain Python scripts in `tools/`, so nothing about playing depends on Claude.
