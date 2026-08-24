#' Default user-managed reference-photo directory
#'
#' @param db_path Path to the local DuckDB file.
#' @return A writable directory beside the database, separate from sighting
#'   uploads and package assets.
#' @export
bird_reference_photo_path <- function(db_path = bird_db_path()) {
  file.path(dirname(normalizePath(db_path, mustWork = FALSE)), "reference-photos")
}

reference_photo_slug <- function(common_name) {
  value <- iconv(trimws(as.character(common_name)), from = "", to = "ASCII//TRANSLIT", sub = "")
  value <- tolower(gsub("[^a-zA-Z0-9]+", "-", value))
  value <- gsub("(^-+|-+$)", "", value)
  value
}

#' Report user-managed reference-photo coverage
#'
#' @param con An open DuckDB connection.
#' @param reference_path Directory containing user-supplied reference photos.
#' @return A data frame with one row per catalog species and diagnostic attributes.
#' @export
reference_photo_coverage <- function(con, reference_path = bird_reference_photo_path()) {
  species <- list_species(con)
  files <- if (dir.exists(reference_path)) list.files(reference_path, full.names = TRUE) else character()
  file_index <- stats::setNames(files, tolower(basename(files)))
  rows <- lapply(seq_len(nrow(species)), function(i) {
    slug <- reference_photo_slug(species$common_name[[i]])
    candidates <- paste0(slug, c(".jpg", ".jpeg", ".png"))
    matching <- unname(file_index[tolower(candidates)])
    matching <- matching[!is.na(matching)]
    path <- if (length(matching)) matching[[1]] else NA_character_
    data.frame(species_code = species$species_code[[i]],
      common_name = species$common_name[[i]], expected_filename = paste0(slug, ".jpg/.jpeg/.png"),
      file_path = path, status = if (is.na(path)) "missing" else "found",
      stringsAsFactors = FALSE)
  })
  report <- do.call(rbind, rows)
  recognized <- tolower(basename(report$file_path[!is.na(report$file_path)]))
  attr(report, "unrecognized_files") <- basename(files)[
    !tolower(basename(files)) %in% recognized]
  attr(report, "reference_path") <- normalizePath(reference_path, mustWork = FALSE)
  report
}

#' Write a CSV reference-photo coverage report
#'
#' @param con An open DuckDB connection.
#' @param output_path Destination CSV path.
#' @param reference_path Directory containing user-supplied reference photos.
#' @return `output_path`, invisibly.
#' @export
write_reference_photo_report <- function(con, output_path,
                                         reference_path = bird_reference_photo_path()) {
  report <- reference_photo_coverage(con, reference_path)
  utils::write.csv(report, output_path, row.names = FALSE, na = "", fileEncoding = "UTF-8")
  invisible(output_path)
}
