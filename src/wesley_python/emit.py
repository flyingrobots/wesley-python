# Copyright 2026 Captain James
# SPDX-License-Identifier: Apache-2.0
"""Plain GraphQL: Wesley IR in, a :class:`~wesley_python.syntax.Module` of ``TypedDict`` classes out.

This target is generic. It reads every type in the IR and ignores every directive.

- ``OBJECT``, ``INPUT_OBJECT`` and ``INTERFACE`` become ``TypedDict`` classes. Every field is a required
  key: GraphQL nullability means a value may be ``null``, not that the key may be absent, so a
  nullable field is typed ``Union[T, None]``.
- ``ENUM`` becomes an alias of a ``Literal`` of its value names.
- ``UNION`` becomes an alias of a ``Union`` of its members.
- ``SCALAR`` declarations emit nothing. ``String`` and ``ID`` are ``str``, ``Int`` is ``int``,
  ``Float`` is ``float``, ``Boolean`` is ``bool``, and any other scalar is ``Any``.
- A list is ``List[...]``. Its items are nullable unless ``listItemNullable`` is ``false``, as in
  GraphQL, where ``[T]`` holds nullable items.

Types are emitted in IR order, except that a union alias moves to just after the last of its members,
because a type checker reads ``A = 'B'`` as a string and not as an alias. A reference to a type emitted
later inside a field or a subscript is a string forward reference.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from wesley_python.syntax import AliasDef, Definition, Field, Module, TypedDictDef
from wesley_python.types import (
    AnyValue,
    Bool,
    Float,
    Int,
    ListOf,
    Literal,
    NoneType,
    Ref,
    Str,
    TypeExpr,
    UnionOf,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = ["SUPPORTED_IR_VERSION", "IRError", "module_from_ir"]

SUPPORTED_IR_VERSION = "1.0.0"

_RECORD_KINDS = frozenset({"OBJECT", "INPUT_OBJECT", "INTERFACE"})
_KINDS = _RECORD_KINDS | {"ENUM", "UNION", "SCALAR"}

_BUILTIN_SCALARS: Mapping[str, TypeExpr] = {
    "String": Str(),
    "ID": Str(),
    "Int": Int(),
    "Float": Float(),
    "Boolean": Bool(),
}


class IRError(ValueError):
    """The input is not Wesley IR this target reads."""


def _object(value: object, path: str) -> dict[str, object]:
    if not isinstance(value, dict):
        msg = f"{path} must be an object"
        raise IRError(msg)
    return {str(key): item for key, item in value.items()}


def _get(record: dict[str, object], key: str, path: str) -> object:
    if key not in record:
        msg = f"{path}.{key} is missing"
        raise IRError(msg)
    return record[key]


def _string(value: object, path: str) -> str:
    if not isinstance(value, str):
        msg = f"{path} must be a string"
        raise IRError(msg)
    return value


def _boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        msg = f"{path} must be a boolean"
        raise IRError(msg)
    return value


def _array(value: object, path: str) -> list[object]:
    if not isinstance(value, list):
        msg = f"{path} must be an array"
        raise IRError(msg)
    return value


def _description(record: dict[str, object], path: str) -> str | None:
    if "description" not in record or record["description"] is None:
        return None
    return _string(record["description"], f"{path}.description")


def _strings(record: dict[str, object], key: str, path: str) -> list[str]:
    items = _array(_get(record, key, path), f"{path}.{key}")
    if not items:
        msg = f"{path}.{key} must not be empty"
        raise IRError(msg)
    return [_string(item, f"{path}.{key}[{index}]") for index, item in enumerate(items)]


class _Reader:
    """Turns IR records into definitions, knowing every declared type's kind."""

    def __init__(self, kinds: dict[str, str]) -> None:
        self.kinds = kinds

    def named(self, base: str) -> TypeExpr:
        if base in _BUILTIN_SCALARS:
            return _BUILTIN_SCALARS[base]
        kind = self.kinds.get(base, "SCALAR")
        return AnyValue() if kind == "SCALAR" else Ref(base)

    def reference(self, value: object, path: str) -> TypeExpr:
        record = _object(value, path)
        base = _string(_get(record, "base", path), f"{path}.base")
        nullable = _boolean(_get(record, "nullable", path), f"{path}.nullable")
        is_list = _boolean(_get(record, "isList", path), f"{path}.isList")
        result = self.named(base)
        if is_list:
            item_nullable = True
            if "listItemNullable" in record:
                item_nullable = _boolean(record["listItemNullable"], f"{path}.listItemNullable")
            result = ListOf(UnionOf(result, NoneType()) if item_nullable else result)
        return UnionOf(result, NoneType()) if nullable else result

    def field(self, value: object, path: str) -> Field:
        record = _object(value, path)
        name = _string(_get(record, "name", path), f"{path}.name")
        type_ = self.reference(_get(record, "type", path), f"{path}.type")
        return Field(name, type_, required=True, doc=_description(record, path))

    def definition(self, record: dict[str, object], name: str, kind: str, path: str) -> Definition | None:
        doc = _description(record, path)
        if kind in _RECORD_KINDS:
            raw = _array(record.get("fields", []), f"{path}.fields")
            fields = [self.field(item, f"{path}.fields[{index}]") for index, item in enumerate(raw)]
            return TypedDictDef(name, fields, doc=doc)
        if kind == "ENUM":
            values = _strings(record, "enumValues", path)
            return AliasDef(name, UnionOf(*(Literal(value) for value in values)), doc=doc)
        if kind == "UNION":
            members = _strings(record, "unionMembers", path)
            return AliasDef(name, UnionOf(*(Ref(member) for member in members)), doc=doc)
        return None


