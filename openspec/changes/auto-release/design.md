## Context

See proposal.md — Why and Standard approach. The pinned reusable workflows already handle a release PR: at
`v3.34.1` `reusable-agent-review.yml` step "Detect a release PR" and `quality.yml` (same step, then
`if: steps.release.outputs.release != 'true'` on "Verify the PR links its issue") run `release_pr.py`, which
returns `no release-please-config.json at the base` while the config is absent and otherwise judges the PR by the
config's `extra-files`, the manifest and the changelog. The default-branch ruleset requires
`agent-process / quality` and `agent-review / agent-review` with `strict_required_status_checks_policy: true`;
`agent-process person approves` requires one approval (read with `gh api repos/ekolvah/trailer-search/rulesets/<id>`,
2026-11-18).

## Goals / Non-Goals

**Goals:** see proposal.md — What Changes.

**Non-Goals:** the distribution's `stable` fast-forward (no marketplace consumer here); repinning lampa-mediacenter;
a `__version__` attribute in the package.

## Decisions

- **`release-type: simple` with `extra-files`, not `python`.** The `python` strategy writes `pyproject.toml`, and
  `src/<pkg>/__init__.py` / `version.py` when present, implicitly (`src/strategies/python.ts` lines 85-132), while
  `release_pr.py` `_release_set` admits only the manifest, the changelog and `extra-files`: the release PR would be
  judged `pyproject.toml outside the release set`, then wait for the review and an issue link. `simple` plus
  `{"type": "toml", "path": "pyproject.toml", "jsonpath": "$.project.version"}` and
  `{"type": "generic", "path": "README.md"}` is the distribution's config, whose PR #523 changed only those
  files. Alternative: `python` plus the same `extra-files` — rejected, two writers of one place.
- **`bootstrap-sha` = `e4f34f4742a158bf2ea90434999686ed2bc61d9a` (`v0.2.0`).** `gh release list` is empty, so
  release-please finds no previous release; the manifest-releaser doc: "cause release-please to stop there for
  collecting changelog commits … once a release-please generated PR has been merged, this config value will be
  ignored". Without it the first PR collects every commit since the root, `feat` included, and proposes `0.3.0`.
  Alternative: `last-release-sha` — rejected, "never ignored: remove/change it once a good release PR is merged".
- **`detect-secrets` skips the `bootstrap-sha` line (found at implementation).** The edit-time hook flagged
  `release-please-config.json:4` as `Hex High Entropy String`; JSON allows no `pragma: allowlist secret` comment.
  `--exclude-lines '"bootstrap-sha": "[0-9a-f]{40}"'` exempts that one line shape, leaving the rest of the file
  scanned. Alternatives: `exclude:` of the whole file (wider); a `.secrets.baseline` (a new file to maintain).
- **`always-update: true`.** The doc: needed "if pull requests must not be out-of-date with the base branch",
  which the strict required-checks policy enforces.
- **This PR is titled `chore: auto-release`.** No library behaviour changes, and a `feat` would make the first
  release `0.3.0` instead of the `0.2.1` the fix warrants.
- **Workflows copy the distribution's**, minus the `stable` step: push to `main` releases a merged release PR
  (`skip-github-pull-request` on push, filtered to `paths: [.release-please-manifest.json]`, which every release PR
  moves; the nightly run also creates a missed release); the nightly cron and `workflow_dispatch` open or update the release PR, then
  `github-actions` approves it with `GITHUB_TOKEN` and `RELEASE_PLEASE_TOKEN` enables `--auto --squash`. The PAT is
  needed because "With the exception of `workflow_dispatch` and `repository_dispatch`, … other
  `GITHUB_TOKEN`-triggered events do not create workflow runs at all"
  (https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows,
  `pull_request` note), so the required checks would never run. A `github-actions` approval of a PAT-authored PR
  satisfies one required approval: distribution PR #523, author `ekolvah`, review `github-actions` `APPROVED`, state
  `MERGED` (`gh pr view 523 -R ekolvah/agent-process-distribution --json author,state,reviews`, 2026-11-18).
  Nightly rather than per push: each release PR update re-runs `quality` and `agent-review`, so several merges in a
  day cost one cycle; a fix waits at most a day, and `workflow_dispatch` releases at once.
