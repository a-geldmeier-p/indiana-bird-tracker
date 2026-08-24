# GitHub self-documenting agent workflow

This document describes the future automation for Indiana Bird Tracker. It is a design and implementation checklist; the local MVP does not enable GitHub, LLM, or Playwright automation yet.

## Desired PR flow

```text
Developer PR
    |
    v
Deterministic validation ----> Roxygen / tests / Shiny smoke check
    |
    v
Bounded documentation agent -> README, NEWS, USER_GUIDE, workflow inventory
    |
    v
Playwright MCP request ------> browser workflow videos and screenshots
    |
    v
Bot commit to PR branch ----> checks rerun
    |
    v
Assign human reviewer --------> developer reviews and merges
```

## Recommended repository layout

```text
.github/
  workflows/
    pr-check.yml                 # deterministic checks on every PR
    self-documenting-pr.yml      # bounded agent job, opt-in/manual first
  CODEOWNERS                     # assigns the human reviewer
  agents/
    documentation-policy.yml     # allowed files, limits, required checks
    workflow-contract.yml        # four workflows and stable IDs
docs/
  GITHUB_SELF_DOCUMENTING_AGENT.md
  agent-prompts/
    document-pr.md               # versioned prompt template
  playwright/
    manifest.yml                 # workflow -> video artifact mapping
    README.md                    # MCP adapter contract
scripts/
  check_docs.R                   # links, headings, placeholder validation
  update_news.R                  # deterministic NEWS entry helper
  update_workflow_inventory.R
```

## 1. Trigger and permissions

Start with `workflow_dispatch` and a trusted-branch `pull_request` trigger. Do not run write-capable automation on untrusted fork code with `pull_request_target`. Use a dedicated bot branch or the PR head branch only after checking out the exact PR commit.

The job should request the minimum permissions:

```yaml
permissions:
  contents: write       # only needed for the bot commit
  pull-requests: write  # comment and assign reviewer
  checks: read
```

Keep the LLM/API and Playwright MCP credentials in GitHub environment secrets. Never pass repository code, tokens, or user-uploaded photos to an external service by default.

## 2. Two-phase deterministic validation

The first job must pass before an agent can edit documentation. It checks application behavior, not documentation freshness:

1. Install the pinned R version and package dependencies.
2. Run `testthat::test_local()`.
3. Launch the app with temporary DuckDB/photo/reference paths and check an HTTP 200 response.

If preflight fails, comment the failure on the PR and stop. The documentation agent must not “fix” production code while documenting a failed PR. After the agent edits allowed documentation, the post-agent gate runs `R CMD check`, verifies that roxygen creates no additional changes, validates the documentation contract and workflow inventory, and repeats the Shiny smoke check.

## 3. Documentation agent contract

Give the agent a structured PR summary and the diff, not the entire repository history. The agent may edit only:

- roxygen comments in `R/` and generated `man/` files;
- `tests/testthat/`;
- `README.md`, `NEWS.md`, `USER_GUIDE.md`, and `WORKFLOW_INVENTORY.md`;
- `docs/playwright/manifest.yml` and generated media links.

The agent must:

1. Inventory exported functions changed by the PR and add/update roxygen parameters, return values, examples, and links.
2. Add non-UI tests for changed data/database behavior and UI-module tests for stable IDs and workflow states.
3. Update README setup, paths, limitations, and user-visible behavior.
4. Add one concise dated entry under the current `NEWS.md` development section.
5. Update the relevant step-by-step section in `USER_GUIDE.md`.
6. Update `WORKFLOW_INVENTORY.md` if a workflow, label, or input ID changes.
7. Run roxygenise, tests, documentation checks, and the UI smoke check again.

The agent should produce a short PR comment listing files changed, checks run, and any item requiring human review. It must not merge the PR.

## 4. Playwright MCP adapter

GitHub Actions should call a small, authenticated adapter rather than embedding MCP protocol logic in the R package. The adapter receives a bounded request such as:

```json
{
  "base_url": "http://127.0.0.1:PORT",
  "workflows": ["catalog", "record_sighting", "my_sightings", "dashboard"],
  "artifact_dir": "docs/playwright/artifacts",
  "commit_sha": "..."
}
```

The adapter runs only the documented browser steps, captures an MP4 or WebM plus a poster image, and returns a manifest with workflow name, run date, commit, browser version, and artifact paths. It must use temporary local DuckDB/photo/reference directories and synthetic data; never use the developer’s personal database or photos.

If MCP access is unavailable, preserve the video placeholder and write a clear PR comment. Do not fabricate a video link.

## 5. Commit and reviewer handoff

After all checks pass:

1. Configure the bot identity.
2. Commit only the generated documentation, tests, roxygen output, and Playwright artifacts to the PR branch.
3. Push the bot commit to the existing PR branch.
4. Re-run the full checks on the resulting commit.
5. Add the repository owner or configured maintainer through `CODEOWNERS`/GitHub reviewer assignment.
6. Comment a concise summary and leave the PR open for human review.

If the branch is protected or the PR comes from a fork, upload a patch artifact and ask the author to apply it instead of attempting a write. This avoids granting write access to untrusted code.

## 6. GitHub Pages publishing

Publish `USER_GUIDE.md` through a small documentation site (for example, MkDocs or Quarto) from a trusted `main`-branch workflow. The PR agent should update source Markdown and media references only; a separate Pages workflow builds and deploys the site after merge.

## Acceptance checklist

- [ ] PR preflight is deterministic and read-only.
- [ ] Agent edits are allow-listed and bounded.
- [ ] Roxygen, tests, README, NEWS, user guide, and workflow inventory are all checked.
- [ ] Playwright MCP uses temporary data and returns a manifest or an explicit unavailable result.
- [ ] Generated artifacts are reviewed before commit.
- [ ] Bot commits only after checks pass.
- [ ] A human reviewer is assigned; the agent never merges.
