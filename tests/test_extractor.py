from pathlib import Path

import pytest

from archdoc import ModuleInfo, ProjectContext, Symbol, extract_module, extract_project
from archdoc.extractor import extract_source

SAMPLE = '''"""Sample module."""
import os
from collections import OrderedDict


def greet(name: str, excited: bool = False) -> str:
    """Return a greeting."""
    return name


def _helper():
    pass


class Greeter:
    """Greets people."""

    def hello(self):
        pass

    def __repr__(self):
        return "g"
'''


def test_extract_module_basics():
    info = extract_module(SAMPLE, "sample.py")
    assert info.docstring == "Sample module."
    assert info.imports == ["collections", "os"]
    names = {s.name: s for s in info.symbols}
    assert set(names) == {"greet", "_helper", "Greeter", "Greeter.hello", "Greeter.__repr__"}
    assert names["greet"].signature == "(name: str, excited: bool=False) -> str"
    assert names["greet"].summary == "Return a greeting."
    assert names["greet"].end_lineno == 8
    assert names["Greeter.hello"].kind == "method"


def test_public_symbols_excludes_private_and_dunder():
    info = extract_module(SAMPLE)
    assert {s.name for s in info.public_symbols} == {"greet", "Greeter", "Greeter.hello"}


def test_invalid_source_raises():
    with pytest.raises(SyntaxError):
        extract_module("def (")


def test_extract_project_skips_excluded_and_broken(tmp_path: Path):
    (tmp_path / "good.py").write_text(SAMPLE)
    (tmp_path / "broken.py").write_text("def (")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "ignored.py").write_text(SAMPLE)
    ctx = extract_project(tmp_path)
    assert [m.path for m in ctx.modules] == ["good.py"]


def test_extract_project_custom_excludes(tmp_path: Path):
    (tmp_path / "keep.py").write_text(SAMPLE)
    (tmp_path / "gen").mkdir()
    (tmp_path / "gen" / "skip.py").write_text(SAMPLE)
    ctx = extract_project(tmp_path, excludes={"gen"})
    assert [m.path for m in ctx.modules] == ["keep.py"]


def test_extract_source_dispatches_by_extension():
    assert extract_source("x = 1", "a.py").language == "python"
    assert extract_source("package main\n", "a.go").language == "go"
    assert extract_source("export const a = 1;", "a.ts").language == "typescript"
    assert extract_source("export const a = 1;", "a.js").language == "javascript"


def test_models_round_trip():
    ctx = ProjectContext(root="r", modules=[extract_module(SAMPLE, "sample.py")])
    again = ProjectContext.from_dict(ctx.to_dict())
    assert again == ctx
    assert isinstance(again.modules[0], ModuleInfo)
    assert isinstance(again.modules[0].symbols[0], Symbol)
    assert Symbol.from_dict({"name": "x", "kind": "function", "lineno": 1, "extra": 1}).name == "x"
