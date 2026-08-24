mod_sightings_ui <- function(id) {
  ns <- shiny::NS(id)
  shiny::fluidPage(
    shiny::tags$section(class = "panel filter-panel",
      shiny::tags$h3("Filter my sightings"),
      shiny::fluidRow(
        shiny::column(3, shiny::selectizeInput(ns("species_code"), "Species", choices = NULL)),
        shiny::column(3, shiny::selectInput(ns("county"), "County", choices = c("All counties" = ""))),
        shiny::column(3, shiny::div(class = "date-filter-toggle",
          shiny::checkboxInput(ns("use_date_filter"), "Filter by observation date", value = FALSE))),
        shiny::column(3, shiny::conditionalPanel(
          condition = sprintf("input['%s']", ns("use_date_filter")),
          shiny::dateRangeInput(ns("date_range"), "Observation date range",
            start = Sys.Date() - 30L, end = Sys.Date(), separator = " to ")))),
      shiny::div(class = "sightings-filter-actions",
        shiny::actionButton(ns("apply_filters"), "Filter sightings", class = "btn-primary"),
        shiny::actionButton(ns("reset_filters"), "Reset filters", class = "btn-default"))),
    shiny::tags$section(class = "panel", shiny::uiOutput(ns("sightings_table"))),
    shiny::tags$section(class = "panel",
      shiny::tags$h3("Sighting photos"),
      shiny::uiOutput(ns("sighting_photos")))
  )
}

mod_sightings_server <- function(id, con, species_choices, photo_library, reference_path, refresh) {
  shiny::moduleServer(id, function(input, output, session) {
    shiny::updateSelectizeInput(session, "species_code",
      choices = c("All species" = "", species_choices), server = TRUE)
    shiny::observe({
      refresh()
      counties <- list_sightings(con)$county
      counties <- sort(unique(counties[!is.na(counties) & nzchar(counties)]))
      shiny::updateSelectInput(session, "county",
        choices = c("All counties" = "", counties), selected = input$county %||% "")
    })
    applied <- shiny::reactiveValues(species = "", county = "", use_dates = FALSE,
      start = NULL, end = NULL)
    shiny::observeEvent(input$apply_filters, {
      range <- input$date_range
      applied$species <- input$species_code %||% ""
      applied$county <- input$county %||% ""
      applied$use_dates <- isTRUE(input$use_date_filter)
      applied$start <- if (!applied$use_dates || is.null(range) || is.na(range[[1]])) NULL else range[[1]]
      applied$end <- if (!applied$use_dates || is.null(range) || is.na(range[[2]])) NULL else range[[2]]
    }, ignoreInit = FALSE)
    shiny::observeEvent(input$reset_filters, {
      shiny::updateSelectizeInput(session, "species_code", selected = "")
      shiny::updateSelectInput(session, "county", selected = "")
      shiny::updateCheckboxInput(session, "use_date_filter", value = FALSE)
      shiny::updateDateRangeInput(session, "date_range", start = Sys.Date() - 30L, end = Sys.Date())
      applied$species <- ""; applied$county <- ""; applied$use_dates <- FALSE
      applied$start <- NULL; applied$end <- NULL
    }, ignoreInit = TRUE)
    filtered <- shiny::reactive({
      refresh()
      list_sightings(con, applied$species, applied$county, applied$start, applied$end)
    })
    output$sightings_table <- shiny::renderUI({
      sightings <- filtered()
      if (nrow(sightings)) sightings$observed_at <- format_observation_time(sightings$observed_at)
      reference_bird_table(sightings, c("common_name", "scientific_name", "observed_at",
        "location", "county", "notes"), reference_path)
    })
    output$sighting_photos <- shiny::renderUI({
      data <- filtered()
      photographed <- data[!is.na(data$photo_reference) & nzchar(data$photo_reference), , drop = FALSE]
      if (!nrow(photographed)) return(shiny::tags$p("No photos are linked to these sightings."))
      cards <- lapply(seq_len(nrow(photographed)), function(i) {
        row <- photographed[i, ]
        ref <- row$photo_reference[[1]]
        is_url <- grepl("^https?://", ref, ignore.case = TRUE)
        local_path <- managed_photo_absolute_path(ref, photo_library)
        image <- if (is_url) {
          shiny::tags$img(src = ref, alt = paste(row$common_name, "sighting photo"),
                          class = "sighting-photo",
                          style = "width:220px;height:220px;object-fit:contain;display:block;")
        } else if (!is.na(local_path) && file.exists(local_path)) {
          segments <- strsplit(gsub("\\\\", "/", ref), "/", fixed = TRUE)[[1]]
          src <- paste0("bird-photos/", paste(vapply(segments, utils::URLencode,
                                                     character(1), reserved = TRUE), collapse = "/"))
          shiny::tags$img(src = src, alt = paste(row$common_name, "sighting photo"),
                          class = "sighting-photo",
                          style = "width:220px;height:220px;object-fit:contain;display:block;")
        } else {
          shiny::tags$div(class = "photo-missing", "Photo file is missing or outside the managed library.")
        }
        shiny::tags$article(class = "photo-card",
          shiny::tags$h4(paste0(row$common_name, " - ", row$location)), image,
          shiny::tags$p(class = "source-note", ref))
      })
      shiny::tags$div(class = "photo-grid", cards)
    })
  })
}
