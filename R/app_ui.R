#' Application user interface
#'
#' Provides the top-level navigation, including the county map view.
#' @param request Internal Shiny request object.
#' @return Shiny UI.
#' @keywords internal
app_ui <- function(request) {
  golem::add_resource_path("www", app_sys("app", "www"))
  shiny::tagList(
    shiny::tags$style(htmltools::HTML(".navbar{min-height:76px!important}.navbar-brand{height:auto!important;min-height:76px!important;white-space:nowrap!important;overflow:visible!important}.sightings-filter-actions{display:flex;gap:10px;margin:0 15px 4px}.sightings-filter-actions .btn{white-space:nowrap}")),
    golem::bundle_resources(path = app_sys("app", "www"), app_title = "Indiana Bird Tracker"),
    shiny::navbarPage(
      title = shiny::tagList(shiny::span("Indiana Bird Tracker", class = "app-title"),
                             shiny::span("Personal field notes", class = "app-subtitle")),
      id = "main-navigation",
      header = shiny::tags$div(class = "hero",
        shiny::tags$h2("Your Indiana birding, in one quiet place"),
        shiny::tags$p("Browse a starter catalog, record observations, and watch your personal list grow.")),
      shiny::tabPanel("Dashboard", value = "dashboard", mod_dashboard_ui("dashboard")),
      shiny::tabPanel("Map View", value = "map", mod_map_ui("map")),
      shiny::tabPanel("Species catalog", value = "species", mod_species_ui("species")),
      shiny::tabPanel("Record sighting", value = "record", mod_record_ui("record")),
      shiny::tabPanel("My sightings", value = "sightings", mod_sightings_ui("sightings")),
      footer = shiny::tags$footer("Local-first: your sightings stay in your DuckDB file.")
    )
  )
}

#' Locate packaged application files
#'
#' @param ... Components passed to [system.file()].
#' @return The resolved path within the installed package.
#' @keywords internal
app_sys <- function(...) system.file(..., package = "indianabirdtracker")
