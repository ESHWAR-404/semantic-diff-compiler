"""
Report formatter: turns SemanticChange + ModuleDiff into human-readable output.
Supports three output formats: text (default), json, html.
"""
import json
import os
import sys
from .classifier import SemanticChange
from .diff_engine import ModuleDiff, FunctionDiff


def _reconfigure_stdout_utf8():
    """Force stdout to UTF-8 on Windows so Unicode arrows/symbols render."""
    if os.name == "nt":
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, Exception):
            try:
                import io
                sys.stdout = io.TextIOWrapper(
                    sys.stdout.buffer, encoding="utf-8", errors="replace"
                )
            except Exception:
                pass


_reconfigure_stdout_utf8()


# ---------------------------------------------------------------------------
# ANSI colors (disabled when stdout is not a tty or on Windows)
# ---------------------------------------------------------------------------

def _supports_color() -> bool:
    import os
    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


_COLOR = _supports_color()

_RESET  = "\033[0m"  if _COLOR else ""
_BOLD   = "\033[1m"  if _COLOR else ""
_RED    = "\033[31m" if _COLOR else ""
_YELLOW = "\033[33m" if _COLOR else ""
_GREEN  = "\033[32m" if _COLOR else ""
_CYAN   = "\033[36m" if _COLOR else ""
_DIM    = "\033[2m"  if _COLOR else ""

_SEV_COLOR = {
    "significant": _RED,
    "warning":     _YELLOW,
    "info":        _CYAN,
}

_CAT_ICON = {
    "VECTORIZATION":    "[VEC]",
    "LOOP_UNROLLING":   "[LOOP]",
    "INLINING":         "[INLINE]",
    "DEAD_CODE":        "[DEAD]",
    "CONTROL_FLOW":     "[CFG]",
    "FUNCTION_ADDED":   "[NEW]",
    "FUNCTION_REMOVED": "[DEL]",
    "SIGNATURE":        "[SIG]",
}


# ---------------------------------------------------------------------------
# Text report
# ---------------------------------------------------------------------------

def _fmt_change(sc: SemanticChange, verbose: bool) -> str:
    icon  = _CAT_ICON.get(sc.category, "[?]")
    color = _SEV_COLOR.get(sc.severity, "")
    sev   = f"[{sc.severity.upper()}]"
    lines = [f"{color}{_BOLD}{icon} {sev}{_RESET} @{sc.function}: {sc.headline}"]
    if verbose and sc.details:
        for d in sc.details:
            lines.append(f"    {_DIM}{d}{_RESET}")
    return "\n".join(lines)


def _summary_stats(changes: list[SemanticChange]) -> dict[str, int]:
    from collections import Counter
    return dict(Counter(c.category for c in changes))


