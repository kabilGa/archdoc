"""Drift checks: documentation gaps, test gaps, stale doc references and snapshot diffs."""

from __future__ import annotations

import builtins
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from archdoc.extractor import EXTRACTORS
from archdoc.models import ModuleInfo, ProjectContext, Symbol

_TEST_SUFFIXES = (
    "_test.py",
    "_test.go",
    ".test.ts",
    ".test.tsx",
    ".test.js",
    ".spec.ts",
    ".spec.js",
)


def is_test_path(path: str, tests_name: str = "tests") -> bool:
    """Whether ``path`` looks like a test file (so it is not itself checked)."""
    p = Path(path)
    return (
        any(part in {tests_name, "test", "tests", "__tests__"} for part in p.parts[:-1])
        or p.name.startswith("test_")
        or p.name == "conftest.py"
        or p.name.endswith(_TEST_SUFFIXES)
    )


def _ignored(patterns: Iterable[str], module_path: str, name: str) -> bool:
    return any(fnmatch(name, p) or fnmatch(f"{module_path}:{name}", p) for p in patterns)


def _checkable(ctx: ProjectContext, tests_name: str) -> list[ModuleInfo]:
    return [m for m in ctx.modules if not is_test_path(m.path, tests_name)]


def find_undocumented(
    ctx: ProjectContext, ignore: Iterable[str] = (), tests_name: str = "tests"
) -> list[tuple[str, Symbol]]:
    """Public symbols without a docstring or doc comment, as ``(module_path, symbol)``."""
    return [
        (m.path, s)
        for m in _checkable(ctx, tests_name)
        for s in m.public_symbols
        if not s.docstring and not _ignored(ignore, m.path, s.name)
    ]


