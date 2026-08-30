args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2L) {
  stop("Usage: Rscript scripts/seed_playwright_demo.R DB_PATH PHOTO_LIBRARY")
}

db_path <- args[[1]]
photo_library <- args[[2]]
dir.create(photo_library, recursive = TRUE, showWarnings = FALSE)

con <- indianabirdtracker::bird_db_connect(db_path)
disconnected <- FALSE
on.exit({
  if (!disconnected) DBI::dbDisconnect(con, shutdown = TRUE)
}, add = TRUE)
indianabirdtracker::initialize_bird_db(con)

DBI::dbExecute(con, "DELETE FROM sightings WHERE notes LIKE 'Playwright demo:%'")

demo <- data.frame(
  species_code = c(
    "CARDINALIS_CARDINALIS",
    "SPINUS_TRISTIS",
    "BRANTA_CANADENSIS",
    "CYANOCITTA_CRISTATA"
  ),
  common_name = c(
    "Northern Cardinal",
    "American Goldfinch",
    "Canada Goose",
    "Blue Jay"
  ),
  observed_at = as.POSIXct(c(
    "2026-08-20 08:15",
    "2026-08-21 10:30",
    "2026-08-22 14:10",
    "2026-08-23 17:45"
  ), tz = "America/Indiana/Indianapolis"),
  location = c(
    "Eagle Creek Park",
    "Fort Harrison State Park",
    "White River State Park",
    "Monon Trail"
  ),
  county = c("Marion", "Marion", "Marion", "Hamilton"),
  notes = c(
    "Playwright demo: singing near the woodland edge.",
    "Playwright demo: feeding on native seed heads.",
    "Playwright demo: resting beside the water.",
    "Playwright demo: calling from an oak canopy."
  ),
  stringsAsFactors = FALSE
)

for (i in seq_len(nrow(demo))) {
  folder <- tolower(gsub("[^a-zA-Z0-9]+", "-", demo$common_name[[i]]))
  photo_dir <- file.path(photo_library, folder)
  dir.create(photo_dir, recursive = TRUE, showWarnings = FALSE)
  photo_name <- "tutorial-photo.svg"
  photo_path <- file.path(photo_dir, photo_name)
  label <- demo$common_name[[i]]
  svg <- paste0(
    '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500" viewBox="0 0 800 500">',
    '<rect width="800" height="500" fill="#dcebd8"/>',
    '<circle cx="400" cy="210" r="110" fill="#6f8f62"/>',
    '<path d="M310 230 Q400 90 490 230 Q400 340 310 230" fill="#f4f0df"/>',
    '<circle cx="440" cy="190" r="10" fill="#202820"/>',
    '<text x="400" y="410" text-anchor="middle" font-family="sans-serif" font-size="38" fill="#243024">',
    label,
    '</text><text x="400" y="452" text-anchor="middle" font-family="sans-serif" font-size="24" fill="#4b5c49">Synthetic tutorial image</text>',
    '</svg>'
  )
  writeLines(svg, photo_path, useBytes = TRUE)
  relative_photo <- paste(folder, photo_name, sep = "/")
  indianabirdtracker::add_sighting(
    con,
    demo$species_code[[i]],
    demo$observed_at[[i]],
    demo$location[[i]],
    demo$county[[i]],
    demo$notes[[i]],
    relative_photo
  )
}

message("Seeded four synthetic Playwright tutorial sightings in: ", db_path)

DBI::dbDisconnect(con, shutdown = TRUE)
disconnected <- TRUE

if (length(args) >= 3L && identical(args[[3]], "--serve")) {
  reference_path <- if (length(args) >= 4L) args[[4]] else file.path(dirname(db_path), "reference-photos")
  dir.create(reference_path, recursive = TRUE, showWarnings = FALSE)
  app <- indianabirdtracker::run_app(
    db_path = db_path,
    photo_library = photo_library,
    reference_path = reference_path
  )
  shiny::runApp(app, host = "127.0.0.1", port = 3838, launch.browser = FALSE)
}