def text_report(
    changes: list[SemanticChange],
    module_diff: ModuleDiff,
    verbose: bool = False,
    show_block_diff: bool = False,
) -> str:
    lines: list[str] = []

    lines.append(f"{_BOLD}{'='*70}{_RESET}")
    lines.append(f"{_BOLD}  Semantic IR Diff Report{_RESET}")
    lines.append(f"{_BOLD}{'='*70}{_RESET}")
    lines.append(f"  Old: {module_diff.old_path}")
    lines.append(f"  New: {module_diff.new_path}")
    lines.append(f"{_BOLD}{'-'*70}{_RESET}")

    # Function summary
    n_added    = len(module_diff.added_functions)
    n_removed  = len(module_diff.removed_functions)
    n_modified = len(module_diff.modified_functions)
    lines.append(
        f"  Functions: {n_added} added, {n_removed} removed, "
        f"{n_modified} modified"
    )
    lines.append(f"{_BOLD}{'-'*70}{_RESET}")

    if not changes:
        lines.append(f"  {_GREEN}No semantic changes detected.{_RESET}")
        lines.append(f"{_BOLD}{'='*70}{_RESET}")
        return "\n".join(lines)

    # Group by function
    funcs_seen: list[str] = []
    seen: set[str] = set()
    for c in changes:
        if c.function not in seen:
            funcs_seen.append(c.function)
            seen.add(c.function)

    for func in funcs_seen:
        func_changes = [c for c in changes if c.function == func]
        lines.append(f"\n{_BOLD}  Function: @{func}{_RESET}")
        for sc in func_changes:
            lines.append(f"    {_fmt_change(sc, verbose)}")

    lines.append(f"\n{_BOLD}{'-'*70}{_RESET}")

    # Stats
    stats = _summary_stats(changes)
    lines.append(f"  Change summary:")
    for cat, cnt in sorted(stats.items()):
        icon = _CAT_ICON.get(cat, cat)
        lines.append(f"    {icon:12s} {cnt} occurrence(s)")

    # Block-level diff (optional)
    if show_block_diff:
        lines.append(f"\n{_BOLD}  Block-level diff:{_RESET}")
        for fd in module_diff.function_diffs:
            if fd.status in ("same", "added", "removed"):
                continue
            if not fd.block_diffs:
                continue
            lines.append(f"  @{fd.func_name}:")
            for bd in fd.block_diffs:
                if bd.status == "same":
                    continue
                marker = {"added": "+", "removed": "-", "modified": "~"}.get(bd.status, "?")
                lines.append(f"    [{marker}] {bd.block_name} "
                             f"(+{bd.added_instructions} -{bd.removed_instructions} "
                             f"~{bd.changed_instructions} instr)")

    lines.append(f"\n{_BOLD}{'='*70}{_RESET}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON report
# ---------------------------------------------------------------------------

def json_report(changes: list[SemanticChange], module_diff: ModuleDiff) -> str:
    payload = {
        "old": module_diff.old_path,
        "new": module_diff.new_path,
        "summary": {
            "functions_added":    len(module_diff.added_functions),
            "functions_removed":  len(module_diff.removed_functions),
            "functions_modified": len(module_diff.modified_functions),
        },
        "changes": [
            {
                "category": c.category,
                "severity": c.severity,
                "function": c.function,
                "headline": c.headline,
                "details":  c.details,
            }
            for c in changes
        ],
    }
    return json.dumps(payload, indent=2)


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

_HTML_TMPL = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Semantic IR Diff Report</title>
  <style>
    body {{ font-family: monospace; background: #1e1e1e; color: #d4d4d4; padding: 1em; }}
    h1 {{ color: #569cd6; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th {{ background: #333; padding: 6px; text-align: left; }}
    td {{ padding: 4px 6px; border-bottom: 1px solid #333; }}
    .significant {{ color: #f44; }}
    .warning {{ color: #fa0; }}
    .info {{ color: #4cf; }}
    .details {{ color: #888; font-size: 0.9em; }}
    .func {{ color: #4ec9b0; }}
  </style>
</head>
<body>
  <h1>Semantic IR Diff Report</h1>
  <p>Old: <code>{old}</code><br>New: <code>{new}</code></p>
  <table>
    <tr><th>Cat</th><th>Sev</th><th>Function</th><th>Description</th></tr>
    {rows}
  </table>
</body>
</html>
"""

def html_report(changes: list[SemanticChange], module_diff: ModuleDiff) -> str:
    rows = []
    for c in changes:
        details_html = "<br>".join(c.details) if c.details else ""
        rows.append(
            f'<tr>'
            f'<td>{c.category}</td>'
            f'<td class="{c.severity}">{c.severity.upper()}</td>'
            f'<td class="func">@{c.function}</td>'
            f'<td>{c.headline}'
            f'{"<div class=details>" + details_html + "</div>" if details_html else ""}'
            f'</td></tr>'
        )
    return _HTML_TMPL.format(
        old=module_diff.old_path,
        new=module_diff.new_path,
        rows="\n    ".join(rows),
    )


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def render(
    changes: list[SemanticChange],
    module_diff: ModuleDiff,
    fmt: str = "text",
    verbose: bool = False,
    show_block_diff: bool = False,
) -> str:
    if fmt == "json":
        return json_report(changes, module_diff)
    if fmt == "html":
        return html_report(changes, module_diff)
    return text_report(changes, module_diff, verbose=verbose,
                       show_block_diff=show_block_diff)
