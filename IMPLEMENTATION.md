# Implementation Reference — Semantic Diff for Compiler IR &nbsp; `v2.0`

## 1. LLVM IR Grammar Subset (Implemented)

The parser handles the following LLVM IR constructs:

```
module       ::= ( function | declaration | global )* metadata*
function     ::= "define" ret_type "@" name "(" params ")" "{" block+ "}"
declaration  ::= "declare" ret_type "@" name "(" params ")"
block        ::= label? ":" (";" preds_comment)? instruction* terminator
instruction  ::= (result "=")? opcode type operands...
terminator   ::= br | ret | switch | invoke | unreachable | ...
```

Notable constructs *not* parsed (treated as opaque instruction text):
- `landingpad` / `cleanuppad` (exception handling)
- Inline assembly (`asm` keyword)
- Complex `getelementptr` with multiple indices (captured as raw text)

---

## 2. Normalization Pipeline (`src/normalizer.py`)

### 2.1 Line-level filtering

```python
_META_LINE = re.compile(r'^(?:!\d+\s*=|source_filename\s*=|target\s+...|attributes\s+#\d+\s*=)')
```

Lines matching `_META_LINE` are dropped entirely. This removes:
- Metadata node definitions: `!42 = !{...}`
- Module banners: `source_filename = "foo.c"`
- Target specs: `target datalayout = "..."`, `target triple = "..."`
- Attribute groups: `attributes #0 = { nounwind uwtable ... }`

### 2.2 Inline annotation removal

```python
_INLINE_META = re.compile(
    r",?\s*!(?:dbg|tbaa|tbaa\.struct|noalias|alias\.scope|...)  \s*!\d+"
)
```

Applied to every surviving line. Removes annotations like:
- `, !dbg !23`
- `, !tbaa !4`
- `, !nontemporal !1`

### 2.3 Attribute reference removal

```python
_ATTR_REF = re.compile(r"\s+#\d+\b")
```

Removes `#0`, `#1`, etc. from function definitions and call instructions.

### 2.4 Register canonicalization

```python
def _canonicalize_registers(func_lines: list[str]) -> list[str]:
    order: dict[str, int] = {}
    counter = 0
    for line in func_lines:
        for m in _NUMBERED_REG.finditer(line):
            reg = m.group(1)
            if reg not in order:
                order[reg] = counter
                counter += 1
    def replace(m):
        return f"%r{order[m.group(1)]}"
    return [_NUMBERED_REG.sub(replace, l) for l in func_lines]
```

**Input**: `%5 = add i32 %3, %4`  
**Output**: `%r2 = add i32 %r0, %r1`  (assuming %3→r0, %4→r1, %5→r2 in order)

Named registers (`%arr`, `%result`, `%i.04`) are intentionally preserved:
- They carry semantic meaning (variable names from source).
- They are stable across minor IR changes (unlike numbered ones).

---

## 3. CFG Parser (`src/cfg_parser.py`)

### 3.1 Data model

```
Module
 └─ functions: dict[name → Function]
     └─ blocks: dict[name → BasicBlock]
         └─ instructions: list[Instruction]
```

Key `Instruction` fields:
- `opcode: str` — first word of instruction body (e.g., `"load"`, `"br"`)
- `type_sig: str` — `"opcode"` or `"opcode:<N x T>"` for vector ops
- `is_vector: bool`, `vector_width: int` — extracted from `<N x T>` pattern
- `is_call: bool`, `call_target: str | None` — call target name
- `is_phi: bool` — marks PHI nodes (loop header indicators)
- `is_terminator: bool` — marks block terminators

### 3.2 Block label detection

```python
_BLOCK_LABEL = re.compile(r'^([A-Za-z_][A-Za-z0-9_.]*)\s*:(?:\s*;.*)?$')
```

Matches both simple labels (`for.body:`) and labels with predecessor comments
(`for.body:   ; preds = %entry, %for.inc`).

The entry block (first block in a function) often has no label — the parser
assigns it the synthetic name `"entry"`.

### 3.3 Successor extraction

Successors are extracted from terminator instructions:

