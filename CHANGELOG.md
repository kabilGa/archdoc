# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-11-11

### Added
- `[tool.archdoc]` configuration in `pyproject.toml` (`tests`, `docs`, `exclude`, `ignore`).
- `archdoc diff` to compare the public API against a JSON snapshot.
- Stale documentation reference detection in `archdoc check`.
- Coverage-aware untested detection via `--coverage` (coverage.py JSON).
- JavaScript/TypeScript and Go extractors.
- Reusable GitHub Action (`action.yml`) and pre-commit hook.
- Release workflow, `SECURITY.md`, Dependabot and CODEOWNERS.

### Changed
- Distribution name on PyPI is `archdoc-cli` (command and import name stay `archdoc`).
- Methods are now reported with qualified names for nested classes; dunder and
  underscore-prefixed members are non-public.

## [0.1.0] - 2026-11-11

### Added
- Initial release: Python extraction, Markdown/JSON output and the `check` command.
