# Architecture

archdoc is a small pipeline with a strict separation between **extraction**,
**data model** and **presentation**.

```
files ──► extractor ──► ProjectContext ──► render / checks ──► cli output
```

## Design principles

1. **Static only.** Source is parsed with `ast`, never imported or executed, so it is
   safe on untrusted code and works without installing the target's dependencies.
2. **Plain data in the middle.** `ProjectContext` is a tree of dataclasses that
   serialises to JSON. New outputs and checks consume it without touching the parser.
3. **No runtime dependencies.** Keeps installs trivial and CI fast.
4. **Resilient traversal.** Files that fail to parse are skipped, not fatal.

## Components

- `models.py`: `Symbol` (function/class/method with signature and docstring),
  `ModuleInfo` (path, docstring, imports, symbols), `ProjectContext` (root + modules).
- `extractor.py`: `extract_module(source, path)` for one file; `extract_project(root)`
  for a tree (skips `.git`, `.venv`, `__pycache__`, etc.); `find_undocumented` and
  `find_untested` implement the drift checks.
- `render.py`: `to_markdown` and `to_json`.
- `cli.py`: argparse commands `extract` and `check`; exit codes: `0` ok, `1` gaps
  found, `2` bad input.

## Extending

- **New output format**: add a function in `render.py` taking a `ProjectContext`, then
  add it to the `--format` choices in `cli.py`.
- **New check**: add a function in `extractor.py` (or a new module) returning findings,
  and call it from `_run_check`.
- **New language**: implement an extractor returning `ModuleInfo`; the rest of the
  pipeline is language-agnostic. (On the roadmap.)
