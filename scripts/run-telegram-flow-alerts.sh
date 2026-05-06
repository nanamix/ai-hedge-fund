#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

if [[ -x ".venv/bin/python" ]]; then
  exec .venv/bin/python -m src.notifications.telegram_flow_check "$@"
fi

if [[ -x "/Users/hajinyoung/.local/bin/uv" ]]; then
  exec env UV_CACHE_DIR=/tmp/uv-cache /Users/hajinyoung/.local/bin/uv run python -m src.notifications.telegram_flow_check "$@"
fi

exec python3 -m src.notifications.telegram_flow_check "$@"
