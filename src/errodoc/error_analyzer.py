from __future__ import annotations

import ast
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from errodoc.llm import get_llm_suggestion
Status = Literal["success", "error"]
ErrorKind = Literal["syntax", "runtime", "timeout", "none"]


@dataclass(frozen=True)
class AnalysisResult:
    """Structured result returned by `analyze_file`."""

    status: Status
    file: str
    error_kind: ErrorKind = "none"
    error: str | None = None
    description: str | None = None
    fix: str | None = None
    output: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_source(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"File is not valid UTF-8: {path}") from exc


def _check_syntax(source_code: str, path: Path) -> str | None:
    """Return a formatted SyntaxError message, or None if the file parses."""
    try:
        ast.parse(source_code, filename=str(path))
    except SyntaxError as error:
        return (
            f"SyntaxError: {error.msg}\n"
            f"File: {error.filename}\n"
            f"Line: {error.lineno}\n"
            f"Offset: {error.offset}"
        )
    return None


def _run_file(path: Path, timeout: int) -> tuple[bool, str | None, str | None]:
    """
    Execute the file. Returns (ok, error_message, stdout).
    `error_message` is set whenever ok is False.
    """
    try:
        result = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(path.parent),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, f"Execution timed out after {timeout} seconds.", None
    except OSError as exc:
        return False, f"Failed to launch interpreter: {exc}", None

    if result.returncode == 0:
        return True, None, result.stdout

    error_message = (
        result.stderr.strip()
        or result.stdout.strip()
        or f"Python exited with code {result.returncode}."
    )
    return False, error_message, result.stdout


def _llm_result(error_message: str, source_code: str, **extra: Any) -> AnalysisResult:
    """Call the LLM and build an error result, safely."""
    try:
        suggestion = get_llm_suggestion(
            user_message=error_message,
            source_code=source_code,
        )
    except Exception as exc:  # noqa: BLE001 — we surface LLM failure to caller
        return AnalysisResult(
            status="error",
            error=error_message,
            error_kind=extra.get("error_kind", "runtime"),
            description=f"LLM call failed: {exc}",
            fix=None,
            file=extra["file"],
        )

    return AnalysisResult(
        status="error",
        file=extra["file"],
        error_kind=extra.get("error_kind", "runtime"),
        error=error_message,
        description=suggestion.get("description"),
        fix=suggestion.get("fix"),
        output=extra.get("output"),
    )


def analyze_file(
    file_path: str,
    run_code: bool = False,
    timeout: int = 5,
) -> dict[str, Any]:
    """
    Analyze a Python file and, on syntax or runtime errors, request an
    LLM-generated explanation and fix. The original file is never modified.
    """
    path = Path(file_path).resolve()

    if not path.is_file():
        raise FileNotFoundError(f"Python file not found: {path}")
    if path.suffix.lower() != ".py":
        raise ValueError("Please provide a Python (.py) file.")
    if timeout <= 0:
        raise ValueError("timeout must be a positive number of seconds.")

    source_code = _read_source(path)

    # --- Step 1: syntax check (no execution) 
    syntax_error = _check_syntax(source_code, path)
    if syntax_error is not None:
        return _llm_result(
            syntax_error,
            source_code,
            file=str(path),
            error_kind="syntax",
        ).to_dict()

    if not run_code:
        return AnalysisResult(
            status="success",
            file=str(path),
            description=(
                "No syntax errors detected. "
                "Runtime errors have not been checked (run_code=False)."
            ),
        ).to_dict()

    # --- Step 2: execute and capture runtime failures 
    ok, runtime_error, stdout = _run_file(path, timeout)
    if ok:
        return AnalysisResult(
            status="success",
            file=str(path),
            description="The script ran successfully.",
            output=stdout,
        ).to_dict()

    # --- Step 3: ask the LLM to explain the failure 
    assert runtime_error is not None  # guaranteed by _run_file contract
    kind: ErrorKind = "timeout" if "timed out" in runtime_error else "runtime"
    return _llm_result(
        runtime_error,
        source_code,
        file=str(path),
        error_kind=kind,
        output=stdout,
    ).to_dict()