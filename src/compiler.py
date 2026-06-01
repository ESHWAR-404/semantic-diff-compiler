"""
Compiler interface: invoke clang to produce LLVM IR (.ll) from C/C++ sources.
Falls back gracefully when clang is unavailable (accepts .ll files directly).
"""
import subprocess
import shutil
import sys
from pathlib import Path


class CompilationError(Exception):
    pass


def find_executable(names: list[str]) -> str | None:
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def find_clang() -> str | None:
    candidates = ["clang", "clang-17", "clang-16", "clang-15", "clang-14",
                  "clang-13", "clang-12", "clang-11"]
    return find_executable(candidates)


def find_opt() -> str | None:
    candidates = ["opt", "opt-17", "opt-16", "opt-15", "opt-14",
                  "opt-13", "opt-12", "opt-11"]
    return find_executable(candidates)


def compile_to_ir(source_file: str, output_file: str,
                  opt_level: str = "O2",
                  extra_flags: list[str] | None = None) -> str:
    """
    Compile source_file to LLVM IR and write to output_file.
    Raises CompilationError if clang is unavailable or compilation fails.
    Returns the path to the generated .ll file.
    """
    clang = find_clang()
    if not clang:
        raise CompilationError(
            "clang not found in PATH.\n"
            "Install LLVM (https://releases.llvm.org/) or supply pre-compiled\n"
            ".ll files directly as input arguments."
        )

    src = Path(source_file)
    if not src.exists():
        raise CompilationError(f"Source file not found: {source_file}")

    cmd = [
        clang,
        f"-{opt_level}",
        "-S", "-emit-llvm",
        "-fno-discard-value-names",   # preserve named temporaries
        "-Xclang", "-disable-llvm-passes" if opt_level == "O0" else "-O2",
        str(src),
        "-o", output_file,
    ]
    # Simpler cmd that works more reliably
    cmd = [
        clang,
        f"-{opt_level}",
        "-S", "-emit-llvm",
        "-fno-discard-value-names",
        str(src),
        "-o", output_file,
    ]
    if extra_flags:
        cmd.extend(extra_flags)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise CompilationError("Compilation timed out after 60 s.")
    except FileNotFoundError:
        raise CompilationError(f"Clang executable not found: {clang}")

    if result.returncode != 0:
        raise CompilationError(
            f"Compilation failed (exit {result.returncode}):\n{result.stderr.strip()}"
        )
    return output_file


def prepare_ir(path: str, tmp_dir: str, tag: str,
               opt_level: str = "O2") -> str:
    """
    Given a path that is either a .c/.cpp source or a .ll file, return the
    path to a ready-to-use .ll file inside tmp_dir.
    """
    p = Path(path)
    if p.suffix in {".ll", ".bc"}:
        # Already IR – use as-is (copy is cheap, keeps tmp_dir clean)
        dest = str(Path(tmp_dir) / f"{tag}.ll")
        shutil.copy(str(p), dest)
        return dest

    if p.suffix in {".c", ".cpp", ".cc", ".cxx"}:
        dest = str(Path(tmp_dir) / f"{tag}.ll")
        return compile_to_ir(str(p), dest, opt_level=opt_level)

    raise CompilationError(
        f"Unsupported input file type '{p.suffix}'. "
        "Expected .c, .cpp, or .ll"
    )
