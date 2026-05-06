#!/usr/bin/env zsh
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 '<approval request text>'" >&2
  exit 2
fi

QUEUE_PATH="${HERMES_QUEUE_PATH:-/Users/hajinyoung/Dev/ai-hedge-fund/.cache/hermes-alerts}"
mkdir -p "$QUEUE_PATH"

STAMP="$(date '+%Y%m%d-%H%M%S')"
OUTFILE="${QUEUE_PATH}/approval-request-${STAMP}-$$.json"
REQUEST_TEXT="$*"
MESSAGE_TEXT="[승인요청] Codex
${REQUEST_TEXT}"

HERMES_HOME_DIR="${HERMES_HOME:-/Users/hajinyoung/.hermes}"
HERMES_AGENT_DIR="${HERMES_AGENT_DIR:-${HERMES_HOME_DIR}/hermes-agent}"
HERMES_PYTHON="${HERMES_PYTHON:-${HERMES_AGENT_DIR}/venv/bin/python}"

if [[ -x "$HERMES_PYTHON" && -d "$HERMES_AGENT_DIR" ]]; then
  if [[ -f "${HERMES_HOME_DIR}/.env" ]]; then
    set -a
    source "${HERMES_HOME_DIR}/.env"
    set +a
  fi

  if DIRECT_RESULT="$(
    cd "$HERMES_AGENT_DIR"
    "$HERMES_PYTHON" - "$MESSAGE_TEXT" <<'PY'
import json
import sys

from tools.send_message_tool import send_message_tool

message = sys.argv[1]
raw = send_message_tool({
    "action": "send",
    "target": "telegram",
    "message": message,
})

print(raw)
result = json.loads(raw)
if not result.get("success"):
    raise SystemExit(1)
PY
  )"; then
    echo "$DIRECT_RESULT"
    exit 0
  fi
fi

python3 - "$OUTFILE" "$MESSAGE_TEXT" <<'PY'
import datetime as _dt
import json
import sys

outfile = sys.argv[1]
message_text = sys.argv[2]

payload = {
    "channel": "telegram",
    "kind": "approval_request",
    "priority": "approval",
    "created_at": _dt.datetime.now().isoformat(timespec="seconds"),
    "text": message_text,
}

with open(outfile, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY

echo "$OUTFILE"
