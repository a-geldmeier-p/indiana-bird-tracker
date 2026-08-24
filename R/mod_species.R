mod_species_ui <- function(id) {
  ns <- shiny::NS(id)
  shiny::fluidPage(
    shiny::tags$section(class = "panel catalog-filter-panel",
      shiny::tags$h3("Browse the Indiana catalog"),
      shiny::tags$div(class = "catalog-filter-row",
        shiny::textInput(ns("search"), "Search common or scientific name",
                         placeholder = "Try cardinal, Aphelocoma, or warbler"),
        shiny::selectInput(ns("bird_group"), "Bird group", choices = c("All groups" = "")),
        shiny::selectInput(ns("status_note"), "Indiana listing status",
                           choices = c("All statuses" = "")),
        shiny::actionButton(ns("filter_catalog"), "Filter catalog", class = "btn-primary"),
        shiny::actionButton(ns("reset_filters"), "Reset filters", class = "btn-default")
      ),
      shiny::tags$p(class = "filter-help", "Results update as you change a filter. Press Filter catalog to apply the current search explicitly.")),
    shiny::tags$section(class = "panel catalog-table-panel",
      shiny::uiOutput(ns("catalog_status")),
      shiny::uiOutput(ns("species_table"))),
    shiny::tags$p(class = "source-note",
      "Catalog scope: Indiana DNR state list (revised September 2021), enriched with Cornell eBird/Clements v2025 range context.")
  )
}

mod_species_server <- function(id, con, reference_path) {
  shiny::moduleServer(id, function(input, output, session) {
    groups <- sort(unique(list_species(con)$bird_group))
    statuses <- sort(unique(list_species(con)$status_note))
    shiny::updateSelectInput(session, "bird_group", choices = c("All groups" = "", groups), selected = "")
    shiny::updateSelectInput(session, "status_note", choices = c("All statuses" = "", statuses), selected = "")
    filtered <- shiny::reactive(list_species(con, input$search %||% "",
      input$bird_group %||% "", input$status_note %||% ""))
    shiny::observeEvent(input$filter_catalog, {
      invisible(filtered())
    }, ignoreInit = TRUE)
    shiny::observeEvent(input$reset_filters, {
      shiny::updateTextInput(session, "search", value = "")
      shiny::updateSelectInput(session, "bird_group", selected = "")
      shiny::updateSelectInput(session, "status_note", selected = "")
    }, ignoreInit = TRUE)
    output$catalog_status <- shiny::renderUI({
      rows <- filtered()
      if (!nrow(rows)) {
        return(shiny::tags$p(class = "catalog-no-match",
          "No catalog records match these filters. Try a broader search or select Reset filters."))
      }
      shiny::tags$p(class = "catalog-result-count",
        paste("Showing", nrow(rows), "of", nrow(list_species(con)), "catalog records."))
    })
    output$species_table <- shiny::renderUI({
      reference_bird_table(filtered(), c("common_name", "scientific_name", "bird_group",
        "status_note", "brief_description"), reference_path)
    })
  })
}

`%||%` <- function(x, y) if (is.null(x)) y else x
