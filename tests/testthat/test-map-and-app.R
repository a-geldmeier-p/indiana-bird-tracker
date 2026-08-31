test_that("county keys normalize county naming variations", {
  expect_equal(normalize_county_key(c(" Monroe ", "Monroe County", "St. Joseph")),
               c("monroe", "monroe", "stjoseph"))
})

test_that("county map data contains Indiana counties and distinct species counts", {
  con <- local_bird_db()
  add_sighting(con, "CARDINALIS_CARDINALIS", as.POSIXct("2026-05-10 07:30"),
               "Backyard", "Monroe")
  add_sighting(con, "TURDUS_MIGRATORIUS", as.POSIXct("2026-05-11 07:30"),
               "Park", "Monroe County")
  data <- indiana_county_map_data(con)
  expect_true(inherits(data, "sf"))
  expect_true("distinct_species" %in% names(data))
  expect_equal(data$distinct_species[data$county_key == "monroe"], 2L)
  expect_true(all(data$distinct_species >= 0L))
})

test_that("map UI exposes the county map output", {
  html <- htmltools::renderTags(mod_map_ui("map"))$html
  expect_match(html, "Indiana county birding map")
  expect_match(html, "map-county_map")
  expect_match(html, "Darker counties")
})

test_that("top-level UI exposes Map View and application helpers", {
  expect_true(is.function(app_ui))
  expect_true(is.function(app_sys))
  expect_true(is.function(app_server))
  expect_match(as.character(app_sys("app", "www")), "app/www")
  html <- htmltools::renderTags(app_ui(NULL))$html
  expect_match(html, "Map View")
  expect_match(html, "main-navigation")
})

test_that("map server is a callable Shiny module server", {
  con <- local_bird_db()
  refresh <- shiny::reactiveVal(0L)
  expect_true(is.function(mod_map_server))
  expect_length(formals(mod_map_server), 3L)
  expect_s3_class(refresh, "reactiveVal")
})
