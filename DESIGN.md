# Design Document — Semantic Diff for Compiler IR

## 1. Problem Statement

When a compiler (clang/LLVM) compiles two versions of the same source file,
the generated IR differs in ways that are hard to understand from a raw text diff.
A text diff of LLVM IR is noisy: every inserted line shifts all subsequent register
numbers (`%5` becomes `%7`), metadata IDs shift, and structural patterns
(loops, vectorized blocks) are not visually obvious.

The goal is a tool that answers: *"What semantically changed in the compiler's
view of this code?"* — in terms a developer can act on.

---

## 2. Approaches Considered

### 2.1 Plain text diff (rejected)

**What it is**: Run `diff old.ll new.ll`.

**Problems**:
- Extremely noisy: adding one instruction shifts all `%N` register names.
- No semantic grouping: cannot distinguish "loop unrolled" from "unrelated insertion".
- Produces no actionable information about *why* the IR differs.

### 2.2 Source-level AST diff (rejected)

**What it is**: Parse both `.c` files into ASTs and diff them.

**Problems**:
- Shows *source* changes, not *compiler behavior* changes.
- Cannot detect whether the compiler chose to vectorize, unroll, or inline —
  those decisions happen *after* the AST stage.
- Requires a full C/C++ parser (heavy dependency).

### 2.3 Disassembly diff (considered, partial use)

**What it is**: Compare objdump/llvm-objdump output of compiled binaries.

**Problems**:
- Highly architecture-specific; not portable.
- Register allocation noise (different physical registers for same logical value).
- Very hard to map back to high-level concepts.

### 2.4 IR structural diff (chosen) ✓

**What it is**: Parse LLVM IR into a structured graph (functions → basic blocks →
instructions), normalize away syntactic noise, and compute a semantic diff on
the graph structure.

**Why it wins**:
- IR is at the right abstraction level: post-optimization decisions are visible
  (vector types, call sites, block structure) but higher-level than assembly.
- LLVM IR has a clean, well-defined grammar — parsing is straightforward.
- Register numbers can be normalized to remove insertion-noise.
- Vector types (`<N x T>`), call targets, branch structure, and phi nodes
  directly encode the semantic concepts we want to detect.
- No external library needed: pure Python with stdlib.

---

## 3. Architecture Overview

```
 Input files (.c/.cpp or .ll)
        │
        ▼
 ┌──────────────┐
 │  compiler.py │  clang -O2 -S -emit-llvm (or passthrough for .ll)
 └──────┬───────┘
        │  .ll text
        ▼
 ┌───────────────┐
 │ normalizer.py │  Strip metadata, canonicalize registers
 └──────┬────────┘
        │  clean .ll text (×2)
        ▼
 ┌──────────────┐
 │ cfg_parser.py│  Build Module → Function → BasicBlock → Instruction AST
 └──────┬───────┘
        │  Module objects (×2)
        ▼
 ┌───────────────┐
 │ diff_engine.py│  Match functions → match blocks → LCS instruction diff
 └──────┬────────┘
        │  ModuleDiff (FunctionDiff + BlockDiff + InstructionDiff)
        ▼
 ┌───────────────┐
 │ classifier.py │  Pattern-match IR diff → SemanticChange objects
 └──────┬────────┘
        │  [SemanticChange, ...]
        ▼
 ┌──────────────┐
 │  reporter.py │  Render text / JSON / HTML report
 └──────────────┘
```

---

## 4. Key Design Decisions

### 4.1 Normalization strategy

The normalizer must remove noise without destroying signal:

| Removed (noise)                          | Preserved (signal)              |
|------------------------------------------|---------------------------------|
| `!dbg`, `!tbaa`, `!llvm.*` metadata      | `<N x T>` vector types          |
| Attribute groups (`#0`, `#1`)            | Call targets (`@function_name`) |
| `dso_local`, `unnamed_addr`              | Branch structure (label names)  |
| Numbered register names (`%5` → `%r5`)  | PHI node predecessor lists      |
| `align N` on load/store                 | Return types                    |
| `source_filename`, `target datalayout`  | Opcode names                    |

Register canonicalization is performed *within each function independently*.
We scan in definition order and assign canonical names `%r0, %r1, ...` only
to numbered temporaries; named registers (from `-fno-discard-value-names`)
are preserved because they carry semantic information (e.g., `%arr`, `%result`).

### 4.2 Function matching

