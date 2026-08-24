test_that("catalog UI exposes compact filter controls and stable IDs", {
  html <- htmltools::renderTags(mod_species_ui("species"))$html
  expect_match(html, "species-search")
  expect_match(html, "species-bird_group")
  expect_match(html, "species-status_note")
  expect_match(html, "species-filter_catalog")
  expect_match(html, "species-reset_filters")
  expect_match(html, "Filter catalog")
  expect_match(html, "Reset filters")
})

test_that("user-managed reference photo mapping covers the catalog", {
  expect_equal(reference_photo_slug("Carolina Wren"), "carolina-wren")
  expect_equal(reference_photo_slug("Black-and-white Warbler"), "black-and-white-warbler")
  con <- bird_db_connect(tempfile(fileext = ".duckdb"))
  on.exit(DBI::dbDisconnect(con, shutdown = TRUE), add = TRUE)
  initialize_bird_db(con)
  path <- tempfile()
  dir.create(path)
  writeBin(charToRaw("fake image"), file.path(path, "carolina-wren.jpg"))
  writeBin(charToRaw("unused"), file.path(path, "not-a-species.jpg"))
  report <- reference_photo_coverage(con, path)
  expect_equal(nrow(report), 425)
  expect_equal(sum(report$status == "found"), 1)
  expect_true("not-a-species.jpg" %in% attr(report, "unrecognized_files"))
  missing <- as.character(reference_bird_image("CARDINALIS_CARDINALIS", "Northern Cardinal", path))
  expect_match(missing, "Reference photo missing")
  writeBin(charToRaw("fake image"), file.path(path, "northern-cardinal.png"))
  found <- as.character(reference_bird_image("CARDINALIS_CARDINALIS", "Northern Cardinal", path))
  expect_match(found, "bird-reference-photos/northern-cardinal.png")
})

test_that("recording UI includes a separate reference preview hook", {
  html <- htmltools::renderTags(mod_record_ui("record"))$html
  expect_match(html, "record-species_preview")
  expect_match(html, "record-photo_upload")
})

test_that("sightings filters use the compact horizontal layout", {
  html <- htmltools::renderTags(mod_sightings_ui("sightings"))$html
  expect_match(html, "class=\"row\"")
  expect_match(html, "Filter sightings")
  expect_match(html, "Reset filters")
  expect_match(html, "sightings-date_range")
  expect_match(html, "use_date_filter")
  expect_match(html, "sightings-species_code")
  expect_match(html, "sightings-date_range")
})
