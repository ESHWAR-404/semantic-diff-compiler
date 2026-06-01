#!/usr/bin/env bash
# run2.sh — SemDiff v2.0 Batch Runner
# Runs all 15 test cases and prints a summary table.
#
# Usage:
#   ./run2.sh               # text output for all cases
#   ./run2.sh --html        # also generate HTML report per case
#   ./run2.sh --json        # also generate JSON output per case
#   ./run2.sh --verbose     # verbose mode for all cases
#   ./run2.sh --dashboard   # generate full dashboard (calls demo.py)
#   ./run2.sh --filter VEC  # only show cases with matching change tag

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

C_RED='\033[0;31m'; C_GREEN='\033[0;32m'; C_YELLOW='\033[1;33m'
C_CYAN='\033[0;36m'; C_BOLD='\033[1m'; C_MUTED='\033[2m'; C_RESET='\033[0m'

# Parse flags
DO_HTML=0; DO_JSON=0; VERBOSE=""; DASHBOARD=0; FILTER=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --html)      DO_HTML=1 ;;
        --json)      DO_JSON=1 ;;
        --verbose|-v) VERBOSE="--verbose" ;;
        --dashboard) DASHBOARD=1 ;;
        --filter)    FILTER="$2"; shift ;;
        --help|-h)
            echo "Usage: ./run2.sh [--html] [--json] [--verbose] [--dashboard] [--filter TAG]"
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

# Find Python
PYTHON=""
for cmd in python python3 python3.12 python3.11 python3.10; do
    if command -v "$cmd" &>/dev/null 2>&1; then
        if "$cmd" -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" 2>/dev/null; then
            PYTHON="$cmd"; break
        fi
    fi
done
[[ -z "$PYTHON" ]] && { echo "ERROR: Python 3.9+ not found."; exit 1; }

echo ""
echo -e "${C_BOLD}══════════════════════════════════════════════════════════${C_RESET}"
echo -e "${C_BOLD}  SemDiff v2.0 — Batch Runner${C_RESET}"
echo -e "${C_BOLD}══════════════════════════════════════════════════════════${C_RESET}"
echo ""

PASS=0; FAIL=0; SKIP=0; TOTAL_CHANGES=0

declare -a TC_LABELS=(
    "TC1  Loop Bounds"
    "TC2  Inlining"
    "TC3  Dead Code"
    "TC4  Vectorization"
    "TC5  Control Flow"
    "E01  Loop Unrolling"
    "E02  Vec Narrowing"
    "E03  Helper Inline"
    "E04  Dead Store"
    "E05  Tail Recursion"
    "E06  New Vec Variant"
    "E07  Const Folding"
    "E08  AoS → SoA"
    "E09  Loop Fusion"
    "E10  i32 → i64"
)

declare -a V1_PATHS=(
    "testcases/tc1_loop_bounds/v1.ll"
    "testcases/tc2_inlining/v1.ll"
    "testcases/tc3_dead_code/v1.ll"
    "testcases/tc4_vectorization/v1.ll"
    "testcases/tc5_control_flow/v1.ll"
    "testcases/eval/eval_01/v1.ll"
    "testcases/eval/eval_02/v1.ll"
    "testcases/eval/eval_03/v1.ll"
    "testcases/eval/eval_04/v1.ll"
    "testcases/eval/eval_05/v1.ll"
    "testcases/eval/eval_06/v1.ll"
    "testcases/eval/eval_07/v1.ll"
    "testcases/eval/eval_08/v1.ll"
    "testcases/eval/eval_09/v1.ll"
    "testcases/eval/eval_10/v1.ll"
)

declare -a V2_PATHS=(
    "testcases/tc1_loop_bounds/v2.ll"
    "testcases/tc2_inlining/v2.ll"
    "testcases/tc3_dead_code/v2.ll"
    "testcases/tc4_vectorization/v2.ll"
    "testcases/tc5_control_flow/v2.ll"
    "testcases/eval/eval_01/v2.ll"
    "testcases/eval/eval_02/v2.ll"
    "testcases/eval/eval_03/v2.ll"
    "testcases/eval/eval_04/v2.ll"
    "testcases/eval/eval_05/v2.ll"
    "testcases/eval/eval_06/v2.ll"
    "testcases/eval/eval_07/v2.ll"
    "testcases/eval/eval_08/v2.ll"
    "testcases/eval/eval_09/v2.ll"
    "testcases/eval/eval_10/v2.ll"
)

