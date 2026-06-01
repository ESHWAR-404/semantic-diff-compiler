"""
LLVM IR → structured CFG / DFG representation.

Parses a (normalized) .ll file into:
  Module → Functions → BasicBlocks → Instructions

Key structural information extracted:
  - Block successors / predecessors (CFG edges)
  - PHI nodes (loop induction variables, join points)
  - Call instructions and their targets
  - Vector-type instructions (vectorization markers)
  - Memory access patterns
"""
import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Instruction:
    result: Optional[str]      # None for void instructions (store, br, ret)
    opcode: str
    type_sig: str              # normalized type string
    operands: list[str]
    raw: str                   # de-noised original text
    is_vector: bool = False    # contains a <N x T> type
    vector_width: int = 0      # N if is_vector
    is_call: bool = False
    call_target: Optional[str] = None
    is_phi: bool = False
    is_terminator: bool = False

    @property
    def pattern(self) -> str:
        """Opcode + type signature — used for structural matching."""
        return f"{self.opcode}:{self.type_sig}"


@dataclass
class BasicBlock:
    name: str
    instructions: list[Instruction] = field(default_factory=list)
    successors: list[str] = field(default_factory=list)
    predecessors: list[str] = field(default_factory=list)

    # Derived stats (populated after parsing)
    has_phi: bool = False
    vector_ops: int = 0
    call_targets: list[str] = field(default_factory=list)
    terminators: list[Instruction] = field(default_factory=list)

    def instruction_patterns(self) -> list[str]:
        return [i.pattern for i in self.instructions]


@dataclass
class Function:
    name: str
    return_type: str
    param_types: list[str] = field(default_factory=list)
    blocks: dict[str, BasicBlock] = field(default_factory=dict)
    block_order: list[str] = field(default_factory=list)

    # Derived
    is_declaration: bool = False   # `declare` — no body
    total_vector_ops: int = 0
    call_sites: list[tuple[str, str]] = field(default_factory=list)  # (block, target)

    def entry_block(self) -> Optional[BasicBlock]:
        if self.block_order:
            return self.blocks.get(self.block_order[0])
        return None

    def loop_headers(self) -> list[BasicBlock]:
        """Heuristic: blocks with PHI nodes that have a back-edge predecessor."""
        headers = []
        for name, block in self.blocks.items():
            if block.has_phi:
                my_idx = self.block_order.index(name) if name in self.block_order else -1
                for pred in block.predecessors:
                    # Self-loop (pred == self) or a true back edge (pred comes later)
                    if pred == name:
                        headers.append(block)
                        break
                    pred_idx = (self.block_order.index(pred)
                                if pred in self.block_order else -1)
                    if pred_idx >= my_idx:
                        headers.append(block)
                        break
        return headers


