## 0. Delivery start

- [x] 0.1 Run `agent-process start_change auto-release --planner Claude --implementer Claude` (tracking issue 12); verify it exits 0 and prints the worktree path, then enter it with `EnterWorktree`.

## 1. RED

- [ ] 1.1 Add `tests/test_version_drift.py` with `test_version_places_match_manifest` (reads `.release-please-manifest.json`, `pyproject.toml` via `tomllib`, and the version on the `README.md` line carrying `x-release-please-version`) and `test_lagging_place_named` (the comparison on in-memory values names the lagging place); verify `agent-process check_red tests/test_version_drift.py::test_version_places_match_manifest` reports it failing, then commit RED.

## 2. Release config

- [ ] 2.1 Add `release-please-config.json` (`release-type: simple`, `include-component-in-tag: false`, `always-update: true`, `bootstrap-sha: e4f34f4742a158bf2ea90434999686ed2bc61d9a`, `extra-files` toml `pyproject.toml` `$.project.version` and generic `README.md`) and `.release-please-manifest.json` `{".": "0.2.0"}`; append `# x-release-please-version` to the `README.md` install line; verify `python -m pytest tests/test_version_drift.py` passes.

## 3. Workflows

- [ ] 3.1 Add `.github/workflows/release-please.yml` (distribution copy without the `stable` step: push, nightly cron, `workflow_dispatch`; `skip-github-pull-request` on push; approve with `GITHUB_TOKEN`, `gh pr merge --auto --squash` with `RELEASE_PLEASE_TOKEN`) and `.github/workflows/pr-title.yml` (`amannn/action-semantic-pull-request@v6`, types `feat fix docs test refactor chore`); verify `python -c "import yaml,sys;[yaml.safe_load(open(f)) for f in sys.argv[1:]]" .github/workflows/release-please.yml .github/workflows/pr-title.yml` exits 0.

## 4. Verify

- [ ] 4.1 Run `/simplify` and commit its edits.
- [ ] 4.2 Run `openspec validate --strict --all`; verify exit 0.
- [ ] 4.3 Run `pre-commit run --hook-stage manual --all-files --show-diff-on-failure`; verify exit 0.

## 5. Deliver

- [ ] 5.1 Confirm with the person that `RELEASE_PLEASE_TOKEN` is set (`gh secret list` shows it) and Actions may approve PRs; run `agent-process archive_change auto-release`, open the PR titled `chore: auto-release` with the report body, run `gh pr edit <PR> --title "auto release"` and verify the `pr-title` check fails, then `gh pr edit <PR> --title "chore: auto-release"` and verify it passes (an `edited` event re-runs only `pr-title`; the head does not move); run `gh pr merge <PR> --auto --squash` and `agent-process wait_for_pr <PR>`; verify the head settles with no open P0/P1 thread.
- [ ] 5.2 After merge: the person creates the ruleset `pr-title` requiring the `pr-title` context on `main`; take its id from `gh api repos/ekolvah/trailer-search/rulesets` and verify `gh api repos/ekolvah/trailer-search/rulesets/<id> --jq '.rules[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context'` prints `pr-title`. Run `gh workflow run release-please.yml`; verify a release PR proposing `0.2.1` changes only `.release-please-manifest.json`, `pyproject.toml`, `README.md` and `CHANGELOG.md`, its `agent-review` and `quality` pass with `release=true`, it auto-merges, `git ls-remote --tags origin v0.2.1` prints the tag and `gh release view v0.2.1` shows the Release.

## Scenario → test map

| Spec | Scenario | Test |
|---|---|---|
| release | Places match the manifest | `tests/test_version_drift.py::test_version_places_match_manifest` |
| release | A place lags the manifest | `tests/test_version_drift.py::test_lagging_place_named` |
| release | Title without a type | n/a: platform check; task 5.1 observes `pr-title` fail on the title `auto release`, task 5.2 reads back the ruleset requiring it |
| release | First release after a fix | n/a: GitHub Actions run; task 5.2 observes the `0.2.1` release PR, its auto-merge, the tag and `gh release view v0.2.1` |