N=${#TC_LABELS[@]}

for (( i=0; i<N; i++ )); do
    label="${TC_LABELS[$i]}"
    v1="${V1_PATHS[$i]}"
    v2="${V2_PATHS[$i]}"

    if [[ ! -f "$ROOT/$v1" || ! -f "$ROOT/$v2" ]]; then
        echo -e "  ${C_YELLOW}[SKIP]${C_RESET} $label"
        ((SKIP++)); continue
    fi

    # Build args
    ARGS=("$ROOT/$v1" "$ROOT/$v2")
    [[ -n "$VERBOSE" ]] && ARGS+=("--verbose")

    T0=$SECONDS
    OUT=$("$PYTHON" "$ROOT/src/main.py" "${ARGS[@]}" 2>&1) && RC=0 || RC=$?
    ELAPSED=$(( SECONDS - T0 ))

    # Apply filter
    if [[ -n "$FILTER" ]] && ! echo "$OUT" | grep -q "\[$FILTER\]"; then
        continue
    fi

    CHANGES=$(echo "$OUT" | grep -cE '\[(VEC|LOOP|INLINE|DEAD|CFG|SIG|NEW|DEL)\]' || true)
    TOTAL_CHANGES=$((TOTAL_CHANGES + CHANGES))

    if [[ $RC -eq 0 ]]; then
        echo -e "  ${C_GREEN}[PASS]${C_RESET} ${C_BOLD}${label}${C_RESET}  ${C_MUTED}(${ELAPSED}s · ${CHANGES} change(s))${C_RESET}"
        ((PASS++))
    else
        echo -e "  ${C_RED}[FAIL]${C_RESET} ${C_BOLD}${label}${C_RESET}"
        echo "$OUT" | head -5 | sed 's/^/         /'
        ((FAIL++))
    fi

    if [[ $RC -eq 0 ]]; then
        # HTML report
        if [[ $DO_HTML -eq 1 ]]; then
            SLUG=$(echo "${label// /_}" | tr '[:upper:]' '[:lower:]')
            HTML_OUT="reports/${SLUG}.html"
            mkdir -p "$ROOT/reports"
            "$PYTHON" "$ROOT/src/main.py" "$ROOT/$v1" "$ROOT/$v2" \
                --format html --output "$ROOT/$HTML_OUT" 2>/dev/null || true
            echo -e "       ${C_MUTED}→ $HTML_OUT${C_RESET}"
        fi

        # JSON output
        if [[ $DO_JSON -eq 1 ]]; then
            SLUG=$(echo "${label// /_}" | tr '[:upper:]' '[:lower:]')
            JSON_OUT="reports/${SLUG}.json"
            mkdir -p "$ROOT/reports"
            "$PYTHON" "$ROOT/src/main.py" "$ROOT/$v1" "$ROOT/$v2" \
                --format json --output "$ROOT/$JSON_OUT" 2>/dev/null || true
            echo -e "       ${C_MUTED}→ $JSON_OUT${C_RESET}"
        fi
    fi
done

echo ""
echo -e "${C_BOLD}──────────────────────────────────────────────────────────${C_RESET}"
echo -e "  ${C_GREEN}${PASS} passed${C_RESET}  ${C_RED}${FAIL} failed${C_RESET}  ${C_YELLOW}${SKIP} skipped${C_RESET}  ·  ${TOTAL_CHANGES} total change(s) detected"
echo -e "${C_BOLD}══════════════════════════════════════════════════════════${C_RESET}"
echo ""

# Generate dashboard if requested
if [[ $DASHBOARD -eq 1 ]]; then
    echo -e "${C_CYAN}Generating dashboard...${C_RESET}"
    "$PYTHON" "$ROOT/demo.py"
fi