def load_coverage(path: Path) -> dict[str, tuple[set[int], set[int]]]:
    """Read a ``coverage json`` report into ``{file: (executed_lines, missing_lines)}``."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        name.replace("\\", "/"): (set(info["executed_lines"]), set(info["missing_lines"]))
        for name, info in data["files"].items()
    }


def _coverage_for(coverage: dict, module_path: str):
    for name, value in coverage.items():
        if name == module_path or name.endswith("/" + module_path):
            return value
    return None


def _uncovered(symbol: Symbol, lines: tuple[set[int], set[int]]) -> bool:
    executed, missing = lines
    last = max(symbol.end_lineno, symbol.lineno)
    span = range(symbol.lineno + 1, last + 1) if last > symbol.lineno else [symbol.lineno]
    return any(n in missing for n in span) and not any(n in executed for n in span)


def find_untested(
    ctx: ProjectContext,
    tests_dir: Path | None = None,
    coverage: dict | None = None,
    ignore: Iterable[str] = (),
) -> list[tuple[str, Symbol]]:
    """Public symbols that look untested.

    With ``coverage`` (from :func:`load_coverage`) Python symbols are judged by executed
    lines: a symbol is untested when its body has statements but none ran. Otherwise, and
    for non-Python files, a public function/class is flagged when its name never appears
    in any file under ``tests_dir`` (a heuristic, not proof).
    """
    tests_name = Path(tests_dir).name if tests_dir else "tests"
    corpus = ""
    if tests_dir and Path(tests_dir).is_dir():
        corpus = "\n".join(
            p.read_text(encoding="utf-8", errors="ignore")
            for p in sorted(Path(tests_dir).rglob("*"))
            if p.suffix in EXTRACTORS
        )
    missing: list[tuple[str, Symbol]] = []
    for module in _checkable(ctx, tests_name):
        lines = (
            _coverage_for(coverage, module.path)
            if coverage and module.language == "python"
            else None
        )
        use_coverage = bool(coverage) and module.language == "python"
        has_methods = {s.name.split(".")[0] for s in module.symbols if s.kind == "method"}
        for symbol in module.public_symbols:
            if _ignored(ignore, module.path, symbol.name):
                continue
            if use_coverage:
                if symbol.kind == "class" and symbol.name in has_methods:
                    continue
                if lines is None or _uncovered(symbol, lines):
                    missing.append((module.path, symbol))
            elif symbol.kind != "method" and not re.search(
                rf"(?<![\w$]){re.escape(symbol.name)}(?![\w$])", corpus
            ):
                missing.append((module.path, symbol))
    return missing


_SPAN = re.compile(r"`([^`\n]+)`")
_CALL = re.compile(r"^[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*\(\)$")
_DOTTED = re.compile(r"^[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+$")
_BUILTINS = set(dir(builtins))
_FILE_EXTENSIONS = {
    "py", "md", "toml", "json", "yml", "yaml", "ts", "tsx", "js", "jsx", "mjs", "cjs",
    "go", "txt", "cfg", "ini", "lock", "html", "css",
}  # fmt: skip


def _doc_files(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        path = Path(path)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
        elif path.is_file():
            files.append(path)
    return files


def find_stale_doc_refs(
    ctx: ProjectContext, docs: Iterable[Path], ignore: Iterable[str] = ()
) -> list[tuple[str, int, str]]:
    """Inline-code references in Markdown that no longer match a real symbol.

    Checks ``name()`` calls and dotted names rooted in a project module or class, e.g.
    ``extract_project()`` or ``archdoc.render.to_json``. Fenced code blocks are skipped.
    Returns ``(file, line_number, reference)`` triples.
    """
    bare: set[str] = set()
    roots: set[str] = set()
    for module in ctx.modules:
        p = Path(module.path)
        roots.update(part for part in p.parts[:-1])
        roots.add(p.stem)
        for symbol in module.symbols:
            bare.add(symbol.name.split(".")[-1])
            roots.add(symbol.name.split(".")[0])
    known = bare | roots

    stale: list[tuple[str, int, str]] = []
    for doc in _doc_files(docs):
        fenced = False
        for number, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), start=1):
            if line.lstrip().startswith(("```", "~~~")):
                fenced = not fenced
                continue
            if fenced:
                continue
            for span in _SPAN.findall(line):
                ref = span.strip()
                if _ignored(ignore, str(doc), ref):
                    continue
                if _CALL.match(ref):
                    parts = ref[:-2].split(".")
                    if len(parts) == 1:
                        if parts[0] in known or parts[0] in _BUILTINS:
                            continue
                    elif parts[0] not in roots or parts[-1] in known:
                        continue
                    stale.append((str(doc), number, ref))
                elif _DOTTED.match(ref):
                    parts = ref.split(".")
                    if parts[-1] in _FILE_EXTENSIONS:
                        continue
                    if parts[0] in roots and parts[-1] not in known:
                        stale.append((str(doc), number, ref))
    return stale


@dataclass(frozen=True)
class Change:
    """One difference between two project contexts."""

    kind: str  # "added" | "removed" | "changed"
    module: str
    name: str
    detail: str = ""

    def __str__(self) -> str:
        sign = {"added": "+", "removed": "-", "changed": "~"}[self.kind]
        suffix = f": {self.detail}" if self.detail else ""
        return f"{sign} {self.module}:{self.name}{suffix}"


def diff_contexts(old: ProjectContext, new: ProjectContext) -> list[Change]:
    """Public-API differences between a saved snapshot ``old`` and the current ``new``."""
    before = {m.path: {s.name: s for s in m.public_symbols} for m in old.modules}
    after = {m.path: {s.name: s for s in m.public_symbols} for m in new.modules}
    changes: list[Change] = []
    for path in sorted(before.keys() | after.keys()):
        if path not in after:
            changes.append(Change("removed", path, "<module>"))
        elif path not in before:
            changes.append(Change("added", path, "<module>"))
        old_syms, new_syms = before.get(path, {}), after.get(path, {})
        for name in sorted(old_syms.keys() | new_syms.keys()):
            if name not in new_syms:
                changes.append(Change("removed", path, name))
            elif name not in old_syms:
                changes.append(Change("added", path, name))
            elif old_syms[name].signature != new_syms[name].signature:
                changes.append(
                    Change(
                        "changed",
                        path,
                        name,
                        f"{old_syms[name].signature or '()'} -> {new_syms[name].signature or '()'}",
                    )
                )
    return changes
