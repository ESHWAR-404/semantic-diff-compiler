# Semantic Diff for Compiler IR

A production-grade CLI tool that compares two versions of a source file (or
pre-compiled LLVM IR), computes a structural diff of their Control Flow Graphs
and Data Flow elements, and reports semantic/optimization changes in plain English.

---

## What It Detects

| Category         | Example Finding                                            |
|------------------|------------------------------------------------------------|
| **VECTORIZATION** | "Vectorization GAINED (width=8): 4 vector ops introduced" |
| **LOOP_UNROLLING**| "Loop REROLLED (was ~4x unrolled): block count 8 → 3"    |
| **INLINING**      | "Call to @clamp reduced: 1 → 0 (callee removed)"          |
| **DEAD_CODE**     | "Dead-code eliminated: 2 block(s) removed"                 |
| **CONTROL_FLOW**  | "Branch eliminated: 3 conditional block(s) removed"        |
| **FUNCTION_ADDED**| "New function @l2_norm_avx added to module"                |
| **SIGNATURE**     | "Return type changed: 'i32' → 'i64'"                      |

---

## System Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python      | ≥ 3.9   | Uses dataclasses, `match` not required |
| clang/LLVM  | 11–17   | **Optional** — only needed to compile `.c`/`.cpp` inputs |

The tool works fully out-of-the-box with pre-compiled `.ll` LLVM IR files
(all 15 test cases include `.ll` files).

---

## Quick Start

### 1. Build / verify setup

```bash
./build.sh
```

This checks Python, optionally sets up a `.venv`, syntax-checks all sources,
and runs a smoke test. No internet connection or pip required.

### 2. Run against the included test cases

```bash
# TC1 — fixed vs variable loop bounds (vectorization lost)
./run.sh testcases/tc1_loop_bounds/v1.ll testcases/tc1_loop_bounds/v2.ll

# TC2 — inlining with always_inline
./run.sh testcases/tc2_inlining/v1.ll testcases/tc2_inlining/v2.ll

# TC3 — dead code elimination
./run.sh testcases/tc3_dead_code/v1.ll testcases/tc3_dead_code/v2.ll

# TC4 — vectorization gained via __restrict__
./run.sh testcases/tc4_vectorization/v1.ll testcases/tc4_vectorization/v2.ll

# TC5 — control flow restructuring
./run.sh testcases/tc5_control_flow/v1.ll testcases/tc5_control_flow/v2.ll

# Evaluation cases
./run.sh testcases/eval/eval_01/v1.ll testcases/eval/eval_01/v2.ll
./run.sh testcases/eval/eval_02/v1.ll testcases/eval/eval_02/v2.ll --verbose
```

### 3. Compile from C sources (requires clang)

```bash
./run.sh testcases/tc1_loop_bounds/v1.c testcases/tc1_loop_bounds/v2.c --opt O2
./run.sh testcases/tc4_vectorization/v1.c testcases/tc4_vectorization/v2.c --opt O3
```

### 4. JSON / HTML output

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
======================================================================
  Semantic IR Diff Report
======================================================================
  Old: testcases/tc1_loop_bounds/v1.ll
  New: testcases/tc1_loop_bounds/v2.ll
----------------------------------------------------------------------
  Functions: 0 added, 0 removed, 2 modified
----------------------------------------------------------------------

  Function: @sum_array
    [VEC] [SIGNIFICANT] @sum_array: Vectorization LOST: 2 vector ops removed
        Old version had <4 x i32> instructions
        New version uses scalar operations only
    [SIG] [SIGNIFICANT] @sum_array: Parameter types changed
        Old: ['i32*', 'i32*']
        New: ['i32*', 'i32*', 'i32']

  Function: @scale_array
    [VEC] [SIGNIFICANT] @scale_array: Vectorization LOST: 4 vector ops removed
        Old version had <8 x float> instructions
        New version uses scalar operations only

----------------------------------------------------------------------
  Change summary:
    [SIG]        1 occurrence(s)
    [VEC]        2 occurrence(s)
======================================================================
```

---

## Running All Tests at Once

```bash
for tc in tc1_loop_bounds tc2_inlining tc3_dead_code tc4_vectorization tc5_control_flow; do
    echo "=== $tc ==="
    ./run.sh "testcases/$tc/v1.ll" "testcases/$tc/v2.ll"
done

for i in $(seq -w 1 10); do
    echo "=== eval_$i ==="
    ./run.sh "testcases/eval/eval_$i/v1.ll" "testcases/eval/eval_$i/v2.ll"
done
```

---

## Project Layout

```
.
├── build.sh              Setup and verification script
├── run.sh                Main entry-point wrapper
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
│   └── eval/eval_01–10/  Realistic commit-level evaluation cases
├── README.md             This file
├── DESIGN.md             Architecture and design decisions
├── IMPLEMENTATION.md     Technical implementation details
└── EVALUATION.md         Test results and performance analysis
```

---

## Windows Notes

All scripts require a POSIX shell (Git Bash, WSL, or Cygwin).
Alternatively, run the tool directly with Python:

```powershell
python src\main.py testcases\tc1_loop_bounds\v1.ll testcases\tc1_loop_bounds\v2.ll
python src\main.py --help
```
