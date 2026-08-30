# indianabirdtracker 0.0.1.9000

## Current changes

- Added a step-by-step `USER_GUIDE.md` suitable for GitHub Pages, with four reserved video placeholders for tutorial recordings.
- Added separate California Scrub-Jay and Woodhouse's Scrub-Jay catalog records, with a migration for older combined records.
- Limited catalog text search to common and scientific names; bird group and Indiana status remain separate filters.
- Added dynamic county filtering, explicit sightings filter/reset controls, and a toggle-controlled observation date range.
- Added local reference-photo mapping, managed sighting-photo uploads, and a fixed three-column sighting-photo grid.
- Fixed Windows path normalization so valid uploaded photos display from the managed library.
- Updated the self-documenting pull-request workflow to run on selected pull-request events, separate application preflight checks from documentation, and use the pull-request number for both automatic and manually dispatched runs.
- Added a GitHub Actions Playwright job that seeds synthetic DuckDB and photo data, starts a temporary Shiny app, records the catalog, record-sighting, My Sightings, and dashboard tutorials, and uploads videos and diagnostics as a 30-day workflow artifact.

## Future maintenance

Tutorial videos remain temporary workflow artifacts until a later publication step copies verified files into `docs/playwright/artifacts/`. The four user-guide placeholders must remain unchanged until real artifact paths are verified.
