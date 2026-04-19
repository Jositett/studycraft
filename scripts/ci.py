#!/usr/bin/env python3
"""
StudyCraft CI script -- runs lint, test, and build locally.

Usage:
    uv run python scripts/ci.py          # full pipeline
    uv run python scripts/ci.py --lint   # lint only
    uv run python scripts/ci.py --test   # test only
    uv run python scripts/ci.py --build  # build only
"""

import subprocess
import sys

RED = "\033[91m"
GREEN = "\033[92m"
DIM = "\033[2m"
RESET = "\033[0m"


def run(label: str, cmd: list[str]) -> bool:
    print(f"\n{DIM}--- {label} ---{RESET}")
    print(f"{DIM}$ {' '.join(cmd)}{RESET}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"{RED}FAILED: {label}{RESET}")
        return False
    print(f"{GREEN}PASSED: {label}{RESET}")
    return True


def main() -> None:
    args = set(sys.argv[1:])
    run_all = not args or args == {"--all"}

    steps: list[tuple[str, list[str], bool]] = [
        ("Lint", ["uv", "run", "ruff", "check", "src/", "tests/"], run_all or "--lint" in args),
        ("Test", ["uv", "run", "pytest", "tests/", "-v"], run_all or "--test" in args),
        ("Build", ["uv", "build"], run_all or "--build" in args),
    ]

    failed = []
    for label, cmd, should_run in steps:
        if should_run and not run(label, cmd):
            failed.append(label)

    print()
    if failed:
        print(f"{RED}CI FAILED: {', '.join(failed)}{RESET}")
        sys.exit(1)
    else:
        print(f"{GREEN}CI PASSED{RESET}")


if __name__ == "__main__":
    main()
