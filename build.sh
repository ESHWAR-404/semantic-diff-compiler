#!/usr/bin/env bash
# build.sh — Set up the Semantic Diff for Compiler IR tool
# Works on Linux, macOS, and Windows (Git Bash / WSL)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_CYAN='\033[0;36m'
COLOR_RESET='\033[0m'

info()    { echo -e "${COLOR_CYAN}[INFO]${COLOR_RESET}  $*"; }
ok()      { echo -e "${COLOR_GREEN}[OK]${COLOR_RESET}    $*"; }
warn()    { echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET}  $*"; }
fail()    { echo -e "${COLOR_RED}[FAIL]${COLOR_RESET}  $*" >&2; exit 1; }

echo ""
echo "======================================================"
echo "  Semantic Diff for Compiler IR — Build Script"
echo "======================================================"
echo ""

# ---- Step 1: Python ----
info "Checking Python..."
PYTHON=""
for cmd in python python3 python3.12 python3.11 python3.10; do
    if command -v "$cmd" &>/dev/null 2>&1; then
        # Guard: capture version without triggering set -e on Windows Store stub
        VER=$("$cmd" --version 2>/dev/null) || VER=""
        [[ -z "$VER" ]] && continue
        # Check version >= 3.9 (also guarded)
        if "$cmd" -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" 2>/dev/null; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    fail "Python 3.9+ not found. Install from https://python.org"
fi
PYVER=$("$PYTHON" --version)
ok "Found: $PYVER ($PYTHON)"

# ---- Step 2: Optional virtual environment ----
VENV_DIR="$ROOT/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
    info "Creating virtual environment at .venv ..."
    "$PYTHON" -m venv "$VENV_DIR"
    ok "Virtual environment created"
else
    ok "Virtual environment already exists"
fi

# Activate venv
if [[ -f "$VENV_DIR/bin/activate" ]]; then
    source "$VENV_DIR/bin/activate"
elif [[ -f "$VENV_DIR/Scripts/activate" ]]; then
    source "$VENV_DIR/Scripts/activate"
fi
PYTHON="$("$PYTHON" -c "import sys; print(sys.executable)")"

# ---- Step 3: Python dependencies (stdlib only — no pip needed) ----
info "Checking Python standard library modules..."
MISSING=()
for mod in re dataclasses pathlib argparse tempfile shutil json subprocess; do
    if ! "$PYTHON" -c "import $mod" &>/dev/null; then
        MISSING+=("$mod")
    fi
done
if [[ ${#MISSING[@]} -gt 0 ]]; then
    fail "Missing Python modules: ${MISSING[*]}"
else
    ok "All required Python modules available (stdlib only)"
fi

# ---- Step 4: LLVM / clang (optional) ----
echo ""
info "Checking for LLVM/clang (optional — needed only for .c/.cpp inputs)..."
CLANG_FOUND=0
for cmd in clang clang-17 clang-16 clang-15 clang-14 clang-13; do
    if command -v "$cmd" &>/dev/null; then
        VER=$("$cmd" --version 2>/dev/null | head -1)
        ok "Found: $VER"
        CLANG_FOUND=1
        break
    fi
done

if [[ $CLANG_FOUND -eq 0 ]]; then
    warn "clang not found. The tool will work with pre-compiled .ll files."
    warn "To compile .c/.cpp files, install LLVM: https://releases.llvm.org/"
    warn "  Ubuntu/Debian: sudo apt install clang"
    warn "  macOS:         brew install llvm"
    warn "  Windows:       choco install llvm  OR  winget install LLVM.LLVM"
fi

OPT_FOUND=0
for cmd in opt opt-17 opt-16 opt-15 opt-14; do
    if command -v "$cmd" &>/dev/null; then
        ok "Found opt: $cmd"
        OPT_FOUND=1
        break
    fi
done
[[ $OPT_FOUND -eq 0 ]] && warn "opt not found (optional — used for extra optimization passes)"

# ---- Step 5: Verify source files ----
echo ""
info "Verifying project source files..."
REQUIRED=(
    "src/__init__.py"
    "src/main.py"
    "src/compiler.py"
    "src/normalizer.py"
    "src/cfg_parser.py"
    "src/diff_engine.py"
    "src/classifier.py"
    "src/reporter.py"
)
ALL_OK=1
for f in "${REQUIRED[@]}"; do
    if [[ -f "$ROOT/$f" ]]; then
        ok "  $f"
    else
        warn "  MISSING: $f"
        ALL_OK=0
    fi
done
[[ $ALL_OK -eq 0 ]] && fail "Some source files are missing"

# ---- Step 6: Syntax check ----
echo ""
info "Syntax-checking Python sources..."
for f in "${REQUIRED[@]}"; do
    if ! "$PYTHON" -m py_compile "$ROOT/$f" 2>/dev/null; then
        fail "Syntax error in $f"
    fi
done
ok "All sources pass syntax check"

# ---- Step 7: Quick smoke test ----
echo ""
info "Running smoke test (TC1: loop bounds)..."
TC1_V1="$ROOT/testcases/tc1_loop_bounds/v1.ll"
TC1_V2="$ROOT/testcases/tc1_loop_bounds/v2.ll"

if [[ -f "$TC1_V1" && -f "$TC1_V2" ]]; then
    if "$PYTHON" "$ROOT/src/main.py" "$TC1_V1" "$TC1_V2" > /dev/null 2>&1; then
        ok "Smoke test passed"
    else
        warn "Smoke test produced non-zero exit — check manually:"
        warn "  python src/main.py testcases/tc1_loop_bounds/v1.ll testcases/tc1_loop_bounds/v2.ll"
    fi
else
    warn "TC1 test files not found — skipping smoke test"
fi

# ---- Step 8: Make run.sh executable ----
chmod +x "$ROOT/run.sh" 2>/dev/null || true
chmod +x "$ROOT/build.sh" 2>/dev/null || true

echo ""
echo "======================================================"
ok "Build complete!"
echo ""
echo "  Quick start:"
echo "    ./run.sh testcases/tc1_loop_bounds/v1.ll testcases/tc1_loop_bounds/v2.ll"
echo "    ./run.sh testcases/tc2_inlining/v1.ll testcases/tc2_inlining/v2.ll"
echo "    ./run.sh --help"
echo ""
if [[ $CLANG_FOUND -eq 1 ]]; then
    echo "  With C source files:"
    echo "    ./run.sh testcases/tc1_loop_bounds/v1.c testcases/tc1_loop_bounds/v2.c --opt O2"
fi
echo "======================================================"
echo ""
