# EVAL-01: Loop Unrolling Threshold Tightened

## Commit Context
Inspired by LLVM commit rG5f3a2b1c: "Tighten loop unroll threshold for variable-count loops"

## What Changed
The compiler's loop unroller threshold was lowered. The `compute_checksum` function,
previously unrolled 4× due to a small (but non-constant) trip count, now runs as a
simple single-iteration loop.

## Expected Tool Output
- `[LOOP] [SIGNIFICANT] @compute_checksum`: Loop REROLLED — block count 5 → 3
- Old IR had 4 body blocks (unroll factor = 4), new IR has 1 body block.

## Semantic Impact
- Code size: reduced (4× smaller loop body)
- IPC: reduced (fewer instructions in flight per cycle)
- Branch misprediction: more frequent (4× more iterations)
- Compile time: faster (less IR generated)
