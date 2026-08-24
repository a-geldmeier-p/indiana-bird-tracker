reference_bird_image <- function(species_code, common_name,
                                 reference_path = bird_reference_photo_path(), size = 96) {
  slug <- reference_photo_slug(common_name)
  files <- if (dir.exists(reference_path)) list.files(reference_path, full.names = TRUE) else character()
  matching <- files[tolower(basename(files)) %in% paste0(slug, c(".jpg", ".jpeg", ".png"))]
  if (!length(matching)) {
    return(shiny::tags$span(class = "reference-bird-missing",
      paste("Reference photo missing:", paste0(slug, ".jpg"))))
  }
  filename <- basename(matching[[1]])
  shiny::tags$img(src = paste0("bird-reference-photos/", utils::URLencode(filename, reserved = TRUE)),
    alt = paste(common_name, "reference photo"),
    class = "reference-bird-thumbnail", loading = "lazy",
    style = paste0("width:", size, "px;height:", size, "px;max-width:", size,
      "px;max-height:", size, "px;object-fit:contain;display:block;"))
}

reference_bird_table <- function(data, columns,
                                 reference_path = bird_reference_photo_path()) {
  if (!nrow(data)) return(NULL)
  labels <- c(common_name = "Common name", scientific_name = "Scientific name",
              bird_group = "Bird group", status_note = "Indiana status",
              brief_description = "Brief description", observed_at = "Observed at",
              location = "Location", county = "County", notes = "Notes")
  header <- shiny::tags$tr(shiny::tags$th("Reference"),
    lapply(columns, function(x) shiny::tags$th(labels[[x]] %||% x)))
  body <- lapply(seq_len(nrow(data)), function(i) {
    row <- data[i, , drop = FALSE]
    cells <- lapply(columns, function(x) shiny::tags$td(as.character(row[[x]][[1]] %||% "")))
      shiny::tags$tr(shiny::tags$td(reference_bird_image(row$species_code[[1]],
      row$common_name[[1]], reference_path)), cells)
  })
  shiny::tags$table(class = "table table-striped table-hover reference-bird-table",
    shiny::tags$thead(header), shiny::tags$tbody(body))
}
