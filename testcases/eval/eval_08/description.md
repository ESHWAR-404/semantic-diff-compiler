# EVAL-08: AoS → SoA Layout Change Enables Vectorization

## Commit Context
Data structure layout change in a particle physics simulation (inspired by
CERN's ROOT framework AoS→SoA migration).

## What Changed
- Old: `update_particles_aos` — Array-of-Structs, strided access, scalar loop
- New: `update_particles_soa` — Struct-of-Arrays, contiguous access, vectorized loop

## Expected Tool Output
- `[DEL] [WARNING] @update_particles_aos`: Function removed
- `[NEW] [INFO] @update_particles_soa`: New function with <8 x float> vectorization

## Semantic Impact
- Memory bandwidth: much more efficient (sequential vs strided access)
- SIMD utilization: 8 particles updated per instruction instead of 1
- Typical speedup: 4–8× for this class of simulation
- API change: callers must reorganize data layout (breaking change)
