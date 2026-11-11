# Contributing to archdoc

Thanks for helping out! This guide covers local setup, pull requests and issue reporting.
By participating you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Local development

Requires Python 3.9+ and git.

```bash
git clone https://github.com/<your-username>/archdoc.git
cd archdoc
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Run the checks (the same ones CI runs):

```bash
pytest                      # tests
ruff check .                # lint
ruff format --check .       # formatting (use `ruff format .` to fix)
```

Try the CLI against this repo:

```bash
archdoc check src --tests tests
```

## Project layout

- `src/archdoc/`: the package (see [docs/architecture.md](docs/architecture.md))
- `tests/`: pytest suite; mirror module names, e.g. `test_extractor.py`
- `docs/`: design and architecture notes
- `.github/`: issue/PR templates and CI

## Pull requests

1. Open an issue first for anything larger than a small fix, so we can agree on direction.
2. Fork, then branch from `main` (`feat/short-name` or `fix/short-name`).
3. Keep PRs focused: one logical change per PR.
4. Add or update tests. Bug fixes should include a test that fails without the fix.
5. Update docs (README, `docs/`) when behaviour changes.
6. Make sure `pytest`, `ruff check .` and `ruff format --check .` pass.
7. Fill in the pull request template and link the issue (`Fixes #123`).

Commit messages: short imperative subject line (`Add JSON output flag`), with detail in
the body when useful.

A maintainer will review as soon as possible. Expect feedback; it is part of the process.

## Reporting issues

- **Bugs**: use the *Bug report* template. Include the archdoc version
  (`archdoc --version`), Python version, OS, the command you ran, and a minimal
  reproduction.
- **Features**: use the *Feature request* template and describe the problem before the
  solution.
- **Security problems**: do not open a public issue; contact the maintainers privately.

Search existing issues first to avoid duplicates.
