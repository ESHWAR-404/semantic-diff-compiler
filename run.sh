#!/usr/bin/env bash
# run.sh — Entry-point wrapper for Semantic Diff for Compiler IR
#
# Usage:
#   ./run.sh <old_file> <new_file> [options]
#   ./run.sh --help
#
# Examples:
#   ./run.sh testcases/tc1_loop_bounds/v1.ll testcases/tc1_loop_bounds/v2.ll
#   ./run.sh testcases/tc4_vectorization/v1.ll testcases/tc4_vectorization/v2.ll --verbose
#   ./run.sh testcases/tc2_inlining/v1.ll testcases/tc2_inlining/v2.ll --format json
#   ./run.sh file_a.c file_b.c --opt O2 --show-block-diff

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find Python (prefer venv)
PYTHON=""
VENV_PY_UNIX="$ROOT/.venv/bin/python"
VENV_PY_WIN="$ROOT/.venv/Scripts/python"

if   [[ -x "$VENV_PY_UNIX" ]]; then PYTHON="$VENV_PY_UNIX"
elif [[ -x "$VENV_PY_WIN"  ]]; then PYTHON="$VENV_PY_WIN"
fi

if [[ -z "$PYTHON" ]]; then
    for cmd in python3 python python3.10 python3.11 python3.12; do
        if command -v "$cmd" &>/dev/null; then
            if "$cmd" -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" 2>/dev/null; then
                PYTHON="$cmd"
                break
            fi
        fi
    done
fi

if [[ -z "$PYTHON" ]]; then
    echo "ERROR: Python 3.9+ not found. Run ./build.sh first." >&2
    exit 1
fi

if [[ $# -eq 0 ]]; then
    exec "$PYTHON" "$ROOT/src/main.py" --help
fi

exec "$PYTHON" "$ROOT/src/main.py" "$@"
