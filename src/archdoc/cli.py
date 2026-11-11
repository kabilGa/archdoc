"""Command-line interface: ``archdoc extract``, ``archdoc check`` and ``archdoc diff``."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from archdoc import __version__
from archdoc.checks import (
    diff_contexts,
    find_stale_doc_refs,
    find_undocumented,
    find_untested,
    load_coverage,
)
from archdoc.config import Config, ConfigError, load_config
from archdoc.extractor import DEFAULT_EXCLUDES, extract_project
from archdoc.models import ProjectContext
from archdoc.render import to_json, to_markdown


def build_parser() -> argparse.ArgumentParser:
    """Create the ``archdoc`` argument parser with its three subcommands."""
    parser = argparse.ArgumentParser(
        prog="archdoc",
        description="Extract architecture context to keep docs and tests in sync.",
    )
    parser.add_argument("--version", action="version", version=f"archdoc {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("path", type=Path, nargs="?", default=Path("."))
        p.add_argument(
            "--exclude", action="append", default=[], metavar="DIR", help="Directory name to skip."
        )

    extract = sub.add_parser("extract", help="Print extracted context for a project.")
    common(extract)
    extract.add_argument("--format", choices=["markdown", "json"], default="markdown")
    extract.add_argument("-o", "--output", type=Path, help="Write to a file instead of stdout.")

    check = sub.add_parser(
        "check", help="Report undocumented symbols, untested symbols and stale doc references."
    )
    common(check)
    check.add_argument(
        "--tests", type=Path, help="Tests directory (default: from config or ./tests)."
    )
    check.add_argument(
        "--coverage", type=Path, help="coverage.py JSON report for precise test gaps."
    )
    check.add_argument(
        "--docs", type=Path, nargs="+", help="Markdown files or directories to cross-check."
    )
    check.add_argument(
        "--ignore", action="append", default=[], metavar="PATTERN", help="fnmatch pattern to skip."
    )

    diff = sub.add_parser("diff", help="Compare the public API against a saved JSON snapshot.")
    diff.add_argument("snapshot", type=Path, help="JSON from `archdoc extract --format json`.")
    common(diff)
    return parser


def _context(args: argparse.Namespace, config: Config) -> ProjectContext:
    excludes = set(DEFAULT_EXCLUDES) | set(config.exclude) | set(args.exclude)
    return extract_project(args.path, excludes)


def _run_extract(args: argparse.Namespace, config: Config) -> int:
    ctx = _context(args, config)
    text = to_json(ctx) if args.format == "json" else to_markdown(ctx)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")
    return 0


def _default_docs(config: Config) -> list[Path]:
    if config.docs:
        return config.docs
    return [p for p in (config.base / "README.md", config.base / "docs") if p.exists()]


def _run_check(args: argparse.Namespace, config: Config) -> int:
    ctx = _context(args, config)
    ignore = [*config.ignore, *args.ignore]
    tests = args.tests or config.tests or Path("tests")
    coverage = None
    if args.coverage:
        try:
            coverage = load_coverage(args.coverage)
        except (OSError, ValueError, KeyError) as exc:
            print(f"error: cannot read coverage report {args.coverage}: {exc}", file=sys.stderr)
            return 2
    undocumented = find_undocumented(ctx, ignore, Path(tests).name)
    untested = find_untested(ctx, tests, coverage, ignore)
    stale = find_stale_doc_refs(ctx, args.docs or _default_docs(config), ignore)
    for path, sym in undocumented:
        print(f"undocumented: {path}:{sym.lineno} {sym.name}")
    for path, sym in untested:
        print(f"untested?:    {path}:{sym.lineno} {sym.name}")
    for doc, line, ref in stale:
        print(f"stale-doc:    {doc}:{line} `{ref}`")
    if undocumented or untested or stale:
        print(
            f"\n{len(undocumented)} undocumented, {len(untested)} possibly untested, "
            f"{len(stale)} stale doc references."
        )
        return 1
    print("OK: no documentation, test or doc-reference gaps found.")
    return 0


def _run_diff(args: argparse.Namespace, config: Config) -> int:
    try:
        old = ProjectContext.from_dict(json.loads(args.snapshot.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        print(f"error: cannot read snapshot {args.snapshot}: {exc}", file=sys.stderr)
        return 2
    changes = diff_contexts(old, _context(args, config))
    for change in changes:
        print(change)
    if changes:
        print(f"\n{len(changes)} public API change(s) since the snapshot.")
        return 1
    print("OK: public API matches the snapshot.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. Returns ``0`` ok, ``1`` problems found, ``2`` bad input."""
    args = build_parser().parse_args(argv)
    if not args.path.exists():
        print(f"error: path not found: {args.path}", file=sys.stderr)
        return 2
    try:
        config = load_config(args.path)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    handlers = {"extract": _run_extract, "check": _run_check, "diff": _run_diff}
    return handlers[args.command](args, config)
