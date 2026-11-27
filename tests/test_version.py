# Copyright 2026 Captain James
# SPDX-License-Identifier: Apache-2.0
"""The package version has one value: pyproject.toml, ``__version__`` and the changelog agree."""

from __future__ import annotations

import unittest

import wesley_python
from scripts import release
from tests.support import ROOT


class VersionTest(unittest.TestCase):
    def test_dunder_version_is_the_project_version(self) -> None:
        self.assertEqual(wesley_python.__version__, release.project_version(ROOT / "pyproject.toml"))

    def test_the_changelog_has_a_section_for_the_project_version(self) -> None:
        version = release.project_version(ROOT / "pyproject.toml")
        text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertTrue(release.changelog_section(text, version))


if __name__ == "__main__":
    unittest.main()
