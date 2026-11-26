# Copyright 2026 Captain James
# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for the test suite: paths, golden files and the example modules."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from wesley_python import syntax
from wesley_python.types import (
    AnyValue,
    Bool,
    DictOf,
    Float,
    Int,
    ListOf,
    Literal,
    NoneType,
    Ref,
    Str,
    UnionOf,
)

if TYPE_CHECKING:
    import unittest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
TESTS = ROOT / "tests"
GOLDEN = TESTS / "golden"
FIXTURES = TESTS / "fixtures"
TYPECHECK = TESTS / "typecheck"

UPDATE_ENV = "WESLEY_PYTHON_UPDATE_GOLDENS"


def assert_golden(case: unittest.TestCase, name: str, actual: str) -> None:
    """Compare ``actual`` to ``tests/golden/<name>``; rewrite it when asked to by the environment."""
    path = GOLDEN / name
    if os.environ.get(UPDATE_ENV) == "1":
        path.write_bytes(actual.encode("utf-8"))
    case.assertTrue(path.is_file(), f"missing golden {path}; run with {UPDATE_ENV}=1")
    expected = path.read_text(encoding="utf-8")
    case.assertEqual(expected, actual, f"output differs from golden {path}")


def messages_module() -> syntax.Module:
    """Build a Parley-shaped module: keyword keys, optional keys, literals, nested refs, lists, docs."""
    return syntax.Module(
        [
            syntax.AliasDef(
                "Phase",
                UnionOf(Literal("start"), Literal("end")),
                doc="Where a run is.",
            ),
            syntax.TypedDictDef(
                "Window",
                [
                    syntax.Field("from", Int(), required=True, doc="The first line, inclusive."),
                    syntax.Field("to", Int(), required=False, doc="The last line, exclusive."),
                ],
                doc="A range of line numbers.",
            ),
            syntax.TypedDictDef(
                "Redaction",
                [
                    syntax.Field("in", Str(), required=True),
                    syntax.Field("class", UnionOf(Str(), NoneType()), required=True),
                ],
            ),
            syntax.TypedDictDef(
                "RunEnd",
                [
                    syntax.Field("event", Literal("end"), required=True, doc="Always ``end``."),
                    syntax.Field("_schema", Str(), required=True),
                    syntax.Field("phase", Ref("Phase"), required=True),
                    syntax.Field("window", Ref("Window"), required=False),
                    syntax.Field("redactions", ListOf(Ref("Redaction")), required=False),
                    syntax.Field("counts", DictOf(Int()), required=True),
                    syntax.Field("ratio", Float(), required=False),
                    syntax.Field("ok", Bool(), required=True),
                    syntax.Field("detail", AnyValue(), required=False),
                    syntax.Field("next", Ref("Step"), required=False, doc="A later step.\nDefined below."),
                ],
                doc="The last line of a run.\n\nIt closes the run.",
            ),
            syntax.TypedDictDef(
                "Step",
                [
                    syntax.Field("name", Str(), required=True),
                    syntax.Field("children", ListOf(Ref("Step")), required=True),
                    syntax.Field("flag", UnionOf(Literal(1), Literal(value=True)), required=False),
                ],
            ),
            syntax.AliasDef("Message", UnionOf(Ref("RunEnd"), Ref("Step"))),
        ],
        doc="Message types for a run.",
    )


def minimal_module() -> syntax.Module:
    """Build edge shapes: no fields, only optional keys, only required keys, no docs at all."""
    return syntax.Module(
        [
            syntax.TypedDictDef("Empty", []),
            syntax.TypedDictDef("OnlyOptional", [syntax.Field("a", Str(), required=False)]),
            syntax.TypedDictDef("OnlyRequired", [syntax.Field("b", Int(), required=True)]),
            syntax.TypedDictDef("Documented", [], doc="Has a docstring and no fields."),
            syntax.AliasDef("Single", UnionOf(Str())),
        ],
    )
