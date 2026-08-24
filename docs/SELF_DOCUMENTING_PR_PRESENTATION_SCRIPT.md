# Presentation Script: Indiana Bird Tracker Self-Documenting PRs

## Opening

“Today I’m going to explain how Indiana Bird Tracker turns a normal GitHub pull request into a documented, tested, and reviewable change.

The goal is not to let an AI freely rewrite the project. The goal is to make documentation a dependable part of the software-development process. Every change is checked first, the AI is given a narrow job, its output is validated, and a human still reviews and merges the pull request.”

## The problem this solves

“In many projects, code changes faster than documentation. A developer adds a feature, but the README, user guide, NEWS file, examples, tests, and API documentation are updated later—or never.

That creates a gap between what the software does and what people are told it does. New users struggle to learn the application, maintainers have to reconstruct decisions, and future contributors cannot easily tell which workflows are current.

This project addresses that gap by making documentation part of the pull-request lifecycle.”

## What happens when a PR is opened

“When a pull request is opened, reopened, or updated, GitHub Actions starts the self-documenting workflow.

The workflow is divided into stages. The stages are deliberately ordered: safety and deterministic checks happen before AI editing, and the full test suite runs again after the AI edits.”

## Stage one: identify the exact change

“The first job is called `validate-pr`.

It asks GitHub which repository, pull request, branch, and commit are being reviewed. This matters because a pull request can receive new commits while a workflow is running. The agent must document the exact commit under review, not an older or different version.

This stage also protects forked pull requests. A fork may contain code from someone outside the repository. The workflow must not give untrusted code permission to push into the main project.”

## Stage two: preflight validation

“Next comes `preflight`, which is deterministic. It does not ask the AI to fix anything.

The job installs the pinned R version and dependencies, installs the package, runs the testthat suite, starts the Shiny application with temporary database and photo paths, and checks that the local application returns HTTP 200.

This answers a critical question: does the application work before the documentation agent touches it?

If preflight fails, the AI agent does not start. The failure is reported on the pull request so the developer can fix the application or its tests first. This prevents documentation automation from hiding a broken build.”

## Why temporary data is used

“The smoke test and future browser recordings use temporary DuckDB files, temporary photo directories, and synthetic data.

That protects personal bird sightings and photographs. It also makes CI repeatable: every run starts from a controlled environment instead of depending on one developer’s computer.”

## Stage three: the documentation agent

“Only after preflight passes does the documentation job start.

The agent receives the pull-request diff, the documentation policy, the current README, NEWS file, user guide, workflow inventory, and the versioned prompt. In other words, it sees both what changed and what the current documentation already says.

The agent is not asked to redesign the application. It is asked to compare the change with the existing documentation and produce only the updates justified by the pull request.”

## What the agent may change

“The allowed files are intentionally limited.

The agent may update Roxygen comments and generated `man` pages so the R API stays accurate. It may add focused testthat tests when behavior changed. It may update the README, NEWS file, user guide, and workflow inventory. It may update Playwright links only when real media artifacts exist.

It may not change application behavior, dependencies, CI definitions, policy files, or invent features, screenshots, videos, links, or test results.

Every documentation area is reviewed on every run. However, the agent does not make meaningless edits just to create activity. It changes a file only when the pull-request diff provides a truthful reason.”

## Why the agent returns a patch

“The agent returns a Git patch instead of directly editing the repository.

A patch is a proposed set of changes. The workflow can inspect it, validate it, restrict which paths it touches, and apply it only when Git accepts it.

The script first asks for a standard unified Git patch. It removes accidental Markdown fences and validates the patch with `git apply --check`. If the response is malformed, it asks for a corrected patch. If necessary, it asks for complete file contents in structured JSON and generates the patch locally. This gives us a deterministic final patch rather than trusting the model’s formatting.”

## Stage four: allow-list enforcement

“After the patch is applied, the workflow checks every changed path against the policy.

This is a second safety boundary. The prompt tells the AI what it should do, but the allow-list verifies what it actually attempted to do. If a patch touches an unapproved file, the workflow stops.”

## Stage five: validation after editing

“The workflow then runs the quality checks again.

It regenerates Roxygen documentation, checks that generated files are consistent, runs R CMD check, runs the tests, checks documentation headings and links, updates the workflow inventory, and repeats the Shiny smoke test.

This second validation matters because documentation can include examples, identifiers, paths, and references that must remain consistent with the package. The goal is not just to create text; it is to verify that the repository remains healthy after the update.”

## The bot commit

“The bot commits only after all checks pass. The commit contains the allow-listed documentation, tests, Roxygen output, and any real generated artifacts.

It pushes that commit to the existing pull-request branch. Because the branch changed, GitHub runs the checks again. This confirms the exact commit that the human reviewer will see.

The bot never merges the pull request. A human reviews the generated changes and decides whether the feature and its documentation are correct.”

## Playwright videos

“The next automation phase is Playwright.

Playwright will open the Shiny application in a real browser and run the documented workflows: browsing the catalog, recording a sighting, reviewing personal sightings, and viewing the dashboard.

Each workflow will use synthetic data and temporary files. Playwright will capture a video and poster image, then return a manifest that records the workflow ID, commit SHA, browser version, and artifact paths.

The important safety rule is that a missing video remains a missing video. The system never fabricates a link. If Playwright is unavailable, the user guide keeps its placeholder and the pull request reports that the recording was unavailable.”

## GitHub Pages

“After the pull request is merged, GitHub Pages publishes the trusted user guide from the main branch.

The pull-request agent updates the source Markdown. A separate Pages workflow publishes it only after merge. This separates editing from publication and prevents an unreviewed pull request from becoming the public documentation site.”

## Why this design is useful to other projects

“This pattern applies beyond bird tracking.

First, it separates deterministic validation from AI assistance. Tests and smoke checks decide whether the software works; the AI helps keep the explanation current.

Second, it bounds the AI by file allow-lists and structured prompts. The agent has a narrow responsibility and cannot silently broaden its scope.

Third, it uses temporary synthetic data for browser automation. That makes recordings reproducible and protects private information.

Fourth, it preserves human review. Automation prepares a better pull request, but a maintainer remains responsible for the final decision.

Finally, it treats documentation as a tested project artifact. README instructions, user workflows, API documentation, tests, and browser demonstrations are maintained alongside the code that they describe.”

## Closing

“The result is a self-documenting development loop:

The developer opens a pull request. GitHub verifies the application. The agent reviews the change and prepares bounded documentation updates. The repository regenerates and tests its documentation. Optional browser automation creates demonstrations from synthetic data. The bot pushes only validated changes. A human reviews and merges.

That process makes the project easier to learn, easier to maintain, and safer to extend—without giving up testing, privacy, or human judgment.”
