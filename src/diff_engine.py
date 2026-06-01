"""
Structural diff engine for two CFG Modules.

Algorithm:
  1. Match functions by name (exact).
  2. For matched functions, match basic blocks by name (exact first, then
     fuzzy Jaccard similarity on instruction patterns).
  3. For matched blocks, compute an instruction-level diff using a simple
     LCS (longest common subsequence) on instruction patterns.
  4. Summarise added/removed/modified blocks and functions.
"""
from dataclasses import dataclass, field
from typing import Optional
from .cfg_parser import Module, Function, BasicBlock, Instruction


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class InstructionDiff:
    status: str          # 'same' | 'added' | 'removed' | 'changed'
    old_ins: Optional[Instruction]
    new_ins: Optional[Instruction]


@dataclass
class BlockDiff:
    block_name: str
    status: str          # 'same' | 'added' | 'removed' | 'modified'
    old_block: Optional[BasicBlock]
    new_block: Optional[BasicBlock]
    instruction_diffs: list[InstructionDiff] = field(default_factory=list)

    # Derived convenience fields
    added_instructions: int = 0
    removed_instructions: int = 0
    changed_instructions: int = 0

    def __post_init__(self):
        self.added_instructions = sum(
            1 for d in self.instruction_diffs if d.status == "added"
        )
        self.removed_instructions = sum(
            1 for d in self.instruction_diffs if d.status == "removed"
        )
        self.changed_instructions = sum(
            1 for d in self.instruction_diffs if d.status == "changed"
        )


@dataclass
class FunctionDiff:
    func_name: str
    status: str          # 'same' | 'added' | 'removed' | 'modified'
    old_func: Optional[Function]
    new_func: Optional[Function]
    block_diffs: list[BlockDiff] = field(default_factory=list)

    # Convenience
    added_blocks: list[str] = field(default_factory=list)
    removed_blocks: list[str] = field(default_factory=list)
    modified_blocks: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.added_blocks = [d.block_name for d in self.block_diffs if d.status == "added"]
        self.removed_blocks = [d.block_name for d in self.block_diffs if d.status == "removed"]
        self.modified_blocks = [d.block_name for d in self.block_diffs if d.status == "modified"]


@dataclass
class ModuleDiff:
    old_path: str
    new_path: str
    function_diffs: list[FunctionDiff] = field(default_factory=list)
    added_functions: list[str] = field(default_factory=list)
    removed_functions: list[str] = field(default_factory=list)
    modified_functions: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.added_functions = [d.func_name for d in self.function_diffs if d.status == "added"]
        self.removed_functions = [d.func_name for d in self.function_diffs if d.status == "removed"]
        self.modified_functions = [d.func_name for d in self.function_diffs if d.status == "modified"]


# ---------------------------------------------------------------------------
# LCS-based instruction diff
# ---------------------------------------------------------------------------

def _lcs_diff(old_ins: list[Instruction],
              new_ins: list[Instruction]) -> list[InstructionDiff]:
    """
    LCS diff on instruction *patterns* (opcode:type_sig).
    Returns a flat list of InstructionDiff entries.
    """
    a = [i.pattern for i in old_ins]
    b = [i.pattern for i in new_ins]
    m, n = len(a), len(b)

    # DP table
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m - 1, -1, -1):
        for j in range(n - 1, -1, -1):
            if a[i] == b[j]:
                dp[i][j] = 1 + dp[i + 1][j + 1]
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])

    diffs: list[InstructionDiff] = []
    i, j = 0, 0
    while i < m and j < n:
        if a[i] == b[j]:
            diffs.append(InstructionDiff("same", old_ins[i], new_ins[j]))
            i += 1; j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            diffs.append(InstructionDiff("removed", old_ins[i], None))
            i += 1
        else:
            diffs.append(InstructionDiff("added", None, new_ins[j]))
            j += 1
    while i < m:
        diffs.append(InstructionDiff("removed", old_ins[i], None))
        i += 1
    while j < n:
        diffs.append(InstructionDiff("added", None, new_ins[j]))
        j += 1
    return diffs


# ---------------------------------------------------------------------------
# Block matching
# ---------------------------------------------------------------------------

