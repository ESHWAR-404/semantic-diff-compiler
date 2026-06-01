"""
Change classifier: maps structural IR diffs onto human-readable semantic concepts.

Detected categories
-------------------
  VECTORIZATION  — vector-type instructions gained, lost, or width-changed
  LOOP_UNROLLING — loop body block count changed (unrolled/rerolled)
  INLINING       — call site disappeared; callee may have been inlined
  DEAD_CODE      — basic block removed with no apparent loop reason
  CONTROL_FLOW   — basic block added/removed that changes branch structure
  FUNCTION_ADDED — entirely new function
  FUNCTION_REMOVED — function deleted
  SIGNATURE      — return type or parameter types changed
"""
import re
from dataclasses import dataclass, field
from typing import Optional
from .cfg_parser import Function, BasicBlock, Module
from .diff_engine import ModuleDiff, FunctionDiff, BlockDiff


# ---------------------------------------------------------------------------
# Semantic change types
# ---------------------------------------------------------------------------

@dataclass
class SemanticChange:
    category: str
    severity: str          # 'info' | 'warning' | 'significant'
    function: str
    headline: str          # one-line summary
    details: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_vector_ops(func: Optional[Function]) -> dict[int, int]:
    """Return {vector_width: count} across all blocks."""
    counts: dict[int, int] = {}
    if func is None:
        return counts
    for block in func.blocks.values():
        for ins in block.instructions:
            if ins.is_vector and ins.vector_width > 0:
                counts[ins.vector_width] = counts.get(ins.vector_width, 0) + 1
    return counts


def _dominant_width(counts: dict[int, int]) -> int:
    """Return the most frequent vector width, or 0."""
    if not counts:
        return 0
    return max(counts, key=lambda w: counts[w])


def _call_sites(func: Optional[Function]) -> dict[str, int]:
    """Return {callee_name: call_count}."""
    if func is None:
        return {}
    result: dict[str, int] = {}
    for _, target in func.call_sites:
        result[target] = result.get(target, 0) + 1
    return result


def _loop_like_blocks(func: Optional[Function]) -> list[BasicBlock]:
    """Return blocks that look like loop headers (has phi + back-edge)."""
    if func is None:
        return []
    return func.loop_headers()


def _block_count_in_loop(func: Optional[Function]) -> int:
    """
    Rough count of 'loop body' blocks: those that are successors of a header
    and can reach back to the header.
    Approximation: total blocks minus entry-block minus pure exit blocks.
    """
    if func is None or not func.blocks:
        return 0
    # Heuristic: count blocks reachable from loop headers
    headers = _loop_like_blocks(func)
    if not headers:
        return 0
    body_blocks: set[str] = set()
    for h in headers:
        body_blocks.add(h.name)
        for succ in h.successors:
            body_blocks.add(succ)
    return len(body_blocks)


def _similar_block_groups(func: Optional[Function]) -> list[list[str]]:
    """
    Find groups of similarly-structured blocks — evidence of loop unrolling.
    Two blocks are 'similar' if their instruction pattern lists share ≥ 80%
    of opcodes (Jaccard).
    """
    if func is None:
        return []
    blocks = list(func.blocks.values())
    if len(blocks) < 2:
        return []

    visited: set[str] = set()
    groups: list[list[str]] = []

    for i, b1 in enumerate(blocks):
        if b1.name in visited:
            continue
        group = [b1.name]
        visited.add(b1.name)
        p1 = set(b1.instruction_patterns())
        for b2 in blocks[i + 1:]:
            if b2.name in visited:
                continue
            p2 = set(b2.instruction_patterns())
            union = len(p1 | p2)
            inter = len(p1 & p2)
            if union and inter / union >= 0.80:
                group.append(b2.name)
                visited.add(b2.name)
        if len(group) > 1:
            groups.append(group)
    return groups


def _is_intrinsic(name: str) -> bool:
    return name.startswith("llvm.")


# ---------------------------------------------------------------------------
# Individual classifiers
# ---------------------------------------------------------------------------

