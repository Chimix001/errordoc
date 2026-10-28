
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from errodoc.error_analyzer import analyze_file
PROG_NAME = "errordoc"
EXIT_OK = 0
EXIT_ERROR_FOUND = 1
EXIT_USAGE = 2

SKIP_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules",
    "__pycache__", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".tox", "build", "dist",
}


@dataclass(frozen=True)
class CliArgs:
    path: str | None
    run: bool
    timeout: int
    quiet: bool
    interactive: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG_NAME,
        description="Analyze Python code and suggest AI-powered fixes.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Python file or project directory. Defaults to the current directory.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute a single Python file to check runtime errors.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="Execution timeout in seconds (default: 5).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Hide the header banner.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start interactive mode.",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> CliArgs:
    parser = build_parser()
    ns = parser.parse_args(argv)

    if ns.timeout < 1:
        parser.error("--timeout must be at least 1 second.")

    if ns.run and ns.path is None:
        parser.error("--run requires a Python file path.")

    return CliArgs(
        path=ns.path,
        run=ns.run,
        timeout=ns.timeout,
        quiet=ns.quiet,
        interactive=ns.interactive,
    )


def print_result(result: dict[str, Any]) -> int:
    if result.get("status") == "success":
        print(result.get("description") or "No issues detected.")
        output = result.get("output")
        if output:
            print("\nProgram output:")
            print(output, end="" if output.endswith("\n") else "\n")
        return EXIT_OK

    print(f"\nDetected {result.get('error_kind', 'runtime')} error:")
    print(result.get("error") or "No error message available.")

    if result.get("description"):
        print(f"\nExplanation:\n{result['description']}")

    if result.get("fix"):
        print(f"\nSuggested fix:\n{result['fix']}")

    print("\nOriginal file unchanged.")
    return EXIT_ERROR_FOUND


def analyze_one(path: Path, run_code: bool, timeout: int) -> int:
    if path.suffix.lower() != ".py":
        print(f"Not a Python file: {path}", file=sys.stderr)
        return EXIT_USAGE

    print(f"\nAnalyzing: {path}")

    try:
        result = analyze_file(
            file_path=str(path),
            run_code=run_code,
            timeout=timeout,
        )
        return print_result(result)
    except (OSError, ValueError) as error:
        print(f"Could not analyze {path}: {error}", file=sys.stderr)
        return EXIT_USAGE
    except Exception as error:
        print(f"Analysis failed for {path}: {error}", file=sys.stderr)
        return EXIT_ERROR_FOUND


def analyze_directory(directory: Path, timeout: int) -> int:
    files = sorted(
        path for path in directory.rglob("*.py")
        if not any(part in SKIP_DIRS for part in path.parts)
    )

    if not files:
        print(f"No Python files found in {directory}")
        return EXIT_OK

    print(f"Found {len(files)} Python file(s).")
    failures = 0

    # Directory mode analyzes files without executing them.
    for path in files:
        if analyze_one(path, run_code=False, timeout=timeout) != EXIT_OK:
            failures += 1

    print(f"\nFinished: {len(files) - failures} successful, "
          f"{failures} failed.")

    return EXIT_ERROR_FOUND if failures else EXIT_OK


def interactive_mode(timeout: int) -> int:
    print("\nPython Error Doctor — Interactive Mode")
    print("Enter a Python file or directory. Type 'q' to quit.")

    while True:
        try:
            value = input("\nPath: ").strip().strip('"')
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            return EXIT_OK

        if value.lower() in {"q", "quit", "exit"}:
            print("Goodbye!")
            return EXIT_OK

        if not value:
            continue

        path = Path(value).expanduser()

        if not path.exists():
            print(f"Path not found: {path}")
        elif path.is_dir():
            analyze_directory(path, timeout)
        else:
            analyze_one(path, run_code=False, timeout=timeout)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    if args.interactive:
        return interactive_mode(args.timeout)

    path = Path(args.path or ".").expanduser().resolve()

    if not path.exists():
        print(f"Path not found: {path}", file=sys.stderr)
        return EXIT_USAGE

    if not args.quiet:
        print("\nPython Error Doctor")
        print("=" * 40)

    if path.is_dir():
        if args.run:
            print(
                "--run works on one file only. "
                "Choose a single .py file.",
                file=sys.stderr,
            )
            return EXIT_USAGE
        return analyze_directory(path, args.timeout)

    if args.run:
        print("Warning: executing the target runs its code.")

    return analyze_one(path, args.run, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
