test_that("top-level UI exposes navigation and application helpers", {
  expect_true(is.function(app_ui))
  expect_true(is.function(app_sys))
  expect_true(is.function(app_server))
  expect_match(as.character(app_sys("app", "www")), "app/www")
  html <- htmltools::renderTags(app_ui(NULL))$html
  expect_match(html, "main-navigation")
  expect_match(html, "Species catalog")
  expect_match(html, "Record sighting")
  expect_match(html, "My sightings")
})
