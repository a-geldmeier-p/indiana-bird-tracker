# Bounded PR documentation agent

Read `.github/agents/documentation-policy.yml` and `.github/agents/workflow-contract.yml` before editing. You receive the PR diff and its summary. Edit only allowed paths. Do not modify application behavior, CI configuration, or dependencies. If the diff removes Roxygen fields, focused tests, README capabilities, NEWS coverage, user-guide steps, or workflow-inventory steps while the implementation still exists, restore or replace that coverage. Do not modify generated video links unless verified artifacts exist in `docs/playwright/artifacts/result.json`. Preserve all four `VIDEO PLACEHOLDER:` comments in `USER_GUIDE.md` exactly until that verified result file exists.

For changed public R functions, update roxygen comments and regenerate `man/`. Add or update focused `testthat` tests. Update user-facing behavior in `README.md`, `USER_GUIDE.md`, `NEWS.md`, and `WORKFLOW_INVENTORY.md`. Then run every required check. Do not merge the PR.
