# EVAL-06: New Vectorized Variant Added (Function Addition)

## Commit Context
Inspired by BLAS Level-1 optimization in OpenBLAS: adding an explicit AVX2
hand-vectorized variant alongside the portable scalar version.

## What Changed
- `l2_norm_scalar`: unchanged (scalar fallback preserved)
- `l2_norm_avx`: NEW function with <8 x float> SIMD implementation

## Expected Tool Output
- `[NEW] [INFO] @l2_norm_avx`: New function @l2_norm_avx added to module

## Semantic Impact
- Runtime dispatch can now select AVX2 path on supported hardware
- 8× potential throughput improvement for large vectors
- The scalar function remains as fallback for old CPUs
