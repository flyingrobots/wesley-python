# Copyright 2026 Captain James
# SPDX-License-Identifier: Apache-2.0
"""The syntax API: types and definitions become an ``ast`` tree printed by ``ast.unparse``."""

from __future__ import annotations

import ast
import unittest

from tests.support import assert_golden, messages_module, minimal_module
from wesley_python import syntax
from wesley_python.types import (
    Int,
    ListOf,
    Literal,
    NoneType,
    Ref,
    Str,
    UnionOf,
)


def _expr(type_: object) -> str:
    """Render one type expression by putting it in an alias."""
    module = syntax.Module([syntax.AliasDef("X", type_)])  # type: ignore[arg-type]
    tree = syntax.to_ast(module)
    assign = tree.body[-1]
    assert isinstance(assign, ast.Assign)  # noqa: S101 - narrows the type for mypy
    return ast.unparse(assign.value)


class GoldenTest(unittest.TestCase):
    def test_messages_module_matches_golden(self) -> None:
        assert_golden(self, "syntax_messages.py", syntax.render(messages_module()))

    def test_minimal_module_matches_golden(self) -> None:
        assert_golden(self, "syntax_minimal.py", syntax.render(minimal_module()))


class RenderTest(unittest.TestCase):
    def test_render_ends_with_exactly_one_newline(self) -> None:
        text = syntax.render(minimal_module())
        self.assertTrue(text.endswith("\n"))
        self.assertFalse(text.endswith("\n\n"))

    def test_render_is_deterministic(self) -> None:
        self.assertEqual(syntax.render(messages_module()), syntax.render(messages_module()))

    def test_to_ast_returns_a_module_that_compiles(self) -> None:
        tree = syntax.to_ast(messages_module())
        self.assertIsInstance(tree, ast.Module)
        compile(tree, "<generated>", "exec")

    def test_imports_are_exactly_the_names_used_and_sorted(self) -> None:
        tree = syntax.to_ast(syntax.Module([syntax.AliasDef("A", ListOf(Literal("x")))]))
        imports = [node for node in tree.body if isinstance(node, ast.ImportFrom)]
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0].module, "typing")
        self.assertEqual([alias.name for alias in imports[0].names], ["List", "Literal"])

    def test_module_without_typing_names_has_no_import(self) -> None:
        tree = syntax.to_ast(syntax.Module([syntax.AliasDef("A", Str())]))
        self.assertFalse(any(isinstance(node, ast.ImportFrom) for node in tree.body))


