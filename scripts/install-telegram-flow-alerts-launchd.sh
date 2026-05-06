#!/usr/bin/env bash
set -euo pipefail

PLIST_NAME="com.nanamix.ai-hedge-flow-alerts.plist"
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/${PLIST_NAME}"
TARGET="${HOME}/Library/LaunchAgents/${PLIST_NAME}"

cp "${SOURCE}" "${TARGET}"
launchctl unload "${TARGET}" >/dev/null 2>&1 || true
launchctl load "${TARGET}"
launchctl kickstart -k "gui/$(id -u)/com.nanamix.ai-hedge-flow-alerts" || true
echo "Installed ${TARGET}"
