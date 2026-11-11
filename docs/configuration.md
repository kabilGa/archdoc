# Configuration

archdoc reads an optional `[tool.archdoc]` table from `pyproject.toml`. It looks in the
target directory and then each parent, using the first `pyproject.toml` that contains the
table. Relative paths resolve against that file's directory. Unknown keys are an error.

```toml
[tool.archdoc]
tests = "tests"
docs = ["README.md", "docs"]
exclude = ["generated", "migrations"]
ignore = ["*.__call__", "legacy/*:*", "main"]
```

| Key | Type | Meaning |
| --- | --- | --- |
| `tests` | string | Tests directory used by the untested check (default `tests`). |
| `docs` | list of strings | Markdown files or directories cross-checked for stale references (default: `README.md` and `docs/` if present). |
| `exclude` | list of strings | Extra directory names to skip, added to the built-in list (`.git`, `.venv`, `node_modules`, `build`, `dist`, ...). |
| `ignore` | list of strings | `fnmatch` patterns matched against `name` or `module:name`. Matching symbols and doc references are not reported. |

Command-line flags (`--tests`, `--docs`, `--exclude`, `--ignore`) override or extend these
values for a single run.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | No problems found |
| `1` | `check` found gaps, or `diff` found API changes |
| `2` | Bad input: missing path, unreadable snapshot or coverage file, invalid config |

## Stale documentation references

`archdoc check` scans inline code spans in Markdown (outside fenced blocks). It flags:

- calls such as `` `old_helper()` `` whose name matches no symbol (builtins are allowed);
- dotted names rooted in a project module or class, e.g. `` `mypkg.render.to_xml` ``, whose
  last segment matches no symbol.

File names such as `` `models.py` `` are ignored. Use `ignore` to silence a reference.

## Coverage-based test gaps

Generate a report with `coverage json` (or `pytest --cov --cov-report=json`) and pass it
with `--coverage`. A Python symbol is reported when its body contains statements and none
of them executed. Non-Python files fall back to the name-matching heuristic.
