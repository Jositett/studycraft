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

    # 2. Bump version in pyproject.toml
    text = PYPROJECT.read_text(encoding="utf-8")
    new_text = re.sub(r'version = "[^"]+"', f'version = "{version}"', text)
    PYPROJECT.write_text(new_text, encoding="utf-8")
    print(f"{GREEN}Version bumped to {version}{RESET}")

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
