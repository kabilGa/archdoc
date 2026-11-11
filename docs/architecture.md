# Architecture

archdoc is a small pipeline with a strict separation between **extraction**,
**data model** and **presentation/checks**.

```
files ──► extractor ──► ProjectContext ──► render / checks / diff ──► cli output
```

## Design principles

1. **Static only.** Source is parsed, never imported or executed, so it is safe on
   untrusted code and works without installing the target's dependencies.
2. **Plain data in the middle.** `ProjectContext` is a tree of dataclasses that
   serialises to JSON. Outputs and checks consume it without touching any parser.
3. **Minimal dependencies.** Only `tomli` on Python < 3.11, for reading config.
4. **Resilient traversal.** Files that fail to parse are skipped, not fatal.

## Components

- `models.py`: `Symbol` (function/class/method with signature, docstring, line span and
  public flag), `ModuleInfo` (path, language, docstring, imports, symbols) and
  `ProjectContext` (root + modules). All round-trip through `to_dict` / `from_dict`, which
  is what makes JSON snapshots possible.
- `extractor.py`: `extract_module` (Python, via `ast`), `extract_source` (dispatch by file
  extension through the `EXTRACTORS` registry) and `extract_project` (directory walk that
  prunes excluded directories).
- `langs.py`: `extract_javascript`, `extract_typescript`, `extract_go`. They clean strings
  and comments, track brace depth, match declarations with regexes and attach the doc
  comment directly above each one.
- `checks.py`: `find_undocumented`, `find_untested` (name heuristic or coverage-based via
  `load_coverage`), `find_stale_doc_refs` and `diff_contexts`.
- `render.py`: `to_markdown` and `to_json`.
- `config.py`: `load_config` walks up from the target path to the nearest `pyproject.toml`
  with a `[tool.archdoc]` table and validates it (`ConfigError` on bad input).
- `cli.py`: argparse commands `extract`, `check`, `diff`. Exit codes: `0` ok, `1` problems
  found, `2` bad input.

## Public vs private

A symbol is public when no part of its qualified name starts with `_` (Python), when it is
capitalised (Go), or when it is exported / the file has no exports (JavaScript/TypeScript).
Test files (`tests/`, `test_*.py`, `*_test.go`, `*.spec.ts`, ...) are never reported by
`check`.

## Extending

- **New output format**: add a function in `render.py` taking a `ProjectContext`, then add
  it to the `--format` choices in `cli.py`.
- **New check**: add a function in `checks.py` and call it from `_run_check`.
- **New language**: write a function `(source, path) -> ModuleInfo` and register its file
  extension in `EXTRACTORS` in `extractor.py`. Everything downstream is language-agnostic.