def _classify_vectorization(fd: FunctionDiff) -> list[SemanticChange]:
    changes = []
    old_counts = _count_vector_ops(fd.old_func)
    new_counts = _count_vector_ops(fd.new_func)
    old_total = sum(old_counts.values())
    new_total = sum(new_counts.values())
    old_width = _dominant_width(old_counts)
    new_width = _dominant_width(new_counts)
    fname = fd.func_name

    if old_total == 0 and new_total > 0:
        changes.append(SemanticChange(
            category="VECTORIZATION",
            severity="significant",
            function=fname,
            headline=f"Vectorization GAINED (width={new_width}): {new_total} vector ops introduced",
            details=[f"New version uses <{new_width} x T> instructions",
                     f"Total vector operations: {new_total}"],
        ))
    elif old_total > 0 and new_total == 0:
        changes.append(SemanticChange(
            category="VECTORIZATION",
            severity="significant",
            function=fname,
            headline=f"Vectorization LOST: {old_total} vector ops removed",
            details=[f"Old version had <{old_width} x T> instructions",
                     "New version uses scalar operations only"],
        ))
    elif old_total > 0 and new_total > 0 and old_width != new_width:
        direction = "widened" if new_width > old_width else "narrowed"
        changes.append(SemanticChange(
            category="VECTORIZATION",
            severity="warning",
            function=fname,
            headline=f"Vector width {direction} from {old_width} to {new_width}",
            details=[f"Old: {old_total} ops at width {old_width}",
                     f"New: {new_total} ops at width {new_width}"],
        ))
    elif old_total > 0 and new_total > 0 and abs(new_total - old_total) > max(1, old_total // 4):
        delta = new_total - old_total
        direction = "increased" if delta > 0 else "decreased"
        changes.append(SemanticChange(
            category="VECTORIZATION",
            severity="info",
            function=fname,
            headline=f"Vector op count {direction}: {old_total} → {new_total}",
            details=[f"Width unchanged at {old_width}"],
        ))
    return changes


def _classify_inlining(fd: FunctionDiff,
                       old_module: Module,
                       new_module: Module) -> list[SemanticChange]:
    changes = []
    fname = fd.func_name
    if fd.old_func is None or fd.new_func is None:
        return changes

    old_calls = _call_sites(fd.old_func)
    new_calls = _call_sites(fd.new_func)

    for callee, old_count in old_calls.items():
        if _is_intrinsic(callee):
            continue
        new_count = new_calls.get(callee, 0)
        if new_count < old_count:
            # Was the callee removed from the new module?
            callee_gone = callee not in new_module.defined_functions()
            reason = " (callee removed from module — likely inlined)" if callee_gone else ""
            changes.append(SemanticChange(
                category="INLINING",
                severity="significant",
                function=fname,
                headline=f"Call to @{callee} reduced: {old_count} → {new_count}{reason}",
                details=[
                    f"Old version called @{callee} {old_count} time(s)",
                    f"New version calls it {new_count} time(s)",
                    "Possible causes: always_inline, function body merged, "
                    "or dead-call elimination",
                ],
            ))

    # New calls added (un-inlining / refactoring)
    for callee, new_count in new_calls.items():
        if _is_intrinsic(callee):
            continue
        old_count = old_calls.get(callee, 0)
        if new_count > old_count:
            changes.append(SemanticChange(
                category="INLINING",
                severity="info",
                function=fname,
                headline=f"New/increased call to @{callee}: {old_count} → {new_count}",
                details=["Function may have been un-inlined (extracted into helper)"],
            ))
    return changes


def _classify_loop_unrolling(fd: FunctionDiff) -> list[SemanticChange]:
    changes = []
    fname = fd.func_name
    if fd.old_func is None or fd.new_func is None:
        return changes

    old_groups = _similar_block_groups(fd.old_func)
    new_groups = _similar_block_groups(fd.new_func)
    old_loops = _loop_like_blocks(fd.old_func)
    new_loops = _loop_like_blocks(fd.new_func)

    old_unrolled = sum(len(g) for g in old_groups)
    new_unrolled = sum(len(g) for g in new_groups)

    old_block_count = len(fd.old_func.blocks)
    new_block_count = len(fd.new_func.blocks)

    # Large block-count change often signals unrolling
    if old_block_count > 0 and new_block_count > 0:
        ratio = new_block_count / old_block_count
        if ratio >= 2.0 and new_unrolled > old_unrolled:
            factor = round(ratio)
            changes.append(SemanticChange(
                category="LOOP_UNROLLING",
                severity="significant",
                function=fname,
                headline=f"Loop UNROLLED ~{factor}x: block count {old_block_count} → {new_block_count}",
                details=[
                    f"Old: {old_block_count} blocks, {len(old_loops)} loop header(s)",
                    f"New: {new_block_count} blocks, {len(new_loops)} loop header(s)",
                    f"Similar-block groups: {len(old_groups)} → {len(new_groups)}",
                ],
            ))
        elif ratio <= 0.5 and old_unrolled > new_unrolled:
            factor = round(1 / ratio) if ratio > 0 else "?"
            changes.append(SemanticChange(
                category="LOOP_UNROLLING",
                severity="significant",
                function=fname,
                headline=f"Loop REROLLED (was ~{factor}x unrolled): block count {old_block_count} → {new_block_count}",
                details=[
                    f"Old: {old_block_count} blocks with {len(old_groups)} similar-block group(s)",
                    f"New: {new_block_count} blocks — loop rerolled or trip-count became dynamic",
                ],
            ))

    # Within-block unrolling: loop body block shrank significantly (rerolled)
    # or grew significantly (unrolled inline). Detected via instruction-diff counts.
    if fd.block_diffs and old_loops:
        loop_header_names = {b.name for b in old_loops}
        for bd in fd.block_diffs:
            if bd.status != "modified":
                continue
            # Check blocks that look like loop bodies (successors of headers)
            is_loop_block = (
                bd.block_name in loop_header_names
                or (bd.old_block and any(
                    p in loop_header_names
                    for p in bd.old_block.predecessors
                ))
            )
            if not is_loop_block:
                continue
            old_count = len(bd.old_block.instructions) if bd.old_block else 0
            new_count = len(bd.new_block.instructions) if bd.new_block else 0
            if old_count == 0:
                continue
            instr_ratio = new_count / old_count
            if instr_ratio <= 0.4 and old_count >= 6:
                factor = round(1 / instr_ratio) if instr_ratio > 0 else "?"
                changes.append(SemanticChange(
                    category="LOOP_UNROLLING",
                    severity="significant",
                    function=fname,
                    headline=(
                        f"Loop body REROLLED in block '{bd.block_name}': "
                        f"{old_count} → {new_count} instructions (~{factor}x reduction)"
                    ),
                    details=[
                        f"Old block had {old_count} instructions (likely {factor}x unrolled)",
                        f"New block has {new_count} instructions (canonical single-iteration body)",
                    ],
                ))
            elif instr_ratio >= 2.5 and new_count >= 6:
                factor = round(instr_ratio)
                changes.append(SemanticChange(
                    category="LOOP_UNROLLING",
                    severity="significant",
                    function=fname,
                    headline=(
                        f"Loop body UNROLLED in block '{bd.block_name}': "
                        f"{old_count} → {new_count} instructions (~{factor}x expansion)"
                    ),
                    details=[
                        f"Old block had {old_count} instructions",
                        f"New block has {new_count} instructions (unrolled body)",
                    ],
                ))

    # Loop header change
    if len(old_loops) != len(new_loops):
        if len(new_loops) < len(old_loops):
            changes.append(SemanticChange(
                category="LOOP_UNROLLING",
                severity="info",
                function=fname,
                headline=f"Loop count reduced: {len(old_loops)} → {len(new_loops)} loop header(s)",
                details=["Possible loop fusion, elimination, or full unrolling"],
            ))
        else:
            changes.append(SemanticChange(
                category="LOOP_UNROLLING",
                severity="info",
                function=fname,
                headline=f"Loop count increased: {len(old_loops)} → {len(new_loops)} loop header(s)",
                details=["Possible loop fission or new conditional loop"],
            ))
    return changes


def _classify_control_flow(fd: FunctionDiff) -> list[SemanticChange]:
    changes = []
    fname = fd.func_name
    if not fd.block_diffs:
        return changes

    added = [d.block_name for d in fd.block_diffs if d.status == "added"]
    removed = [d.block_name for d in fd.block_diffs if d.status == "removed"]

    # Exclude loop-body blocks (already classified above)
    def is_cond_block(name: str) -> bool:
        return any(kw in name for kw in
                   ("if", "then", "else", "cond", "true", "false",
                    "switch", "case", "default", "land", "lor"))

    cond_added = [n for n in added if is_cond_block(n)]
    cond_removed = [n for n in removed if is_cond_block(n)]

    if cond_removed and not cond_added:
        changes.append(SemanticChange(
            category="CONTROL_FLOW",
            severity="warning",
            function=fname,
            headline=f"Branch eliminated: {len(cond_removed)} conditional block(s) removed",
            details=[f"Removed: {', '.join(cond_removed[:5])}",
                     "Possible causes: constant folding, dead branch removal"],
        ))
    elif cond_added and not cond_removed:
        changes.append(SemanticChange(
            category="CONTROL_FLOW",
            severity="info",
            function=fname,
            headline=f"New branch added: {len(cond_added)} conditional block(s) added",
            details=[f"Added: {', '.join(cond_added[:5])}"],
        ))
    elif removed and not added and not cond_removed:
        # Generic block removal
        changes.append(SemanticChange(
            category="DEAD_CODE",
            severity="info",
            function=fname,
            headline=f"Dead-code eliminated: {len(removed)} block(s) removed",
            details=[f"Removed blocks: {', '.join(removed[:5])}"],
        ))
    elif added and not removed:
        changes.append(SemanticChange(
            category="CONTROL_FLOW",
            severity="info",
            function=fname,
            headline=f"{len(added)} new basic block(s) added",
            details=[f"Added: {', '.join(added[:5])}"],
        ))
    return changes


def _classify_signature(fd: FunctionDiff) -> list[SemanticChange]:
    changes = []
    if fd.old_func is None or fd.new_func is None:
        return changes
    fname = fd.func_name
    if fd.old_func.return_type != fd.new_func.return_type:
        changes.append(SemanticChange(
            category="SIGNATURE",
            severity="significant",
            function=fname,
            headline=f"Return type changed: {fd.old_func.return_type!r} → {fd.new_func.return_type!r}",
        ))
    if fd.old_func.param_types != fd.new_func.param_types:
        changes.append(SemanticChange(
            category="SIGNATURE",
            severity="significant",
            function=fname,
            headline="Parameter types changed",
            details=[f"Old: {fd.old_func.param_types}",
                     f"New: {fd.new_func.param_types}"],
        ))
    return changes


# ---------------------------------------------------------------------------
# Top-level classifier
# ---------------------------------------------------------------------------

def classify(module_diff: ModuleDiff,
             old_module: Module,
             new_module: Module) -> list[SemanticChange]:
    """
    Produce a list of SemanticChange objects ordered by severity then function.
    """
    all_changes: list[SemanticChange] = []

    for fd in module_diff.function_diffs:
        if fd.status == "added":
            all_changes.append(SemanticChange(
                category="FUNCTION_ADDED",
                severity="info",
                function=fd.func_name,
                headline=f"New function @{fd.func_name} added to module",
            ))
            continue
        if fd.status == "removed":
            all_changes.append(SemanticChange(
                category="FUNCTION_REMOVED",
                severity="warning",
                function=fd.func_name,
                headline=f"Function @{fd.func_name} removed from module",
                details=["Possible: inlined into all call sites or dead code elimination"],
            ))
            continue
        if fd.status == "same":
            continue

        # Modified function — run all classifiers
        all_changes.extend(_classify_signature(fd))
        all_changes.extend(_classify_vectorization(fd))
        all_changes.extend(_classify_inlining(fd, old_module, new_module))
        all_changes.extend(_classify_loop_unrolling(fd))
        all_changes.extend(_classify_control_flow(fd))

    # Sort: significant first, then warning, then info
    order = {"significant": 0, "warning": 1, "info": 2}
    all_changes.sort(key=lambda c: (order.get(c.severity, 3), c.function))
    return all_changes
