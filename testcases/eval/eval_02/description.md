# EVAL-02: AVX2 → SSE4.2 Target Change (Vector Width Narrowing)

## Commit Context
Inspired by a real portability fix: "-march=native" → "-march=x86-64-v2" in Makefile
affecting a numerical computation library.

## What Changed
Build target changed from AVX2-capable machine to baseline x86-64-v2.
`matrix_multiply_row` uses 4-wide <4 x float> instead of 8-wide <8 x float>.

## Expected Tool Output
- `[VEC] [WARNING] @matrix_multiply_row`: Vector width narrowed from 8 to 4
- Old: 3 ops at width 8; New: 3 ops at width 4

## Semantic Impact
- Throughput: halved on old hardware (2 SSE iterations per AVX2 iteration)
- Portability: now runs on all x86-64 processors without SIGILL
- Performance gap can be significant (up to 2× slowdown on bandwidth-bound code)
