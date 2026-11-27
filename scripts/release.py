# Copyright 2026 Captain James
# SPDX-License-Identifier: Apache-2.0
"""Release checks: a tag names the package version, and the changelog has that version's section."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def version_from_tag(tag: str) -> str:
    """Return the PEP 440 version a release tag names."""
    raise NotImplementedError(tag)


def is_prerelease(version: str) -> bool:
    """Return whether a PEP 440 version from :func:`version_from_tag` is a pre-release."""
    raise NotImplementedError(version)


def changelog_section(text: str, version: str) -> str:
    """Return the body of the changelog section for ``version``."""
    raise NotImplementedError(text, version)


def project_version(pyproject: Path) -> str:
    """Return ``project.version`` from a ``pyproject.toml``."""
    raise NotImplementedError(pyproject)


def main(argv: list[str]) -> int:
    """Run a release check from the command line; return the exit status."""
    raise NotImplementedError(argv)
