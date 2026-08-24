#' Default managed photo-library path
#'
#' @param db_path Path to the bird tracker DuckDB file.
#' @return A path to a `photos` directory beside the database. For an in-memory
#'   database, a temporary session directory is used.
#' @export
bird_photo_library_path <- function(db_path = bird_db_path()) {
  if (identical(db_path, ":memory:")) {
    return(file.path(tempdir(), "indianabirdtracker-photos"))
  }
  file.path(dirname(normalizePath(db_path, mustWork = FALSE)), "photos")
}

ensure_directory <- function(path, label = "Directory") {
  if (!dir.exists(path)) {
    created <- dir.create(path, recursive = TRUE, showWarnings = FALSE)
    if (!isTRUE(created) && !dir.exists(path)) {
      stop(label, " could not be created: ", path, call. = FALSE)
    }
  }
  invisible(path)
}

#' Store an uploaded sighting photo in the managed local library
#'
#' The file is copied to a safe species folder and named with its sighting ID.
#' JPEG, PNG, GIF, and WebP files are accepted only when their file signature
#' matches the filename extension. Image bytes are never stored in DuckDB.
#'
#' @param source_path Path to the temporary uploaded file.
#' @param original_name Original client filename, used to determine extension.
#' @param species_name Common species name used for the safe folder slug.
#' @param sighting_id Positive sighting identifier.
#' @param library_path Root of the app-managed photo library.
#' @return A forward-slash relative path beneath `library_path`.
#' @export
store_sighting_photo <- function(source_path, original_name, species_name,
                                 sighting_id, library_path) {
  if (length(source_path) != 1L || !file.exists(source_path)) {
    stop("Uploaded photo file was not found.", call. = FALSE)
  }
  sighting_id <- as.integer(sighting_id)
  if (length(sighting_id) != 1L || is.na(sighting_id) || sighting_id < 1L) {
    stop("sighting_id must be a positive integer.", call. = FALSE)
  }
  original_name <- basename(validate_required_text(original_name, "Photo filename"))
  extension <- tolower(tools::file_ext(original_name))
  if (identical(extension, "jpeg")) extension <- "jpg"
  detected <- detect_image_type(source_path)
  if (!extension %in% c("jpg", "png", "gif", "webp") || !identical(extension, detected)) {
    stop("Photo must be a valid JPEG, PNG, GIF, or WebP image.", call. = FALSE)
  }

  species_folder <- safe_species_slug(species_name)
  target_directory <- file.path(library_path, species_folder)
  ensure_directory(target_directory, "Photo directory")
  stem <- paste0("sighting-", sighting_id)
  target <- file.path(target_directory, paste0(stem, ".", extension))
  counter <- 2L
  while (file.exists(target)) {
    target <- file.path(target_directory, paste0(stem, "-", counter, ".", extension))
    counter <- counter + 1L
  }
  if (!file.copy(source_path, target, overwrite = FALSE, copy.date = TRUE)) {
    stop("The photo could not be copied to the local library.", call. = FALSE)
  }
  paste(species_folder, basename(target), sep = "/")
}

safe_species_slug <- function(species_name) {
  value <- validate_required_text(species_name, "Species name")
  value <- iconv(value, from = "", to = "ASCII//TRANSLIT", sub = "")
  value <- tolower(gsub("[^a-zA-Z0-9]+", "-", value))
  value <- gsub("(^-+|-+$)", "", value)
  if (!nzchar(value)) stop("Species name cannot form a safe folder name.", call. = FALSE)
  value
}

detect_image_type <- function(path) {
  header <- readBin(path, what = "raw", n = 12L)
  hex <- paste(sprintf("%02x", as.integer(header)), collapse = "")
  if (startsWith(hex, "ffd8ff")) return("jpg")
  if (startsWith(hex, "89504e470d0a1a0a")) return("png")
  if (length(header) >= 12L && rawToChar(header[1:4]) == "RIFF" &&
      rawToChar(header[9:12]) == "WEBP") return("webp")
  if (length(header) >= 6L) {
    text <- rawToChar(header[1:6], multiple = FALSE)
    if (identical(text, "GIF87a") || identical(text, "GIF89a")) return("gif")
  }
  NA_character_
}

managed_photo_absolute_path <- function(photo_reference, library_path) {
  if (is.na(photo_reference) || !nzchar(photo_reference)) return(NA_character_)
  candidate <- normalizePath(file.path(library_path, photo_reference),
                             mustWork = FALSE)
  root <- normalizePath(library_path, mustWork = FALSE)
  # normalizePath() can return backslashes while .Platform$file.sep is `/`
  # under some Windows R builds. Compare canonical forward-slash paths.
  candidate_norm <- tolower(gsub("\\\\", "/", candidate))
  root_norm <- tolower(gsub("\\\\", "/", root))
  boundary <- paste0(sub("/+$", "", root_norm), "/")
  if (!startsWith(candidate_norm, boundary)) return(NA_character_)
  candidate
}
