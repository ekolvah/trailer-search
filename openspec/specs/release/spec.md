# release Specification

## Purpose
Delivers every merged `feat` or `fix` to consumers as a tagged release without a manual version bump, and keeps
every place that states the version in agreement.

## Requirements

### Requirement: Version places agree
The `pyproject.toml` project version and the tag on the `README.md` install line SHALL equal the version recorded
for `.` in `.release-please-manifest.json`; the repository `test` SHALL fail otherwise.

#### Scenario: Places match the manifest
- **WHEN** the manifest, `pyproject.toml` and the `README.md` install tag state the same version
- **THEN** the version drift test passes

#### Scenario: A place lags the manifest
- **WHEN** the manifest states a version that `pyproject.toml` or the `README.md` install tag does not
- **THEN** the version drift test fails naming the lagging place

### Requirement: Conventional PR title
A pull request into `main` SHALL carry a title of type `feat`, `fix`, `docs`, `test`, `refactor` or `chore`, and the
`pr-title` check SHALL fail otherwise.

#### Scenario: Title without a type
- **WHEN** a pull request is titled `auto release`
- **THEN** the `pr-title` check fails and the PR cannot merge

### Requirement: Release from merged commits
After a `fix` or `feat` commit lands on `main`, the release workflow SHALL keep a release PR that bumps the patch
or minor version in every version place and `CHANGELOG.md`; the release PR SHALL merge once its required checks
pass without the person's approval, and its merge SHALL create the tag `v<version>` and a GitHub Release.

#### Scenario: First release after a fix
- **WHEN** the release workflow is dispatched on `main` whose only `feat`/`fix` commit since `v0.2.0` is
  `fix: accept-release-year`
- **THEN** a release PR proposes `0.2.1`, changes only the manifest, `pyproject.toml`, `README.md` and
  `CHANGELOG.md`, and after it merges the tag `v0.2.1` exists
