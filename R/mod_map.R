#' Normalize an Indiana county name for matching
#'
#' Removes surrounding whitespace, a trailing `County` suffix, and
#' punctuation differences.
#' @param value County name or names.
#' @return Lower-case alphanumeric county keys.
#' @keywords internal
normalize_county_key <- function(value) {
  value <- tolower(trimws(as.character(value)))
  value <- sub("[[:space:]]+county$", "", value)
  gsub("[^a-z0-9]+", "", value)
}

#' Build county map data with recorded species counts
#'
#' Loads Indiana county boundaries and joins each county to the number of
#' distinct species recorded in the sightings table.
#' @param con An initialized DBI connection.
#' @return An `sf` data frame containing county geometry and
#'   `distinct_species` counts.
#' @keywords internal
indiana_county_map_data <- function(con) {
  county_map <- maps::map("county", regions = "indiana", fill = TRUE, plot = FALSE)
  counties <- sf::st_as_sf(county_map)
  county_id <- sub("^[^,]+,", "", counties$ID)
  counties$county_key <- normalize_county_key(county_id)
  counties$county_name <- tools::toTitleCase(county_id)

  observed <- DBI::dbGetQuery(con, "SELECT county, species_code FROM sightings")
  if (nrow(observed)) {
    observed$county_key <- normalize_county_key(observed$county)
    grouped <- split(observed, observed$county_key)
    summary <- data.frame(
      county_key = names(grouped),
      distinct_species = vapply(grouped, function(rows) {
        length(unique(rows$species_code))
      }, integer(1)),
      stringsAsFactors = FALSE
    )
    matched <- match(counties$county_key, summary$county_key)
    counties$distinct_species <- summary$distinct_species[matched]
  } else {
    counties$distinct_species <- 0L
  }

  counties$distinct_species[is.na(counties$distinct_species)] <- 0L
  counties
}

#' Create the county map module UI
#'
#' @param id Shiny module namespace identifier.
#' @return A Shiny UI fragment containing the county map output.
#' @keywords internal
mod_map_ui <- function(id) {
  ns <- shiny::NS(id)
  shiny::fluidPage(
    shiny::tags$section(
      class = "panel map-panel",
      shiny::tags$h3("Indiana county birding map"),
      shiny::tags$p(
        class = "map-help",
        "Darker counties have more distinct species. Hover over a county to see its unique species count."
      ),
      leaflet::leafletOutput(ns("county_map"), height = "650px")
    )
  )
}

#' Run the county map module server
#'
#' Reactively renders the Indiana county map and refreshes its counts when the
#' application refresh value changes.
#' @param id Shiny module namespace identifier.
#' @param con An initialized DBI connection.
#' @param refresh Reactive refresh value.
#' @return A Shiny module server result, invisibly.
#' @keywords internal
mod_map_server <- function(id, con, refresh) {
  shiny::moduleServer(id, function(input, output, session) {
    map_data <- shiny::reactive({
      refresh()
      indiana_county_map_data(con)
    })

    output$county_map <- leaflet::renderLeaflet({
      counties <- map_data()
      maximum <- max(counties$distinct_species, na.rm = TRUE)
      domain <- c(0, max(1L, maximum))
      palette <- leaflet::colorNumeric(
        palette = c("#edf1ea", "#c9ddb8", "#8fbd78", "#4f8d55", "#19352c"),
        domain = domain,
        na.color = "#edf1ea"
      )
      labels <- sprintf(
        "<strong>%s County</strong><br>%d unique species seen",
        htmltools::htmlEscape(counties$county_name),
        counties$distinct_species
      )

      leaflet::leaflet(
        counties,
        options = leaflet::leafletOptions(minZoom = 6, maxZoom = 10)
      ) |>
        leaflet::setView(lng = -86.15, lat = 39.9, zoom = 7) |>
        leaflet::addPolygons(
          fillColor = ~palette(distinct_species),
          fillOpacity = 0.88,
          color = "#ffffff",
          weight = 1,
          opacity = 1,
          label = lapply(labels, htmltools::HTML),
          labelOptions = leaflet::labelOptions(
            direction = "auto",
            textsize = "13px",
            style = list("font-family" = "Segoe UI, sans-serif")
          ),
          highlightOptions = leaflet::highlightOptions(
            weight = 3,
            color = "#dda94b",
            fillOpacity = 1,
            bringToFront = TRUE
          )
        ) |>
        leaflet::addLegend(
          position = "bottomright",
          pal = palette,
          values = ~distinct_species,
          title = "Distinct species seen",
          opacity = 0.9
        )
    })
  })
}