```python
_BR_COND   = re.compile(r'br\s+i1\s+[^,]+,\s*label\s+%([^\s,]+),\s*label\s+%([^\s,]+)')
_BR_UNCOND = re.compile(r'br\s+label\s+%([^\s,}]+)')
_SWITCH    = re.compile(r'switch\s+\S+\s+[^,]+,\s*label\s+%([^\s[]+)(.*)', re.DOTALL)
_INVOKE    = re.compile(r'invoke\s+.*?to\s+label\s+%([^\s]+)\s+unwind\s+label\s+%([^\s]+)')
```

Predecessors are back-filled after all blocks in a function are parsed,
by iterating over all blocks and adding to each successor's predecessor list.

### 3.4 Loop header heuristic

```python
def loop_headers(self) -> list[BasicBlock]:
    headers = []
    for name, block in self.blocks.items():
        if block.has_phi:
            my_idx = self.block_order.index(name)
            for pred in block.predecessors:
                pred_idx = self.block_order.index(pred)
                if pred_idx > my_idx:           # back edge
                    headers.append(block)
                    break
    return headers
```

A block is a loop header if:
1. It has a PHI node (values from multiple predecessors — loop induction).
2. At least one predecessor appears later in the block layout order (back edge).

---

## 4. Diff Engine (`src/diff_engine.py`)

### 4.1 LCS instruction diff

The LCS table is computed on instruction *patterns* (`opcode:type_sig`), not
on raw text. This means:
- `%r5 = add i32 %r3, %r4` matches `%r7 = add i32 %r5, %r6` (same pattern: `"add"`)
- `load <4 x i32>` does NOT match `load <8 x i32>` (different patterns)
- `call @foo` does NOT match `call @bar` (different call targets in opcode)

Wait — call targets are in the operands, not the opcode. The `pattern` property:

```python
@property
def pattern(self) -> str:
    return f"{self.opcode}:{self.type_sig}"
```

So `call @foo` and `call @bar` both have pattern `"call"`. This means the LCS
would consider them "same" for structural purposes. The *inlining* classifier
separately compares call targets to detect the semantic change. This is
intentional: the structural diff says "a call instruction is here", while the
classifier says "but it's calling a different function".

### 4.2 Jaccard block matching

```python
def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0
```

Applied to instruction *pattern* lists. A threshold of 0.30 is used —
lower than typical similarity thresholds — because IR blocks often differ
significantly between versions even when semantically related.

---

## 5. Change Classifier (`src/classifier.py`)

### 5.1 Vectorization classifier

```python
old_counts = _count_vector_ops(fd.old_func)   # {width: count}
new_counts = _count_vector_ops(fd.new_func)
old_total = sum(old_counts.values())
new_total = sum(new_counts.values())
old_width = _dominant_width(old_counts)
new_width = _dominant_width(new_counts)
```

Decision tree:
1. `old_total == 0` and `new_total > 0` → **GAINED**
2. `old_total > 0` and `new_total == 0` → **LOST**
3. Both > 0 and `old_width != new_width` → **WIDTH CHANGED**
4. Both > 0 and count differs by > 25% → **COUNT CHANGED** (info)

### 5.2 Inlining classifier

```python
old_calls = _call_sites(fd.old_func)   # {callee: count}
new_calls = _call_sites(fd.new_func)

for callee, old_count in old_calls.items():
    if _is_intrinsic(callee): continue
    new_count = new_calls.get(callee, 0)
    if new_count < old_count:
        callee_gone = callee not in new_module.defined_functions()
        ...
```

LLVM intrinsics (`llvm.*`) are excluded from inlining analysis — they are
not user-defined functions and their presence/absence reflects code generation
choices, not inlining decisions.

### 5.3 Loop unrolling classifier

```python
old_groups = _similar_block_groups(fd.old_func)  # groups of Jaccard >= 0.80
new_groups = _similar_block_groups(fd.new_func)
ratio = new_block_count / old_block_count
```

The similar-block-group finder (`_similar_block_groups`) uses a greedy O(n²)
algorithm. For typical functions (< 100 blocks), this is fast. For pathologically
large functions (generated code, large unrolled loops), performance may degrade —
future: add a block-count early-exit.

### 5.4 Control flow classifier