def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def _match_blocks(old_f: Function,
                  new_f: Function) -> list[tuple[Optional[BasicBlock],
                                                  Optional[BasicBlock]]]:
    """
    Return a list of (old_block, new_block) pairs.
    Unmatched blocks appear as (block, None) or (None, block).
    Strategy:
      1. Exact name matches.
      2. Remaining: greedy best-Jaccard match (threshold 0.3).
      3. Unmatched → added/removed.
    """
    old_names = set(old_f.blocks.keys())
    new_names = set(new_f.blocks.keys())

    pairs: list[tuple[Optional[BasicBlock], Optional[BasicBlock]]] = []
    matched_old: set[str] = set()
    matched_new: set[str] = set()

    # Exact name matches
    for name in old_names & new_names:
        pairs.append((old_f.blocks[name], new_f.blocks[name]))
        matched_old.add(name)
        matched_new.add(name)

    # Fuzzy matches for remaining
    remaining_old = [old_f.blocks[n] for n in old_names - matched_old]
    remaining_new = [new_f.blocks[n] for n in new_names - matched_new]

    used_new: set[str] = set()
    for ob in remaining_old:
        best_score = 0.3  # minimum threshold
        best_nb = None
        for nb in remaining_new:
            if nb.name in used_new:
                continue
            score = _jaccard(ob.instruction_patterns(), nb.instruction_patterns())
            if score > best_score:
                best_score = score
                best_nb = nb
        if best_nb:
            pairs.append((ob, best_nb))
            used_new.add(best_nb.name)
        else:
            pairs.append((ob, None))

    for nb in remaining_new:
        if nb.name not in used_new:
            pairs.append((None, nb))

    return pairs


# ---------------------------------------------------------------------------
# Top-level diff
# ---------------------------------------------------------------------------

def diff_blocks(old_b: Optional[BasicBlock],
                new_b: Optional[BasicBlock]) -> BlockDiff:
    if old_b is None:
        name = new_b.name if new_b else "?"
        return BlockDiff(block_name=name, status="added",
                         old_block=None, new_block=new_b)
    if new_b is None:
        return BlockDiff(block_name=old_b.name, status="removed",
                         old_block=old_b, new_block=None)

    name = old_b.name
    idiffs = _lcs_diff(old_b.instructions, new_b.instructions)
    changed = any(d.status != "same" for d in idiffs)
    status = "modified" if changed else "same"
    bd = BlockDiff(block_name=name, status=status,
                   old_block=old_b, new_block=new_b,
                   instruction_diffs=idiffs)
    return bd


def diff_functions(old_f: Optional[Function],
                   new_f: Optional[Function]) -> FunctionDiff:
    name = (old_f or new_f).name  # type: ignore[union-attr]

    if old_f is None:
        return FunctionDiff(func_name=name, status="added",
                            old_func=None, new_func=new_f)
    if new_f is None:
        return FunctionDiff(func_name=name, status="removed",
                            old_func=old_f, new_func=None)
    if old_f.is_declaration and new_f.is_declaration:
        return FunctionDiff(func_name=name, status="same",
                            old_func=old_f, new_func=new_f)

    pairs = _match_blocks(old_f, new_f)
    block_diffs = [diff_blocks(ob, nb) for ob, nb in pairs]
    changed = any(d.status != "same" for d in block_diffs)
    status = "modified" if changed else "same"
    return FunctionDiff(func_name=name, status=status,
                        old_func=old_f, new_func=new_f,
                        block_diffs=block_diffs)


def diff_modules(old_m: Module, new_m: Module) -> ModuleDiff:
    """Compute the full structural diff between two parsed Modules."""
    old_defs = old_m.defined_functions()
    new_defs = new_m.defined_functions()

    all_names = set(old_defs) | set(new_defs)
    fdiffs: list[FunctionDiff] = []

    for name in sorted(all_names):
        old_f = old_defs.get(name)
        new_f = new_defs.get(name)
        if old_f is None and new_f is not None:
            fdiffs.append(FunctionDiff(func_name=name, status="added",
                                       old_func=None, new_func=new_f))
        elif old_f is not None and new_f is None:
            fdiffs.append(FunctionDiff(func_name=name, status="removed",
                                       old_func=old_f, new_func=None))
        else:
            fdiffs.append(diff_functions(old_f, new_f))

    return ModuleDiff(
        old_path=old_m.source_path,
        new_path=new_m.source_path,
        function_diffs=fdiffs,
    )
