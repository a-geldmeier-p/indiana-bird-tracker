# Indiana Bird Tracker User Guide

Indiana Bird Tracker is a local-first birding notebook. It keeps your catalog and sightings in DuckDB on your computer; it does not require a cloud account.

> This Markdown guide is published through GitHub Pages. Playwright records short demonstrations during pull-request automation; placeholders remain until verified videos are promoted from temporary workflow artifacts into the published site.

## Start the app

From the project folder, open R and run:

```r
indianabirdtracker::run_app()
```

By default, the app uses `bird_tracker.duckdb`, `photos/`, and `reference-photos/` in the current project folder. You can provide alternate locations with `run_app(db_path = ..., photo_library = ..., reference_path = ...)`.

## Browse the Indiana catalog

1. Open **Species catalog**.
2. The complete catalog appears when the tab opens.
3. Type a common or scientific name in **Search common or scientific name**.
4. Optionally choose a **Bird group** or **Indiana listing status**.
5. Select **Filter catalog** to apply the current search explicitly. Results also update as controls change.
6. Select **Reset filters** to restore the full catalog.
7. Use the result count and the table to review common name, scientific name, group, status, and description.

### Reference photos

The catalog shows a user-supplied reference photo when one is available. Add files to the `reference-photos/` folder using a lower-case common-name slug, such as `american-coot.jpg` or `woodhouses-scrub-jay.png`. Supported formats are `.jpg`, `.jpeg`, and `.png`. Missing files show a placeholder rather than a broken image.

<!-- VIDEO PLACEHOLDER: Catalog browsing and filtering (Playwright recording) -->

## Record a sighting

1. Open **Record sighting**.
2. Choose a species from **Species**. The species reference preview appears below the selector.
3. Enter the **Observation date** and **Observation time**.
4. Enter a **Location** and **Indiana county**.
5. To attach a photo, select **Upload photo (optional)** and choose a JPEG, PNG, GIF, or WebP image. The app copies it into a safe species folder under `photos/`; image bytes are not stored in DuckDB.
6. Alternatively, enter an optional photo path or URL.
7. Select **Save sighting** and confirm the success message.

<!-- VIDEO PLACEHOLDER: Recording a sighting with a photo (Playwright recording) -->

## Review and filter My Sightings

1. Open **My sightings**.
2. Use the horizontal filter row to choose a species and select a county from counties that have recorded sightings. The county list updates after new sightings are saved.
3. To filter by dates, turn on the **Filter by observation date** slider. The **Observation date range** control appears beside it; choose the start and end dates.
4. Review the table of observations. Dates and times are shown in a readable local format.
5. Open the **Sighting photos** section to view linked local images in a three-column fixed-size grid. Photos preserve their aspect ratio inside each box; missing files are reported clearly.

<!-- VIDEO PLACEHOLDER: Filtering and reviewing My Sightings (Playwright recording) -->

## View the dashboard

1. Open **Dashboard**.
2. Review **Total sightings** and **Distinct species**.
3. Read the **Recent observations** table, including each species reference thumbnail and observation details.

<!-- VIDEO PLACEHOLDER: Dashboard overview (Playwright recording) -->

## Add or replace reference photos

Reference photos are separate from sighting uploads. To see which catalog files are missing, use:

```r
con <- indianabirdtracker::bird_db_connect("bird_tracker.duckdb")
indianabirdtracker::write_reference_photo_report(con, "reference-photo-coverage.csv")
DBI::dbDisconnect(con, shutdown = TRUE)
```

The report lists every catalog species, its expected filename, and whether a matching file was found. Correctly named files are picked up on the next app refresh or session.

## Local data and backups

The DuckDB file contains catalog and sighting metadata. User-uploaded images remain in `photos/`, while catalog reference images remain in `reference-photos/`. Back up the database and these folders together if you want a complete personal archive.

## Troubleshooting

- **The catalog is empty:** restart the app once so the local schema and seed catalog can initialize.
- **A photo is missing:** check the filename slug and extension, then refresh the app.
- **The browser shows an old layout:** stop and restart the Shiny app, then reload the page.
- **You changed data locations:** pass the same `db_path`, `photo_library`, and `reference_path` values every time you launch the app.
