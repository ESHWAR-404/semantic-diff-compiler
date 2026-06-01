# EVAL-04: Dead Store Elimination

## Commit Context
Enabling `-fno-strict-aliasing` was replaced with proper restrict qualifiers,
allowing LLVM's Dead Store Elimination (DSE) pass to fire on two functions.

## What Changed
- `init_buffer`: the zero-initializer store (immediately overwritten) is removed;
  the `add val, 1` is hoisted out of the loop.
- `compute_with_temp`: alloca + two dead stores eliminated; function now consists
  of two arithmetic instructions and a return.

## Expected Tool Output
- `@init_buffer`: modified (store removed, add instruction moved)
- `@compute_with_temp`: modified (alloca + dead stores removed — block structure simplified)

## Semantic Impact
- Reduced memory traffic: eliminates unnecessary write-then-overwrite
- Enables loop-invariant code motion (add hoisted to preheader)
- compute_with_temp: alloca removed → no stack frame needed (may enable tail-call)
