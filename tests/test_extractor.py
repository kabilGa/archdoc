from pathlib import Path

import pytest

from archdoc import extract_module, extract_project
from archdoc.extractor import find_undocumented, find_untested

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
'''


def test_extract_module_basics():
    info = extract_module(SAMPLE, "sample.py")
    assert info.docstring == "Sample module."
    assert info.imports == ["collections", "os"]
    names = {s.name: s for s in info.symbols}
    assert set(names) == {"greet", "_helper", "Greeter", "Greeter.hello"}
    assert names["greet"].signature == "(name: str, excited: bool=False) -> str"
    assert names["greet"].summary == "Return a greeting."
    assert names["Greeter.hello"].kind == "method"


def test_public_symbols_excludes_private():
    info = extract_module(SAMPLE)
    assert "_helper" not in [s.name for s in info.public_symbols]


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


def test_find_undocumented(tmp_path: Path):
    (tmp_path / "m.py").write_text(SAMPLE)
    ctx = extract_project(tmp_path)
    flagged = {s.name for _, s in find_undocumented(ctx)}
    assert flagged == {"Greeter.hello"}


def test_find_untested(tmp_path: Path):
    (tmp_path / "m.py").write_text(SAMPLE)
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_m.py").write_text("from m import greet\n")
    ctx = extract_project(tmp_path, excludes={"tests"})
    flagged = {s.name for _, s in find_untested(ctx, tests)}
    assert flagged == {"Greeter"}
