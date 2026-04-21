#!/usr/bin/env bash
# Launch Claude Code in this project directory.
# Usage: ./launch.sh  (make executable first: chmod +x launch.sh)
set -e
cd "$(dirname "$0")"
echo "Starting Claude Code in $(pwd)..."
echo
exec claude
