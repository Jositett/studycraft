#!/usr/bin/env python3
"""
StudyCraft deployment script — HuggingFace Spaces & local Docker.

Usage:
    uv run python scripts/deploy.py --target huggingface --setup
        Create a new HuggingFace Space (Docker SDK) for studycraft.

    uv run python scripts/deploy.py --target huggingface --deploy
        Push code to HuggingFace Spaces (uses hf-deploy branch, swaps README).

    uv run python scripts/deploy.py --target huggingface --secret
        Set OPENROUTER_API_KEY secret on the HuggingFace Space.

    uv run python scripts/deploy.py --target local
        Build and run locally with docker-compose up -d --build.

    uv run python scripts/deploy.py --target local --stop
        Stop local docker-compose deployment.

Options:
    --space-name NAME    Space name (default: studycraft)
    --org ORG           HuggingFace organization/username
    --branch BRANCH     Deploy branch name (default: hf-deploy)
    --secret-value VAL  Secret value (if not provided, will prompt)
"""

import argparse
import subprocess
import sys
from pathlib import Path

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
DIM = "\033[2m"

PROJECT_ROOT = Path(__file__).parent.parent
HF_README = PROJECT_ROOT / "README.hf-spaces.md"
MAIN_README = PROJECT_ROOT / "README.md"


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command, echo it, and return the result."""
    print(f"{DIM}$ {' '.join(cmd)}{RESET}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if check and result.returncode != 0:
        print(f"{RED}Command failed: {' '.join(cmd)}{RESET}")
        sys.exit(1)
    return result


def _ensure_hf_cli() -> None:
    """Check that hf CLI is available."""
    try:
        run(["hf", "--help"], check=False)
    except FileNotFoundError:
        print(f"{RED}Error: hf CLI not found. Install with:{RESET}")
        print(f"  {DIM}pip install huggingface_hub{RESET}")
        sys.exit(1)


def cmd_hf_setup(args: argparse.Namespace) -> None:
    """Create the HuggingFace Space if it doesn't exist."""
    _ensure_hf_cli()
    space_name = args.space_name
    org = args.org or "YOUR_HF_USERNAME"

    repo_id = f"{org}/{space_name}" if org else space_name

    print(f"{YELLOW}Creating HuggingFace Space: {repo_id}{RESET}")
    print(f"  SDK: docker")
    print(f"  Port: 8000")

    # Use hf CLI to create the space
    # The CLI will prompt for confirmation if the space already exists
    cmd = [
        "hf",
        "repo",
        "create",
        space_name,
        "--type",
        "space",
        "--space-sdk",
        "docker",
    ]
    if org:
        cmd.extend(["--organization", org])

    try:
        run(cmd)
        print(f"{GREEN}✓ Space created: https://huggingface.co/spaces/{repo_id}{RESET}")
    except SystemExit:
        print(f"{YELLOW}Space may already exist. Continuing...{RESET}")

    print(f"\nNext steps:")
    print(
        f"  1. Set secrets: {DIM}hf env --repo-id {repo_id} set OPENROUTER_API_KEY <your-key>{RESET}"
    )
    print(
        f"  2. Deploy:      {DIM}uv run python scripts/deploy.py --target huggingface --deploy{RESET}"
    )


def cmd_hf_deploy(args: argparse.Namespace) -> None:
    """Push code to HuggingFace Spaces via a dedicated deploy branch."""
    _ensure_hf_cli()
    space_name = args.space_name
    org = args.org or "YOUR_HF_USERNAME"
    branch = args.branch
    repo_id = f"{org}/{space_name}" if org else space_name

    print(f"{YELLOW}Deploying to HuggingFace Space: {repo_id}{RESET}")
    print(f"  Branch: {branch}")

    # 1. Check for uncommitted changes
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if result.stdout.strip():
        print(f"{RED}Error: You have uncommitted changes. Commit or stash them first.{RESET}")
        sys.exit(1)

    # 2. Ensure HF README exists
    if not HF_README.exists():
        print(f"{RED}Error: Missing {HF_README}{RESET}")
        print(f"  This file should contain the YAML frontmatter for HF Spaces.")
        sys.exit(1)

    # 3. Create/update deploy branch
    current_branch = subprocess.run(
        ["git", "branch", "--show-current"], capture_output=True, text=True
    ).stdout.strip()

    # Check if branch exists
    branches = subprocess.run(["git", "branch", "-a"], capture_output=True, text=True).stdout
    if branch not in branches:
        print(f"{YELLOW}Creating deploy branch '{branch}'...{RESET}")
        run(["git", "checkout", "-b", branch])
    else:
        print(f"{YELLOW}Switching to deploy branch '{branch}'...{RESET}")
        run(["git", "checkout", branch])

    # 4. Replace README.md with HF version
    print(f"{YELLOW}Swapping README.md for HF Spaces version...{RESET}")
    backup = MAIN_README.with_suffix(".md.backup")
    MAIN_README.rename(backup)
    HF_README.copy(MAIN_README)
    run(["git", "add", "README.md"])
    run(["git", "commit", "-m", "chore: use HF Spaces README for deployment"], check=False)

    # 5. Push to HF
    # Add remote if not present
    remote_name = "hf"
    remotes = subprocess.run(["git", "remote"], capture_output=True, text=True).stdout.split()
    if remote_name not in remotes:
        remote_url = f"https://huggingface.co/spaces/{repo_id}"
        print(f"{YELLOW}Adding remote '{remote_name}': {remote_url}{RESET}")
        run(["git", "remote", "add", remote_name, remote_url])

    print(f"{YELLOW}Pushing to HuggingFace Spaces (branch:main)...{RESET}")
    run(["git", "push", remote_name, f"{branch}:main", "--force"])

    # 6. Restore main branch README
    print(f"{YELLOW}Restoring original README...{RESET}")
    run(["git", "checkout", current_branch])
    backup.rename(MAIN_README)

    print(f"\n{GREEN}✓ Deployment complete!{RESET}")
    print(f"  https://huggingface.co/spaces/{repo_id}")
    print(f"\nTo set secrets:")
    print(f"  {DIM}hf env --repo-id {repo_id} set OPENROUTER_API_KEY <your-key>{RESET}")


