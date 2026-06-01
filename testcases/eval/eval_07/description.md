# EVAL-07: Constant Folding + Inline of Constant-returning Function

## Commit Context
Developer marked `get_page_size()` as `__attribute__((const))` allowing LLVM's
constant folding and inliner to propagate its value (4096) through callers.

## What Changed
- `get_page_size`: body simplified to `ret i32 4096` (mul folded to constant)
- `compute_buffer_size`: call to `get_page_size` eliminated; `header` computation
  folded to constant 4160 (4096+64); function now 1 instruction + ret.
- `hash_combine`: magic constant `2654435761` folded to its signed i32 representation
  `-1640531527` (same bit pattern, different IR representation).

## Expected Tool Output
- @compute_buffer_size: INLINING (call to @get_page_size removed) + CFG modified
- @get_page_size: modified (block instructions reduced)
- @hash_combine: modified (operand changed due to constant canonicalization)

## Semantic Impact
- Eliminates function call overhead at each compute_buffer_size call site
- Compile-time resolved computation; zero runtime cost
