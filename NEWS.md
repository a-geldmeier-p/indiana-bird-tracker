# indianabirdtracker 0.0.1.9000

## Current changes

- Added a step-by-step `USER_GUIDE.md` suitable for later GitHub Pages hosting, with reserved placeholders for future Playwright workflow videos.
- Added separate California Scrub-Jay and Woodhouse's Scrub-Jay catalog records, with a migration for older combined records.
- Limited catalog text search to common and scientific names; bird group and Indiana status remain separate filters.
- Added dynamic county filtering, explicit sightings filter/reset controls, and a toggle-controlled observation date range.
- Added local reference-photo mapping, managed sighting-photo uploads, and a fixed three-column sighting-photo grid.
- Fixed Windows path normalization so valid uploaded photos display from the managed library.
- Updated the self-documenting pull-request workflow to run on selected pull-request events, separate application preflight checks from documentation, and use the pull-request number for both automatic and manually dispatched runs.
- Updated workflow dependency setup to install `pak` from the configured R package repository.

## Future maintenance

This file is intentionally human-readable and stable for a future pull-request workflow that can add a concise entry when a reviewed change is merged. That automation is not included in the current local-only MVP.
