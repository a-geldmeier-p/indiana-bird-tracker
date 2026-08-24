mod_record_ui <- function(id) {
  ns <- shiny::NS(id)
  shiny::fluidPage(
    shiny::tags$section(class = "panel form-panel",
      shiny::tags$h3("Record a bird sighting"),
      shiny::selectizeInput(ns("species_code"), "Species", choices = NULL,
                            options = list(placeholder = "Choose a species")),
      shiny::uiOutput(ns("species_preview")),
      shiny::dateInput(ns("observation_date"), "Observation date", value = Sys.Date()),
      shiny::textInput(ns("observation_time"), "Observation time", value = format(Sys.time(), "%H:%M"),
                       placeholder = "HH:MM"),
      shiny::textInput(ns("location"), "Location", placeholder = "Park, refuge, trail, or address"),
      shiny::textInput(ns("county"), "Indiana county", placeholder = "e.g. Monroe"),
      shiny::textAreaInput(ns("notes"), "Notes (optional)", rows = 4),
      shiny::fileInput(ns("photo_upload"), "Upload photo (optional)",
                       accept = c("image/jpeg", "image/png", "image/gif", "image/webp")),
      shiny::textInput(ns("photo_reference"), "Or photo path or URL (optional)"),
      shiny::tags$p(class = "help-block",
        "Uploads are copied to the local app photo library. JPEG, PNG, GIF, and WebP are supported."),
      shiny::actionButton(ns("save_sighting"), "Save sighting", class = "btn-primary"),
      shiny::tags$div(id = ns("save-status"), role = "status", shiny::textOutput(ns("save_status")))
    )
  )
}

mod_record_server <- function(id, con, species_choices, photo_library, reference_path, refresh) {
  shiny::moduleServer(id, function(input, output, session) {
    shiny::updateSelectizeInput(session, "species_code", choices = species_choices, server = TRUE)
    output$species_preview <- shiny::renderUI({
      code <- input$species_code
      if (is.null(code) || !nzchar(code)) return(NULL)
      common_name <- names(species_choices)[match(code, species_choices)]
      shiny::tags$div(class = "record-reference-preview",
        reference_bird_image(code, common_name, reference_path, size = 120),
        shiny::tags$span(paste(common_name, "reference image")))
    })
    status <- shiny::reactiveVal("")
    output$save_status <- shiny::renderText(status())
    shiny::observeEvent(input$save_sighting, {
      tryCatch({
        observed <- as.POSIXct(paste(input$observation_date, input$observation_time),
                               format = "%Y-%m-%d %H:%M", tz = "America/Indiana/Indianapolis")
        upload <- input$photo_upload
        if (!is.null(upload)) {
          detected <- detect_image_type(upload$datapath)
          extension <- tolower(tools::file_ext(upload$name))
          if (identical(extension, "jpeg")) extension <- "jpg"
          if (!extension %in% c("jpg", "png", "gif", "webp") ||
              !identical(extension, detected)) {
            stop("Photo must be a valid JPEG, PNG, GIF, or WebP image.", call. = FALSE)
          }
        }
        id <- add_sighting(con, input$species_code, observed, input$location,
                          input$county, input$notes, input$photo_reference)
        if (!is.null(upload)) {
          species_name <- names(species_choices)[match(input$species_code, species_choices)]
          relative_path <- store_sighting_photo(upload$datapath, upload$name,
            species_name, id, photo_library)
          set_sighting_photo(con, id, relative_path)
        }
        status(paste("Saved sighting", id))
        refresh(refresh() + 1L)
        shiny::showNotification("Sighting saved.", type = "message")
      }, error = function(e) {
        status(conditionMessage(e))
        shiny::showNotification(conditionMessage(e), type = "error")
      })
    })
  })
}
