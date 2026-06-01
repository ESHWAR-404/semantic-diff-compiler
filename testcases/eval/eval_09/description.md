# EVAL-09: Loop Fusion + Vectorization

## Commit Context
Performance fix in a signal processing library: two sequential passes over
the same source array merged into one, enabling vectorization of the fused loop.

## What Changed
- Two separate scalar loops (one filling `a`, one filling `b`) fused into one
  vectorized loop that reads `src` once and writes to both `a` and `b`.
- src array read count: 2n scalar loads → n/8 vector loads (8× reduction)

## Expected Tool Output
- `[VEC] [SIGNIFICANT] @process_arrays`: Vectorization GAINED (width=8)
- `[LOOP] [INFO] @process_arrays`: Loop count reduced 2 → 1

## Semantic Impact
- Memory bandwidth: src loaded once instead of twice (cache-friendly)
- Vectorized: 8 elements per cycle vs 1
- Combined speedup typically 10-16× for memory-bound workloads
