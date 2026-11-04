#!/usr/bin/env python3
"""Report documentation coverage for the project's Python modules.

The report counts module docstrings and public classes/functions (names not
starting with ``_``) that lack a docstring. It is used by
``docs/documentation-plan.md`` to measure progress.

Usage:
    python scripts/check_docs.py
    python scripts/check_docs.py --top 20
    python scripts/check_docs.py --missing src/_config.py
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
from typing import NamedTuple

ROOTS = ("src", "scripts", "photoshop", "plugins", "tests")
SKIP_PARTS = {"__pycache__", ".git", "node_modules"}


class ModuleStats(NamedTuple):
    """Documentation counters for one module."""

    path: Path
    has_module_doc: bool
    public_total: int
    public_missing: tuple[str, ...]


def iter_modules(roots: tuple[str, ...]) -> list[Path]:
    """Yield every ``.py`` file under ``roots``, skipping caches."""
    modules: list[Path] = []
    for root in roots:
        base = Path(root)
        if not base.is_dir():
            continue
        modules.extend(
            path
            for path in base.rglob("*.py")
            if not SKIP_PARTS.intersection(path.parts)
        )
    return sorted(modules)


def _is_type_stub(node: ast.AST) -> bool:
    """Whether a function is only a type declaration (overload or protocol stub)."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "overload":
            return True
    body = [item for item in node.body if not isinstance(item, ast.Expr) or not isinstance(item.value, ast.Constant)]
    if len(body) == 1 and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and body[0].value.value is Ellipsis:
        return True
    return bool(node.body) and all(
        isinstance(item, ast.Expr)
        and isinstance(item.value, ast.Constant)
        and item.value.value is Ellipsis
        for item in node.body
    )


def _iter_public_api(tree: ast.Module) -> list[ast.AST]:
    """Yield module-level classes/functions and their public methods."""
    found: list[ast.AST] = []

    def walk(node: ast.AST) -> None:
        """Walk."""
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                if not child.name.startswith("_"):
                    found.append(child)
                walk(child)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Only module-level functions and class methods; skip nested
                # closures and type-only declarations.
                if not child.name.startswith("_") and not _is_type_stub(child):
                    found.append(child)
            else:
                walk(child)

    walk(tree)
    return found


def analyze_module(path: Path) -> ModuleStats:
    """Return the documentation counters for a single module."""
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    api = _iter_public_api(tree)
    missing = tuple(
        node.name for node in api if not ast.get_docstring(node)  # type: ignore[arg-type]
    )
    return ModuleStats(
        path, bool(ast.get_docstring(tree)), len(api), missing
    )


def render_report(stats: list[ModuleStats], top: int) -> str:
    """Build the textual coverage report."""
    modules = len(stats)
    documented_modules = sum(1 for item in stats if item.has_module_doc)
    public_total = sum(item.public_total for item in stats)
    public_missing = sum(len(item.public_missing) for item in stats)

    lines = [
        f"Modules: {documented_modules}/{modules} with module docstring",
        (
            "Public classes/functions: "
            f"{public_total - public_missing}/{public_total} documented"
        ),
        "",
        f"Files with the most missing docstrings (top {top}):",
    ]
    ranked = sorted(
        (item for item in stats if item.public_missing),
        key=lambda item: len(item.public_missing),
        reverse=True,
    )
    for item in ranked[:top]:
        lines.append(
            f"  {len(item.public_missing):4}/{item.public_total:4}  {item.path}"
        )
    return "\n".join(lines)


def render_missing(stats: list[ModuleStats]) -> str:
    """Build a per-module list of missing public docstrings."""
    lines: list[str] = []
    for item in stats:
        if not item.has_module_doc:
            lines.append(f"{item.path}: missing module docstring")
        if item.public_missing:
            lines.append(f"{item.path}: {', '.join(item.public_missing)}")
    return "\n".join(lines)


def main() -> int:
    """Run the audit and print the requested report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of files to show in the summary (default: 20).",
    )
    parser.add_argument(
        "--missing",
        nargs="*",
        type=Path,
        default=None,
        help="Only analyze these files and list every missing docstring.",
    )
    parser.add_argument(
        "--roots",
        nargs="+",
        default=list(ROOTS),
        help="Directories to scan (default: src scripts photoshop plugins tests).",
    )
    args = parser.parse_args()

    paths = args.missing if args.missing else iter_modules(tuple(args.roots))
    stats = [analyze_module(path) for path in paths]

    if args.missing:
        print(render_missing(stats))
    else:
        print(render_report(stats, args.top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
