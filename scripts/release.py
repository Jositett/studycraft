#!/usr/bin/env python3
"""
StudyCraft release script -- runs CI, tags, and builds.

Usage:
    uv run python scripts/release.py 0.7.0
"""

import re
import subprocess
import sys
from pathlib import Path

RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

PYPROJECT = Path("pyproject.toml")
INIT_PY = Path("src/studycraft/__init__.py")
WEB_PY = Path("src/studycraft/web.py")


def _bump_version(version: str) -> None:
    """Bump version in all files that contain it."""
    # pyproject.toml
    text = PYPROJECT.read_text(encoding="utf-8")
    PYPROJECT.write_text(
        re.sub(r'version = "[^"]+"', f'version = "{version}"', text),
        encoding="utf-8",
    )

    # __init__.py
    text = INIT_PY.read_text(encoding="utf-8")
    INIT_PY.write_text(
        re.sub(r'__version__ = "[^"]+"', f'__version__ = "{version}"', text),
        encoding="utf-8",
    )

    # web.py (FastAPI version)
    text = WEB_PY.read_text(encoding="utf-8")
    WEB_PY.write_text(
        re.sub(r'version="[^"]+"', f'version="{version}"', text),
        encoding="utf-8",
    )


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: uv run python scripts/release.py <version>")
        print(f"  e.g. uv run python scripts/release.py 0.7.0")
        sys.exit(1)

    version = sys.argv[1]
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        print(f"{RED}Invalid version: {version} (expected X.Y.Z){RESET}")
        sys.exit(1)

    # 1. Run CI
    print(f"\n--- Running CI ---")
    r = subprocess.run([sys.executable, "scripts/ci.py"])
    if r.returncode != 0:
        print(f"{RED}CI failed, aborting release.{RESET}")
        sys.exit(1)

    # 2. Bump version in all files
    _bump_version(version)
    print(f"{GREEN}Version bumped to {version} (pyproject.toml, __init__.py, web.py){RESET}")

    # 3. Commit and tag
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "commit", "-m", f"release: v{version}"], check=True)
    subprocess.run(["git", "tag", f"v{version}"], check=True)
    print(f"{GREEN}Tagged v{version}{RESET}")

    # 4. Build
    subprocess.run(["uv", "build"], check=True)
    print(f"\n{GREEN}Release v{version} ready!{RESET}")
    print(f"  dist/ contains the built packages.")
    print(f"  Push with: git push && git push --tags")


if __name__ == "__main__":
    main()
