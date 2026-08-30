test_that("sightings round-trip and dashboard counts are correct", {
  con <- local_bird_db()
  id <- add_sighting(con, "CARDINALIS_CARDINALIS", as.POSIXct("2026-05-10 07:30", tz = "America/Indiana/Indianapolis"),
                     "Backyard", "Monroe", "Singing", "photos/cardinal.jpg")
  expect_equal(id, 1L)
  sightings <- list_sightings(con)
  expect_equal(nrow(sightings), 1)
  expect_equal(sightings$common_name, "Northern Cardinal")
  expect_equal(format_observation_time(sightings$observed_at), "May 10, 2026 07:30 AM")
  summary <- dashboard_summary(con)
  expect_equal(summary$total_sightings, 1L)
  expect_equal(summary$distinct_species, 1L)
})

test_that("valid uploaded photos use safe collision-resistant paths", {
  library_path <- file.path(tempdir(), paste0("bird-photo-test-", Sys.getpid()))
  dir.create(library_path, recursive = TRUE, showWarnings = FALSE)
  withr::defer(unlink(library_path, recursive = TRUE, force = TRUE))
  png <- file.path(tempdir(), "upload.png")
  writeBin(as.raw(c(0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a,
                    0x00, 0x00, 0x00, 0x00)), png)
  first <- store_sighting_photo(png, "Backyard Bird.PNG", "American Robin", 7L, library_path)
  second <- store_sighting_photo(png, "Backyard Bird.PNG", "American Robin", 7L, library_path)
  expect_equal(first, "american-robin/sighting-7.png")
  expect_equal(second, "american-robin/sighting-7-2.png")
  expect_true(file.exists(file.path(library_path, first)))
  expect_equal(normalizePath(managed_photo_absolute_path(first, library_path)),
               normalizePath(file.path(library_path, first)))
})

test_that("filters and validation protect data quality", {
  con <- local_bird_db()
  add_sighting(con, "CARDINALIS_CARDINALIS", as.POSIXct("2026-05-10 07:30"), "Backyard", "Monroe")
  add_sighting(con, "TURDUS_MIGRATORIUS", as.POSIXct("2026-06-12 08:00"), "City park", "Marion")
  expect_equal(nrow(list_sightings(con, county = "Monroe")), 1)
  expect_equal(nrow(list_sightings(con, start_date = "2026-06-01")), 1)
  expect_error(add_sighting(con, "NOPE", Sys.time(), "Park", "Marion"), "not in the catalog")
  expect_error(add_sighting(con, "CARDINALIS_CARDINALIS", Sys.time(), "", "Marion"), "Location is required")
  expect_error(list_sightings(con, start_date = "2026-07-01", end_date = "2026-06-01"), "on or before")
})
