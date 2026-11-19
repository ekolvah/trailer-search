## Why

A merged fix reaches no consumer until someone bumps the version and pushes a tag by hand. Observed 2026-11-18:
`fix: accept-release-year` merged as `231d7ea` (PR #11), yet `pyproject.toml` says `version = "0.2.0"`, the
`README.md` install line pins `@v0.2.0`, and `git rev-parse v0.2.0^{commit}` prints `e4f34f4`, the commit before
it; `gh release list` prints nothing. lampa-mediacenter pins a tag, so it does not get the fix. The bump lived as a
task inside each change (series-season-trailer tasks 4.1, 6.3) and the #10 plan left it out: a "remember to" rule
with no gate.

## Standard approach

- release-please (`googleapis/release-please-action@v4`): reads Conventional Commits on `main`, keeps a release PR
  that bumps the version places and `CHANGELOG.md`, and tags `vX.Y.Z` with a GitHub Release when it merges —
  https://github.com/googleapis/release-please-action, manifest config and `bootstrap-sha`:
  https://github.com/googleapis/release-please/blob/main/docs/manifest-releaser.md
- `amannn/action-semantic-pull-request@v6` checks that the PR title, which becomes the squash commit, is a
  Conventional Commit — https://github.com/amannn/action-semantic-pull-request
- Prior art in the process source, chosen by the person (variant A, 2026-11-18):
  `ekolvah/agent-process-distribution` `.github/workflows/release-please.yml`, `pr-title.yml`,
  `release-please-config.json`, ADR 0030 (releases via release-please), 0031 (release PRs merge without the person),
  0047 (nightly release PR). Its release PR #523 (`chore(main): release 3.34.1`) changed only the manifest,
  `CHANGELOG.md` and the config's `extra-files`.

## What Changes

- `release-please-config.json` (`release-type: simple`, `extra-files` for `pyproject.toml` and `README.md`,
  `bootstrap-sha` at `v0.2.0`) and `.release-please-manifest.json` seeded at `0.2.0`.
- `README.md` install line carries the `x-release-please-version` marker.
- `.github/workflows/release-please.yml`: release on push to `main`, release PR opened or updated nightly and on
  `workflow_dispatch`; `github-actions` approves it and it auto-merges with `--squash`.
- `.github/workflows/pr-title.yml` and a person-created ruleset `pr-title` that requires its context.
- A test that every version place agrees with the manifest, so a release PR missing a place fails `quality`.
- `agent-review` and `agent-process / quality` need no change: the pinned reusable workflows (`@v3.34.1`) already
  run `release_pr.py`, which reads this repository's `release-please-config.json` at the PR's base.
- After merge the first release PR is `0.2.1` from `fix: accept-release-year`; this PR is titled `chore:` so it
  adds no bump of its own.

Out of scope: lampa-mediacenter repinning to the new tag (done in that repository); the distribution's `stable`
branch step.

## Capabilities

### New Capabilities
- `release`: version places agree; merged `feat`/`fix` commits reach a tagged release without manual steps.

### Modified Capabilities

## Impact

- Added: `.github/workflows/release-please.yml`, `.github/workflows/pr-title.yml`, `release-please-config.json`,
  `.release-please-manifest.json`, `tests/test_version_drift.py`.
- Edited: `README.md` (marker on the install line).
- Added by release-please on the first release PR, not by this change: `CHANGELOG.md`.
- Installer-managed files (`agent-process:managed` header: `.github/workflows/agent-process.yml`, `agent-review.yml`,
  `task-readings.yml`, `.claude/rules/agent-process.md`, the `openspec/config.yaml` block): none touched. No new
  file is rendered by `agent-process init` (its `init.py` at `v3.34.1` names no release-please path).
- New CI dependencies (§VII, approved by variant A): `googleapis/release-please-action@v4`,
  `amannn/action-semantic-pull-request@v6`. No Python dependency.
- Person, before merge: repository secret `RELEASE_PLEASE_TOKEN` (fine-grained PAT, Contents + Pull requests
  read/write on this repository); "Allow GitHub Actions to create and approve pull requests" on. Auto-merge is
  already on (`allow_auto_merge: true`). After merge: the `pr-title` ruleset.
