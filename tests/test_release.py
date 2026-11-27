# Copyright 2026 Captain James
# SPDX-License-Identifier: Apache-2.0
"""The release checks map a tag to the package version and find that version's changelog section."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import release

CHANGELOG = """# Changelog

Preamble.

## Unreleased

## [0.2.0] - 2026-12-01

### Added

- Something new.

## [0.1.0a1] - 2026-11-26

### Added

- The first release.

[0.2.0]: https://example.invalid/0.2.0
"""


class VersionFromTagTest(unittest.TestCase):
    def test_a_final_release(self) -> None:
        self.assertEqual(release.version_from_tag("v1.2.3"), "1.2.3")

    def test_pre_releases(self) -> None:
        cases = {
            "v0.1.0-alpha.1": "0.1.0a1",
            "v0.1.0-beta.2": "0.1.0b2",
            "v10.20.30-rc.0": "10.20.30rc0",
        }
        for tag, version in cases.items():
            with self.subTest(tag=tag):
                self.assertEqual(release.version_from_tag(tag), version)

    def test_refuses_a_tag_that_is_not_a_release(self) -> None:
        for tag in (
            "0.1.0",
            "v0.1",
            "v0.1.0a1",
            "v0.1.0-alpha",
            "v0.1.0-alpha.01",
            "v01.1.0",
            "v0.1.0-dev.1",
            "v0.1.0-alpha.1\n",
            "v0.1.0-alpha.1 ",
            "refs/tags/v0.1.0",
        ):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                release.version_from_tag(tag)


class PrereleaseTest(unittest.TestCase):
    def test_pre_releases_and_final_releases(self) -> None:
        cases = {"0.1.0a1": True, "0.1.0b2": True, "1.0.0rc1": True, "1.0.0": False, "10.2.3": False}
        for version, expected in cases.items():
            with self.subTest(version=version):
                self.assertIs(release.is_prerelease(version), expected)


class ChangelogSectionTest(unittest.TestCase):
    def test_returns_the_body_of_a_section_followed_by_another(self) -> None:
        self.assertEqual(release.changelog_section(CHANGELOG, "0.2.0"), "### Added\n\n- Something new.")

    def test_the_last_section_ends_before_link_definitions(self) -> None:
        self.assertEqual(release.changelog_section(CHANGELOG, "0.1.0a1"), "### Added\n\n- The first release.")

    def test_refuses_a_missing_version(self) -> None:
        with self.assertRaisesRegex(ValueError, r"## \[0\.3\.0\]"):
            release.changelog_section(CHANGELOG, "0.3.0")

    def test_a_version_is_matched_whole_not_as_a_prefix(self) -> None:
        with self.assertRaises(ValueError):
            release.changelog_section(CHANGELOG, "0.1.0")

    def test_refuses_an_empty_section(self) -> None:
        with self.assertRaisesRegex(ValueError, "empty"):
            release.changelog_section("## [1.0.0] - 2026-01-01\n\n## [0.9.0] - 2025-01-01\n\n- x\n", "1.0.0")


class ProjectVersionTest(unittest.TestCase):
    def test_reads_the_project_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pyproject.toml"
            path.write_text('[project]\nname = "x"\nversion = "0.1.0a1"\n', encoding="utf-8")
            self.assertEqual(release.project_version(path), "0.1.0a1")


class CheckTagTest(unittest.TestCase):
    def test_the_command_line_refuses_a_tag_for_another_version(self) -> None:
        self.assertEqual(release.main(["check", "v99.0.0"]), 1)

    def test_the_command_line_refuses_a_malformed_tag(self) -> None:
        self.assertEqual(release.main(["check", "main"]), 1)


if __name__ == "__main__":
    unittest.main()
