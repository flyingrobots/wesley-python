# wesley-python

A [Wesley](https://github.com/flyingrobots/wesley) target that emits stdlib-only Python: `TypedDict` models embeddable in a single-file module.

Wesley compiles GraphQL SDL into an intermediate representation (IR), and does nothing else: it attaches no meaning to any directive and runs no targets. Every output language is its own repository, a standalone program and library that reads the IR (`wesley schema lower --json`). This one is a **generic** target: it understands no directives and emits plain GraphQL, and it is the language tooling other targets (such as [wesley-parley](https://github.com/flyingrobots/wesley-parley)) render through. The decisions are recorded in flyingrobots/parley#116 and flyingrobots/wesley#882.

## Status

A first version (0.1.0, unreleased) exists: the package `wesley_python`, with a syntax API for building Python modules of `TypedDict` classes and type aliases, and a plain-GraphQL emitter on the command line. It reads IR version `1.0.0` as Wesley prints it today; the versioned IR contract is still flyingrobots/wesley#881. There is no `--fragment` mode, no marker-wrapped output and no generated header naming the schema hash yet (#1).

The package runs on Python 3.9 or later and imports nothing outside the standard library. Its generated modules do the same.

## Usage

### The command line

```sh
wesley schema lower --schema schema.graphql --json | python -m wesley_python emit > models.py
python -m wesley_python emit --ir ir.json --out models.py
```

`emit` reads Wesley IR JSON from `--ir` (standard input by default) and writes a module to `--out` (standard output by default). An IR whose `version` is not `1.0.0`, malformed IR or invalid JSON is an error: a message on standard error and exit status 1. Installing the package also installs the same command as `wesley-python`.

The emitter is generic: it ignores every directive. It maps GraphQL as follows.

| GraphQL | Python |
| --- | --- |
| `type`, `input`, `interface` | a `TypedDict`; every field is a required key |
| nullable field `T` | `Union[T, None]`: GraphQL null is a value, not an absent key |
| `[T!]`, `[T]` | `List[T]`, `List[Union[T, None]]` |
| `enum` | an alias of `Literal['A', 'B', ...]` of the value names |
| `union` | an alias of `Union[...]` of the members |
| `String`, `ID`, `Int`, `Float`, `Boolean` | `str`, `str`, `int`, `float`, `bool` |
| any other scalar | `Any` |

Types are written in IR order, except that a union alias moves to just after the last of its members: a type checker reads `A = 'B'` as a string, not as an alias, and Python 3.9 has no `typing.TypeAlias`. A reference to a type written later, inside a field or a subscript such as `List['B']`, is a string forward reference, so the module imports.

### The syntax API

Other targets build modules with the syntax API and print them with `render`. Optional keys, keys that are Python keywords and `Literal` values all work on Python 3.9.

```python
from wesley_python.syntax import Field, Module, TypedDictDef, render
from wesley_python.types import Int, Literal, Ref

module = Module(
    [
        TypedDictDef(
            "Window",
            [
                Field("from", Int(), required=True, doc="The first line, inclusive."),
                Field("to", Int(), required=False),
            ],
            doc="A range of line numbers.",
        ),
        TypedDictDef(
            "End",
            [
                Field("event", Literal("end"), required=True),
                Field("window", Ref("Window"), required=False),
            ],
        ),
    ]
)
print(render(module), end="")
```

prints, exactly as `ast.unparse` lays it out,

```text
from typing import Literal, TypedDict
_WindowRequired = TypedDict('_WindowRequired', {'from': int})
_WindowOptional = TypedDict('_WindowOptional', {'to': int}, total=False)

class Window(_WindowRequired, _WindowOptional):
    """A range of line numbers.

    from: The first line, inclusive.
    """
_EndRequired = TypedDict('_EndRequired', {'event': Literal['end']})
_EndOptional = TypedDict('_EndOptional', {'window': Window}, total=False)

class End(_EndRequired, _EndOptional):
    pass
```

- `wesley_python.types`: `Str()`, `Int()`, `Float()`, `Bool()`, `AnyValue()`, `NoneType()`, `Literal(value)` for a `str`, `int` or `bool`, `ListOf(item)`, `DictOf(value)` (string keys), `Ref(name)` for a type the module defines, and `UnionOf(*members)`. A union of one member prints as that member, and a union of literals prints as one `Literal[...]`.
- `wesley_python.syntax`: `Field(name, type, required, doc=None)`, `TypedDictDef(name, fields, doc=None)`, `AliasDef(name, type, doc=None)`, `Module(definitions, doc=None)`, `to_ast(module)` returning the `ast.Module`, and `render(module)` returning its source, ending in one newline.

How a `TypedDict` is written: `typing.NotRequired` is new in Python 3.11, and the class syntax cannot name a key such as `from`. So the required keys and the optional keys are each a functional-form `TypedDict`, the optional one `total=False`, and the class inherits from both; a side with no keys is left out, and a definition with no keys inherits from `TypedDict`. `ast.unparse` cannot print comments, so field docs go into the class docstring as a `name: doc` list, and an alias's doc is a string statement after it. The `from typing import ...` line names exactly the names used, sorted.

The caller orders the definitions; `render` keeps the given order. A reference to a later definition is a string forward reference, which is allowed inside a field type or a subscript but not as the whole type of an alias: `AliasDef('Result', Ref('Item'))` before `Item` is a `ValueError` naming both. An alias whose whole type is `None` is written `Name = Literal[None]`, because `Name = None` binds a value rather than an alias. A definition name must be a Python identifier; two definitions may not bind the same name (including the `_NameRequired` and `_NameOptional` helpers), and a definition may not shadow a `typing` or builtin name the module uses. These are `ValueError`s.

## Development

```sh
uv venv -p 3.9 .venv && uv pip install -p .venv -r requirements-dev.txt
git config --local core.hooksPath scripts/hooks
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -t .
.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy
```

`requirements-dev.txt` pins mypy and ruff exactly; they are development tools, not dependencies. The pre-commit hook runs ruff and mypy, and the pre-push hook runs the test suite. CI runs all of it on Python 3.9 and 3.13.

The goldens under `tests/golden/` are compared byte for byte, compiled with `py_compile`, imported, and type-checked by `mypy --strict --python-version 3.9` together with the fixtures under `tests/typecheck/`: the good uses must pass and each `bad_*.py` must fail with its expected error (a wrong `event` literal, a keyword key read as the wrong type, a missing required key). To rewrite the goldens after an intended change, run the suite with `WESLEY_PYTHON_UPDATE_GOLDENS=1` and review the diff.

## Where it comes from

The plan is issue #1 (transferred from flyingrobots/wesley#858). Its first consumer is Parley's vendorable Python writer (flyingrobots/parley#121).

## How it generates code

The output is built as a syntax tree of the target language and printed by that language's printer. There is no string templating and no regex anywhere in the generator.

| Concern | Choice |
| --- | --- |
| Written in | Python 3.9 or later, standard library only |
| Syntax tree | the standard library `ast` module |
| Printer | `ast.unparse` |
| Checked by | `py_compile` and a static type checker on every golden module, on the oldest and newest supported Python |

Rules every change keeps:

- **No code as strings.** A generated identifier, literal or comment enters the output as a node of the tree, never by concatenating source text. Escaping is the printer's job.
- **Golden output is checked by the real toolchain.** Every golden file is compiled or type-checked in CI by the toolchain named above, not only compared byte for byte.
- **Deterministic to the byte.** The same IR and options give the same bytes on every machine. CI runs the generator twice and compares.
- **The IR is the only input.** The target reads the published IR (flyingrobots/wesley#881) and never depends on Wesley's internals.

## License

Apache 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
