#!/usr/bin/env python3
"""
semdiff — Semantic Diff for Compiler IR
========================================
Compare two C/C++ source files (or pre-compiled .ll LLVM IR files) and report
semantic/optimization changes at the IR level.

Usage:
  python src/main.py <old_file> <new_file> [options]

Examples:
  python src/main.py tc1/v1.c tc1/v2.c
  python src/main.py tc1/v1.ll tc1/v2.ll --format json
  python src/main.py tc1/v1.c tc1/v2.c --opt O2 --verbose --show-block-diff
"""
import argparse
import sys
import os
import tempfile
import traceback
from pathlib import Path


def _ensure_utf8_stdout():
    """Reconfigure stdout/stderr to UTF-8 on Windows (avoids CP1252 errors)."""
    import os, io
    if os.name == "nt":
        for stream_name in ("stdout", "stderr"):
            s = getattr(sys, stream_name)
            try:
                s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
            except AttributeError:
                try:
                    setattr(sys, stream_name,
                            io.TextIOWrapper(s.buffer, encoding="utf-8",
                                             errors="replace"))
                except Exception:
                    pass


def _ensure_src_on_path():
    """Add the project root to sys.path so `src.*` imports resolve."""
    here = Path(__file__).resolve().parent
    root = here.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_ensure_utf8_stdout()
_ensure_src_on_path()

from src.compiler   import prepare_ir, CompilationError
from src.normalizer import normalize_file
from src.cfg_parser import parse_file, parse_ir
from src.diff_engine import diff_modules
from src.classifier  import classify
from src.reporter    import render


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="semdiff",
        description="Semantic Diff for Compiler IR — compare two source or IR files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("old", metavar="OLD_FILE",
                   help="Old source (.c/.cpp) or IR (.ll) file")
    p.add_argument("new", metavar="NEW_FILE",
                   help="New source (.c/.cpp) or IR (.ll) file")
    p.add_argument("--opt", metavar="LEVEL", default="O2",
                   choices=["O0", "O1", "O2", "O3", "Os", "Oz"],
                   help="Optimization level for clang compilation (default: O2)")
    p.add_argument("--format", metavar="FMT", default="text",
                   choices=["text", "json", "html"],
                   help="Output format: text (default), json, html")
    p.add_argument("--output", metavar="FILE", default=None,
                   help="Write report to FILE instead of stdout")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="Show detailed change descriptions")
    p.add_argument("--show-block-diff", action="store_true",
                   help="Include block-level diff in text report")
    p.add_argument("--show-ir", action="store_true",
                   help="Print the normalized IR for both versions before the report")
    p.add_argument("--keep-tmp", action="store_true",
                   help="Keep temporary compiled .ll files (for debugging)")
    return p


def run(args: argparse.Namespace) -> int:
    old_path = Path(args.old)
    new_path = Path(args.new)

    for p in (old_path, new_path):
        if not p.exists():
            print(f"ERROR: File not found: {p}", file=sys.stderr)
            return 2

    tmp = tempfile.mkdtemp(prefix="semdiff_")

    try:
        # ---- Step 1: Obtain IR ----
        try:
            old_ir = prepare_ir(str(old_path), tmp, "old", opt_level=args.opt)
            new_ir = prepare_ir(str(new_path), tmp, "new", opt_level=args.opt)
        except CompilationError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1

        # ---- Step 2: Normalize ----
        old_norm = normalize_file(old_ir)
        new_norm = normalize_file(new_ir)

        if args.show_ir:
            print("=" * 60)
            print(f"  Normalized IR — OLD ({old_path.name})")
            print("=" * 60)
            print(old_norm)
            print()
            print("=" * 60)
            print(f"  Normalized IR — NEW ({new_path.name})")
            print("=" * 60)
            print(new_norm)
            print()

        # ---- Step 3: Parse ----
        old_module = parse_ir(old_norm, source_path=str(old_path))
        new_module = parse_ir(new_norm, source_path=str(new_path))

        # ---- Step 4: Diff ----
        module_diff = diff_modules(old_module, new_module)

        # ---- Step 5: Classify ----
        changes = classify(module_diff, old_module, new_module)

        # ---- Step 6: Report ----
        report = render(
            changes,
            module_diff,
            fmt=args.format,
            verbose=args.verbose,
            show_block_diff=args.show_block_diff,
        )

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"Report written to {args.output}", file=sys.stderr)
        else:
            print(report)

    except Exception:
        print("\nInternal error — please report this bug.", file=sys.stderr)
        traceback.print_exc()
        return 3
    finally:
        if not args.keep_tmp:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    return 0


def main():
    parser = build_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    args = parser.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