@dataclass
class Module:
    source_path: str
    functions: dict[str, Function] = field(default_factory=dict)
    global_vars: list[str] = field(default_factory=list)

    def defined_functions(self) -> dict[str, Function]:
        return {n: f for n, f in self.functions.items() if not f.is_declaration}


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_FUNC_DEF = re.compile(
    r'^define\s+(?P<rettype>[^@]+?)\s+@(?P<name>[^\s(]+)\s*\((?P<params>[^)]*)\)'
)
_FUNC_DECL = re.compile(r'^declare\s+(?P<rettype>[^@]+?)\s+@(?P<name>[^\s(]+)')
_BLOCK_LABEL = re.compile(r'^([A-Za-z_][A-Za-z0-9_.]*)\s*:(?:\s*;.*)?$')
_PREDS = re.compile(r';\s*preds\s*=\s*(.+)')
_BR_COND = re.compile(
    r'br\s+i1\s+[^,]+,\s*label\s+%([^\s,]+),\s*label\s+%([^\s,]+)'
)
_BR_UNCOND = re.compile(r'br\s+label\s+%([^\s,}]+)')
_SWITCH = re.compile(r'switch\s+\S+\s+[^,]+,\s*label\s+%([^\s[]+)(.*)', re.DOTALL)
_SWITCH_CASE = re.compile(r'label\s+%([^\s,\]]+)')
_INVOKE = re.compile(
    r'invoke\s+.*?to\s+label\s+%([^\s]+)\s+unwind\s+label\s+%([^\s]+)'
)
_CALL = re.compile(
    r'(?:(?:%\S+)\s*=\s*)?(?:tail\s+|musttail\s+)?call\s+[^@]*@([A-Za-z0-9_.]+)\s*\('
)
_VECTOR_TYPE = re.compile(r'<(\d+)\s+x\s+[^>]+>')
_RESULT_DEF = re.compile(r'^(%\S+)\s*=\s*(.+)')
_OPCODE = re.compile(r'^([a-z][a-z0-9]*(?:\.[a-z0-9]+)*)')
_TERMINATORS = frozenset(
    ["br", "ret", "switch", "indirectbr", "invoke", "callbr",
     "resume", "catchswitch", "catchret", "cleanupret", "unreachable"]
)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _parse_instruction(raw: str) -> Instruction:
    raw = raw.strip()
    result = None
    body = raw

    m = _RESULT_DEF.match(raw)
    if m:
        result = m.group(1)
        body = m.group(2).strip()

    op_m = _OPCODE.match(body)
    opcode = op_m.group(1) if op_m else "unknown"

    # Extract type signature (simplified)
    type_sig = opcode  # default
    # For vector types, capture the full vector type
    vec_m = _VECTOR_TYPE.search(body)
    is_vector = bool(vec_m)
    vec_width = int(vec_m.group(1)) if vec_m else 0
    if is_vector:
        type_sig = f"{opcode}:{vec_m.group(0)}"

    # Call instruction
    call_m = _CALL.match(body)
    is_call = bool(call_m)
    call_target = call_m.group(1) if call_m else None

    is_phi = opcode == "phi"
    is_term = opcode in _TERMINATORS

    # Operands (rough extraction)
    operands = []

    return Instruction(
        result=result,
        opcode=opcode,
        type_sig=type_sig,
        operands=operands,
        raw=raw,
        is_vector=is_vector,
        vector_width=vec_width,
        is_call=is_call,
        call_target=call_target,
        is_phi=is_phi,
        is_terminator=is_term,
    )


def _extract_successors(terminator: Instruction) -> list[str]:
    raw = terminator.raw.strip()
    succs = []
    if terminator.opcode == "br":
        m = _BR_COND.search(raw)
        if m:
            succs = [m.group(1), m.group(2)]
        else:
            m = _BR_UNCOND.search(raw)
            if m:
                succs = [m.group(1)]
    elif terminator.opcode == "switch":
        m = _SWITCH.search(raw)
        if m:
            succs.append(m.group(1))
            succs.extend(_SWITCH_CASE.findall(m.group(2)))
    elif terminator.opcode == "invoke":
        m = _INVOKE.search(raw)
        if m:
            succs = [m.group(1), m.group(2)]
    return succs


def _parse_params(param_str: str) -> list[str]:
    types = []
    for part in param_str.split(","):
        part = part.strip()
        if not part:
            continue
        # Take just the type portion (before any %)
        t = part.split("%")[0].strip()
        types.append(t)
    return types


def _join_multiline_defines(lines: list[str]) -> list[str]:
    """
    clang sometimes emits `define` spanning multiple lines when the parameter
    list is long.  Join them into a single line so our regex can match.
    Example:
        define void @foo(float* noalias %a,
                         float* noalias %b) {
      →  define void @foo(float* noalias %a, float* noalias %b) {
    """
    out: list[str] = []
    pending: str | None = None
    for line in lines:
        if pending is not None:
            pending = pending.rstrip() + " " + line.strip()
            # Done when we've balanced the parentheses
            if pending.count("(") <= pending.count(")"):
                out.append(pending)
                pending = None
        elif line.lstrip().startswith("define ") and "(" in line and ")" not in line:
            pending = line.rstrip()
        else:
            out.append(line)
    if pending is not None:
        out.append(pending)
    return out


