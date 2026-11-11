"""Static extraction of architecture context. Python uses the standard-library ``ast``."""

from __future__ import annotations

import ast
import os
from collections.abc import Iterable
from pathlib import Path

from archdoc.langs import extract_go, extract_javascript, extract_typescript
from archdoc.models import ModuleInfo, ProjectContext, Symbol

DEFAULT_EXCLUDES = frozenset(
    {".git", ".venv", "venv", "__pycache__", "node_modules", "build", "dist", ".tox", "vendor"}
)


def _signature(node: ast.AST) -> str:
    args = ast.unparse(node.args)  # type: ignore[attr-defined]
    returns = getattr(node, "returns", None)
    suffix = f" -> {ast.unparse(returns)}" if returns is not None else ""
    return f"({args}){suffix}"


def _collect(body: list[ast.stmt], prefix: str = "") -> Iterable[Symbol]:
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qual = prefix + node.name
            yield Symbol(
                name=qual,
                kind="method" if prefix else "function",
                lineno=node.lineno,
                signature=_signature(node),
                docstring=ast.get_docstring(node),
                end_lineno=node.end_lineno or node.lineno,
                public=not any(part.startswith("_") for part in qual.split(".")),
            )
        elif isinstance(node, ast.ClassDef):
            qual = prefix + node.name
            yield Symbol(
                name=qual,
                kind="class",
                lineno=node.lineno,
                docstring=ast.get_docstring(node),
                end_lineno=node.end_lineno or node.lineno,
                public=not any(part.startswith("_") for part in qual.split(".")),
            )
            yield from _collect(node.body, prefix=qual + ".")


def _imports(tree: ast.Module) -> list[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return sorted(found)


def extract_module(source: str, path: str = "<string>") -> ModuleInfo:
    """Extract context from Python ``source``. Raises ``SyntaxError`` on invalid code."""
    tree = ast.parse(source, filename=path)
    return ModuleInfo(
        path=path,
        docstring=ast.get_docstring(tree),
        imports=_imports(tree),
        symbols=list(_collect(tree.body)),
        language="python",
    )


EXTRACTORS = {
    ".py": extract_module,
    ".js": extract_javascript,
    ".jsx": extract_javascript,
    ".mjs": extract_javascript,
    ".cjs": extract_javascript,
    ".ts": extract_typescript,
    ".tsx": extract_typescript,
    ".go": extract_go,
}


def extract_source(source: str, path: str) -> ModuleInfo:
    """Extract context from ``source`` using the extractor for ``path``'s extension."""
    extractor = EXTRACTORS[Path(path).suffix]
    return extractor(source, path)


def _skip_file(name: str) -> bool:
    return name.endswith((".d.ts", ".min.js")) or Path(name).suffix not in EXTRACTORS


def extract_project(root: Path, excludes: Iterable[str] | None = None) -> ProjectContext:
    """Walk ``root`` and extract every supported source file.

    Supports Python, JavaScript/TypeScript and Go. Unparseable files are skipped.
    ``excludes`` replaces :data:`DEFAULT_EXCLUDES` when given.
    """
    root = Path(root)
    skip = set(DEFAULT_EXCLUDES if excludes is None else excludes)
    modules: list[ModuleInfo] = []
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in skip)
        for name in sorted(files):
            if _skip_file(name):
                continue
            file = Path(current) / name
            rel = file.relative_to(root).as_posix()
            try:
                modules.append(extract_source(file.read_text(encoding="utf-8"), rel))
            except (SyntaxError, UnicodeDecodeError):
                continue
    modules.sort(key=lambda m: m.path)
    return ProjectContext(root=str(root), modules=modules)
