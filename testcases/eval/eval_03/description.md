# EVAL-03: Inlining of small helper function

## Commit Context
Developer added `__attribute__((always_inline))` to `fast_abs` after profiling
showed overhead from the call in tight loop (inspired by OpenBLAS refactoring).

## What Changed
`fast_abs` is inlined into `normalize_signal` and removed from the module.
The call site disappears; the function body (neg + select) appears inline.

## Expected Tool Output
- `[DEL] [WARNING] @fast_abs`: Function removed from module
- `[INLINE] [SIGNIFICANT] @normalize_signal`: Call to @fast_abs reduced 1 → 0 (callee removed)

## Semantic Impact
- Eliminates call overhead (setup/teardown) inside tight loop
- Enables further optimization: combined abs+sdiv may be folded
- Code size: slightly larger (no shared fast_abs body)
