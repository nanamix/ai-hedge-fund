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

python3 - "$OUTFILE" "$REQUEST_TEXT" <<'PY'
import datetime as _dt
import json
import sys

outfile = sys.argv[1]
request_text = sys.argv[2]

payload = {
    "channel": "telegram",
    "kind": "approval_request",
    "priority": "approval",
    "created_at": _dt.datetime.now().isoformat(timespec="seconds"),
    "text": "[승인요청] Codex\n" + request_text,
}

with open(outfile, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY

echo "$OUTFILE"
