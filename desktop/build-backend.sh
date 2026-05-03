#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="$SCRIPT_DIR/backend-dist"
WORK_DIR="$SCRIPT_DIR/backend-build"
SPEC_DIR="$SCRIPT_DIR/backend-spec"

mkdir -p "$OUT_DIR" "$WORK_DIR" "$SPEC_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN=python
fi

"$PYTHON_BIN" -m PyInstaller \
  --onefile \
  --name advanced-scraper-backend \
  --distpath "$OUT_DIR" \
  --workpath "$WORK_DIR" \
  --specpath "$SPEC_DIR" \
  --paths "$ROOT_DIR" \
  "$SCRIPT_DIR/backend_entry.py"
