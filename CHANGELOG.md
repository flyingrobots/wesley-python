# Changelog

All notable changes to this project are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html). A heading names the package version as PEP 440 spells it (`0.1.0a1`); its git tag is the Semantic Versioning spelling (`v0.1.0-alpha.1`).

## Unreleased

## [0.1.0a1] - 2026-11-26

The first release, a pre-release published to PyPI as `wesley-python` 0.1.0a1 from the git tag `v0.1.0-alpha.1`.

### Added

- The package `wesley_python` (0.1.0a1), for Python 3.9 or later with no runtime dependencies (#1).
- A syntax API that builds modules as a standard-library `ast` tree and prints them with `ast.unparse`: type expressions in `wesley_python.types` (`Str`, `Int`, `Float`, `Bool`, `AnyValue`, `NoneType`, `Literal`, `ListOf`, `DictOf`, `Ref`, `UnionOf`) and definitions in `wesley_python.syntax` (`Field`, `TypedDictDef`, `AliasDef`, `Module`, `to_ast`, `render`). A `TypedDict` is written as functional-form required and `total=False` optional parts under one class, so keys such as `from` and optional keys work on Python 3.9 without `NotRequired` (flyingrobots/parley#121).
- A plain-GraphQL emitter, `python -m wesley_python emit [--ir FILE] [--out FILE]` (also installed as `wesley-python`), that reads Wesley IR version `1.0.0` and writes `TypedDict` classes for objects, inputs and interfaces, `Literal` aliases for enums and `Union` aliases for unions, ignoring every directive.
- Every alias is a real type alias on Python 3.9. The emitter places a union alias just after the last of its members, keeping IR order otherwise, and refuses union members that form a cycle; the syntax API refuses, with a `ValueError` naming both, an `AliasDef` whose whole type is a reference to a later definition, since `Result = 'Item'` is a string to a type checker. Forward references inside field types and subscripts are unchanged. An alias whose whole type is `None` is written `Literal[None]`, since `Null = None` binds a value rather than a type alias (review of #3).
- Golden tests whose modules are compiled, imported and type-checked by `mypy --strict --python-version 3.9`, with fixtures that must fail (a wrong `event` literal, a keyword key read as the wrong type, a missing required key); tests that the package imports only the standard library and builds no code from strings; and a determinism test across hash seeds.
- Strict ruff and mypy configuration, pinned development tools in `requirements-dev.txt`, git hooks in `scripts/hooks/`, and CI on Python 3.9 and 3.13.
- The repository, its license, and the rules for how the target generates code (flyingrobots/parley#116, flyingrobots/wesley#882).
- Packaging for PyPI: an SPDX `Apache-2.0` license with `LICENSE` and `NOTICE` in both the sdist and the wheel, classifiers, keywords and project URLs. `__version__`, `pyproject.toml` and this changelog agree, and a test fails if they do not (#4).
- A CI build check that builds the sdist and wheel, runs `twine check --strict`, checks that both contain `LICENSE` and `NOTICE`, and installs the wheel into fresh environments on Python 3.9 and 3.13 to run the command line and import the package (#4).
- A release workflow, `.github/workflows/release.yml`, run by pushing an annotated `v*` tag on `main`: it checks the tag against the package version and the changelog, runs every check, builds once, publishes to PyPI by trusted publishing after approval in the `pypi` environment, uploading only the files PyPI lacks and stopping on a file whose SHA-256 differs (so a partial upload can be completed; review of #5), verifies that the published version installs, and creates the GitHub release. `scripts/release.py` maps a tag such as `v0.1.0-alpha.1` to its PEP 440 version `0.1.0a1`. The procedure is in [RELEASING.md](RELEASING.md) (#4).

[0.1.0a1]: https://github.com/flyingrobots/wesley-python/releases/tag/v0.1.0-alpha.1
