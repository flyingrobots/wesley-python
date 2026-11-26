# Copyright 2026 Captain James
# SPDX-License-Identifier: Apache-2.0
"""Every golden module is checked by the real toolchain: compiled, imported and type-checked."""

from __future__ import annotations

import py_compile
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support import GOLDEN, TYPECHECK

# Each fixture that must fail, with the mypy error code it must fail with.
EXPECTED_FAILURES = {
    "bad_event.py": "typeddict-item",
    "bad_keyword_key.py": "assignment",
    "bad_missing_required.py": "typeddict-item",
    "bad_null_field.py": "typeddict-item",
    "bad_nullable_omitted.py": "typeddict-item",
}


def _goldens() -> list[Path]:
    return sorted(GOLDEN.glob("*.py"))


def _run_mypy(workdir: Path) -> list[str]:
    """Run mypy --strict for Python 3.9 over every file in ``workdir``; return its error lines."""
    config = workdir / "mypy.ini"
    config.write_text("[mypy]\n", encoding="utf-8")
    files = sorted(path.name for path in workdir.glob("*.py"))
    result = subprocess.run(  # noqa: S603 - runs mypy from this interpreter's environment
        [
            sys.executable,
            "-m",
            "mypy",
            "--strict",
            "--python-version",
            "3.9",
            "--config-file",
            str(config),
            "--cache-dir",
            str(workdir / ".mypy_cache"),
            "--no-error-summary",
            "--show-error-codes",
            *files,
        ],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in {0, 1}:
        msg = f"mypy did not run: {result.stdout}{result.stderr}"
        raise AssertionError(msg)
    return [line for line in result.stdout.splitlines() if ": error: " in line]


class GoldenToolchainTest(unittest.TestCase):
    def test_there_are_goldens(self) -> None:
        self.assertGreaterEqual(len(_goldens()), 5)

    def test_every_golden_compiles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for path in _goldens():
                with self.subTest(golden=path.name):
                    py_compile.compile(str(path), cfile=str(Path(tmp) / "out.pyc"), doraise=True)

    def test_every_golden_imports_on_this_python(self) -> None:
        for path in _goldens():
            with self.subTest(golden=path.name):
                runpy.run_path(str(path), run_name=path.stem)

    def test_required_and_optional_keys_at_runtime(self) -> None:
        namespace = runpy.run_path(str(GOLDEN / "syntax_messages.py"))
        window = namespace["Window"]
        self.assertEqual(window.__required_keys__, frozenset({"from"}))
        self.assertEqual(window.__optional_keys__, frozenset({"to"}))
        run_end = namespace["RunEnd"]
        self.assertEqual(
            run_end.__optional_keys__,
            frozenset({"window", "redactions", "ratio", "detail", "next"}),
        )


class MypyTest(unittest.TestCase):
    """mypy --strict, for Python 3.9, over the goldens and the fixtures that use them."""

    errors: list[str]

    @classmethod
    def setUpClass(cls) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            for path in [*_goldens(), *sorted(TYPECHECK.glob("*.py"))]:
                shutil.copy(path, workdir / path.name)
            cls.errors = _run_mypy(workdir)

    def _errors_in(self, name: str) -> list[str]:
        return [line for line in self.errors if line.startswith(f"{name}:")]

    def test_goldens_and_good_uses_are_clean(self) -> None:
        clean = [path.name for path in _goldens()] + ["uses_goldens.py"]
        for name in clean:
            with self.subTest(file=name):
                self.assertEqual(self._errors_in(name), [])

    def test_every_bad_fixture_fails_with_its_expected_error(self) -> None:
        on_disk = {path.name for path in TYPECHECK.glob("bad_*.py")}
        self.assertEqual(on_disk, set(EXPECTED_FAILURES))
        for name, code in EXPECTED_FAILURES.items():
            with self.subTest(file=name):
                errors = self._errors_in(name)
                self.assertTrue(errors, f"mypy accepted {name}")
                for line in errors:
                    self.assertIn(f"[{code}]", line)

    def test_wrong_event_literal_is_reported_on_the_event_key(self) -> None:
        (line,) = self._errors_in("bad_event.py")
        self.assertIn('"event"', line)
        self.assertIn("Literal['end']", line)


if __name__ == "__main__":
    unittest.main()
