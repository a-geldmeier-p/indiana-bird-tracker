#' Run the Indiana Bird Tracker
#'
#' Starts the Shiny application. The DuckDB file is initialized automatically
#' when the first session opens.
#'
#' @param db_path Path to the local DuckDB database file. Defaults to
#'   `bird_tracker.duckdb` in the current package/project folder.
#' @param photo_library Path to the app-managed local photo directory. Defaults
#'   to a `photos` folder beside `db_path`.
#' @param reference_path Path to the user-managed reference-photo directory.
#'   Defaults to a `reference-photos` folder beside `db_path`.
#' @param ... Additional arguments passed to [shiny::shinyApp()].
#' @return A Shiny application object, invisibly when launched by Shiny.
#' @export
run_app <- function(db_path = file.path(getwd(), "bird_tracker.duckdb"),
                    photo_library = bird_photo_library_path(db_path),
                    reference_path = bird_reference_photo_path(db_path), ...) {
  options(golem.app.prod = TRUE)
  ensure_directory(photo_library, "Photo library")
  ensure_directory(reference_path, "Reference photo library")
  paths <- shiny::resourcePaths()
  if ("bird-photos" %in% names(paths)) shiny::removeResourcePath("bird-photos")
  shiny::addResourcePath("bird-photos", photo_library)
  if ("bird-reference-photos" %in% names(paths)) shiny::removeResourcePath("bird-reference-photos")
  shiny::addResourcePath("bird-reference-photos", reference_path)
  shiny::shinyApp(
    ui = app_ui,
    server = function(input, output, session) {
      app_server(input, output, session, db_path = db_path,
                 photo_library = photo_library, reference_path = reference_path)
    },
    ...
  )
}