```python
def is_cond_block(name: str) -> bool:
    return any(kw in name for kw in
               ("if", "then", "else", "cond", "true", "false",
                "switch", "case", "default", "land", "lor"))
```

This name-based heuristic works well with clang's default block naming
(`-fno-discard-value-names`). Without that flag (or with `-O0`-stripped IR),
blocks may be named `bb1`, `bb2`, etc. and the heuristic may not fire.
The tool still detects *structural* changes (added/removed blocks) even
when the semantic classification is uncertain.

---

## 6. Reporter (`src/reporter.py`)

### 6.1 ANSI color support

```python
def _supports_color() -> bool:
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleMode(
                ctypes.windll.kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
```

On Windows, the tool attempts to enable VT100 processing via `SetConsoleMode`.
This works on Windows 10 v1511+ (Threshold 2) and Windows 11. On older systems,
color codes are disabled.

### 6.2 Severity ordering

Changes are sorted by:
1. Severity: `significant` < `warning` < `info`
2. Function name (alphabetical within each severity)

This ensures the most important changes appear first in the report.

---

## 7. Error Handling

| Error condition | Behavior |
|-----------------|----------|
| File not found | `ERROR: File not found: <path>` → exit 2 |
| clang not in PATH | `ERROR: clang not found...` with install hint → exit 1 |
| Compilation failure | Full stderr from clang → exit 1 |
| Syntax error in .ll | Parser tolerates it; unknown lines become `opcode=unknown` |
| Empty IR file | Produces empty Module; report: "No semantic changes detected" |
| Internal Python error | Full traceback → exit 3 (bug report requested) |

---

## 8. Performance Characteristics

| Input size | Parse time | Diff time | Total |
|------------|-----------|-----------|-------|
| 2 small functions (TC3) | < 1 ms | < 1 ms | ~50 ms |
| 5 functions, 20 blocks each | ~5 ms | ~5 ms | ~80 ms |
| Large IR (1000 blocks) | ~200 ms | ~500 ms | ~1 s |

The dominant cost is Python startup + file I/O, not the algorithm itself.
For production use with very large IR files (generated code, link-time IR),
a C extension or Rust port of the parser would be appropriate.

---

## 9. v2.0 Additions

### 9.1 Dashboard Generator (`demo.py`)

`demo.py` drives the tool as a subprocess for all 15 test cases and aggregates
results into a single self-contained HTML file with embedded Chart.js graphs.

Key implementation notes:

- Runs each test case **twice** — once with `--format text` (for display) and once
  with `--format json` (for structured data extraction). The JSON path allows the
  dashboard to compute per-category totals without screen-scraping.
- `colorize_text(text)` applies HTML `<span>` tags to known patterns (`[VEC]`,
  `[SIGNIFICANT]`, etc.) using `html.escape()` first to prevent XSS from file paths.
- The dashboard is **fully self-contained**: Chart.js is loaded from CDN but all
  result data is inlined as JSON literals — no server needed, works offline after
  first load.

### 9.2 Batch Runner (`run2.sh`)

`run2.sh` uses Bash arrays to map labels → v1/v2 paths. Key design choices:

- Uses `grep -c` with `|| true` to count change tags without triggering `set -e`
  on zero matches.
- `--filter TAG` uses a secondary `grep -q` on the output before printing, allowing
  selective display (e.g., `./run2.sh --filter VEC` shows only vectorization cases).
- `--html` / `--json` modes create a `reports/` directory automatically and write
  per-case files using slug-ified label names (`tc1__loop_bounds.html`).

### 9.3 GitHub Pages Site (`docs/index.html`)

The site is a single self-contained HTML file with:

- **No build step** — plain HTML + CSS + inline `<script>` blocks
- **Chart.js 4.4** via CDN for all four interactive graphs
- **Sticky nav** with `backdrop-filter: blur` for a glass morphism effect
- **CSS custom properties** (`--bg`, `--accent`, etc.) for a consistent dark theme
- **Responsive grid** via `repeat(auto-fit, minmax(...))` — works on mobile without
  media query breakpoints for most components
- **Terminal mockup** using pure CSS flexbox and a monospace code block — no images

All chart data is hardcoded from the evaluation results (deterministic across runs).
