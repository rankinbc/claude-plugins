#!/usr/bin/env bash
# Mac double-click launcher. Finder treats .command files as executables
# and opens them in Terminal automatically.
set -e
cd "$(dirname "$0")"
echo "Starting Claude Code in $(pwd)..."
echo
exec claude
