# Changelog

All notable changes to this project are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- The package `wesley_python` (0.1.0), for Python 3.9 or later with no runtime dependencies (#1).
- A syntax API that builds modules as a standard-library `ast` tree and prints them with `ast.unparse`: type expressions in `wesley_python.types` (`Str`, `Int`, `Float`, `Bool`, `AnyValue`, `NoneType`, `Literal`, `ListOf`, `DictOf`, `Ref`, `UnionOf`) and definitions in `wesley_python.syntax` (`Field`, `TypedDictDef`, `AliasDef`, `Module`, `to_ast`, `render`). A `TypedDict` is written as functional-form required and `total=False` optional parts under one class, so keys such as `from` and optional keys work on Python 3.9 without `NotRequired` (flyingrobots/parley#121).
- A plain-GraphQL emitter, `python -m wesley_python emit [--ir FILE] [--out FILE]` (also installed as `wesley-python`), that reads Wesley IR version `1.0.0` and writes `TypedDict` classes for objects, inputs and interfaces, `Literal` aliases for enums and `Union` aliases for unions, ignoring every directive.
- Every alias is a real type alias on Python 3.9. The emitter places a union alias just after the last of its members, keeping IR order otherwise, and refuses union members that form a cycle; the syntax API refuses, with a `ValueError` naming both, an `AliasDef` whose whole type is a reference to a later definition, since `Result = 'Item'` is a string to a type checker. Forward references inside field types and subscripts are unchanged. An alias whose whole type is `None` is written `Literal[None]`, since `Null = None` binds a value rather than a type alias (review of #3).
- Golden tests whose modules are compiled, imported and type-checked by `mypy --strict --python-version 3.9`, with fixtures that must fail (a wrong `event` literal, a keyword key read as the wrong type, a missing required key); tests that the package imports only the standard library and builds no code from strings; and a determinism test across hash seeds.
- Strict ruff and mypy configuration, pinned development tools in `requirements-dev.txt`, git hooks in `scripts/hooks/`, and CI on Python 3.9 and 3.13.
- The repository, its license, and the rules for how the target generates code (flyingrobots/parley#116, flyingrobots/wesley#882).
