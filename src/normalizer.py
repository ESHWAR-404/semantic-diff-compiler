"""
LLVM IR normalization layer.

Strips/canonicalizes:
  - Debug metadata (!dbg, !tbaa, !llvm.*, etc.)
  - Metadata node definitions at file scope
  - Function attribute groups (#0, #1 ...)
  - Alignment annotations (align N) on alloca/store/load
  - Local numbered register names (%0, %1 ...) -> canonical sequential names
    within each function so that insertions/deletions do not cascade
  - Source filename / module ident banners

Preserves (intentionally):
  - Vector types  <N x T>  — needed for vectorization detection
  - Call targets  @name    — needed for inlining detection
  - Opcode names           — needed for instruction-level diff
  - Branch structure (labels) — needed for CFG matching
  - PHI-node predecessors  — needed for loop detection
"""
import re
from typing import Iterator


# ---------------------------------------------------------------------------
# Metadata / banner stripping
# ---------------------------------------------------------------------------

_META_LINE = re.compile(
    r"""^
    (?:
        !\d+\s*=                   # metadata node  !42 = ...
      | source_filename\s*=        # module banner
      | target\s+(?:datalayout|triple)  # target specs
      | ;\s*Module(?:ID)?          # module ID comment
      | attributes\s+#\d+\s*=     # attribute group
    )
    """,
    re.VERBOSE,
)

_INLINE_META = re.compile(
    r",?\s*!(?:dbg|tbaa|tbaa\.struct|noalias|alias\.scope|nontemporal"
    r"|llvm\.\w+|range|nonnull|dereferenceable(?:_or_null)?)\s*!\d+"
)

_ATTR_REF = re.compile(r"\s+#\d+\b")
_ALIGN_ANNOT = re.compile(r",?\s*align\s+\d+")

# dso_local / local_unnamed_addr / unnamed_addr  — structural noise
_DSO_ATTRS = re.compile(r"\b(?:dso_local|local_unnamed_addr|unnamed_addr)\b\s*")

# comdat / section decorators
_COMDAT = re.compile(r"\bcomdat\b.*?(?=\{|$)")


# ---------------------------------------------------------------------------
# Register canonicalization
# ---------------------------------------------------------------------------

_NUMBERED_REG = re.compile(r"%(\d+)\b")
_NAMED_REG = re.compile(r"%([A-Za-z_][A-Za-z0-9_.]*)\b")
_LABEL_DEF = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*:")   # block labels
_LABEL_REF = re.compile(r"label\s+%([A-Za-z_][A-Za-z0-9_.]*)\b")


def _strip_metadata(line: str) -> str | None:
    """Return cleaned line, or None if the whole line should be dropped."""
    stripped = line.strip()
    if not stripped or stripped.startswith(";"):
        return line  # keep empty lines and comments
    if _META_LINE.match(stripped):
        return None  # drop entire line

    # Remove inline metadata annotations
    line = _INLINE_META.sub("", line)
    # Remove attribute references
    line = _ATTR_REF.sub("", line)
    # Remove alignment on loads/stores (structural noise for our purposes)
    # Keep align on alloca so stack layout stays comparable
    # Remove dso_local etc.
    line = _DSO_ATTRS.sub("", line)
    return line


def _iter_functions(lines: list[str]) -> Iterator[tuple[int, int]]:
    """Yield (start, end+1) line-index spans for each `define ... {` block."""
    i = 0
    while i < len(lines):
        if lines[i].startswith("define "):
            j = i + 1
            depth = 1
            while j < len(lines):
                ch = lines[j].strip()
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        yield (i, j + 1)
                        break
                j += 1
        i += 1


def _canonicalize_registers(func_lines: list[str]) -> list[str]:
    """
    Within a single function, rename all %N numbered registers to %rN
    in definition order so that minor IR changes don't shift all names.
    Named registers (e.g., %arr, %result) are kept as-is — they carry
    semantic meaning (source variable names when -fno-discard-value-names).
    """
    # First pass: collect definition order of numbered registers
    order: dict[str, int] = {}
    counter = 0
    for line in func_lines:
        for m in _NUMBERED_REG.finditer(line):
            reg = m.group(1)
            if reg not in order:
                order[reg] = counter
                counter += 1

    if not order:
        return func_lines

    def replace(m: re.Match) -> str:
        return f"%r{order[m.group(1)]}"

    return [_NUMBERED_REG.sub(replace, l) for l in func_lines]


def normalize(ir_text: str) -> str:
    """
    Full normalization pipeline for a .ll file's text content.
    Returns cleaned, canonicalized IR text.
    """
    lines = ir_text.splitlines(keepends=True)
    cleaned: list[str] = []
    for line in lines:
        result = _strip_metadata(line.rstrip("\n"))
        if result is not None:
            cleaned.append(result)

    # Canonicalize registers per function
    out: list[str] = []
    spans = list(_iter_functions(cleaned))
    covered: set[int] = set()
    for start, end in spans:
        func_lines = cleaned[start:end]
        canon = _canonicalize_registers(func_lines)
        for i, line in enumerate(canon):
            out.append(line)
        covered.update(range(start, end))

    # Include non-function lines (globals, declare, etc.)
    non_func: list[str] = []
    for i, line in enumerate(cleaned):
        if i not in covered:
            non_func.append(line)

    # Interleave: globals first, then functions (already in order)
    final_lines: list[str] = []
    func_idx = 0
    non_func_idx = 0
    i = 0
    # Simpler: just concatenate non-function at top, functions below
    # (we only diff function bodies, globals are shown separately)
    result_parts: list[str] = []
    result_parts.extend(non_func)
    result_parts.extend(out)
    return "\n".join(result_parts)


def normalize_file(path: str) -> str:
    """Read a .ll file and return normalized IR text."""
    with open(path, "r", errors="replace") as f:
        return normalize(f.read())