- **`pr-title` is required by its own ruleset, created by the person.** The squash commit takes the PR title and
  release-please reads only its type. A separate ruleset leaves the installer-written `agent-process default branch`
  ruleset as `init` renders it. Rulesets need admin, and `gh api repos/ekolvah/trailer-search --jq .permissions`
  as `ekolvah-agent` prints `"admin":false` (2026-11-18).
- **`tests/test_version_drift.py` (new check).** Closes a listed place the release PR fails to move (a lost marker,
  a wrong `jsonpath`); a new place nobody lists stays uncaught, as with any list. The standard (release-please's
  `extra-files`) writes the places it is told about and verifies none; ADR 0031 D3 relies on such a test, but no
  file exists to copy at `v3.34.1`. The test reads the
  manifest, `pyproject.toml` (`tomllib`) and the version on the `README.md` line carrying
  `x-release-please-version`, and runs in `agent-process / quality` on every head, the release PR's included.

### Guards the release PR drops

`release_pr.py` lets the release PR skip the Claude review and the issue link, and `github-actions` replaces the
person's approval.

| Lost proof | Catcher actually reached |
|---|---|
| Review of the diff | `release_pr.py` in `agent-review / agent-review` on the release PR head: every line unchanged or changed only by the version |
| A version place left unbumped | `tests/test_version_drift.py` in `agent-process / quality` on the release PR head |
| Issue link | each `feat`/`fix` PR the changelog names was linked on its own head by `quality` |
| Person's look at `CHANGELOG.md` | none; a wrong but valid type shows in the release notes and the next `fix` corrects it |

New input `RELEASE_PLEASE_TOKEN` and the approval setting. A red run notifies whom the docs name: "Notifications
for scheduled workflows are sent to the user who initially created the workflow", and "You can subscribe to
notifications about workflow runs that you trigger"
(https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/notifications-for-workflow-runs).
The workflow file arrives in this PR's squash commit, authored by `ekolvah-agent`, and push runs are triggered by
the merging actor, so neither notice reaches the person.

| Failure | Where it shows | Catcher reaching the person |
|---|---|---|
| PAT expired, revoked, or lacking `Contents`/`Pull requests: write` | action or auto-merge step red | none (accepted risk, below); the docs say only "Upon reaching your token's expiration date, the token is automatically revoked" (https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/token-expiration-and-revocation), no notice to the person found |
| Actions not allowed to approve | approve step red; PR open, waiting for an approval | the open release PR, visible in the person's PR list |

## Risks / Trade-offs

- [An expired, revoked or under-scoped PAT stops releases with no notice to the person — the stall #12 describes] →
  accepted: the person's choice in plan review is to accept it or ask for a failure notice (e.g. an issue opened by
  the workflow), which would be a new mechanism (§VII). The first dispatched run (task 5.2) proves the token once.
- [Ruleset `agent-process person approves` (27309738) has `dismiss_stale_reviews_on_push: true` and
  `require_extra_approval_for_unattributed_changes: true`] → each nightly update re-approves in the same run, and
  the PAT author is the person; the distribution, whose PR #523 merged this way, has the same ruleset shape
  (`gh api repos/ekolvah/agent-process-distribution/rulesets/<id>` for "agent-process person approves":
  `dismiss_stale_reviews_on_push: true`, `require_extra_approval_for_unattributed_changes: true`,
  `required_approving_review_count: 1`, read 2026-11-18).
  Task 5.2 observes the merge here; if it is held, the person approves and an issue follows.
- [README marker in a `sh` block shows to readers] → a trailing shell comment, harmless when copied.

## Migration Plan

Person's steps: tasks 5.1 and 5.2. Rollback: revert the PR; tags and Releases already created stay.