def parse_ir(ir_text: str, source_path: str = "<unknown>") -> Module:
    """Parse normalized LLVM IR text into a Module."""
    module = Module(source_path=source_path)
    lines = _join_multiline_defines(ir_text.splitlines())

    i = 0
    current_func: Optional[Function] = None
    current_block: Optional[BasicBlock] = None
    in_func = False
    brace_depth = 0

    def finalize_block():
        nonlocal current_block
        if current_block and current_func:
            # Populate derived stats
            current_block.has_phi = any(ins.is_phi for ins in current_block.instructions)
            current_block.vector_ops = sum(1 for ins in current_block.instructions if ins.is_vector)
            current_block.call_targets = [
                ins.call_target for ins in current_block.instructions
                if ins.is_call and ins.call_target
            ]
            # Collect terminators and extract successors
            for ins in current_block.instructions:
                if ins.is_terminator:
                    current_block.terminators.append(ins)
                    current_block.successors.extend(_extract_successors(ins))
            current_func.blocks[current_block.name] = current_block
            current_func.block_order.append(current_block.name)

    def finalize_func():
        nonlocal current_func
        if current_func:
            # Back-fill predecessors
            for bname, block in current_func.blocks.items():
                for succ_name in block.successors:
                    if succ_name in current_func.blocks:
                        current_func.blocks[succ_name].predecessors.append(bname)
            # Aggregate stats
            current_func.total_vector_ops = sum(
                b.vector_ops for b in current_func.blocks.values()
            )
            current_func.call_sites = [
                (bname, ct)
                for bname, block in current_func.blocks.items()
                for ct in block.call_targets
            ]
            module.functions[current_func.name] = current_func

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # ---- Function definition ----
        if not in_func and stripped.startswith("define "):
            m = _FUNC_DEF.match(stripped)
            if m:
                finalize_func()
                current_func = Function(
                    name=m.group("name"),
                    return_type=m.group("rettype").strip(),
                    param_types=_parse_params(m.group("params")),
                )
                current_block = None
                in_func = True
                brace_depth = 1 if "{" in stripped else 0

        # ---- Declaration ----
        elif not in_func and stripped.startswith("declare "):
            m = _FUNC_DECL.match(stripped)
            if m:
                f = Function(name=m.group("name"),
                             return_type=m.group("rettype").strip(),
                             is_declaration=True)
                module.functions[m.group("name")] = f

        # ---- Global variable ----
        elif not in_func and "@" in stripped and "=" in stripped:
            module.global_vars.append(stripped)

        # ---- Inside a function ----
        elif in_func:
            if stripped == "}":
                finalize_block()
                finalize_func()
                current_func = None
                current_block = None
                in_func = False

            elif stripped and not stripped.startswith(";"):
                # Block label?
                lm = _BLOCK_LABEL.match(stripped)
                if lm and current_func:
                    finalize_block()
                    label = lm.group(1)
                    current_block = BasicBlock(name=label)
                    # Extract predecessor hints from comment
                    pm = _PREDS.search(stripped)
                    if pm:
                        for pred in pm.group(1).split(","):
                            pred = pred.strip().lstrip("%")
                            if pred:
                                current_block.predecessors.append(pred)
                elif current_func:
                    # Handle entry block (no label — first instructions after {)
                    if current_block is None:
                        current_block = BasicBlock(name="entry")
                    ins = _parse_instruction(stripped)
                    current_block.instructions.append(ins)

        i += 1

    # Finalize trailing function
    if in_func:
        finalize_block()
        finalize_func()

    return module


def parse_file(path: str) -> Module:
    """Read and parse a normalized .ll file."""
    with open(path, "r", errors="replace") as f:
        text = f.read()
    from .normalizer import normalize
    return parse_ir(normalize(text), source_path=path)
