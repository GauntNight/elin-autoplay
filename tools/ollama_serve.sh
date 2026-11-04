#!/usr/bin/env bash
# Start the repo-local Ollama server: the user's installed ollama.exe, but with its models in
# .ollama/models inside this repo (gitignored) and listening on 127.0.0.1:11435 only, so it
# never touches the user's own Ollama instance (127.0.0.1:11434) or its model folder.
# Settings are set for this process only (no user/machine environment change).
# Output goes to .ollama/serve.log. Stopping the bash task does NOT stop ollama.exe: on
# 2026-10-16 Claude Code reaped the task under memory pressure and the server kept running,
# orphaned, still on 11435. So this script reuses a server that already answers there.
#
# Going off (the user, 2026-11-03; KB #155): the close-out's last step ends the server with
# tools/ollama_stop.py, the only allowed way; never Stop-Process/taskkill/kill by hand (machine
# rules). In case a session dies first, the server also starts under `timeout`, 12 hours unless
# ELIN_OLLAMA_MAX says otherwise. tools/offcheck.py lists a server left running.
# Idle, it holds about 80 MB (the model unloads after 5 minutes).
#
# usage: bash tools/ollama_serve.sh        (run in the background; then tools/kb.py embed)
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$here/.ollama/models"
export OLLAMA_MODELS="$(cygpath -w "$here/.ollama/models")"
export OLLAMA_HOST="127.0.0.1:11435"
exe="$(cygpath -u "$LOCALAPPDATA")/Programs/Ollama/ollama.exe"
if curl -s --max-time 2 "http://$OLLAMA_HOST/api/version" > /dev/null; then
  echo "repo-local ollama already answers on $OLLAMA_HOST: reusing it"
  exit 0
fi
echo "$(date '+%F %T') starting repo-local ollama on $OLLAMA_HOST, models in .ollama/models" >> "$here/.ollama/serve.log"
exec /usr/bin/timeout "${ELIN_OLLAMA_MAX:-12h}" "$exe" serve >> "$here/.ollama/serve.log" 2>&1
