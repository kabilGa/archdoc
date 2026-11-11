import json
from pathlib import Path

from archdoc.cli import build_parser, main
from archdoc.config import ConfigError, load_config
from archdoc.render import to_json, to_markdown

CODE = '"""Mod."""\n\n\ndef run():\n    """Run it."""\n'


def _project(tmp_path: Path) -> Path:
    (tmp_path / "app.py").write_text(CODE)
    return tmp_path


def test_parser_has_subcommands():
    parser = build_parser()
    assert parser.parse_args(["extract"]).command == "extract"
    assert parser.parse_args(["check"]).command == "check"
    assert parser.parse_args(["diff", "snap.json"]).command == "diff"


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


def test_render_other_languages(tmp_path):
    (tmp_path / "a.go").write_text("package a\n\n// Do does.\nfunc Do() {}\n")
    from archdoc import extract_project

    ctx = extract_project(tmp_path)
    assert "*Language: go*" in to_markdown(ctx)
    assert '"language": "go"' in to_json(ctx)


def test_check_reports_untested(tmp_path, capsys):
    proj = _project(tmp_path)
    assert main(["check", str(proj), "--tests", str(proj / "tests")]) == 1
    assert "untested?" in capsys.readouterr().out


def test_check_ok(tmp_path, capsys):
    proj = _project(tmp_path)
    (proj / "tests").mkdir()
    (proj / "tests" / "test_app.py").write_text("run()\n")
    assert main(["check", str(proj), "--tests", str(proj / "tests")]) == 0


def test_check_stale_docs(tmp_path, capsys):
    proj = _project(tmp_path)
    (proj / "tests").mkdir()
    (proj / "tests" / "test_app.py").write_text("run()\n")
    (proj / "README.md").write_text("Call `gone()` to run.\n")
    code = main(["check", str(proj), "--tests", str(proj / "tests")])
    assert code == 1
    assert "stale-doc" in capsys.readouterr().out


def test_check_with_coverage(tmp_path, capsys):
    proj = _project(tmp_path)
    cov = tmp_path / "cov.json"
    cov.write_text(json.dumps({"files": {"app.py": {"executed_lines": [5], "missing_lines": []}}}))
    assert main(["check", str(proj), "--coverage", str(cov), "--docs", str(proj)]) == 0
    assert main(["check", str(proj), "--coverage", str(tmp_path / "nope.json")]) == 2


def test_diff_command(tmp_path, capsys):
    proj = _project(tmp_path)
    snap = tmp_path / "snap.json"
    assert main(["extract", str(proj), "--format", "json", "-o", str(snap)]) == 0
    assert main(["diff", str(snap), str(proj)]) == 0
    (proj / "app.py").write_text(CODE + "\n\ndef extra():\n    pass\n")
    assert main(["diff", str(snap), str(proj)]) == 1
    assert "+ app.py:extra" in capsys.readouterr().out
    assert main(["diff", str(tmp_path / "missing.json"), str(proj)]) == 2


def test_missing_path(capsys):
    assert main(["extract", "does-not-exist-xyz"]) == 2


def test_config_loaded_from_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.archdoc]\nexclude = ["gen"]\nignore = ["run"]\ntests = "t"\ndocs = ["README.md"]\n'
    )
    cfg = load_config(tmp_path)
    assert cfg.exclude == ["gen"]
    assert cfg.ignore == ["run"]
    assert cfg.tests == tmp_path / "t"
    assert cfg.docs == [tmp_path / "README.md"]
    assert cfg.source == tmp_path / "pyproject.toml"


def test_config_found_in_parent_and_applied(tmp_path, capsys):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.archdoc]\nignore = ["run"]\nexclude = ["gen"]\n'
    )
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("def run():\n    pass\n")
    (src / "gen").mkdir()
    (src / "gen" / "x.py").write_text("def bad():\n    pass\n")
    # `run` is ignored and gen/ is excluded by config, so nothing is reported
    assert main(["check", str(src), "--tests", str(tmp_path / "none")]) == 0
    # the CLI --ignore/--exclude flags work too
    (tmp_path / "pyproject.toml").write_text("")
    assert main(["check", str(src), "--tests", str(tmp_path / "none")]) == 1
    assert (
        main(
            [
                "check",
                str(src),
                "--tests",
                str(tmp_path / "none"),
                "--ignore",
                "*",
                "--exclude",
                "gen",
            ]
        )
        == 0
    )
    capsys.readouterr()


def test_config_defaults_without_file(tmp_path):
    cfg = load_config(tmp_path)
    assert cfg.source is None and cfg.exclude == []


def test_config_errors(tmp_path, capsys):
    (tmp_path / "pyproject.toml").write_text("[tool.archdoc]\nbogus = 1\n")
    try:
        load_config(tmp_path)
    except ConfigError as exc:
        assert "bogus" in str(exc)
    else:
        raise AssertionError("expected ConfigError")
    (tmp_path / "app.py").write_text(CODE)
    assert main(["extract", str(tmp_path)]) == 2
    (tmp_path / "pyproject.toml").write_text('[tool.archdoc]\nexclude = "gen"\n')
    assert main(["extract", str(tmp_path)]) == 2


def test_config_dataclass_defaults(tmp_path):
    from archdoc.config import Config

    cfg = Config(base=tmp_path)
    assert cfg.docs == [] and cfg.tests is None


def test_stale_ref_ignores_file_names(tmp_path):
    from archdoc import extract_project
    from archdoc.checks import find_stale_doc_refs

    (tmp_path / "models.py").write_text("def f():\n    pass\n")
    doc = tmp_path / "a.md"
    doc.write_text("See `models.py` and `models.nope`.\n")
    refs = [r for _, _, r in find_stale_doc_refs(extract_project(tmp_path), [doc])]
    assert refs == ["models.nope"]
