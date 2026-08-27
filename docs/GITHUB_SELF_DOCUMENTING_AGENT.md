# Self-documenting pull requests: complete runbook

This document explains what happens after a pull request (PR) is opened in Indiana Bird Tracker, why each stage exists, what it needs, and how to diagnose it. The automation can update documentation, tests, and Roxygen, but it never merges a PR or changes application behavior on its own.

## What must already be configured

1. The `Self-documenting PR` workflow is on the default branch.
2. A repository secret named `OPENAI_API_KEY` contains a valid OpenAI project key.
3. Branch protection requires pull requests and the current workflow checks.
4. GitHub Actions is enabled.
5. R 4.4.3-compatible dependencies are available from the configured RSPM.

The current workflow performs the OpenAI documentation phase and then records Playwright tutorial videos directly in GitHub Actions. Videos remain downloadable workflow artifacts until a later publishing step copies verified files into the Pages source.

## Complete PR sequence

```text
PR opened or updated
  -> validate-pr: identify the exact commit and reject fork write attempts
  -> preflight: install R, run tests, and smoke-test Shiny
  -> document: send the PR diff and documentation context to OpenAI
  -> validate and apply the bounded patch
  -> roxygen, R CMD check, tests, documentation checks, and Shiny smoke test
  -> commit only approved generated files and push to the PR branch
  -> checks rerun; a human reviews and merges
```

## 1. Opening or updating a PR

Opening a PR, pushing another commit to its branch, or reopening it triggers the workflow. GitHub supplies the PR number; the workflow obtains the exact head branch and commit so the agent documents the code actually under review.

For a forked PR, the workflow must not push to the fork. It should upload a patch artifact or ask the author to apply the changes. This protects repository secrets from untrusted fork code.

## 2. `validate-pr`

This job uses GitHub's API to verify the PR and record its head branch. It does not run the app or call OpenAI. If it fails, check the PR number, repository name, and whether the PR comes from a fork. Do not bypass this protection by granting write access to untrusted code.

## 3. `preflight`

`preflight` runs on the exact PR commit and is read-only. It installs R 4.4.3 and dependencies, installs the package with `R CMD INSTALL .`, runs `testthat::test_local()`, starts Shiny with temporary database/photo paths, and polls the local URL for HTTP 200.

This answers: “Does the application work before the agent changes anything?” The `document` job has `needs: [validate-pr, preflight]`, so it cannot start unless preflight succeeds. If Shiny never returns HTTP 200, inspect the startup log for a wrong app function, port mismatch, missing dependency, or a process that exited immediately.

## 4. What the documentation agent receives

The agent receives the PR diff from `gh pr diff`, the documentation policy, the current README, NEWS, user guide, workflow inventory, and the versioned prompt in `docs/agent-prompts/document-pr.md`. The API key comes from the `OPENAI_API_KEY` repository secret and is masked in logs.

## 5. What the agent may update

The agent must review every relevant area and may update only:

- Roxygen comments in `R/` and generated `man/` files;
- focused tests in `tests/testthat/` when PR behavior changed;
- `README.md`, `NEWS.md`, `USER_GUIDE.md`, and `WORKFLOW_INVENTORY.md`;
- Playwright manifest/media links only when real artifacts exist.

It may not change application behavior, dependencies, CI workflow definitions, policy files, or invent videos, links, screenshots, features, or test results. Every area is reviewed on every run, but a file changes only when the PR provides a truthful reason to change it.

## 6. Patch generation and validation

The preferred response is a standard Git unified patch beginning with `diff --git`. The script removes accidental Markdown fences or `*** Begin Patch` wrappers and runs `git apply --check` before applying anything.

If the first patch is malformed, the script requests a corrected patch. If that is also malformed, it requests complete replacement file contents as structured JSON and generates the unified patch locally. Git validates the locally generated patch before applying it. If both attempts fail, the job fails visibly; it does not pass while pretending documentation was updated. `git apply --whitespace=fix` removes harmless trailing blank-line whitespace while still rejecting structurally corrupt patches.

## 7. Allow-list and post-agent validation

After applying the patch, changed paths are checked against the policy. The workflow then runs `roxygen2::roxygenise()`, verifies generated changes, runs `rcmdcheck::rcmdcheck()`, runs `scripts/check_docs.R`, updates the workflow inventory, and repeats the Shiny smoke test. Any failure prevents a bot commit.

## 8. Bot commit and human review

Only after all post-agent checks pass does the workflow configure its bot identity, commit allow-listed files, and push to the PR branch. That new commit triggers checks again. A human reviews the bot commit and merges according to branch protection. The agent never merges.

## 9. Playwright tutorial videos

Playwright runs after `document` succeeds, using a temporary Shiny instance, temporary DuckDB, synthetic rows, and temporary photo folders. It runs `catalog`, `record_sighting`, `my_sightings`, and `dashboard`, captures one video per workflow, and uploads the videos and diagnostics as a 30-day GitHub Actions artifact.

```json
{"base_url":"http://127.0.0.1:PORT","workflows":["catalog","record_sighting","my_sightings","dashboard"],"artifact_dir":"docs/playwright/artifacts","commit_sha":"CURRENT_COMMIT"}
```

The user-guide placeholders remain unchanged while videos exist only as temporary Actions artifacts. A later publication step may replace a placeholder only after a real video has been copied to `docs/playwright/artifacts/` and recorded in the manifest. If a recording is missing, never fabricate a link.

## 10. GitHub Pages

The Pages workflow publishes the Markdown user guide from trusted `main`. The PR agent edits source Markdown and media references; deployment happens only after merge. A Pages error saying “Get Pages site failed” means Pages has not been enabled with **Settings -> Pages -> Source: GitHub Actions**.

## Troubleshooting

**Awaiting approval:** Open **Actions**, open the pending run, choose **Review workflows**, and approve only trusted branches. This commonly occurs on a first run or when a job uses repository secrets.

**Agent does not start:** Confirm `preflight` passed, `document` declares `needs: [validate-pr, preflight]`, and `OPENAI_API_KEY` exists as a repository secret.

**API returns 401:** Create a new OpenAI project key and update the repository secret. Never paste the key into an issue, log, or chat.

**Patch is corrupt:** Read the final `git apply` error. The script performs a repair request and structured-content fallback; do not force-apply a failed patch.

**Checks are duplicated or stuck as Expected:** Remove stale check names from branch protection and add the exact job names from the current `Self-documenting PR` workflow.

**Bot cannot push:** For protected or fork branches, upload a patch artifact and ask the PR author to apply it instead of weakening protection.

## Acceptance checklist

- [ ] `validate-pr` passes.
- [ ] `preflight` passes before the agent starts.
- [ ] The agent receives the PR diff and current documentation context.
- [ ] Roxygen, focused tests, README, NEWS, user guide, and inventory are reviewed.
- [ ] The patch is validated and allow-listed.
- [ ] Post-agent checks pass.
- [ ] No fake video or poster links are created.
- [ ] The bot commit is reviewed by a human.
- [ ] The agent leaves the PR open and never merges it.
