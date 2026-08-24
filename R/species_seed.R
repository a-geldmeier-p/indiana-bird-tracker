#' Load and validate the Indiana bird species seed catalog
#'
#' Occurrence scope comes from the Indiana DNR Birds of Indiana list. Taxonomic
#' range context is enriched from the Cornell Lab eBird/Clements v2025 list.
#'
#' @param path Optional path to a CSV seed file.
#' @return A validated data frame with one row per species code.
#' @export
load_species_seed <- function(path = NULL) {
  if (is.null(path)) {
    path <- system.file("extdata", "indiana_bird_catalog.csv",
                        package = "indianabirdtracker")
    if (!nzchar(path)) {
      development_path <- file.path("inst", "extdata", "indiana_bird_catalog.csv")
      if (file.exists(development_path)) path <- development_path
    }
  }
  if (is.null(path) || !length(path) || !nzchar(path) || !file.exists(path)) {
    stop("Species seed CSV was not found.", call. = FALSE)
  }
  seed <- utils::read.csv(path, stringsAsFactors = FALSE, na.strings = character())
  required <- c("species_code", "common_name", "scientific_name", "bird_group",
                "status_note", "brief_description")
  missing <- setdiff(required, names(seed))
  if (length(missing)) {
    stop("Species seed is missing columns: ", paste(missing, collapse = ", "),
         call. = FALSE)
  }
  seed <- seed[required]
  if (!nrow(seed)) stop("Species seed must contain at least one row.", call. = FALSE)
  if (anyDuplicated(seed$species_code)) stop("Species codes must be unique.", call. = FALSE)
  if (any(!nzchar(trimws(as.matrix(seed))))) {
    stop("Species seed fields cannot be blank.", call. = FALSE)
  }
  seed
}
