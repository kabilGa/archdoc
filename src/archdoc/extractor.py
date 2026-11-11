"""Static extraction of architecture context using the standard-library ``ast`` module."""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

from archdoc.models import ModuleInfo, ProjectContext, Symbol

DEFAULT_EXCLUDES = frozenset(
    {".git", ".venv", "venv", "__pycache__", "node_modules", "build", "dist", ".tox"}
)


def _signature(node: ast.AST) -> str:
    args = ast.unparse(node.args)  # type: ignore[attr-defined]
    returns = getattr(node, "returns", None)
    suffix = f" -> {ast.unparse(returns)}" if returns is not None else ""
    return f"({args}){suffix}"


def _collect(body: list[ast.stmt], in_class: bool = False) -> Iterable[Symbol]:
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield Symbol(
                name=node.name,
                kind="method" if in_class else "function",
                lineno=node.lineno,
                signature=_signature(node),
                docstring=ast.get_docstring(node),
            )
        elif isinstance(node, ast.ClassDef):
            yield Symbol(
                name=node.name,
                kind="class",
                lineno=node.lineno,
                docstring=ast.get_docstring(node),
            )
            for member in _collect(node.body, in_class=True):
                yield Symbol(
                    name=f"{node.name}.{member.name}",
                    kind=member.kind,
                    lineno=member.lineno,
                    signature=member.signature,
                    docstring=member.docstring,
                )


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
    )


def extract_project(root: Path, excludes: Iterable[str] | None = None) -> ProjectContext:
    """Walk ``root`` and extract every ``*.py`` file. Unparseable files are skipped."""
    root = Path(root)
    skip = set(DEFAULT_EXCLUDES if excludes is None else excludes)
    modules: list[ModuleInfo] = []
    for file in sorted(root.rglob("*.py")):
        rel = file.relative_to(root)
        if any(part in skip for part in rel.parts):
            continue
        try:
            source = file.read_text(encoding="utf-8")
            modules.append(extract_module(source, rel.as_posix()))
        except (SyntaxError, UnicodeDecodeError):
            continue
    return ProjectContext(root=str(root), modules=modules)


def find_undocumented(ctx: ProjectContext) -> list[tuple[str, Symbol]]:
    """Public symbols without a docstring, as ``(module_path, symbol)`` pairs."""
    return [
        (m.path, s)
        for m in ctx.modules
        for s in m.public_symbols
        if not s.docstring and not s.name.split(".")[0].startswith("_")
    ]


def find_untested(ctx: ProjectContext, tests_dir: Path) -> list[tuple[str, Symbol]]:
    """Public functions/classes whose bare name never appears in any test file.

    A deliberately simple heuristic: it flags candidates for review, not proof of
    missing coverage.
    """
    tests_dir = Path(tests_dir)
    corpus = ""
    if tests_dir.is_dir():
        corpus = "\n".join(
            p.read_text(encoding="utf-8", errors="ignore") for p in tests_dir.rglob("*.py")
        )
    missing = []
    for module in ctx.modules:
        for symbol in module.public_symbols:
            if symbol.kind == "method":
                continue
            if symbol.name not in corpus:
                missing.append((module.path, symbol))
    return missing
