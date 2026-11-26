"""The plain-GraphQL emitter and its command line."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support import FIXTURES, SRC, assert_golden
from wesley_python import syntax
from wesley_python.emit import IRError, module_from_ir

GOLDEN_CASES = {
    "hello.ir.json": "emit_hello.py",
    "plain.ir.json": "emit_plain.py",
    "extensions.ir.json": "emit_extensions.py",
}


def _load(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _cli(*args: str, stdin: str = "", hash_seed: str = "0") -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, PYTHONPATH=str(SRC), PYTHONHASHSEED=hash_seed)
    return subprocess.run(  # noqa: S603 - runs this interpreter on this package
        [sys.executable, "-m", "wesley_python", *args],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _ir(*types: dict[str, object]) -> dict[str, object]:
    return {"version": "1.0.0", "types": list(types)}


def _object(name: str, *fields: dict[str, object]) -> dict[str, object]:
    return {"name": name, "kind": "OBJECT", "directives": {}, "fields": list(fields)}


def _field(name: str, base: str, **type_: object) -> dict[str, object]:
    reference: dict[str, object] = {"base": base, "nullable": False, "isList": False}
    reference.update(type_)
    return {"name": name, "type": reference, "directives": {}}


class GoldenTest(unittest.TestCase):
    def test_fixtures_match_goldens(self) -> None:
        for fixture, golden in GOLDEN_CASES.items():
            with self.subTest(fixture=fixture):
                assert_golden(self, golden, syntax.render(module_from_ir(_load(fixture))))


class MappingTest(unittest.TestCase):
    def _render(self, ir: dict[str, object]) -> str:
        return syntax.render(module_from_ir(ir))

    def test_scalars(self) -> None:
        text = self._render(
            _ir(
                _object(
                    "T",
                    _field("s", "String"),
                    _field("i", "ID"),
                    _field("n", "Int"),
                    _field("f", "Float"),
                    _field("b", "Boolean"),
                    _field("c", "Custom"),
                ),
            ),
        )
        self.assertIn("{'s': str, 'i': str, 'n': int, 'f': float, 'b': bool, 'c': Any}", text)

    def test_nullable_field_is_required_with_none(self) -> None:
        text = self._render(_ir(_object("T", _field("a", "Int", nullable=True))))
        self.assertIn("TypedDict('_TRequired', {'a': Union[int, None]})", text)
        self.assertNotIn("total=False", text)

    def test_list_item_nullability(self) -> None:
        text = self._render(
            _ir(
                _object(
                    "T",
                    _field("a", "Int", isList=True, listItemNullable=False),
                    _field("b", "Int", isList=True, listItemNullable=True),
                    _field("c", "Int", isList=True),
                    _field("d", "Int", isList=True, nullable=True, listItemNullable=False),
                ),
            ),
        )
        self.assertIn(
            "{'a': List[int], 'b': List[Union[int, None]], 'c': List[Union[int, None]], "
            "'d': Union[List[int], None]}",
            text,
        )

    def test_enum_is_a_literal_alias(self) -> None:
        enum = {"name": "E", "kind": "ENUM", "directives": {}, "enumValues": ["A", "B"]}
        self.assertIn("E = Literal['A', 'B']", self._render(_ir(enum)))

    def test_directives_are_ignored(self) -> None:
        plain = _ir(_object("T", _field("a", "Int")))
        decorated = _ir(
            {
                "name": "T",
                "kind": "OBJECT",
                "directives": {"wes_table": {"name": "t"}},
                "fields": [
                    {
                        "name": "a",
                        "type": {"base": "Int", "nullable": False, "isList": False},
                        "directives": {"optional": True, "wes_pk": True},
                    },
                ],
            },
        )
        self.assertEqual(self._render(plain), self._render(decorated))


class InvalidIRTest(unittest.TestCase):
    def test_other_ir_versions_are_refused(self) -> None:
        for version in ("2.0.0", "1.0", None):
            with self.subTest(version=version), self.assertRaisesRegex(IRError, "1.0.0"):
                module_from_ir({"version": version, "types": []})

    def test_malformed_ir_is_refused_with_a_path(self) -> None:
        cases: list[tuple[object, str]] = [
            ([], "IR"),
            ({"version": "1.0.0"}, "types"),
            (_ir({"name": "T", "kind": "THING", "directives": {}}), r"types\[0\]\.kind"),
            (_ir(_object("T", {"name": "a", "directives": {}})), r"types\[0\]\.fields\[0\]\.type"),
            (_ir(_object("T", _field("a", "Int", nullable="no"))), r"nullable"),
            (_ir({"name": "E", "kind": "ENUM", "directives": {}, "enumValues": []}), "enumValues"),
            (_ir({"name": "class", "kind": "OBJECT", "directives": {}, "fields": []}), "class"),
        ]
        for ir, pattern in cases:
            with self.subTest(pattern=pattern), self.assertRaisesRegex(ValueError, pattern):
                syntax.render(module_from_ir(ir))


class CommandLineTest(unittest.TestCase):
    def test_emit_reads_stdin_and_writes_stdout(self) -> None:
        stdin = (FIXTURES / "plain.ir.json").read_text(encoding="utf-8")
        result = _cli("emit", stdin=stdin)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, syntax.render(module_from_ir(_load("plain.ir.json"))))
        self.assertEqual(result.stderr, "")

    def test_emit_reads_and_writes_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.py"
            result = _cli("emit", "--ir", str(FIXTURES / "hello.ir.json"), "--out", str(out))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(out.read_bytes(), syntax.render(module_from_ir(_load("hello.ir.json"))).encode())

    def test_output_is_identical_across_hash_seeds(self) -> None:
        stdin = (FIXTURES / "extensions.ir.json").read_text(encoding="utf-8")
        outputs = {_cli("emit", stdin=stdin, hash_seed=seed).stdout for seed in ("0", "1", "12345")}
        self.assertEqual(len(outputs), 1)

    def test_wrong_ir_version_exits_1_with_a_message(self) -> None:
        result = _cli("emit", stdin=json.dumps({"version": "2.0.0", "types": []}))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("1.0.0", result.stderr)
        self.assertIn("2.0.0", result.stderr)

    def test_invalid_json_exits_1(self) -> None:
        result = _cli("emit", stdin="{not json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("JSON", result.stderr)

    def test_missing_input_file_exits_1(self) -> None:
        result = _cli("emit", "--ir", str(FIXTURES / "does-not-exist.json"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("does-not-exist.json", result.stderr)


if __name__ == "__main__":
    unittest.main()
