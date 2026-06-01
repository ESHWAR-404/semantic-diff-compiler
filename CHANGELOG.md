# Changelog — SemDiff

All notable changes to this project are documented here.

---

## v2.0.0 — 2026-06-01

### Added
- **`docs/index.html`** — Full GitHub Pages website with interactive Chart.js graphs:
  - Detection rate by category (bar chart)
  - End-to-end runtime benchmark (stacked bar chart)
  - Change category distribution (donut chart)
  - Severity distribution (bar chart)
  - Comparison table vs other tools
  - Test case showcase with live output samples
- **`demo.py`** — Interactive HTML dashboard generator. Runs all 15 test cases,
  captures output, and produces a single self-contained `dashboard.html` with:
  - Per-case collapsible output (color-coded)
  - Live Chart.js graphs for timing, category distribution, and change counts
  - Auto-opens in browser on completion
- **`build2.sh`** — Enhanced build script that runs all 15 test cases end-to-end,
  validates output contains expected change tags, and calls `demo.py` to generate
  the dashboard. Reports pass/fail/skip summary.
- **`run2.sh`** — Batch runner for all 15 test cases with flags:
  - `--html` — generate per-case HTML reports to `reports/`
  - `--json` — generate per-case JSON outputs to `reports/`
  - `--verbose` — pass verbose flag to all cases
  - `--dashboard` — trigger full dashboard generation after run
  - `--filter TAG` — only show cases matching a specific change tag (e.g. `VEC`)
- **`CHANGELOG.md`** — This file.

### Changed
- **`README.md`** — Complete v2 rewrite:
  - Added shield badges (Python, tests, detection rate, false positives, deps, version)
  - Added v2.0 What's New comparison table
  - Added `demo.py` and batch runner usage examples
  - Added GitHub Pages website link
  - Added project layout updated with all v2 files
  - Improved comparison table vs other tools

### Unchanged
- `build.sh` — original CLI build script, untouched
- `run.sh` — original CLI entry-point, untouched
- `src/` — all source modules untouched
- `testcases/` — all test cases untouched

---

## v1.0.0 — Initial Release

### Added
- `src/compiler.py` — Clang invocation and `.c` → `.ll` compilation
- `src/normalizer.py` — LLVM IR normalization: metadata stripping, register canonicalization
- `src/cfg_parser.py` — IR parser: Module → Function → BasicBlock → Instruction AST
- `src/diff_engine.py` — LCS-based instruction diff with Jaccard block matching
- `src/classifier.py` — Semantic change classifier: VEC, LOOP, INLINE, DEAD, CFG, SIG, NEW, DEL
- `src/reporter.py` — Text (ANSI), JSON, HTML report rendering
- `src/main.py` — CLI entrypoint with full argument parsing
- `build.sh` — Setup script: Python check, venv, syntax check, smoke test
- `run.sh` — CLI wrapper with Python discovery and venv activation
- `testcases/tc1_loop_bounds/` — Fixed vs variable loop bounds
- `testcases/tc2_inlining/` — always_inline attribute
- `testcases/tc3_dead_code/` — Dead code elimination
- `testcases/tc4_vectorization/` — `__restrict__` enabling SIMD
- `testcases/tc5_control_flow/` — Branchless rewrites
- `testcases/eval/eval_01–10/` — Realistic commit-level evaluation cases
- `README.md`, `DESIGN.md`, `IMPLEMENTATION.md`, `EVALUATION.md`
- 15/15 test cases pass, 24/24 changes detected, 0 false positives
