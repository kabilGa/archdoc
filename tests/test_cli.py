import json
from pathlib import Path

from archdoc.cli import main

CODE = '"""Mod."""\n\n\ndef run():\n    """Run it."""\n'


def _project(tmp_path: Path) -> Path:
    (tmp_path / "app.py").write_text(CODE)
    return tmp_path


def test_extract_markdown(tmp_path, capsys):
    assert main(["extract", str(_project(tmp_path))]) == 0
    out = capsys.readouterr().out
    assert "## `app.py`" in out
    assert "**run**" in out


def test_extract_json_to_file(tmp_path):
    out_file = tmp_path / "ctx.json"
    code = main(["extract", str(_project(tmp_path)), "--format", "json", "-o", str(out_file)])
    assert code == 0
    data = json.loads(out_file.read_text())
    assert data["modules"][0]["path"] == "app.py"


def test_check_reports_untested(tmp_path, capsys):
    proj = _project(tmp_path)
    assert main(["check", str(proj), "--tests", str(proj / "tests")]) == 1
    assert "untested?" in capsys.readouterr().out


def test_check_ok(tmp_path, capsys):
    proj = _project(tmp_path)
    (proj / "tests").mkdir()
    (proj / "tests" / "test_app.py").write_text("run()\n")
    assert main(["check", str(proj), "--tests", str(proj / "tests")]) == 0


def test_missing_path(capsys):
    assert main(["extract", "does-not-exist-xyz"]) == 2
