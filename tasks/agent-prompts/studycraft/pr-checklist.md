StudyCraft PR Checklist (agent-friendly)

- [ ] Title follows: `area: short-summary` (e.g., `detector: handle Roman numerals`)
- [ ] Includes a short description of the change and motivation
- [ ] Tests added or existing tests updated (unit tests preferred)
- [ ] `uv run python scripts/ci.py --test` passes locally (agent will ask before running)
- [ ] Linting applied: `uv run ruff check src/ --fix` or equivalent
- [ ] No secrets or API keys committed
- [ ] `pyproject.toml` changes approved before dependency edits
- [ ] CHANGELOG entry drafted if the change impacts users
- [ ] Reviewer suggestion(s) added (area owners or module maintainers)

Optional (for release PRs):

- [ ] Bumped version in `pyproject.toml` and `src/studycraft/__init__.py` if required
- [ ] Release notes drafted in `CHANGELOG.md`

How to use (agent): produce this checklist as part of the PR description and
include commands the maintainer can run to reproduce tests locally.
