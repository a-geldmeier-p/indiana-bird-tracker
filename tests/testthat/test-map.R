test_that("map UI exposes the county map and stable identifiers", {
  html <- htmltools::renderTags(mod_map_ui("map"))$html
  expect_match(html, "map-county_map")
  expect_match(html, "Indiana county birding map")
  expect_match(html, "Darker counties have more distinct species")
})

test_that("county map data counts distinct species and normalizes county names", {
  con <- local_bird_db()
  add_sighting(con, "CARDINALIS_CARDINALIS", Sys.time(), "Backyard", "Marion County")
  add_sighting(con, "TURDUS_MIGRATORIUS", Sys.time(), "Park", "Marion")
  add_sighting(con, "CARDINALIS_CARDINALIS", Sys.time(), "Trail", "Marion")

  data <- indiana_county_map_data(con)
  marion <- data[data$county_key == "marion", , drop = FALSE]
  expect_equal(nrow(marion), 1L)
  expect_equal(marion$distinct_species, 2L)
  expect_true(all(data$distinct_species >= 0L))
})

test_that("county key normalization handles common suffix and punctuation variants", {
  expect_equal(normalize_county_key(c("Marion County", "marion_county", " Marion ")), rep("marion", 3))
})
