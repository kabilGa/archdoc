# archdoc

[![CI](https://github.com/kabilGa/archdoc/actions/workflows/ci.yml/badge.svg)](https://github.com/kabilGa/archdoc/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Automated context extraction that bridges evolving code architecture and the documentation and tests that describe it.**

## The problem

Codebases change faster than their docs and tests. Modules get renamed, public APIs
appear and disappear, and nobody notices until a README is wrong or a new function
ships with no test. Humans (and AI coding assistants) also need an accurate, compact
map of "what is in this project right now" before they can write good docs or tests.

`archdoc` statically analyses your source, produces that map, and flags where docs
and tests have fallen behind. It never imports or executes your code.

## Features

- **Context extraction**: modules, imports, classes, functions and methods with
  signatures and docstring summaries, as Markdown (for people and LLM prompts) or JSON.
- **Multi-language**: Python (full `ast`), plus JavaScript/TypeScript and Go through
  lightweight built-in extractors.
- **Docs and test drift checks** (`archdoc check`):
  - public symbols with no docstring or doc comment,
  - public symbols never mentioned in your tests, or, with a `coverage.py` JSON report,
    whose body never actually ran,
  - inline-code references in your Markdown (`` `some_function()` ``) that no longer match
    any real symbol.
- **API drift** (`archdoc diff`): compare the public API against a saved JSON snapshot and
  list added, removed and changed symbols.
- **Configurable** via `[tool.archdoc]` in `pyproject.toml`.
- **CI-ready**: non-zero exit codes, a reusable GitHub Action and a pre-commit hook.
- **Safe and light**: static analysis only; the sole dependency is `tomli` on Python < 3.11.

## Architecture

```
 source tree ──► extractor ──► ProjectContext ──┬──► render  (markdown / json)
  (.py .ts .js    (ast / langs)  (dataclasses)  ├──► checks  (docs, tests, stale refs)
   .go)                                          └──► diff    (snapshot comparison)
                                      ▲
                       cli.py ◄── config.py ([tool.archdoc])
```

| Module | Responsibility |
| --- | --- |
| `archdoc/models.py` | Plain dataclasses: `Symbol`, `ModuleInfo`, `ProjectContext` |
| `archdoc/extractor.py` | Python extraction via `ast`, project traversal, extractor registry |
| `archdoc/langs.py` | JavaScript/TypeScript and Go extractors |
| `archdoc/checks.py` | Undocumented / untested / stale-reference checks and `diff_contexts` |
| `archdoc/render.py` | Markdown and JSON formatters |
| `archdoc/config.py` | `[tool.archdoc]` loading and validation |
| `archdoc/cli.py` | `argparse` front end (`extract`, `check`, `diff`) |

More detail in [docs/architecture.md](docs/architecture.md).

## Quickstart

Requires Python 3.9+. The command and import name is `archdoc`; the PyPI distribution
is named `archdoc-cli` because `archdoc` is already taken there by an unrelated project.

```bash
pip install archdoc-cli          # once published; or install from source:
git clone https://github.com/kabilGa/archdoc.git
cd archdoc
pip install .
archdoc --version
```

## Usage

Print a Markdown map of the current directory:

```bash
archdoc extract .
```

Write JSON for another tool:

```bash
archdoc extract src --format json -o context.json
```

Fail CI when public symbols lack docs or tests, or when README/docs mention things that
no longer exist:

```bash
archdoc check src --tests tests
```

Use real coverage data instead of name matching:

```bash
pytest --cov=mypkg --cov-report=json
archdoc check src --coverage coverage.json
```

Track API changes between releases:

```bash
archdoc extract src --format json -o api-snapshot.json   # commit this
archdoc diff api-snapshot.json src                         # later: exits 1 on changes
```

Example output:

```
undocumented: mypkg/cli.py:15 build_parser
untested?:    mypkg/models.py:10 Symbol
stale-doc:    README.md:42 `old_helper()`

1 undocumented, 1 possibly untested, 1 stale doc references.
```

Use as a library:

```python
from pathlib import Path
from archdoc import extract_project

ctx = extract_project(Path("src"))
for module in ctx.modules:
    print(module.path, [s.name for s in module.public_symbols])
```

Configure in `pyproject.toml` (see [docs/configuration.md](docs/configuration.md)):

```toml
[tool.archdoc]
tests = "tests"
docs = ["README.md", "docs"]
exclude = ["generated"]
ignore = ["*.__call__", "legacy/*:*"]
```

### GitHub Action

```yaml
- uses: actions/checkout@v4
- uses: kabilGa/archdoc@main
  with:
    path: src
    tests: tests
```

### pre-commit

```yaml
repos:
  - repo: https://github.com/kabilGa/archdoc
    rev: v0.2.0
    hooks:
      - id: archdoc-check
        args: [src, --tests, tests]
```

> The test check without `--coverage` is a name-matching heuristic: it flags candidates for
> review, not proof of missing coverage. The JavaScript/TypeScript and Go extractors are
> line- and brace-based heuristics, not full parsers.

## Roadmap

- [x] Python extraction, Markdown/JSON output, `check` command
- [x] Config file (`[tool.archdoc]`)
- [x] `archdoc diff` snapshot comparison
- [x] Cross-check names mentioned in Markdown docs against real symbols
- [x] Coverage-aware test gap detection
- [x] JavaScript/TypeScript and Go extractors
- [x] GitHub Action and pre-commit hook
- [ ] tree-sitter backed extractors for exact TS/Go/Rust/Java parsing
- [ ] Detect renamed or moved symbols between snapshots
- [ ] Token-budgeted context output for LLM prompts
- [ ] Dependency graph output (Mermaid)
- [ ] MCP server so AI assistants can query project context

Have an idea? [Open a feature request](../../issues/new/choose).

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and our
[Code of Conduct](CODE_OF_CONDUCT.md). Release history is in [CHANGELOG.md](CHANGELOG.md);
security reports go through [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