def cmd_hf_secret(args: argparse.Namespace) -> None:
    """Set a secret on the HuggingFace Space."""
    _ensure_hf_cli()
    space_name = args.space_name
    org = args.org or "YOUR_HF_USERNAME"
    repo_id = f"{org}/{space_name}" if org else space_name
    secret_name = args.secret_name or "OPENROUTER_API_KEY"
    secret_value = args.secret_value

    if not secret_value:
        import getpass

        secret_value = getpass.getpass(f"Enter value for {secret_name}: ")

    print(f"{YELLOW}Setting secret '{secret_name}' on {repo_id}...{RESET}")
    run(["hf", "env", "--repo-id", repo_id, "set", secret_name, secret_value])
    print(f"{GREEN}✓ Secret set{RESET}")


def cmd_local(args: argparse.Namespace) -> None:
    """Build and run locally with docker-compose."""
    print(f"{YELLOW}Local Docker Compose deployment{RESET}")

    compose_file = PROJECT_ROOT / "docker-compose.yml"
    if not compose_file.exists():
        print(f"{RED}Error: {compose_file} not found{RESET}")
        sys.exit(1)

    if args.stop:
        print(f"{YELLOW}Stopping StudyCraft...{RESET}")
        run(["docker-compose", "-f", str(compose_file), "down"])
        print(f"{GREEN}✓ Stopped{RESET}")
        return

    # Build and start
    print(f"{YELLOW}Building and starting StudyCraft...{RESET}")
    run(["docker-compose", "-f", str(compose_file), "up", "-d", "--build"])
    print(f"{GREEN}✓ StudyCraft is running{RESET}")
    print(f"  Web UI: {DIM}http://localhost:8000{RESET}")
    print(f"  API docs: {DIM}http://localhost:8000/docs{RESET}")
    print(f"\nTo view logs:")
    print(f"  {DIM}docker-compose -f {compose_file} logs -f{RESET}")
    print(f"\nTo stop:")
    print(f"  {DIM}uv run python scripts/deploy.py --target local --stop{RESET}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy StudyCraft to HuggingFace Spaces or local Docker.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # One-time HF Space setup
  uv run python scripts/deploy.py --target huggingface --setup --org my-org

  # Deploy code to HF Spaces
  uv run python scripts/deploy.py --target huggingface --deploy

  # Set API key secret on HF Space
  uv run python scripts/deploy.py --target huggingface --secret

  # Deploy locally with docker-compose
  uv run python scripts/deploy.py --target local

Note: Uses the 'hf' CLI (huggingface_hub). Install with: pip install huggingface_hub
        """,
    )

    parser.add_argument(
        "--target",
        "-t",
        choices=["huggingface", "local"],
        required=True,
        help="Deployment target: huggingface (HF Spaces) or local (docker-compose)",
    )

    # HuggingFace actions
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Create the HuggingFace Space (one-time setup)",
    )
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Push code to HuggingFace Spaces (requires hf-deploy branch workflow)",
    )
    parser.add_argument(
        "--secret",
        action="store_true",
        help="Set a secret on the HuggingFace Space",
    )
    parser.add_argument(
        "--secret-name",
        default="OPENROUTER_API_KEY",
        help="Secret name (default: OPENROUTER_API_KEY)",
    )
    parser.add_argument(
        "--secret-value",
        help="Secret value (will prompt if not provided)",
    )

    # Local actions
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop local docker-compose deployment",
    )

    # Common options
    parser.add_argument(
        "--space-name",
        default="studycraft",
        help="HuggingFace Space name (default: studycraft)",
    )
    parser.add_argument(
        "--org",
        default=None,
        help="HuggingFace organization/username (default: your logged-in user)",
    )
    parser.add_argument(
        "--branch",
        default="hf-deploy",
        help="Deploy branch name (default: hf-deploy)",
    )

    args = parser.parse_args()

    if args.target == "huggingface":
        if args.setup:
            cmd_hf_setup(args)
        elif args.deploy:
            cmd_hf_deploy(args)
        elif args.secret:
            cmd_hf_secret(args)
        else:
            parser.error("Specify --setup, --deploy, or --secret for HuggingFace target")
    elif args.target == "local":
        cmd_local(args)


if __name__ == "__main__":
    main()
