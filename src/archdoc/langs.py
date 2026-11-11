"""Lightweight, dependency-free extractors for JavaScript/TypeScript and Go.

These are line- and brace-based heuristics, not full parsers. They cover the common
declaration forms (functions, classes, methods, arrow-function constants, interfaces,
Go funcs/methods/types) and attach the doc comment directly above each declaration.
"""

from __future__ import annotations

import re

from archdoc.models import ModuleInfo, Symbol

_STRING = re.compile(r"""("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)""")


def _clean_lines(lines: list[str]) -> list[str]:
    """Blank out strings and comments so structure can be matched safely."""
    out = []
    in_comment = False
    for line in lines:
        text = _STRING.sub('""', line)
        result = ""
        i = 0
        while i < len(text):
            if in_comment:
                j = text.find("*/", i)
                if j < 0:
                    i = len(text)
                else:
                    in_comment = False
                    i = j + 2
                continue
            block = text.find("/*", i)
            line_comment = text.find("//", i)
            if line_comment >= 0 and (block < 0 or line_comment < block):
                result += text[i:line_comment]
                i = len(text)
            elif block >= 0:
                result += text[i:block]
                in_comment = True
                i = block + 2
            else:
                result += text[i:]
                i = len(text)
        out.append(result)
    return out


def _depths(clean: list[str]) -> list[int]:
    """Brace depth at the start of each line (one extra entry for the end)."""
    depth = 0
    out = []
    for line in clean:
        out.append(depth)
        depth += line.count("{") - line.count("}")
    out.append(depth)
    return out


def _end(clean: list[str], depths: list[int], start: int) -> int:
    """1-based last line of the block starting at 0-based line ``start``."""
    base = depths[start]
    opened = False
    for j in range(start, len(clean)):
        if "{" in clean[j]:
            opened = True
        if opened and depths[j + 1] <= base:
            return j + 1
        if not opened and (clean[j].rstrip().endswith(";") or j - start > 8):
            return start + 1
    return len(clean)


def _args(clean: list[str], start: int, col: int) -> tuple[str, str]:
    """Text inside the parentheses opening at ``clean[start][col]`` and what follows."""
    depth = 0
    buf: list[str] = []
    for j in range(start, min(len(clean), start + 25)):
        text = clean[j][col:] if j == start else clean[j]
        for k, ch in enumerate(text):
            if ch == "(":
                depth += 1
                if depth == 1:
                    continue
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return " ".join("".join(buf).split()), text[k + 1 :]
            buf.append(ch)
        buf.append(" ")
    return " ".join("".join(buf).split()), ""


def _jsdoc(lines: list[str], idx: int) -> str | None:
    j = idx - 1
    while j >= 0 and lines[j].strip().startswith("@"):
        j -= 1
    if j < 0 or not lines[j].strip().endswith("*/"):
        return None
    k = j
    while k >= 0 and "/*" not in lines[k]:
        k -= 1
    if k < 0:
        return None
    block = "\n".join(lines[k : j + 1])
    block = re.sub(r"^\s*/\*+", "", block)
    block = re.sub(r"\*+/\s*$", "", block)
    text = "\n".join(re.sub(r"^\s*\*\s?", "", ln) for ln in block.splitlines()).strip()
    return text or None


def _slash_doc(lines: list[str], idx: int) -> str | None:
    collected = []
    j = idx - 1
    while (
        j >= 0 and lines[j].lstrip().startswith("//") and not lines[j].lstrip().startswith("//go:")
    ):
        collected.append(re.sub(r"^\s*//\s?", "", lines[j]))
        j -= 1
    text = "\n".join(reversed(collected)).strip()
    return text or None


