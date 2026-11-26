# Copyright 2026 Captain James
# SPDX-License-Identifier: Apache-2.0
"""Type expressions: the right-hand side of a field or an alias, built as ``ast`` nodes.

Each class describes one Python type and knows how to become an ``ast.expr``. Rendering records
which ``typing`` names it used, so the module imports exactly those.
"""

from __future__ import annotations

import ast
import keyword
from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from collections.abc import Iterable

LiteralValue = Union[str, int, bool]


def check_identifier(name: object, what: str) -> str:
    """Return ``name`` if it can be bound as a Python name; raise ``ValueError`` otherwise."""
    if not isinstance(name, str) or not name.isidentifier() or keyword.iskeyword(name):
        msg = f"{what} {name!r} is not a Python identifier"
        raise ValueError(msg)
    return name


class RenderContext:
    """What a type expression needs while it is rendered: imports to record, names not yet bound."""

    def __init__(self, unbound: Iterable[str] = ()) -> None:
        """Start with no imports; ``unbound`` are module names defined at or after this point."""
        self.typing_names: set[str] = set()
        self.builtin_names: set[str] = set()
        self.unbound: frozenset[str] = frozenset(unbound)

    def typing_name(self, name: str) -> ast.Name:
        """Build a name from ``typing`` and record it for the module's import."""
        self.typing_names.add(name)
        return ast.Name(id=name, ctx=ast.Load())

    def builtin_name(self, name: str) -> ast.Name:
        """Build a builtin type name and record it so that no definition may shadow it."""
        self.builtin_names.add(name)
        return ast.Name(id=name, ctx=ast.Load())


class TypeExpr:
    """A Python type expression."""

    def to_ast(self, context: RenderContext) -> ast.expr:
        """Build the expression, recording in ``context`` the names it uses."""
        raise NotImplementedError


def _subscript(value: ast.expr, items: list[ast.expr]) -> ast.Subscript:
    """``value[items]``; one item is the slice itself, several are a tuple."""
    index: ast.expr = items[0] if len(items) == 1 else ast.Tuple(elts=items, ctx=ast.Load())
    return ast.Subscript(value=value, slice=index, ctx=ast.Load())


@dataclass(frozen=True)
class Str(TypeExpr):
    """``str``."""

    def to_ast(self, context: RenderContext) -> ast.expr:
        """Build ``str``."""
        return context.builtin_name("str")


@dataclass(frozen=True)
class Int(TypeExpr):
    """``int``."""

    def to_ast(self, context: RenderContext) -> ast.expr:
        """Build ``int``."""
        return context.builtin_name("int")


@dataclass(frozen=True)
class Float(TypeExpr):
    """``float``."""

    def to_ast(self, context: RenderContext) -> ast.expr:
        """Build ``float``."""
        return context.builtin_name("float")


@dataclass(frozen=True)
class Bool(TypeExpr):
    """``bool``."""

    def to_ast(self, context: RenderContext) -> ast.expr:
        """Build ``bool``."""
        return context.builtin_name("bool")


@dataclass(frozen=True)
class AnyValue(TypeExpr):
    """``typing.Any``."""

    def to_ast(self, context: RenderContext) -> ast.expr:
        """Build ``Any``."""
        return context.typing_name("Any")


@dataclass(frozen=True)
class NoneType(TypeExpr):
    """``None``."""

    def to_ast(self, context: RenderContext) -> ast.expr:  # noqa: ARG002 - the interface's signature
        """Build ``None``."""
        return ast.Constant(value=None)


@dataclass(frozen=True)
class Literal(TypeExpr):
    """``typing.Literal[value]`` for one ``str``, ``int`` or ``bool``."""

    value: LiteralValue

    def __post_init__(self) -> None:
        """Refuse a value ``typing.Literal`` cannot hold."""
        if type(self.value) not in {str, int, bool}:
            msg = f"a Literal holds a str, int or bool, not {self.value!r}"
            raise TypeError(msg)

    def to_ast(self, context: RenderContext) -> ast.expr:
        """Build ``Literal[value]``."""
        return _subscript(context.typing_name("Literal"), [ast.Constant(value=self.value)])


@dataclass(frozen=True)
class ListOf(TypeExpr):
    """``typing.List[item]``."""

    item: TypeExpr

    def __post_init__(self) -> None:
        """Refuse an item that is not a type expression."""
        _check_type(self.item, "a list item")

    def to_ast(self, context: RenderContext) -> ast.expr:
        """Build ``List[item]``."""
        return _subscript(context.typing_name("List"), [self.item.to_ast(context)])


@dataclass(frozen=True)
class DictOf(TypeExpr):
    """``typing.Dict[str, value]``."""

    value: TypeExpr

    def __post_init__(self) -> None:
        """Refuse a value that is not a type expression."""
        _check_type(self.value, "a dict value")

    def to_ast(self, context: RenderContext) -> ast.expr:
        """Build ``Dict[str, value]``."""
        key = context.builtin_name("str")
        return _subscript(context.typing_name("Dict"), [key, self.value.to_ast(context)])


@dataclass(frozen=True)
class Ref(TypeExpr):
    """A named type defined in the module, or imported into it by the caller.

    A reference to a name the module defines later is a string forward reference, so the module
    imports at run time; every other reference is a plain name.
    """

    name: str

    def __post_init__(self) -> None:
        """Refuse a name that cannot be bound."""
        check_identifier(self.name, "a referenced type name")

    def to_ast(self, context: RenderContext) -> ast.expr:
        """Build ``Name`` or, for a definition not yet bound, ``'Name'``."""
        if self.name in context.unbound:
            return ast.Constant(value=self.name)
        return ast.Name(id=self.name, ctx=ast.Load())


@dataclass(frozen=True, init=False)
class UnionOf(TypeExpr):
    """``typing.Union[...]``.

    One member renders as itself. Members that are all literals render as one ``Literal[...]``.
    """

    members: tuple[TypeExpr, ...]

    def __init__(self, *members: TypeExpr) -> None:
        """Hold at least one member."""
        if not members:
            msg = "a union needs at least one member"
            raise ValueError(msg)
        for member in members:
            _check_type(member, "a union member")
        object.__setattr__(self, "members", tuple(members))

    def to_ast(self, context: RenderContext) -> ast.expr:
        """Build ``Union[...]``, ``Literal[...]`` or the single member."""
        if len(self.members) == 1:
            return self.members[0].to_ast(context)
        literals = [member for member in self.members if isinstance(member, Literal)]
        if len(literals) == len(self.members):
            values: list[ast.expr] = [ast.Constant(value=literal.value) for literal in literals]
            return _subscript(context.typing_name("Literal"), values)
        name = context.typing_name("Union")
        return _subscript(name, [member.to_ast(context) for member in self.members])


def _check_type(value: object, what: str) -> None:
    if not isinstance(value, TypeExpr):
        msg = f"{what} must be a type expression, not {value!r}"
        raise TypeError(msg)
