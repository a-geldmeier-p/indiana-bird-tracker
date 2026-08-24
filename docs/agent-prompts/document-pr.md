# Bounded PR documentation agent

Read `.github/agents/documentation-policy.yml` and `.github/agents/workflow-contract.yml` before editing. You receive the PR diff and its summary. Edit only allowed paths. Do not modify application behavior, CI configuration, dependencies, or generated video links unless the Playwright adapter returned real artifacts in `docs/playwright/artifacts/result.json`.

For changed public R functions, update roxygen comments and regenerate `man/`. Add or update focused `testthat` tests. Update user-facing behavior in `README.md`, `USER_GUIDE.md`, `NEWS.md`, and `WORKFLOW_INVENTORY.md`. Then run every required check. Do not merge the PR.