_JS_FUNC = re.compile(
    r"^\s*(?P<export>export\s+)?(?:default\s+)?(?:declare\s+)?(?:async\s+)?"
    r"function\s*\*?\s*(?P<name>[A-Za-z_$][\w$]*)\s*(?:<[^>]*>)?\s*(?=\()"
)
_JS_CLASS = re.compile(
    r"^\s*(?P<export>export\s+)?(?:default\s+)?(?:declare\s+)?(?:abstract\s+)?"
    r"class\s+(?P<name>[A-Za-z_$][\w$]*)"
)
_JS_TYPE = re.compile(
    r"^\s*(?P<export>export\s+)?(?:declare\s+)?(?:const\s+)?(?:interface|enum)\s+(?P<name>[\w$]+)"
)
_JS_ALIAS = re.compile(
    r"^\s*(?P<export>export\s+)?(?:declare\s+)?type\s+(?P<name>[\w$]+)\s*(?:<[^=]*>)?\s*="
)
_JS_ARROW = re.compile(
    r"^\s*(?P<export>export\s+)?(?:const|let|var)\s+(?P<name>[A-Za-z_$][\w$]*)\s*"
    r"(?::[^=]+)?=\s*(?:async\s+)?(?=\(|[A-Za-z_$][\w$]*\s*=>)"
)
_JS_METHOD = re.compile(
    r"^\s*(?P<mods>(?:(?:public|private|protected|static|async|override|abstract|get|set)\s+)*)"
    r"\*?\s*(?P<name>#?[A-Za-z_$][\w$]*)\s*(?:<[^>]*>)?\s*(?=\()"
)
_JS_SKIP = {"if", "for", "while", "switch", "catch", "constructor", "function", "return"}
_JS_RET = re.compile(r"^\s*:\s*([^{;=]+)")
_JS_ARROW_TAIL = re.compile(r"^\s*(?::\s*[^=]*?)?\s*=>")
_JS_IMPORT = re.compile(r"""^\s*import\s+(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]""")
_JS_REQUIRE = re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)""")


def extract_javascript(
    source: str, path: str = "<string>", language: str = "javascript"
) -> ModuleInfo:
    """Extract context from JavaScript or TypeScript ``source`` (heuristic)."""
    lines = source.splitlines()
    clean = _clean_lines(lines)
    depths = _depths(clean)
    has_exports = any(re.match(r"\s*export\b", c) or "module.exports" in c for c in clean)

    imports: set[str] = set()
    for line in lines:
        m = _JS_IMPORT.match(line)
        if m:
            imports.add(m.group(1))
        imports.update(_JS_REQUIRE.findall(line))

    symbols: list[Symbol] = []

    def add(name: str, kind: str, i: int, sig: str, exported: bool, last: int) -> None:
        public = (exported or not has_exports) and not name.split(".")[-1].startswith(("_", "#"))
        symbols.append(Symbol(name, kind, i + 1, sig, _jsdoc(lines, i), last, public))

    for i, c in enumerate(clean):
        if depths[i] != 0:
            continue
        m = _JS_FUNC.match(c)
        if m:
            args, tail = _args(clean, i, m.end())
            ret = _JS_RET.match(tail)
            sig = f"({args})" + (f": {ret.group(1).strip()}" if ret else "")
            add(m["name"], "function", i, sig, bool(m["export"]), _end(clean, depths, i))
            continue
        m = _JS_CLASS.match(c)
        if m:
            last = _end(clean, depths, i)
            add(m["name"], "class", i, "", bool(m["export"]), last)
            class_public = symbols[-1].public
            for j in range(i + 1, last):
                if depths[j] != depths[i] + 1:
                    continue
                mm = _JS_METHOD.match(clean[j])
                if not mm or mm["name"] in _JS_SKIP or "private" in mm["mods"]:
                    continue
                if mm["name"].startswith("#"):
                    continue
                args, tail = _args(clean, j, mm.end())
                ret = _JS_RET.match(tail)
                sig = f"({args})" + (f": {ret.group(1).strip()}" if ret else "")
                add(
                    f"{m['name']}.{mm['name']}",
                    "method",
                    j,
                    sig,
                    class_public,
                    _end(clean, depths, j),
                )
            continue
        m = _JS_TYPE.match(c) or _JS_ALIAS.match(c)
        if m:
            add(m["name"], "class", i, "", bool(m["export"]), _end(clean, depths, i))
            continue
        m = _JS_ARROW.match(c)
        if m:
            rest = c[m.end() :]
            if rest.startswith("("):
                args, tail = _args(clean, i, m.end())
                if not _JS_ARROW_TAIL.match(tail):
                    continue
                ret = re.match(r"^\s*:\s*([^=]+?)\s*=>", tail)
                sig = f"({args})" + (f": {ret.group(1).strip()}" if ret else "")
            else:
                single = re.match(r"[\w$]+", rest)
                sig = f"({single.group(0) if single else ''})"
            add(m["name"], "function", i, sig, bool(m["export"]), _end(clean, depths, i))

    return ModuleInfo(
        path=path, docstring=None, imports=sorted(imports), symbols=symbols, language=language
    )


def extract_typescript(source: str, path: str = "<string>") -> ModuleInfo:
    """Extract context from TypeScript ``source`` (heuristic)."""
    return extract_javascript(source, path, language="typescript")


_GO_FUNC = re.compile(
    r"^func\s+(?:\(\s*(?:\w+\s+)?\*?(?P<recv>\w+)(?:\[[^\]]*\])?\s*\)\s*)?"
    r"(?P<name>\w+)\s*(?:\[[^\]]*\])?\s*(?=\()"
)
_GO_TYPE = re.compile(r"^type\s+(?P<name>\w+)(?:\[[^\]]*\])?\s*(?P<kind>struct|interface)?")
_GO_IMPORT_ONE = re.compile(r'^\s*import\s+(?:[\w.]+\s+)?"([^"]+)"')
_GO_IMPORT_LINE = re.compile(r'^\s*(?:[\w.]+\s+)?"([^"]+)"')


def extract_go(source: str, path: str = "<string>") -> ModuleInfo:
    """Extract context from Go ``source`` (heuristic). Exported means capitalised."""
    lines = source.splitlines()
    clean = _clean_lines(lines)
    depths = _depths(clean)

    imports: set[str] = set()
    in_block = False
    for line in lines:
        if in_block:
            if line.strip().startswith(")"):
                in_block = False
                continue
            m = _GO_IMPORT_LINE.match(line)
            if m:
                imports.add(m.group(1))
        elif re.match(r"^\s*import\s*\(", line):
            in_block = True
        else:
            m = _GO_IMPORT_ONE.match(line)
            if m:
                imports.add(m.group(1))

    symbols: list[Symbol] = []
    module_doc = None
    for i, c in enumerate(clean):
        if c.startswith("package "):
            module_doc = _slash_doc(lines, i)
            continue
        m = _GO_FUNC.match(c)
        if m:
            args, tail = _args(clean, i, m.end())
            ret = tail.split("{")[0].strip()
            sig = f"({args})" + (f" {ret}" if ret else "")
            name = m["name"]
            qual = f"{m['recv']}.{name}" if m["recv"] else name
            symbols.append(
                Symbol(
                    qual,
                    "method" if m["recv"] else "function",
                    i + 1,
                    sig,
                    _slash_doc(lines, i),
                    _end(clean, depths, i),
                    name[0].isupper(),
                )
            )
            continue
        m = _GO_TYPE.match(c)
        if m:
            symbols.append(
                Symbol(
                    m["name"],
                    "class",
                    i + 1,
                    "",
                    _slash_doc(lines, i),
                    _end(clean, depths, i),
                    m["name"][0].isupper(),
                )
            )
    return ModuleInfo(
        path=path, docstring=module_doc, imports=sorted(imports), symbols=symbols, language="go"
    )
