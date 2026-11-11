"""Plain data structures describing extracted codebase context."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Symbol:
    """A function, class or method found in a module."""

    name: str
    kind: str  # "function" | "class" | "method"
    lineno: int
    signature: str = ""
    docstring: str | None = None

    @property
    def is_public(self) -> bool:
        return not self.name.startswith("_")

    @property
    def summary(self) -> str:
        """First line of the docstring, or an empty string."""
        if not self.docstring:
            return ""
        return self.docstring.strip().splitlines()[0]


@dataclass
class ModuleInfo:
    """Context extracted from a single source file."""

    path: str
    docstring: str | None = None
    imports: list[str] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)

    @property
    def public_symbols(self) -> list[Symbol]:
        return [s for s in self.symbols if s.is_public]


@dataclass
class ProjectContext:
    """Context extracted from a whole project tree."""

    root: str
    modules: list[ModuleInfo] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
