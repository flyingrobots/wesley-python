# Copyright 2026 Captain James
# SPDX-License-Identifier: Apache-2.0
"""Definitions and modules: the statements of a generated module, built as an ``ast`` tree.

A :class:`Module` holds definitions in the order the caller gives. :func:`to_ast` builds the
``ast.Module`` and :func:`render` prints it with ``ast.unparse``. No source text is assembled here:
every identifier, key and docstring enters the tree as a node, and the printer does the escaping.

A ``TypedDict`` is rendered so that it runs on Python 3.9, accepts keys that are Python keywords and
marks optional keys without ``typing.NotRequired`` (new in 3.11). The required keys and the optional
keys are each a functional-form ``TypedDict`` (the second one ``total=False``), and a class named by
the definition inherits from both, carrying the docstring. A side with no keys is left out.

Definitions are emitted in the given order; the caller orders them. A reference to a definition
that comes later in the module is printed as a string forward reference, so the module imports.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

from wesley_python.types import RenderContext, TypeExpr, check_identifier

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["AliasDef", "Definition", "Field", "Module", "TypedDictDef", "render", "to_ast"]

_CLASS_INDENT = "    "


def _check_instance(value: object, kinds: type | tuple[type, ...], message: str) -> None:
    """Raise ``TypeError`` with ``message`` unless ``value`` is an instance of ``kinds``.

    The annotations already say this; the check is for callers that are not type-checked.
    """
    if not isinstance(value, kinds):
        raise TypeError(message)


def _check_doc(doc: object) -> None:
    _check_instance(doc, (str, type(None)), f"a doc must be a string or None, not {doc!r}")


@dataclass(frozen=True)
class Field:
    """One key of a ``TypedDict``. The key may be any string, including a Python keyword."""

    name: str
    type: TypeExpr
    required: bool
    doc: str | None = None

    def __post_init__(self) -> None:
        """Check the parts."""
        _check_instance(self.name, str, f"a field name must be a string, not {self.name!r}")
        _check_instance(self.type, TypeExpr, f"field {self.name!r} needs a type expression, not {self.type!r}")
        _check_instance(self.required, bool, f"field {self.name!r}: required must be a bool")
        _check_doc(self.doc)


@dataclass(frozen=True)
class TypedDictDef:
    """A ``TypedDict`` named ``name`` with the given fields."""

    name: str
    fields: Sequence[Field]
    doc: str | None = None

    def __post_init__(self) -> None:
        """Check the parts and keep the fields as a tuple."""
        check_identifier(self.name, "a TypedDict name")
        fields = tuple(self.fields)
        seen: set[str] = set()
        for field in fields:
            _check_instance(field, Field, f"{self.name}: {field!r} is not a Field")
            if field.name in seen:
                msg = f"{self.name}: field {field.name!r} is defined twice"
                raise ValueError(msg)
            seen.add(field.name)
        _check_doc(self.doc)
        object.__setattr__(self, "fields", fields)

    @property
    def required_name(self) -> str:
        """The name bound to the functional ``TypedDict`` of required keys."""
        return f"_{self.name}Required"

    @property
    def optional_name(self) -> str:
        """The name bound to the functional ``TypedDict`` of optional keys."""
        return f"_{self.name}Optional"

    def bound_names(self) -> list[str]:
        """Every module-level name this definition binds."""
        names: list[str] = []
        if any(field.required for field in self.fields):
            names.append(self.required_name)
        if any(not field.required for field in self.fields):
            names.append(self.optional_name)
        names.append(self.name)
        return names

    def statements(self, context: RenderContext) -> list[ast.stmt]:
        """Build the helper assignments and the class."""
        statements: list[ast.stmt] = []
        bases: list[ast.expr] = []
        for name, required in ((self.required_name, True), (self.optional_name, False)):
            fields = [field for field in self.fields if field.required is required]
            if not fields:
                continue
            keys: list[ast.expr | None] = [ast.Constant(value=field.name) for field in fields]
            values = [field.type.to_ast(context) for field in fields]
            call = ast.Call(
                func=context.typing_name("TypedDict"),
                args=[ast.Constant(value=name), ast.Dict(keys=keys, values=values)],
                keywords=[] if required else [ast.keyword(arg="total", value=ast.Constant(value=False))],
            )
            statements.append(ast.Assign(targets=[ast.Name(id=name, ctx=ast.Store())], value=call))
            bases.append(ast.Name(id=name, ctx=ast.Load()))
        if not bases:
            bases.append(context.typing_name("TypedDict"))
        field_docs = [(field.name, field.doc) for field in self.fields if field.doc is not None]
        docstring = _docstring(self.doc, field_docs, _CLASS_INDENT)
        body: list[ast.stmt] = [ast.Pass()] if docstring is None else [_string_statement(docstring)]
        statements.append(ast.ClassDef(name=self.name, bases=bases, keywords=[], body=body, decorator_list=[]))
        return statements


@dataclass(frozen=True)
class AliasDef:
    """A type alias, ``name = type``. A doc follows it as a string statement."""

    name: str
    type: TypeExpr
    doc: str | None = None

    def __post_init__(self) -> None:
        """Check the parts."""
        check_identifier(self.name, "an alias name")
        _check_instance(self.type, TypeExpr, f"alias {self.name} needs a type expression, not {self.type!r}")
        _check_doc(self.doc)

    def bound_names(self) -> list[str]:
        """Every module-level name this definition binds."""
        return [self.name]

    def statements(self, context: RenderContext) -> list[ast.stmt]:
        """Build the assignment and its doc."""
        target = ast.Name(id=self.name, ctx=ast.Store())
        statements: list[ast.stmt] = [ast.Assign(targets=[target], value=self.type.to_ast(context))]
        if self.doc is not None:
            statements.append(_string_statement(self.doc))
        return statements


Definition = Union[TypedDictDef, AliasDef]


@dataclass(frozen=True)
class Module:
    """A module: an optional docstring, the ``typing`` import, then the definitions in order."""

    definitions: Sequence[Definition]
    doc: str | None = None

    def __post_init__(self) -> None:
        """Check the parts and keep the definitions as a tuple."""
        definitions = tuple(self.definitions)
        for definition in definitions:
            _check_instance(
                definition, (TypedDictDef, AliasDef), f"{definition!r} is not a TypedDictDef or an AliasDef"
            )
        _check_doc(self.doc)
        object.__setattr__(self, "definitions", definitions)


def _string_statement(text: str) -> ast.Expr:
    return ast.Expr(value=ast.Constant(value=text))


def _indent_continuation(text: str, indent: str) -> str:
    """Indent every line after the first that has content."""
    first, *rest = text.split("\n")
    return "\n".join([first, *[indent + line if line else line for line in rest]])


def _docstring(doc: str | None, field_docs: list[tuple[str, str]], indent: str) -> str | None:
    """Compose the docstring value: the doc, then a definition list of field docs.

    ``ast.unparse`` prints the value as it is, so lines after the first carry the indentation of the
    body they sit in, and a docstring of several lines ends on a line of its own.
    """
    paragraphs = [] if doc is None else [doc]
    if field_docs:
        entries = [_indent_continuation(f"{name}: {text}", "    ") for name, text in field_docs]
        paragraphs.append("\n".join(entries))
    if not paragraphs:
        return None
    text = "\n\n".join(paragraphs)
    if "\n" not in text:
        return text
    return _indent_continuation(text, indent) + "\n" + indent


def to_ast(module: Module) -> ast.Module:
    """Build the ``ast.Module`` for ``module``, with locations filled in so that it compiles.

    Raises ``ValueError`` when two definitions bind the same name, or a definition shadows a name
    the module uses from ``typing`` or the builtins.
    """
    bound = [(index, name) for index, d in enumerate(module.definitions) for name in d.bound_names()]
    names = [name for _, name in bound]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        msg = f"names bound more than once: {', '.join(duplicates)}"
        raise ValueError(msg)

    context = RenderContext()
    statements: list[ast.stmt] = []
    for index, definition in enumerate(module.definitions):
        context.unbound = frozenset(name for at, name in bound if at >= index)
        statements.extend(definition.statements(context))

    shadowed = sorted(set(names) & (context.typing_names | context.builtin_names))
    if shadowed:
        msg = f"definitions shadow names the module uses: {', '.join(shadowed)}"
        raise ValueError(msg)

    head: list[ast.stmt] = []
    docstring = _docstring(module.doc, [], "")
    if docstring is not None:
        head.append(_string_statement(docstring))
    if context.typing_names:
        aliases = [ast.alias(name=name) for name in sorted(context.typing_names)]
        head.append(ast.ImportFrom(module="typing", names=aliases, level=0))
    return ast.fix_missing_locations(ast.Module(body=[*head, *statements], type_ignores=[]))


def render(module: Module) -> str:
    """Print ``module`` with ``ast.unparse``, ending in exactly one newline."""
    return ast.unparse(to_ast(module)).rstrip("\n") + "\n"
