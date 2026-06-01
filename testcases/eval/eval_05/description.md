# EVAL-05: Tail Recursion Elimination / Iterative Conversion

## Commit Context
Inspired by a Haskell-to-C translation change and a GHC optimization discussion.
Developer rewrote factorial as accumulator-style (tail-recursive) and fib as iterative
to eliminate stack overflow risk for large inputs.

## What Changed
- `factorial`: changed from classic recursion (call + multiply) to accumulator loop
  (phi-based iteration — tail call eliminable).
- `fib`: changed from doubly-recursive (exponential) to iterative (linear).
  Two recursive calls replaced with three phi nodes in a single loop.

## Expected Tool Output
- `@factorial`: INLINING change (recursive call removed/tail-call converted) + CFG change
- `@fib`: INLINING change (two recursive calls to @fib removed) + LOOP_UNROLLING info

## Semantic Impact
- factorial: O(n) stack → O(1) stack; same O(n) time
- fib: O(2^n) → O(n) time; O(n) stack → O(1) stack
- Critical correctness fix: eliminates stack overflow for large n