def _alias_order(items: list[tuple[Definition, set[str]]]) -> list[Definition]:
    """Order definitions so that each follows the definitions it depends on, keeping IR order otherwise.

    Each step takes the first definition, in IR order, whose dependencies in the module are all
    placed. Only a union alias has dependencies (its members): an alias must follow a type it names
    bare, while a forward reference in a ``TypedDict`` field is a string and needs no ordering.
    """
    names = {definition.name for definition, _ in items}
    pending = [(definition, depends & names) for definition, depends in items]
    placed: set[str] = set()
    ordered: list[Definition] = []
    while pending:
        ready = next((index for index, (_, depends) in enumerate(pending) if depends <= placed), None)
        if ready is None:
            cycle = ", ".join(sorted(definition.name for definition, _ in pending))
            msg = f"union members form a cycle among: {cycle}"
            raise IRError(msg)
        definition, _ = pending.pop(ready)
        placed.add(definition.name)
        ordered.append(definition)
    return ordered


def module_from_ir(ir: object) -> Module:
    """Build the module for a Wesley IR document (the parsed JSON of ``wesley schema lower --json``).

    Raises :class:`IRError` when the IR is malformed or its version is not ``1.0.0``, and
    ``ValueError`` when a type name cannot be a Python name.
    """
    root = _object(ir, "IR")
    version = root.get("version")
    if version != SUPPORTED_IR_VERSION:
        msg = f"unsupported IR version {version!r}: this target reads IR version {SUPPORTED_IR_VERSION}"
        raise IRError(msg)
    types = _array(_get(root, "types", "IR"), "IR.types")

    records: list[tuple[dict[str, object], str, str, str]] = []
    kinds: dict[str, str] = {}
    for index, value in enumerate(types):
        path = f"types[{index}]"
        record = _object(value, path)
        name = _string(_get(record, "name", path), f"{path}.name")
        kind = _string(_get(record, "kind", path), f"{path}.kind")
        if kind not in _KINDS:
            msg = f"{path}.kind {kind!r} is not one of {', '.join(sorted(_KINDS))}"
            raise IRError(msg)
        kinds[name] = kind
        records.append((record, name, kind, path))

    reader = _Reader(kinds)
    emitted: list[tuple[Definition, set[str]]] = []
    for record, name, kind, path in records:
        definition = reader.definition(record, name, kind, path)
        if definition is not None:
            members = _strings(record, "unionMembers", path) if kind == "UNION" else []
            emitted.append((definition, set(members)))
    return Module(
        _alias_order(emitted),
        doc=f"Generated by wesley-python from Wesley IR {SUPPORTED_IR_VERSION}. Do not edit.",
    )
