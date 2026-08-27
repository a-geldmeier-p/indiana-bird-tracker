# Workflow inventory

This inventory is the human-readable contract for the Playwright tutorial recordings and automated user-guide maintenance. Labels and IDs below should be treated as stable unless a deliberate workflow change is made.

## 1. Browse the species catalog

- Open the **Species catalog** navigation tab (`main-navigation`, value `species`).
- Enter text in **Search name, status, or description** (`species-search`).
- Choose **Bird group** (`species-bird_group`).
- Choose **Indiana listing status** (`species-status_note`).
- Select **Filter catalog** (`species-filter_catalog`) to explicitly apply the current search, or use **Reset filters** (`species-reset_filters`) to restore all 425 records, including separate California Scrub-Jay and Woodhouse's Scrub-Jay rows.
- Confirm matching rows show common name, scientific name, bird group, status, and brief description in `species-species_table`.
- Confirm each catalog row has a compact user-managed reference thumbnail with descriptive alt text, or an explicit missing-photo placeholder. The catalog status reports found coverage and the expected folder.
- Confirm an unmatched search shows a clear no-results message in `species-catalog_status`.
- Confirm the DNR/Cornell catalog-scope note remains visible.

## 2. Record a sighting

- Open **Record sighting** (`main-navigation`, value `record`).
- Choose **Species** (`record-species_code`).
- Set **Observation date** (`record-observation_date`) and **Observation time** (`record-observation_time`).
- Enter required **Location** and **Indiana county** (`record-location`, `record-county`).
- Optionally upload a supported image (`record-photo_upload`) or enter a path/URL (`record-photo_reference`).
- After choosing a species, confirm the compact catalog reference preview appears; this is separate from the optional user upload.
- Select **Save sighting** (`record-save_sighting`).
- Confirm `record-save-status` reports success; also test a missing required value and confirm an understandable error.

## 3. Browse recorded sightings

- Open **My sightings** (`main-navigation`, value `sightings`).
- Filter by **Species** and **County** (`sightings-species_code`, `sightings-county`).
- To filter dates, enable **Filter by observation date** (`sightings-use_date_filter`) and set **Observation date range** (`sightings-date_range`).
- Confirm `sightings-sightings_table` contains only expected rows and is ordered newest first.
- Confirm each sighting row includes its species reference thumbnail, while the separate photo panel shows only the user's linked sighting photo.
- Confirm `sightings-sighting_photos` renders the uploaded image for its linked sighting.
- Delete or temporarily move a fixture image and confirm the graceful missing-file message appears.

## 4. Review the dashboard

- Open **Dashboard** (`main-navigation`, value `dashboard`).
- Confirm `dashboard-total-sightings` and `dashboard-distinct-species` reflect seeded test sightings.
- Confirm `dashboard-recent_sightings` shows the newest observations first.
- Confirm recent observations include their species reference thumbnails.
- Add a sighting, return to the dashboard, and confirm metrics refresh without restarting the app.

## Suggested browser-test fixture

Each test run should use a new temporary DuckDB path and photo-library directory, call `initialize_bird_db()`, and add only the sightings and tiny image fixtures the test owns. This makes counts deterministic, avoids modifying a person's real data, and allows fixtures to be removed after the app and connection close. Include one valid image, one renamed non-image, two same-ID copies to exercise collision handling, and one intentionally missing managed path.

## 5. Repository pull-request workflows

- `.github/workflows/self-documenting-pr.yml` runs automatically for pull requests that are opened, synchronized, or reopened, and can also be started with `workflow_dispatch`.
- The workflow validates the pull request head repository, checks out the head revision, and runs an application preflight that installs the package, runs local `testthat` tests, and performs the Shiny smoke check.
- After preflight, the documentation job obtains the pull-request diff, asks the documentation agent for an allow-listed patch, and checks that patch before applying it.
- The manual-dispatch path uses the supplied pull-request number; pull-request events use the event's pull-request number.
- The former `.github/workflows/pr-check.yml` workflow has been removed; its application installation, test, and Shiny smoke-check commands are now part of the self-documenting workflow's preflight job.
