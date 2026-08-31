# indianabirdtracker 0.0.1.9000

## Current changes

- Added an interactive **Map View** tab that shades Indiana counties by the number of distinct species recorded there and provides hover counts.
- Added a step-by-step `USER_GUIDE.md` suitable for GitHub Pages, with four reserved video placeholders for tutorial recordings.
- Added separate California Scrub-Jay and Woodhouse's Scrub-Jay catalog records, with a migration for older combined records.
- Limited catalog text search to common and scientific names; bird group and Indiana status remain separate filters.
- Added dynamic county filtering, explicit sightings filter/reset controls, and a toggle-controlled observation date range.
- Added local reference-photo mapping, managed sighting-photo uploads, and a fixed three-column sighting-photo grid.
- Fixed Windows path normalization so valid uploaded photos display from the managed library.
- Updated the self-documenting pull-request workflow to run on selected pull-request events, separate application preflight checks from documentation, and use the pull-request number for both automatic and manually dispatched runs.
- Updated workflow dependency setup to install `pak` from the configured R package repository.
- Replaced the Node Playwright test setup with the Python MCP client and an isolated official Playwright MCP Docker server for deterministic Chromium tutorial recording.
- Added MCP recording of the catalog, record-sighting, My Sightings, and dashboard tutorials, including verified WebM videos and PNG poster images, with videos and diagnostics uploaded as a 30-day workflow artifact.
- Added publication of verified Playwright MCP recordings and poster images into `docs/playwright/artifacts/`, the recording manifest, and the user guide during the documentation workflow.
- Replaced the fixed four-video recording pass with contract fingerprints: the documentation agent runs first, and Playwright MCP records only new, changed, or artifact-missing workflows while preserving unchanged media.

## Future maintenance

Tutorial placeholders remain until verified recordings are available. When recordings are successfully published, the workflow copies the videos and poster images into `docs/playwright/artifacts/`, records their paths and commit in the manifest, updates the corresponding user-guide sections, and commits those reviewed documentation artifacts.
