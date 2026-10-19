# Self-documenting pull requests: complete runbook

This document explains what happens after a pull request (PR) is opened in Indiana Bird Tracker, why each stage exists, what it needs, and how to diagnose it. The automation can update documentation, tests, and Roxygen, but it never merges a PR or changes application behavior on its own.

## What must already be configured

1. The `Self-documenting PR` workflow is on the default branch.
2. A repository secret named `OPENAI_API_KEY` contains a valid OpenAI project key.
3. Branch protection requires pull requests and the current workflow checks.
4. GitHub Actions is enabled.
5. R 4.4.3-compatible dependencies are available from the configured RSPM.

The current workflow performs the OpenAI documentation phase and then records Playwright tutorial videos directly in GitHub Actions. Verified recordings are copied into `docs/playwright/artifacts/`, written into the manifest, and embedded in the user guide before one bot commit is pushed.

## Complete PR sequence

```text
PR opened or updated
  -> validate-pr: identify the exact commit and reject fork write attempts
  -> preflight: install R, run tests, and smoke-test Shiny
  -> document: send the PR diff and documentation context to OpenAI
  -> validate and apply the bounded patch
  -> roxygen, R CMD check, documentation checks, and Shiny smoke test
  -> select videos from contract and changed app source paths
  -> record and publish selected tutorials through Playwright MCP
  -> commit only approved generated files and push to the PR branch
  -> a human reviews and merges
```

## 1. Opening or updating a PR

Opening a PR, pushing another commit to its branch, or reopening it triggers the workflow. GitHub supplies the PR number; the workflow obtains the exact head branch and commit so the agent documents the code actually under review.

The current `validate-pr` job rejects forked PRs; it does not generate a patch artifact for them. This prevents this write-capable workflow from proceeding on a fork.

## 2. `validate-pr`

This job uses GitHub's API to verify the PR and record its head branch. It does not run the app or call OpenAI. If it fails, check the PR number, repository name, and whether the PR comes from a fork. Do not bypass this protection by granting write access to untrusted code.

## 3. `preflight`

`preflight` runs on the PR branch and does not intentionally push changes. It installs R 4.4.3 and dependencies, installs the package with `R CMD INSTALL .`, runs `testthat::test_local()`, starts Shiny with temporary database/photo paths, and polls the local URL for HTTP 200.

This answers: “Does the application work before the agent changes anything?” The `document` job has `needs: [validate-pr, preflight]`, so it cannot start unless preflight succeeds. If Shiny never returns HTTP 200, inspect the startup log for a wrong app function, port mismatch, missing dependency, or a process that exited immediately.

## 4. What the documentation agent receives

The agent receives the PR diff from `gh pr diff`, the documentation policy, the current README, NEWS, user guide, workflow inventory, and the versioned prompt in `docs/agent-prompts/document-pr.md`. The API key comes from the `OPENAI_API_KEY` repository secret and is masked in logs.

## 5. What the agent may update

The agent audits every relevant area and may update only:

- Roxygen comments in `R/` and generated `man/` files;
- focused tests in `tests/testthat/` when PR behavior changed;
- `README.md`, `NEWS.md`, `USER_GUIDE.md`, and `WORKFLOW_INVENTORY.md`;
- `.github/agents/workflow-contract.yml` when the documented browser workflow changes.

The deterministic video publisher, not the model, updates the Playwright manifest and media links after real artifacts are verified. An app change does not force a meaningless edit to every document or test.

It may not change application behavior, dependencies, CI workflow definitions, policy files, or invent videos, links, screenshots, features, or test results. Every area is reviewed on every run, but a file changes only when the PR provides a truthful reason to change it.

## 6. Patch generation and validation

For an application change, the agent returns structured replacement-file contents. The client generates the unified patch locally and runs `git apply --check` before applying it. For other PRs, the agent can return a patch; the client attempts repair and then structured-content fallback if needed. Invalid output fails the job visibly. `git apply --whitespace=fix` fixes harmless whitespace but not corrupt patch structure.

## 7. Allow-list and post-agent validation

After applying the patch, changed paths are checked against the policy. The workflow then runs `roxygen2::roxygenise()`, verifies generated changes, runs `rcmdcheck::rcmdcheck()`, runs `scripts/check_docs.R`, updates the workflow inventory, and repeats the Shiny smoke test. Any failure prevents a bot commit.

## 8. Bot commit and human review

Only after all post-agent checks and selected recordings pass does the workflow configure its bot identity, commit allow-listed files, and push to the PR branch. A push made with the workflow's `GITHUB_TOKEN` does not normally trigger a second `pull_request` workflow run; the checks earlier in this job validate the generated files before the push. A human reviews the bot commit and merges according to branch protection. The agent never merges.

## 9. Playwright tutorial videos

Playwright runs after deterministic documentation checks succeed, using a temporary Shiny instance, temporary DuckDB, synthetic rows, and temporary photo folders. The selector records a contracted workflow when its script/heading/IDs changed, its video or poster is missing, or relevant application source files changed in the PR. A changed source file not mapped by the contract conservatively selects every workflow. The number of videos is not fixed. Verified recordings and diagnostics are also uploaded as a 30-day GitHub Actions artifact.

The contract defines each workflow's `source_paths`, `stable_ids`, heading, and scripted browser actions. `shared_source_paths` maps changes that can affect every workflow. The Action provides the PR-changed file list and one `TUTORIAL_BASE_URL`; the recorder substitutes that local URL into each selected script. The current workflow scripts are specific to this Shiny app, but the selector and recorder are reusable with another app's contract.

The publisher replaces a placeholder only after a real video has been copied to `docs/playwright/artifacts/` and recorded in `result.json` and the manifest. Newly contracted workflows receive placeholders automatically until a matching recording exists. If a recording is missing, never fabricate a link.

## 10. GitHub Pages

The Pages workflow publishes the Markdown user guide from trusted `main`. The PR agent edits source Markdown and media references; deployment happens only after merge. A Pages error saying “Get Pages site failed” means Pages has not been enabled with **Settings -> Pages -> Source: GitHub Actions**.

## Troubleshooting

**Awaiting approval:** Open **Actions**, open the pending run, choose **Review workflows**, and approve only trusted branches. This commonly occurs on a first run or when a job uses repository secrets.

**Agent does not start:** Confirm `preflight` passed, `document` declares `needs: [validate-pr, preflight]`, and `OPENAI_API_KEY` exists as a repository secret.

**API returns 401:** Create a new OpenAI project key and update the repository secret. Never paste the key into an issue, log, or chat.

**Patch is corrupt:** Read the final `git apply` error. Structured-file output is assembled into a patch locally; do not force-apply a failed patch.

**Checks are duplicated or stuck as Expected:** Remove stale check names from branch protection and add the exact job names from the current `Self-documenting PR` workflow.

**Bot cannot push:** A fork is intentionally rejected. For a protected same-repository branch, review its rule settings or have an authorized maintainer apply the generated changes; this workflow does not currently create a patch artifact.

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
