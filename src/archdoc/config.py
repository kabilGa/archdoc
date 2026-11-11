"""Configuration loaded from the ``[tool.archdoc]`` table in ``pyproject.toml``."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on 3.9/3.10
    import tomli as tomllib

KNOWN_KEYS = {"exclude", "tests", "ignore", "docs"}


class ConfigError(ValueError):
    """Raised when ``[tool.archdoc]`` is malformed."""


@dataclass
class Config:
    """Resolved archdoc settings.

    ``exclude`` adds directory names to skip, ``ignore`` holds fnmatch patterns matched
    against ``name`` or ``module:name``, ``tests`` is the tests directory and ``docs``
    lists Markdown files or directories to cross-check. Relative paths are resolved
    against ``base``, the directory containing the config file.
    """

    base: Path
    exclude: list[str] = field(default_factory=list)
    ignore: list[str] = field(default_factory=list)
    tests: Path | None = None
    docs: list[Path] = field(default_factory=list)
    source: Path | None = None


def _string_list(table: dict, key: str) -> list[str]:
    value = table.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(f"[tool.archdoc] {key!r} must be a list of strings")
    return value


def load_config(start: Path) -> Config:
    """Find ``[tool.archdoc]`` in ``start`` or the nearest parent ``pyproject.toml``."""
    start = Path(start).resolve()
    for directory in [start, *start.parents] if start.is_dir() else list(start.parents):
        candidate = directory / "pyproject.toml"
        if not candidate.is_file():
            continue
        with candidate.open("rb") as handle:
            try:
                data = tomllib.load(handle)
            except tomllib.TOMLDecodeError as exc:
                raise ConfigError(f"{candidate}: {exc}") from exc
        table = data.get("tool", {}).get("archdoc")
        if table is None:
            continue
        unknown = set(table) - KNOWN_KEYS
        if unknown:
            raise ConfigError(
                f"{candidate}: unknown [tool.archdoc] keys: {', '.join(sorted(unknown))}"
            )
        tests = table.get("tests")
        if tests is not None and not isinstance(tests, str):
            raise ConfigError("[tool.archdoc] 'tests' must be a string")
        return Config(
            base=directory,
            exclude=_string_list(table, "exclude"),
            ignore=_string_list(table, "ignore"),
            tests=directory / tests if tests else None,
            docs=[directory / d for d in _string_list(table, "docs")],
            source=candidate,
        )
    return Config(base=start if start.is_dir() else start.parent)
