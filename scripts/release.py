# Copyright 2026 Captain James
# SPDX-License-Identifier: Apache-2.0
"""Release checks: a tag names the package version, and the changelog has that version's section.

The release workflow runs ``python scripts/release.py check <tag>``, which prints the PEP 440
version the tag names and exits 1 unless ``pyproject.toml`` has that version and ``CHANGELOG.md``
has a non-empty ``## [<version>]`` section; and ``python scripts/release.py notes <version>``,
which prints that section's body for the GitHub release.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent.parent

_NUMBER = r"(?:0|[1-9][0-9]*)"
_TAG = re.compile(
    rf"v(?P<release>{_NUMBER}\.{_NUMBER}\.{_NUMBER})(?:-(?P<label>alpha|beta|rc)\.(?P<number>{_NUMBER}))?",
)
_LABELS = {"alpha": "a", "beta": "b", "rc": "rc"}
_PRERELEASE = re.compile(rf"{_NUMBER}\.{_NUMBER}\.{_NUMBER}(?:a|b|rc){_NUMBER}")
_HEADING = re.compile(r"## \[(?P<version>[^\]]+)\](?: - \d{4}-\d{2}-\d{2})?")
_LINK_DEFINITION = re.compile(r"\[[^\]]+\]: \S+")


def version_from_tag(tag: str) -> str:
    """Return the PEP 440 version a release tag names.

    ``vX.Y.Z`` names ``X.Y.Z``, and ``vX.Y.Z-alpha.N``, ``-beta.N`` and ``-rc.N`` name ``X.Y.ZaN``,
    ``X.Y.ZbN`` and ``X.Y.ZrcN``. Any other tag raises ``ValueError``.
    """
    match = _TAG.fullmatch(tag)
    if match is None:
        message = f"{tag!r} is not a release tag (vX.Y.Z, optionally -alpha.N, -beta.N or -rc.N)"
        raise ValueError(message)
    label = match.group("label")
    if label is None:
        return match.group("release")
    return f"{match.group('release')}{_LABELS[label]}{match.group('number')}"


def is_prerelease(version: str) -> bool:
    """Return whether a PEP 440 version from :func:`version_from_tag` is a pre-release."""
    return _PRERELEASE.fullmatch(version) is not None


def changelog_section(text: str, version: str) -> str:
    """Return the body of the changelog section headed ``## [<version>]``.

    The body runs to the next ``## `` heading or the link reference definitions that end the file.
    A missing or empty section raises ``ValueError``.
    """
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        match = _HEADING.fullmatch(line.rstrip())
        if match is not None and match.group("version") == version:
            start = index + 1
            break
    if start is None:
        message = f"the changelog has no '## [{version}]' section"
        raise ValueError(message)
    body: list[str] = []
    for line in lines[start:]:
        if line.startswith("## ") or _LINK_DEFINITION.fullmatch(line.rstrip()):
            break
        body.append(line)
    section = "\n".join(body).strip()
    if not section:
        message = f"the changelog section '## [{version}]' is empty"
        raise ValueError(message)
    return section


def published_digests(release: object) -> dict[str, str]:
    """Return the file name to SHA-256 map from a PyPI JSON API answer for one version."""
    raise NotImplementedError(release)


def files_to_upload(built: dict[str, str], published: dict[str, str]) -> list[str]:
    """Return the built files PyPI does not have yet, refusing any file whose digest differs."""
    raise NotImplementedError(built, published)


def project_version(pyproject: Path) -> str:
    """Return ``project.version`` from a ``pyproject.toml``."""
    with pyproject.open("rb") as file:
        data = tomllib.load(file)
    version = data["project"]["version"]
    if not isinstance(version, str):
        message = f"project.version in {pyproject} is not a string"
        raise TypeError(message)
    return version


def _check(tag: str) -> str:
    version = version_from_tag(tag)
    declared = project_version(ROOT / "pyproject.toml")
    if declared != version:
        message = f"tag {tag} names version {version}, but pyproject.toml declares {declared}"
        raise ValueError(message)
    changelog_section((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), version)
    return version


def main(argv: list[str]) -> int:
    """Run a release check from the command line; return the exit status."""
    usage = "usage: release.py check <tag> | release.py notes <version>\n"
    if len(argv) != 2 or argv[0] not in {"check", "notes"}:  # noqa: PLR2004 - a command and its argument
        sys.stderr.write(usage)
        return 2
    command, argument = argv
    try:
        if command == "check":
            output = _check(argument)
        else:
            output = changelog_section((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), argument)
    except ValueError as error:
        sys.stderr.write(f"release.py: {error}\n")
        return 1
    sys.stdout.write(f"{output}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
