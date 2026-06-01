# SemDiff — Semantic Diff for Compiler IR &nbsp; `v2.0`

> **Compare two versions of a C/C++ file (or pre-compiled LLVM IR) and get a plain-English report of what the compiler's optimizer actually changed — vectorization gained/lost, inlining, loop unrolling, dead code, control-flow rewrites, and ABI-breaking signature changes.**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-15%2F15%20passing-brightgreen)](#test-cases)
[![Detection](https://img.shields.io/badge/Detection%20Rate-100%25-brightgreen)](#evaluation)
[![False Positives](https://img.shields.io/badge/False%20Positives-0-brightgreen)](#evaluation)
[![No pip](https://img.shields.io/badge/dependencies-stdlib%20only-blue)](#system-requirements)
[![License](https://img.shields.io/badge/License-MIT-blue)](#)

**🌐 [Interactive Website & Charts →](https://eshwar-404.github.io/semantic-diff-compiler/)**

---

## What's New in v2.0

| Feature | v1 | v2 |
|---|---|---|
| Interactive website with charts | ✗ | ✅ |
| Full HTML dashboard (`demo.py`) | ✗ | ✅ |
| Batch runner (`run2.sh`) | ✗ | ✅ |
| Extended build validation (`build2.sh`) | ✗ | ✅ |
| GitHub Pages site | ✗ | ✅ |
| Stacked performance chart | ✗ | ✅ |

---

## What It Detects

| Category | Example Finding | Severity |
|---|---|---|
| **VECTORIZATION** | `Vectorization GAINED (width=8): 4 vector ops introduced` | SIGNIFICANT |
| **LOOP_UNROLLING** | `Loop REROLLED (was ~4x unrolled): block count 8 → 3` | SIGNIFICANT |
| **INLINING** | `Call to @clamp reduced: 1 → 0 (callee removed — likely inlined)` | SIGNIFICANT |
| **DEAD_CODE** | `Dead-code eliminated: 2 block(s) removed` | INFO |
| **CONTROL_FLOW** | `Branch eliminated: 3 conditional block(s) removed` | WARNING |
| **FUNCTION_ADDED** | `New function @l2_norm_avx added to module` | INFO |
| **FUNCTION_REMOVED** | `Function @fast_abs removed from module` | WARNING |
| **SIGNATURE** | `Return type changed: 'i32' → 'i64'` | SIGNIFICANT |

---

## System Requirements

| Requirement | Version | Notes |
|---|---|---|
| Python | ≥ 3.9 | stdlib only — no pip install needed |
| clang / LLVM | 11–17 | **Optional** — only for `.c`/`.cpp` inputs |

All 15 test cases include pre-compiled `.ll` files — clang is not required to run them.

---

## Quick Start

### 1. Build / verify setup

```bash
./build.sh          # original — checks Python, runs smoke test
./build2.sh         # v2 — full validation: runs all 15 tests, generates dashboard
```

### 2. Run a single comparison

```bash
./run.sh testcases/tc1_loop_bounds/v1.ll testcases/tc1_loop_bounds/v2.ll
./run.sh testcases/tc4_vectorization/v1.ll testcases/tc4_vectorization/v2.ll --verbose
```

### 3. Run all test cases at once (v2 batch runner)

```bash
./run2.sh           # runs all 15 test cases, shows summary
./run2.sh --html    # also generates per-case HTML reports
./run2.sh --json    # also outputs machine-readable JSON for each case
```

### 4. Generate the interactive HTML dashboard (v2)

```bash
python demo.py
# → opens dashboard.html in your browser automatically
```

### 5. Compile from C sources (requires clang)

```bash
./run.sh testcases/tc1_loop_bounds/v1.c testcases/tc1_loop_bounds/v2.c --opt O2
./run.sh testcases/tc4_vectorization/v1.c testcases/tc4_vectorization/v2.c --opt O3
```

### 6. JSON / HTML output

```bash
./run.sh testcases/tc1_loop_bounds/v1.ll testcases/tc1_loop_bounds/v2.ll \
    --format json --output report.json

./run.sh testcases/tc4_vectorization/v1.ll testcases/tc4_vectorization/v2.ll \
    --format html --output report.html
```

---

## CLI Reference

```
usage: semdiff [-h] [--opt LEVEL] [--format FMT] [--output FILE]
               [--verbose] [--show-block-diff] [--show-ir] [--keep-tmp]
               OLD_FILE NEW_FILE

positional arguments:
  OLD_FILE            Old source (.c/.cpp) or IR (.ll) file
  NEW_FILE            New source (.c/.cpp) or IR (.ll) file

options:
  --opt LEVEL         Optimization level: O0 O1 O2 O3 Os Oz (default: O2)
  --format FMT        Output format: text | json | html (default: text)
  --output FILE       Write report to FILE instead of stdout
  --verbose, -v       Show detailed change descriptions
  --show-block-diff   Include block-level diff table in text report
  --show-ir           Print normalized IR before the report (debug)
  --keep-tmp          Keep temporary compiled .ll files
```

---

## Example Output

```
══════════════════════════════════════════════════════════════
  Semantic IR Diff Report  ·  v2.0
══════════════════════════════════════════════════════════════
  Old: testcases/tc1_loop_bounds/v1.ll
  New: testcases/tc1_loop_bounds/v2.ll
──────────────────────────────────────────────────────────────
  Functions: 0 added · 0 removed · 2 modified
──────────────────────────────────────────────────────────────

  Function: @sum_array
    [VEC] [SIGNIFICANT] Vectorization LOST: 2 vector ops removed
        Old version had <4 x i32> instructions
        New version uses scalar operations only
    [SIG] [SIGNIFICANT] Parameter types changed
        Old: ['i32*', 'i32*']
        New: ['i32*', 'i32*', 'i32']

  Function: @scale_array
    [VEC] [SIGNIFICANT] Vectorization LOST: 4 vector ops removed
        Old version had <8 x float> instructions
        New version uses scalar operations only

──────────────────────────────────────────────────────────────
  Change summary:
    [SIG]        1 occurrence(s)
    [VEC]        2 occurrence(s)
══════════════════════════════════════════════════════════════
```

---

## Video Demo

Example video of how to set up the Python venv and run the test cases to generate a report.

---

## Evaluation Results

| Metric | Result |
|---|---|
| Total test cases | 15 (5 synthetic + 10 realistic) |
| Changes to detect | 24 |
| Correctly detected | **24 / 24** |
| Detection rate | **100%** |
| False positive rate | **0%** |
| Avg. runtime | ~70 ms (Python startup dominates) |

See [EVALUATION.md](EVALUATION.md) for per-case breakdown.

---

## Project Layout

```
.
├── build.sh              Original setup and verification script (CLI)
├── build2.sh             v2 — full test suite runner + dashboard generator
├── run.sh                Original CLI entry-point (unchanged)
├── run2.sh               v2 — batch runner for all test cases
├── demo.py               v2 — generates interactive HTML dashboard
├── docs/
│   └── index.html        GitHub Pages website with interactive charts
├── src/
│   ├── main.py           CLI argument parsing and pipeline orchestration
│   ├── compiler.py       Clang invocation; .c → .ll compilation
│   ├── normalizer.py     LLVM IR normalization (metadata strip, register rename)
│   ├── cfg_parser.py     IR → Module/Function/BasicBlock/Instruction AST
│   ├── diff_engine.py    Structural CFG diff (LCS-based instruction matching)
│   ├── classifier.py     Semantic change classification engine
│   └── reporter.py       Text / JSON / HTML report rendering
├── testcases/
│   ├── tc1_loop_bounds/  Fixed vs variable bounds (vectorization/unrolling)
│   ├── tc2_inlining/     always_inline attribute effect
│   ├── tc3_dead_code/    Dead branch elimination
│   ├── tc4_vectorization/ __restrict__ enabling SIMD
│   ├── tc5_control_flow/ Branchless / algorithm redesign
│   └── eval/eval_01–10/ Realistic commit-level evaluation cases
├── README.md             This file
├── DESIGN.md             Architecture and design decisions
├── IMPLEMENTATION.md     Technical implementation details
├── EVALUATION.md         Test results and performance analysis
└── CHANGELOG.md          Version history
```

---

## How It Compares

| Method | Detects Vectorization | Detects Inlining | Actionable Output | Noise |
|---|---|---|---|---|
| `diff old.ll new.ll` | ✗ | ✗ | ✗ | Very High |
| `diff old.c new.c` | ✗ | ✗ | Source only | Medium |
| **SemDiff (this tool)** | **✓** | **✓** | **✓ IR + English** | **Low** |
| `opt -print-changed` | ✓ | ✓ | ✗ (raw verbose) | Very High |
| Compiler Explorer | Manual | Manual | ✗ | N/A |

---

## Windows

All shell scripts require Git Bash, WSL, or Cygwin. Alternatively, use Python directly:

```powershell
python src\main.py testcases\tc1_loop_bounds\v1.ll testcases\tc1_loop_bounds\v2.ll
python demo.py
```

---

*SemDiff v2.0 — 15/15 tests · 24/24 detections · 0 false positives · stdlib only*
