#' Application server
#'
#' The server initializes the local database and connects the dashboard, county
#' map, catalog, recording, and sightings modules.
#' @param input,output,session Standard Shiny server objects.
#' @param db_path DuckDB file path.
#' @param photo_library App-managed photo-library directory.
#' @param reference_path User-managed reference-photo directory.
#' @return Nothing; called for side effects.
#' @keywords internal
app_server <- function(input, output, session, db_path = bird_db_path(),
                       photo_library = bird_photo_library_path(db_path),
                       reference_path = bird_reference_photo_path(db_path)) {
  con <- bird_db_connect(db_path)
  initialize_bird_db(con)
  session$onSessionEnded(function() DBI::dbDisconnect(con, shutdown = TRUE))

  refresh <- shiny::reactiveVal(0L)
  species <- list_species(con)
  choices <- stats::setNames(species$species_code, species$common_name)

  mod_dashboard_server("dashboard", con = con, refresh = refresh, reference_path = reference_path)
  mod_map_server("map", con = con, refresh = refresh)
  mod_species_server("species", con = con, reference_path = reference_path)
  mod_record_server("record", con = con, species_choices = choices,
                    photo_library = photo_library, reference_path = reference_path, refresh = refresh)
  mod_sightings_server("sightings", con = con, species_choices = choices,
                       photo_library = photo_library, reference_path = reference_path, refresh = refresh)
}
