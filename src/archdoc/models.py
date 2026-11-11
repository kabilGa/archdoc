"""Plain data structures describing extracted codebase context."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any


def _known(cls: type, data: dict[str, Any]) -> dict[str, Any]:
    names = {f.name for f in fields(cls)}
    return {k: v for k, v in data.items() if k in names}


@dataclass(frozen=True)
class Symbol:
    """A function, class or method found in a module."""

    name: str
    kind: str  # "function" | "class" | "method"
    lineno: int
    signature: str = ""
    docstring: str | None = None
    end_lineno: int = 0
    public: bool = True

    @property
    def is_public(self) -> bool:
        """Whether the symbol is part of the module's public surface."""
        return self.public

    @property
    def summary(self) -> str:
        """First line of the docstring, or an empty string."""
        if not self.docstring:
            return ""
        return self.docstring.strip().splitlines()[0]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Symbol:
        """Rebuild a symbol from its ``asdict`` form (unknown keys are ignored)."""
        return cls(**_known(cls, data))


@dataclass
class ModuleInfo:
    """Context extracted from a single source file."""

    path: str
    docstring: str | None = None
    imports: list[str] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)
    language: str = "python"

    @property
    def public_symbols(self) -> list[Symbol]:
        """Symbols that are part of the public surface."""
        return [s for s in self.symbols if s.is_public]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModuleInfo:
        """Rebuild a module from its ``asdict`` form."""
        data = dict(_known(cls, data))
        data["symbols"] = [Symbol.from_dict(s) for s in data.get("symbols", [])]
        return cls(**data)


@dataclass
class ProjectContext:
    """Context extracted from a whole project tree."""

    root: str
    modules: list[ModuleInfo] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serialisable nested dicts."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectContext:
        """Rebuild a context from ``to_dict`` output, e.g. a saved snapshot."""
        return cls(
            root=data.get("root", ""),
            modules=[ModuleInfo.from_dict(m) for m in data.get("modules", [])],
        )
