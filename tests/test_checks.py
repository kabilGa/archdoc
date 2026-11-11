import json
from pathlib import Path

from archdoc import extract_project
from archdoc.checks import (
    Change,
    diff_contexts,
    find_stale_doc_refs,
    find_undocumented,
    find_untested,
    is_test_path,
    load_coverage,
)

CODE = '''"""Mod."""


def documented():
    """Yes."""
    return 1


def naked(a):
    return a


class Box:
    """A box."""

    def open(self):
        return 1

    def close(self):
        return 2
'''


def _project(tmp_path: Path):
    (tmp_path / "m.py").write_text(CODE)
    return extract_project(tmp_path)


def test_is_test_path():
    assert is_test_path("tests/test_a.py")
    assert is_test_path("pkg/a_test.go")
    assert is_test_path("web/a.spec.ts")
    assert is_test_path("conftest.py")
    assert not is_test_path("src/app.py")


def test_find_undocumented_and_ignore(tmp_path: Path):
    ctx = _project(tmp_path)
    flagged = {s.name for _, s in find_undocumented(ctx)}
    assert flagged == {"naked", "Box.open", "Box.close"}
    flagged = {s.name for _, s in find_undocumented(ctx, ignore=["Box.*", "m.py:naked"])}
    assert flagged == set()


def test_find_untested_heuristic(tmp_path: Path):
    ctx = _project(tmp_path)
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_m.py").write_text("from m import documented\n")
    flagged = {s.name for _, s in find_untested(ctx, tests)}
    assert flagged == {"naked", "Box"}


def _write_coverage(path: Path, executed, missing):
    path.write_text(
        json.dumps({"files": {"src/m.py": {"executed_lines": executed, "missing_lines": missing}}})
    )


def test_find_untested_with_coverage(tmp_path: Path):
    ctx = _project(tmp_path)
    cov = tmp_path / "cov.json"
    # documented() ran, naked() did not, Box.open ran, Box.close did not
    _write_coverage(cov, executed=[1, 6, 17], missing=[10, 20])
    coverage = load_coverage(cov)
    flagged = {s.name for _, s in find_untested(ctx, None, coverage)}
    assert flagged == {"naked", "Box.close"}


def test_find_untested_file_missing_from_coverage(tmp_path: Path):
    ctx = _project(tmp_path)
    cov = tmp_path / "cov.json"
    cov.write_text(
        json.dumps({"files": {"other.py": {"executed_lines": [1], "missing_lines": []}}})
    )
    flagged = {s.name for _, s in find_untested(ctx, None, load_coverage(cov))}
    assert {"documented", "naked", "Box.open", "Box.close"} <= flagged


def test_find_stale_doc_refs(tmp_path: Path):
    ctx = _project(tmp_path)
    doc = tmp_path / "README.md"
    doc.write_text(
        "Use `documented()` and `Box.open` and `print()`.\n"
        "Old: `removed_function()` and `m.vanished`.\n"
        "Other: `os.getcwd()` and `some thing`.\n"
        "```\n`ignored_in_fence()`\n```\n"
    )
    stale = find_stale_doc_refs(ctx, [doc])
    assert [(line, ref) for _, line, ref in stale] == [
        (2, "removed_function()"),
        (2, "m.vanished"),
    ]
    assert find_stale_doc_refs(ctx, [doc], ignore=["removed_function()", "m.vanished"]) == []


def test_find_stale_doc_refs_scans_directories(tmp_path: Path):
    ctx = _project(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("`gone()`\n")
    assert len(find_stale_doc_refs(ctx, [docs])) == 1


def test_diff_contexts(tmp_path: Path):
    old = _project(tmp_path)
    (tmp_path / "m.py").write_text(
        CODE.replace("def naked(a)", "def naked(a, b)").replace("def close", "def shut")
        + "\n\ndef fresh():\n    pass\n"
    )
    (tmp_path / "n.py").write_text("def x():\n    pass\n")
    new = extract_project(tmp_path)
    text = sorted(str(c) for c in diff_contexts(old, new))
    assert text == [
        "+ m.py:Box.shut",
        "+ m.py:fresh",
        "+ n.py:<module>",
        "+ n.py:x",
        "- m.py:Box.close",
        "~ m.py:naked: (a) -> (a, b)",
    ]
    assert Change("added", "m.py", "f").kind == "added"
    assert diff_contexts(old, old) == []
