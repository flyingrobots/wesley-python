# Copyright 2026 Captain James
# SPDX-License-Identifier: Apache-2.0
"""Release checks: a tag names the package version, and the changelog has that version's section.

The release workflow runs ``python scripts/release.py check <tag>``, which prints the PEP 440
version the tag names and exits 1 unless ``pyproject.toml`` has that version and ``CHANGELOG.md``
has a non-empty ``## [<version>]`` section; ``python scripts/release.py notes <version>``, which
prints that section's body for the GitHub release; and ``python scripts/release.py upload-plan
<dist-dir> [<pypi-json>]``, which prints the built files PyPI does not have yet and exits 1 when
PyPI has a file with another digest.
"""

from __future__ import annotations

import hashlib
import json
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


def project_version(pyproject: Path) -> str:
    """Return ``project.version`` from a ``pyproject.toml``."""
    with pyproject.open("rb") as file:
        data = tomllib.load(file)
    version = data["project"]["version"]
    if not isinstance(version, str):
        message = f"project.version in {pyproject} is not a string"
        raise TypeError(message)
    return version


def published_digests(release: object) -> dict[str, str]:
    """Return the file name to SHA-256 map from a PyPI JSON API answer for one version.

    ``release`` is the decoded answer of ``https://pypi.org/pypi/<project>/<version>/json``; its
    ``urls`` list names every file of the version. An answer of another shape raises ``ValueError``.
    """
    urls = release.get("urls") if isinstance(release, dict) else None
    if not isinstance(urls, list):
        message = "the PyPI answer has no 'urls' list"
        raise ValueError(message)  # noqa: TRY004 - the answer is malformed data, not a wrong argument type
    digests: dict[str, str] = {}
    for entry in urls:
        name = entry.get("filename") if isinstance(entry, dict) else None
        found = entry.get("digests") if isinstance(entry, dict) else None
        sha256 = found.get("sha256") if isinstance(found, dict) else None
        if not isinstance(name, str) or not isinstance(sha256, str):
            message = f"the PyPI answer has a file without a name and SHA-256 digest: {entry!r}"
            raise ValueError(message)  # noqa: TRY004 - malformed data, as above
        digests[name] = sha256
    return digests


def files_to_upload(built: dict[str, str], published: dict[str, str]) -> list[str]:
    """Return, sorted, the built files PyPI does not have yet.

    ``built`` and ``published`` map file names to SHA-256 digests. A file PyPI has with the same
    digest is not uploaded again. A file PyPI has with another digest, or one this build did not
    make, raises ``ValueError``: PyPI never replaces a file, so the release cannot be completed.
    """
    foreign = sorted(set(published) - set(built))
    if foreign:
        message = f"PyPI has files this build did not make: {', '.join(foreign)}"
        raise ValueError(message)
    for name in sorted(set(published) & set(built)):
        if published[name] != built[name]:
            message = f"PyPI has {name} with SHA-256 {published[name]}, but this build made {built[name]}"
            raise ValueError(message)
    return sorted(set(built) - set(published))


def _upload_plan(dist: Path, answer: Path | None) -> list[str]:
    built = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in dist.iterdir() if path.is_file()}
    published = {} if answer is None else published_digests(json.loads(answer.read_text(encoding="utf-8")))
    return files_to_upload(built, published)


def _check(tag: str) -> str:
    version = version_from_tag(tag)
    declared = project_version(ROOT / "pyproject.toml")
    if declared != version:
        message = f"tag {tag} names version {version}, but pyproject.toml declares {declared}"
        raise ValueError(message)
    changelog_section((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), version)
    return version


USAGE = """\
usage: release.py check <tag>
       release.py notes <version>
       release.py upload-plan <dist-dir> [<pypi-json>]
"""


def _run(argv: list[str]) -> str | None:
    """Return the command's output, or None when the arguments are not a command."""
    command, *arguments = argv or [""]
    if command == "check" and len(arguments) == 1:
        return _check(arguments[0])
    if command == "notes" and len(arguments) == 1:
        return changelog_section((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), arguments[0])
    if command == "upload-plan" and len(arguments) in {1, 2}:
        answer = Path(arguments[1]) if len(arguments) == 2 else None  # noqa: PLR2004 - a directory and an answer
        return "".join(f"{name}\n" for name in _upload_plan(Path(arguments[0]), answer))
    return None


def main(argv: list[str]) -> int:
    """Run a release command; return the exit status: 0 done, 1 refused, 2 a usage error."""
    try:
        output = _run(argv)
    except ValueError as error:
        sys.stderr.write(f"release.py: {error}\n")
        return 1
    if output is None:
        sys.stderr.write(USAGE)
        return 2
    sys.stdout.write(output if output.endswith("\n") or not output else f"{output}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
