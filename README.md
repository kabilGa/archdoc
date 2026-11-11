# archdoc

[![CI](https://github.com/OWNER/archdoc/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/archdoc/actions/workflows/ci.yml)
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
  signatures and docstring summaries, from Python source via the standard-library `ast`.
- **Two output formats**: Markdown (for humans and LLM prompts) and JSON (for tooling).
- **Drift checks**: `archdoc check` lists public symbols that lack docstrings or are never
  mentioned in your tests, and exits non-zero so CI can enforce it.
- **Zero runtime dependencies**, safe on untrusted code, fast on large trees.

## Architecture

```
 source tree ──► extractor ──► ProjectContext ──┬──► render (markdown / json)
                (ast, no exec)   (dataclasses)  └──► checks (undocumented / untested)
                                      ▲
                                   cli.py
```

| Module | Responsibility |
| --- | --- |
| `archdoc/models.py` | Plain dataclasses: `Symbol`, `ModuleInfo`, `ProjectContext` |
| `archdoc/extractor.py` | AST walking, project traversal, drift checks |
| `archdoc/render.py` | Markdown and JSON formatters |
| `archdoc/cli.py` | `argparse` front end (`extract`, `check`) |

More detail in [docs/architecture.md](docs/architecture.md).

## Quickstart

Requires Python 3.9+.

```bash
git clone https://github.com/OWNER/archdoc.git
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

Fail CI when public symbols lack docstrings or tests:

```bash
archdoc check src --tests tests
```

Example output:

```
undocumented: archdoc/cli.py:15 build_parser
untested?:    archdoc/models.py:10 Symbol

1 undocumented, 1 possibly untested.
```

Use as a library:

```python
from pathlib import Path
from archdoc import extract_project

ctx = extract_project(Path("src"))
for module in ctx.modules:
    print(module.path, [s.name for s in module.public_symbols])
```

> The "untested" check is a name-matching heuristic: it flags candidates for review,
> not proof of missing coverage.

## Roadmap

- [x] Python extraction, Markdown/JSON output, `check` command
- [ ] Config file (`pyproject.toml` `[tool.archdoc]`) for excludes and rules
- [ ] Detect drift between a committed context snapshot and the current tree (`archdoc diff`)
- [ ] Cross-check names mentioned in Markdown docs against real symbols
- [ ] Coverage-aware test gap detection
- [ ] Language plugins (TypeScript, Go) via tree-sitter
- [ ] GitHub Action and pre-commit hook

Have an idea? [Open a feature request](../../issues/new/choose).

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and our
[Code of Conduct](CODE_OF_CONDUCT.md).

## License

[MIT](LICENSE)