class TypeExpressionTest(unittest.TestCase):
    def test_scalars(self) -> None:
        self.assertEqual(_expr(Str()), "str")
        self.assertEqual(_expr(Int()), "int")
        self.assertEqual(_expr(NoneType()), "None")

    def test_union_of_one_member_collapses_to_it(self) -> None:
        self.assertEqual(_expr(UnionOf(Int())), "int")

    def test_union_of_literals_merges_into_one_literal(self) -> None:
        self.assertEqual(_expr(UnionOf(Literal("a"), Literal(2), Literal(value=False))), "Literal['a', 2, False]")

    def test_union_with_none(self) -> None:
        self.assertEqual(_expr(UnionOf(Str(), NoneType())), "Union[str, None]")

    def test_empty_union_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            UnionOf()

    def test_literal_refuses_other_values(self) -> None:
        with self.assertRaises(TypeError):
            Literal(1.5)  # type: ignore[arg-type]

    def test_literal_escapes_through_the_printer(self) -> None:
        self.assertEqual(_expr(Literal('it\'s "q"\n')), "Literal['it\\'s \"q\"\\n']")

    def test_ref_refuses_a_non_identifier(self) -> None:
        for bad in ("from", "a-b", "", "1a"):
            with self.subTest(name=bad), self.assertRaises(ValueError):
                Ref(bad)

    def test_ref_to_a_later_definition_is_a_string_forward_reference(self) -> None:
        module = syntax.Module(
            [
                syntax.AliasDef("A", ListOf(Ref("B"))),
                syntax.AliasDef("B", Str()),
                syntax.AliasDef("C", Ref("B")),
            ],
        )
        body = [node for node in syntax.to_ast(module).body if isinstance(node, ast.Assign)]
        self.assertEqual([ast.unparse(node.value) for node in body], ["List['B']", "str", "B"])

    def test_ref_to_a_name_outside_the_module_is_a_plain_name(self) -> None:
        self.assertEqual(_expr(Ref("Elsewhere")), "Elsewhere")

    def test_an_alias_of_a_bare_reference_to_a_later_definition_is_refused(self) -> None:
        # ``Result = 'Item'`` would be a str variable to mypy, not a type alias.
        later = syntax.TypedDictDef("Item", [syntax.Field("name", Str(), required=True)])
        for type_ in (Ref("Item"), UnionOf(Ref("Item")), UnionOf(UnionOf(Ref("Item")))):
            with self.subTest(type=type_):
                module = syntax.Module([syntax.AliasDef("Result", type_), later])
                with self.assertRaisesRegex(ValueError, r"Result.*Item"):
                    syntax.render(module)

    def test_an_alias_may_reference_a_later_definition_inside_a_subscript(self) -> None:
        later = syntax.TypedDictDef("Item", [syntax.Field("name", Str(), required=True)])
        module = syntax.Module(
            [
                syntax.AliasDef("Items", ListOf(Ref("Item"))),
                syntax.AliasDef("MaybeItem", UnionOf(Ref("Item"), NoneType())),
                later,
                syntax.AliasDef("Result", Ref("Item")),
            ],
        )
        body = [node for node in syntax.to_ast(module).body if isinstance(node, ast.Assign)]
        aliases = [ast.unparse(node) for node in body if not isinstance(node.value, ast.Call)]
        self.assertEqual(aliases, ["Items = List['Item']", "MaybeItem = Union['Item', None]", "Result = Item"])


class DefinitionTest(unittest.TestCase):
    def test_definition_names_must_be_identifiers(self) -> None:
        with self.assertRaises(ValueError):
            syntax.TypedDictDef("class", [])
        with self.assertRaises(ValueError):
            syntax.AliasDef("not valid", Str())

    def test_field_names_may_be_any_string(self) -> None:
        td = syntax.TypedDictDef("T", [syntax.Field("not an identifier", Str(), required=True)])
        self.assertIn("'not an identifier': str", syntax.render(syntax.Module([td])))

    def test_duplicate_field_names_are_refused(self) -> None:
        with self.assertRaises(ValueError):
            syntax.TypedDictDef(
                "T",
                [syntax.Field("a", Str(), required=True), syntax.Field("a", Int(), required=False)],
            )

    def test_duplicate_bound_names_are_refused(self) -> None:
        module = syntax.Module(
            [
                syntax.TypedDictDef("T", [syntax.Field("a", Str(), required=True)]),
                syntax.AliasDef("_TRequired", Str()),
            ],
        )
        with self.assertRaises(ValueError):
            syntax.render(module)

    def test_a_definition_may_not_shadow_an_imported_typing_name(self) -> None:
        module = syntax.Module([syntax.AliasDef("List", ListOf(Str()))])
        with self.assertRaises(ValueError):
            syntax.render(module)

    def test_a_definition_may_not_shadow_a_builtin_type_it_uses(self) -> None:
        with self.assertRaises(ValueError):
            syntax.render(syntax.Module([syntax.AliasDef("str", Str())]))

    def test_field_requires_a_type_expression(self) -> None:
        with self.assertRaises(TypeError):
            syntax.Field("a", "str", required=True)  # type: ignore[arg-type]

    def test_module_refuses_unknown_definitions(self) -> None:
        with self.assertRaises(TypeError):
            syntax.Module(["X = 1"])  # type: ignore[list-item]


if __name__ == "__main__":
    unittest.main()
