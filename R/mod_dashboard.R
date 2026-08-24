mod_dashboard_ui <- function(id) {
  ns <- shiny::NS(id)
  shiny::fluidPage(
    shiny::tags$div(class = "metric-grid",
      shiny::tags$div(class = "metric-card", shiny::tags$span("Total sightings"),
                      shiny::tags$strong(id = ns("total-sightings"), shiny::textOutput(ns("total_sightings"), inline = TRUE))),
      shiny::tags$div(class = "metric-card", shiny::tags$span("Distinct species"),
                      shiny::tags$strong(id = ns("distinct-species"), shiny::textOutput(ns("distinct_species"), inline = TRUE)))
    ),
    shiny::tags$section(class = "panel",
      shiny::tags$h3("Recent observations"),
      shiny::uiOutput(ns("recent_sightings")))
  )
}

mod_dashboard_server <- function(id, con, refresh, reference_path) {
  shiny::moduleServer(id, function(input, output, session) {
    summary_data <- shiny::reactive({ refresh(); dashboard_summary(con) })
    output$total_sightings <- shiny::renderText(summary_data()$total_sightings)
    output$distinct_species <- shiny::renderText(summary_data()$distinct_species)
    output$recent_sightings <- shiny::renderUI({
      recent <- summary_data()$recent
      if (nrow(recent)) recent$observed_at <- format_observation_time(recent$observed_at)
      reference_bird_table(recent, c("common_name", "observed_at", "location", "county"), reference_path)
    })
  })
}
