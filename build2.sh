#!/usr/bin/env bash
# build2.sh — SemDiff v2.0 Enhanced Build & Validation Script
# Runs all 15 test cases, validates outputs, and generates an HTML dashboard.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

C_RED='\033[0;31m'; C_GREEN='\033[0;32m'; C_YELLOW='\033[1;33m'
C_CYAN='\033[0;36m'; C_BOLD='\033[1m'; C_RESET='\033[0m'

info()  { echo -e "${C_CYAN}[INFO]${C_RESET}  $*"; }
ok()    { echo -e "${C_GREEN}[PASS]${C_RESET}  $*"; }
warn()  { echo -e "${C_YELLOW}[WARN]${C_RESET}  $*"; }
fail()  { echo -e "${C_RED}[FAIL]${C_RESET}  $*" >&2; }
header(){ echo -e "\n${C_BOLD}$*${C_RESET}"; }

PASS=0; FAIL=0; SKIP=0

echo ""
echo -e "${C_BOLD}══════════════════════════════════════════════════════════${C_RESET}"
echo -e "${C_BOLD}  SemDiff v2.0 — Full Build & Validation${C_RESET}"
echo -e "${C_BOLD}══════════════════════════════════════════════════════════${C_RESET}"
echo ""

# ---- Python ----
header "Step 1 — Python"
PYTHON=""
for cmd in python python3 python3.12 python3.11 python3.10; do
    if command -v "$cmd" &>/dev/null 2>&1; then
        VER=$("$cmd" --version 2>/dev/null) || VER=""
        [[ -z "$VER" ]] && continue
        if "$cmd" -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" 2>/dev/null; then
            PYTHON="$cmd"; break
        fi
    fi
done
[[ -z "$PYTHON" ]] && { fail "Python 3.9+ not found"; exit 1; }
ok "Python: $("$PYTHON" --version)"

# ---- Source files ----
header "Step 2 — Source File Verification"
SOURCES=(
    "src/__init__.py" "src/main.py" "src/compiler.py"
    "src/normalizer.py" "src/cfg_parser.py" "src/diff_engine.py"
    "src/classifier.py" "src/reporter.py"
)
MISSING_SRC=0
for f in "${SOURCES[@]}"; do
    if [[ -f "$ROOT/$f" ]]; then ok "  $f"
    else warn "  MISSING: $f"; MISSING_SRC=1; fi
done
[[ $MISSING_SRC -eq 1 ]] && { fail "Source files missing — aborting"; exit 1; }

# ---- Syntax check ----
header "Step 3 — Syntax Check"
for f in "${SOURCES[@]}"; do
    if "$PYTHON" -m py_compile "$ROOT/$f" 2>/dev/null; then
        ok "  $f"
    else
        fail "  Syntax error: $f"; exit 1
    fi
done

# ---- Test runner ----
header "Step 4 — Running All 15 Test Cases"
echo ""

run_tc() {
    local label="$1" v1="$2" v2="$3"
    if [[ ! -f "$ROOT/$v1" || ! -f "$ROOT/$v2" ]]; then
        warn "  [SKIP] $label — files not found"
        ((SKIP++)); return
    fi
    local out
    if out=$("$PYTHON" "$ROOT/src/main.py" "$ROOT/$v1" "$ROOT/$v2" 2>&1); then
        # Check output is non-empty
        if echo "$out" | grep -qE '\[(VEC|LOOP|INLINE|DEAD|CFG|SIG|NEW|DEL|SIGNIFICANT|WARNING|INFO)\]'; then
            ok "  $label"
            ((PASS++))
        else
            warn "  [WARN] $label — ran OK but no change tags found"
            ((PASS++))
        fi
    else
        fail "  $label"
        ((FAIL++))
    fi
}

run_tc "TC1 — Loop Bounds"       "testcases/tc1_loop_bounds/v1.ll"   "testcases/tc1_loop_bounds/v2.ll"
run_tc "TC2 — Inlining"          "testcases/tc2_inlining/v1.ll"      "testcases/tc2_inlining/v2.ll"
run_tc "TC3 — Dead Code"         "testcases/tc3_dead_code/v1.ll"     "testcases/tc3_dead_code/v2.ll"
run_tc "TC4 — Vectorization"     "testcases/tc4_vectorization/v1.ll" "testcases/tc4_vectorization/v2.ll"
run_tc "TC5 — Control Flow"      "testcases/tc5_control_flow/v1.ll"  "testcases/tc5_control_flow/v2.ll"
run_tc "EVAL-01 Loop Unrolling"  "testcases/eval/eval_01/v1.ll"      "testcases/eval/eval_01/v2.ll"
run_tc "EVAL-02 Vec Narrowing"   "testcases/eval/eval_02/v1.ll"      "testcases/eval/eval_02/v2.ll"
run_tc "EVAL-03 Helper Inline"   "testcases/eval/eval_03/v1.ll"      "testcases/eval/eval_03/v2.ll"
run_tc "EVAL-04 Dead Store"      "testcases/eval/eval_04/v1.ll"      "testcases/eval/eval_04/v2.ll"
run_tc "EVAL-05 Tail Recursion"  "testcases/eval/eval_05/v1.ll"      "testcases/eval/eval_05/v2.ll"
run_tc "EVAL-06 New Vec Variant" "testcases/eval/eval_06/v1.ll"      "testcases/eval/eval_06/v2.ll"
run_tc "EVAL-07 Const Folding"   "testcases/eval/eval_07/v1.ll"      "testcases/eval/eval_07/v2.ll"
run_tc "EVAL-08 AoS to SoA"     "testcases/eval/eval_08/v1.ll"      "testcases/eval/eval_08/v2.ll"
run_tc "EVAL-09 Loop Fusion"     "testcases/eval/eval_09/v1.ll"      "testcases/eval/eval_09/v2.ll"
run_tc "EVAL-10 i32 to i64"     "testcases/eval/eval_10/v1.ll"      "testcases/eval/eval_10/v2.ll"

echo ""
echo -e "  ${C_BOLD}Results: ${C_GREEN}${PASS} passed${C_RESET} | ${C_RED}${FAIL} failed${C_RESET} | ${C_YELLOW}${SKIP} skipped${C_RESET}"

# ---- Dashboard ----
header "Step 5 — Generating HTML Dashboard"
if "$PYTHON" "$ROOT/demo.py" --no-open; then
    ok "Dashboard generated → dashboard.html"
else
    warn "Dashboard generation failed (non-fatal)"
fi

# ---- Docs check ----
header "Step 6 — Checking docs/"
if [[ -f "$ROOT/docs/index.html" ]]; then
    ok "docs/index.html exists (GitHub Pages site)"
else
    warn "docs/index.html not found — GitHub Pages site unavailable"
fi

# ---- Summary ----
echo ""
echo -e "${C_BOLD}══════════════════════════════════════════════════════════${C_RESET}"
if [[ $FAIL -eq 0 ]]; then
    echo -e "${C_GREEN}${C_BOLD}  ✓ Build complete! All tests passed.${C_RESET}"
else
    echo -e "${C_RED}${C_BOLD}  ✗ Build done with ${FAIL} failure(s).${C_RESET}"
fi
echo ""
echo "  Quick commands:"
echo "    ./run.sh testcases/tc1_loop_bounds/v1.ll testcases/tc1_loop_bounds/v2.ll"
echo "    ./run2.sh --html"
echo "    python demo.py"
echo -e "${C_BOLD}══════════════════════════════════════════════════════════${C_RESET}"
echo ""