Functions are matched by *name*. This handles:
- Functions present in both versions (matched → diff)
- Functions in old only (removed → FUNCTION_REMOVED)
- Functions in new only (added → FUNCTION_ADDED)

Anonymous functions or lambdas with compiler-generated names may produce
spurious add/remove pairs — this is a known limitation (see EVALUATION.md).

### 4.3 Basic block matching

Blocks are matched in two passes:

1. **Exact name match**: if both versions have a block named `for.body`, they
   are matched directly. This works well when clang preserves IR label names
   from source variable names (which `-fno-discard-value-names` enables).

2. **Fuzzy Jaccard match**: for unmatched blocks, compute the Jaccard index
   on their instruction-pattern sets. Threshold: ≥ 0.30. This handles minor
   renames (e.g., `vector.body` → `for.vector.body`).

### 4.4 Instruction diff algorithm

For matched block pairs, we use Longest Common Subsequence (LCS) on
instruction *patterns* (opcode + type signature). This correctly identifies:
- Inserted instructions (appear as `added`)
- Deleted instructions (appear as `removed`)
- Unchanged structure (appears as `same`)

The LCS is O(m·n) where m,n are instruction counts per block. Typical LLVM
basic blocks have 2–50 instructions, so this is fast in practice.

### 4.5 Loop detection heuristic

LLVM IR does not have an explicit "loop" node; loops are encoded as back edges
in the CFG. We detect loop headers using:

1. A block has at least one PHI node (indicates a value joined from multiple
   predecessors, characteristic of loop induction variables).
2. At least one predecessor of that block appears *later* in block layout order
   (indicates a back edge).

This heuristic correctly identifies natural loops but may miss irreducible
control flow (rare in C/C++ without `goto`).

### 4.6 Unrolling detection

Loop unrolling manifests as:
- Increased total block count in the function.
- Multiple structurally similar blocks (Jaccard ≥ 0.80 on instruction patterns).

We measure the ratio `new_block_count / old_block_count`:
- ≥ 2.0 with more similar-block groups → unrolled
- ≤ 0.5 with fewer similar-block groups → rerolled

The unroll factor is estimated as `round(ratio)`.

### 4.7 Vectorization detection

Vector operations are identified by the presence of `<N x T>` types in any
instruction. We:
1. Count total vector operations per function.
2. Find the dominant vector width (most frequent N).
3. Compare old vs new: gained / lost / width-changed / count-changed.

### 4.8 Inlining detection

When a function `@foo` is inlined at a call site in `bar`:
- The `call @foo` instruction disappears from `bar`'s body.
- `@foo` itself may disappear from the module (if it was `internal` linkage).

We detect this by comparing call-site counts per callee between old and new,
and cross-referencing whether the callee still exists in the new module.

---

## 5. Alternatives Considered for Each Sub-Problem

| Sub-problem | Approach Used | Alternative | Why Not Used |
|-------------|--------------|-------------|--------------|
| Register normalization | Sequential rename within function | Hash of operand tree | Tree hash too expensive; doesn't help fuzzy matching |
| Block matching | Name + Jaccard | Graph isomorphism | NP-hard; overkill for typical IR sizes |
| Instruction diff | LCS on patterns | Edit distance | LCS cheaper; sufficient for our use case |
| Loop detection | PHI + back-edge heuristic | LLVM loop analysis pass | Requires opt binary; adds dependency |
| Vectorization | `<N x T>` regex | Check for shuffle/insert/extract | Vector type is a cleaner signal |

---

## 6. Limitations and Future Work

1. **Obfuscated function names**: C++ mangled names survive normalization.
   Future: add `c++filt`-style demangling.

2. **Intrinsic calls**: LLVM intrinsics (`@llvm.*`) are filtered from inlining
   detection but counted in vectorization metrics. Future: separate categories
   for intrinsic-based vectorization vs explicit vector types.

3. **Interprocedural analysis**: The tool diffs functions independently.
   A change that moves code between functions (e.g., outlining) produces
   an add+remove pair rather than a "moved" annotation. Future: cross-function
   matching for code outlining detection.

4. **Irreducible control flow**: Rare in C/C++, but `goto` can produce
   irreducible CFGs that confuse the loop header heuristic.

5. **Alias analysis**: Cannot tell *why* vectorization was gained/lost (e.g.,
   adding `__restrict__` vs changing the optimization level). The tool reports
   the *effect* rather than the *cause*.
