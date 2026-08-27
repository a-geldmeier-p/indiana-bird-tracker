# Indiana Bird Tracker

A deliberately small, personal Shiny app packaged with a `{golem}`-compatible structure. It stores sightings locally in DuckDB, provides a source-documented Indiana bird catalog, and keeps the UI/workflows stable enough to support browser-tested tutorial recordings.

## What it does

- Search and filter a 425-record Indiana catalog with common name, scientific name, family group, status, and a brief range description.
- Record a sighting with species, date/time, location, county, notes, and an optional photo upload or path/URL.
- Filter saved sightings by species, county, and date range.
- Review total sightings, distinct species, and recent observations.

On **My sightings**, the date filter is an on/off slider. The date-range control is shown only while the slider is enabled; selecting **Filter sightings** applies the visible controls, and **Reset filters** restores all sightings.

## User-managed reference photos

Reference photos are supplied by the user and are never downloaded by the app. The default folder is `reference-photos` beside the DuckDB file (get the exact location with `indianabirdtracker::bird_reference_photo_path()`). Add small `.jpg`, `.jpeg`, or `.png` files named from the lower-case common-name slug, such as `carolina-wren.jpg` or `american-bittern.png`. Matching is case-insensitive.

Reference photos are separate from sighting uploads (`photos/`) and are not stored in DuckDB. The catalog reports unrecognized filenames; `write_reference_photo_report(con, "reference-photo-coverage.csv")` writes a report for all 425 catalog species. Until supplied, the UI shows a missing-photo placeholder. Adding or replacing a correctly named file is picked up on the next refresh/session.

## Catalog scope and provenance

The packaged snapshot contains the 424 rows parsed from the [Indiana DNR Birds of Indiana list](https://secure.in.gov/dnr/fish-and-wildlife/nongame-and-endangered-wildlife/birds/birds-of-indiana-list/), compiled by the state ornithologist, revised September 2021, and retrieved August 18, 2026. The app expands one compound DNR row into separate California Scrub-Jay and Woodhouse's Scrub-Jay records, for 425 catalog rows total; both retain the original Indiana-checklist scope.

Names and concise range context were matched by common name against the [Cornell Lab eBird/Clements Checklist v2025](https://www.birds.cornell.edu/clementschecklist/introduction/updateindex/october-2025/2025-citation-checklist-downloads/), released October 31, 2025 and retrieved August 18, 2026. The compound scrub-jay row is now represented by the two accepted species names above; the catalog deliberately preserves the Indiana checklist scope rather than claiming a current universal checklist.

Accordingly, this is a complete snapshot of the cited DNR table, not a claim to be the single current definitive list of every Indiana record. The Indiana Bird Records Committee separately describes a 420-species official checklist, and taxonomy continues to change. See `inst/extdata/CATALOG_SOURCES.md` and `data-raw/build_species_seed.R` for exact transformation and limitations.

## Setup and run

See the [hosted user guide](https://a-geldmeier-p.github.io/indiana-bird-tracker/) for step-by-step workflows. The guide contains four reserved video sections; pull-request automation records tutorial videos with synthetic data and uploads them as temporary workflow artifacts, but those artifacts are not yet published in the guide. The source is [USER_GUIDE.md](USER_GUIDE.md).
Release notes are kept in [NEWS.md](NEWS.md). The self-documenting pull-request workflow can update documentation after its application preflight and can record the catalog, record-sighting, My Sightings, and dashboard tutorials.

Install the package dependencies, then install this package:

```r
install.packages(c("golem", "shiny", "DBI", "duckdb", "testthat", "roxygen2"))
pak::local_install(".")
```

Run the installed app:

```r
indianabirdtracker::run_app()
```

For development, use `golem::run_dev()` or source `dev/run_dev.R`. `run_app()` uses `bird_tracker.duckdb` plus sibling `photos/` and `reference-photos/` folders in the current package/project folder by default. To use a specific file or folders:

```r
indianabirdtracker::run_app(db_path = "data/my_birds.duckdb")
```

On this Windows computer, the current resolved defaults are:

- Package source: `C:\Users\ageldmeier\Documents\Codex\2026-08-18\indiana-bird-tracker`
- DuckDB: `C:\Users\ageldmeier\AppData\Roaming\R\data\R\indianabirdtracker\bird_tracker.duckdb`
- Managed photos: `C:\Users\ageldmeier\AppData\Roaming\R\data\R\indianabirdtracker\photos`

The source files already exist in the package directory. The DuckDB tables and photo-library contents are created when the app first initializes. All three locations are configurable with `run_app(db_path = ..., photo_library = ..., reference_path = ...)`.

## Data behavior

Database initialization is transactional and idempotent. It creates tables and indexes only when needed and inserts only missing species codes, so restarting the app does not duplicate or delete data.

Uploaded JPEG, PNG, GIF, and WebP images are signature-checked and copied into the app-managed local library at `photos/<safe-species-name>/sighting-<id>.<ext>`. A numeric suffix prevents collisions. DuckDB stores only the relative file path, never image bytes. The library defaults beside the database and can be changed with `run_app(photo_library = ...)`. A manually entered local path or URL remains available as an alternative; arbitrary local paths are displayed as references but are not exposed through the app's web server.

Run non-UI tests with `testthat::test_local()`. See [WORKFLOW_INVENTORY.md](WORKFLOW_INVENTORY.md) for the stable browser-workflow contract and the synthetic tutorial fixture used by pull-request recording.

<!-- automatic documentation test -->
