# EVAL-10: i32 → i64 Type Upgrade (Signature Change)

## Commit Context
Fixing a potential integer overflow bug in a database engine (inspired by
PostgreSQL's transition from int32 to int64 for large-table row counts).

## What Changed
- Both functions: i32 → i64 for array element type, count parameter, and return type.
- Alignment changed from 4 to 8 bytes.
- INT_MIN sentinel: -2147483648 → -9223372036854775808

## Expected Tool Output
- `[SIG] [SIGNIFICANT] @prefix_sum_i32`: Return type changed / parameter types changed
- `[SIG] [SIGNIFICANT] @reduce_max_i32`: Return type i32 → i64

## Semantic Impact
- Correctness: eliminates 32-bit overflow for arrays > 2^31 elements
- Performance: slight regression on 32-bit-heavy workloads (wider loads/stores)
- ABI change: all callers must be recompiled (binary-incompatible)
