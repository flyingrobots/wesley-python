# Releasing

A release is an annotated git tag on `main`. Pushing it runs [`.github/workflows/release.yml`](.github/workflows/release.yml), which checks the tag and the code, builds the distributions once, publishes them to PyPI after the owner approves, checks that PyPI serves them, and creates the GitHub release. Nothing is published from a laptop and no PyPI token exists: the workflow publishes by [trusted publishing](https://docs.pypi.org/trusted-publishers/).

## Versions and tags

The package version is the PEP 440 spelling in `pyproject.toml` (`0.1.0a1`); the tag is the Semantic Versioning spelling of the same version with a `v` (`v0.1.0-alpha.1`). `-alpha.N`, `-beta.N` and `-rc.N` map to `aN`, `bN` and `rcN`; `scripts/release.py` does the mapping and the release refuses a tag that does not name the version in `pyproject.toml`. `src/wesley_python/__init__.py` has the same `__version__`, and `CHANGELOG.md` has a `## [<version>] - <date>` section for it; the test suite fails when either disagrees.

## Prepare the release

Open a pull request that sets the version in `pyproject.toml` and `__version__`, and turns the changelog's `## Unreleased` into `## [<version>] - <date>` with an empty `## Unreleased` above it. Merge it with a merge commit once CI is green.

## Tag it

On an up-to-date `main`, make an annotated tag on the merged commit and push it. A lightweight tag is refused.

```sh
git switch main && git pull --ff-only
git tag -a v0.1.0-alpha.1 -m "wesley-python 0.1.0a1"
git push origin v0.1.0-alpha.1
```

The workflow can also be started by hand (`workflow_dispatch`), but only on a tag: a run on a branch is refused.

## What the workflow does

1. `gate` refuses a lightweight tag, a tag whose commit is not the one checked out, a tag that is not an ancestor of `origin/main`, a tag that does not name the `pyproject.toml` version, and a version without a changelog section. It then runs ruff, mypy and the full test suite on Python 3.13 and 3.9, builds the sdist and wheel, runs `twine check --strict`, checks that both contain `LICENSE`, `NOTICE` and `py.typed`, installs the wheel into fresh environments on 3.9 and 3.13 to run the command line, and uploads the distributions as the `dist` artifact.
2. `publish` waits for approval in the `pypi` environment. Approve it under the run's "Review deployments" button once the gate is green. It then publishes the `dist` artifact by trusted publishing. If PyPI already has that version, it skips publishing rather than failing.
3. `verify` polls PyPI (20 times, 15 seconds apart) until the version's JSON page answers, checks that PyPI's files have the same SHA-256 digests as the `dist` artifact, then installs `wesley-python==<version>` from PyPI into fresh environments on Python 3.9 and 3.13 (an exact pin installs a pre-release without `--pre`) and runs `python -m wesley_python emit --help`, `wesley-python emit --help` and an import that checks `__version__`.
4. `github-release` creates the GitHub release for the tag, marked as a pre-release for an `a`, `b` or `rc` version, with that version's changelog section as notes and the sdist and wheel attached.

If a later job fails, use "Re-run failed jobs" rather than re-running the whole workflow: the re-run reuses the gate's artifact, so `verify` still finds the digests PyPI has. A full re-run builds new files, which PyPI will not accept under a version it already has.

## The first release

PyPI has a pending trusted publisher for the project `wesley-python`: owner `flyingrobots`, repository `wesley-python`, workflow `release.yml`, environment `pypi`. The first successful upload creates the project on PyPI and turns the pending publisher into an ordinary one. Until then the name is not reserved, so release soon after the publisher is configured.

## The `pypi` environment

The repository's `pypi` environment has the owner as its required reviewer and admits only tags matching `v*`. Only the `publish` job uses it, and only that job has `id-token: write`; `github-release` alone has `contents: write`, and every other job reads.

## Yanking a release

A release on PyPI cannot be replaced: a version number, once uploaded, can never be uploaded again, even after deletion. To withdraw a broken release, yank it: on PyPI, open the project's "Manage" page, choose the release, and select "Yank", giving a reason. A yanked version stays downloadable by an exact pin (`wesley-python==<version>`) but is no longer chosen by a range. Then fix the problem and release a new version; record the yank and its reason in the changelog under the new version, and edit the GitHub release to say it was yanked.
