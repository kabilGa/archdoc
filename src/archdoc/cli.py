"""Command-line interface: ``archdoc extract`` and ``archdoc check``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from archdoc import __version__
from archdoc.extractor import extract_project, find_undocumented, find_untested
from archdoc.render import to_json, to_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="archdoc",
        description="Extract architecture context to keep docs and tests in sync.",
    )
    parser.add_argument("--version", action="version", version=f"archdoc {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    extract = sub.add_parser("extract", help="Print extracted context for a project.")
    extract.add_argument("path", type=Path, nargs="?", default=Path("."))
    extract.add_argument("--format", choices=["markdown", "json"], default="markdown")
    extract.add_argument("-o", "--output", type=Path, help="Write to a file instead of stdout.")

    check = sub.add_parser("check", help="Report undocumented and untested public symbols.")
    check.add_argument("path", type=Path, nargs="?", default=Path("."))
    check.add_argument("--tests", type=Path, default=Path("tests"), help="Tests directory.")
    return parser


def _run_extract(args: argparse.Namespace) -> int:
    ctx = extract_project(args.path)
    text = to_json(ctx) if args.format == "json" else to_markdown(ctx)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")
    return 0


def _run_check(args: argparse.Namespace) -> int:
    ctx = extract_project(args.path)
    undocumented = find_undocumented(ctx)
    untested = find_untested(ctx, args.tests)
    for path, sym in undocumented:
        print(f"undocumented: {path}:{sym.lineno} {sym.name}")
    for path, sym in untested:
        print(f"untested?:    {path}:{sym.lineno} {sym.name}")
    if undocumented or untested:
        print(f"\n{len(undocumented)} undocumented, {len(untested)} possibly untested.")
        return 1
    print("OK: no documentation or test gaps found.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.path.exists():
        print(f"error: path not found: {args.path}", file=sys.stderr)
        return 2
    return _run_extract(args) if args.command == "extract" else _run_check(args)
