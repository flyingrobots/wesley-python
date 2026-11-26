"""Repository rules checked over the package source: stdlib only, and no code built from strings."""

from __future__ import annotations

import ast
import re
import sys
import unittest

from tests.support import SRC

PACKAGE = "wesley_python"

# Every top-level module the package may import. Each is in the Python 3.9 standard library.
ALLOWED_IMPORTS = frozenset(
    {"__future__", "argparse", "ast", "collections", "dataclasses", "json", "keyword", "sys", "typing"},
)

# Crude, on purpose: a string that looks like generated Python means someone is templating.
TEMPLATE_PATTERNS = (re.compile(r"TypedDict\("), re.compile(r"class\s+[A-Za-z_]\w*\s*\("))


def _sources() -> list[tuple[str, ast.Module]]:
    return [
        (str(path.relative_to(SRC)), ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        for path in sorted(SRC.rglob("*.py"))
    ]


def _imported_modules(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
            names.add(node.module.split(".")[0])
    return names


class StandardLibraryOnlyTest(unittest.TestCase):
    def test_there_are_sources(self) -> None:
        self.assertTrue(_sources())

    def test_the_package_imports_only_the_standard_library(self) -> None:
        for name, tree in _sources():
            with self.subTest(file=name):
                self.assertLessEqual(_imported_modules(tree) - {PACKAGE}, ALLOWED_IMPORTS)

    @unittest.skipIf(sys.version_info < (3, 10), "sys.stdlib_module_names is new in Python 3.10")
    def test_the_allowed_imports_are_standard_library_modules(self) -> None:
        self.assertLessEqual(ALLOWED_IMPORTS, frozenset(sys.stdlib_module_names))


class NoTemplatingTest(unittest.TestCase):
    def test_no_string_constant_looks_like_generated_code(self) -> None:
        for name, tree in _sources():
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    for pattern in TEMPLATE_PATTERNS:
                        with self.subTest(file=name, line=node.lineno, pattern=pattern.pattern):
                            self.assertIsNone(pattern.search(node.value))

    def test_the_guard_catches_a_template(self) -> None:
        tree = ast.parse("CODE = 'class End(_EndRequired):'\nOTHER = \"X = TypedDict('X', {})\"")
        constants = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant)]
        hits = [c for c in constants if any(p.search(c) for p in TEMPLATE_PATTERNS)]
        self.assertEqual(len(hits), 2)


if __name__ == "__main__":
    unittest.main()
