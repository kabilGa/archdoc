"""Output formatters for extracted context."""

from __future__ import annotations

import json

from archdoc.models import ProjectContext


def to_json(ctx: ProjectContext) -> str:
    """Serialise ``ctx`` as pretty-printed JSON (also the snapshot format)."""
    return json.dumps(ctx.to_dict(), indent=2)


def to_markdown(ctx: ProjectContext) -> str:
    """Render ``ctx`` as a Markdown outline of modules and their public symbols."""
    lines = ["# Codebase context", ""]
    for module in ctx.modules:
        lines.append(f"## `{module.path}`")
        lines.append("")
        if module.language != "python":
            lines += [f"*Language: {module.language}*", ""]
        if module.docstring:
            lines += [module.docstring.strip().splitlines()[0], ""]
        if module.imports:
            lines += ["**Imports:** " + ", ".join(f"`{i}`" for i in module.imports), ""]
        for symbol in module.public_symbols:
            doc = f" - {symbol.summary}" if symbol.summary else ""
            lines.append(f"- `{symbol.kind}` **{symbol.name}**`{symbol.signature}`{doc}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
