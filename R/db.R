#' Default path for the personal bird database
#'
#' @return A normalized path beneath the user's platform-specific application
#'   data directory. The directory is created if necessary.
#' @export
bird_db_path <- function() {
  directory <- tools::R_user_dir("indianabirdtracker", which = "data")
  ensure_directory(directory, "Application data directory")
  file.path(directory, "bird_tracker.duckdb")
}

#' Connect to an Indiana Bird Tracker database
#'
#' @param path DuckDB file path, or `":memory:"` for a temporary database.
#' @return A live DBI connection. Call `DBI::dbDisconnect(con, shutdown = TRUE)`
#'   when finished.
#' @export
bird_db_connect <- function(path = bird_db_path()) {
  stopifnot(is.character(path), length(path) == 1L, nzchar(path))
  if (!identical(path, ":memory:")) {
    ensure_directory(dirname(path), "Database directory")
  }
  DBI::dbConnect(duckdb::duckdb(), dbdir = path, read_only = FALSE)
}

#' Initialize the local DuckDB schema and species catalog
#'
#' This function is idempotent. Existing sightings and species are retained;
#' species missing from the database are added from the seed catalog.
#'
#' @param con A DBI connection returned by [bird_db_connect()].
#' @param seed_path Optional path to a species CSV. When omitted, the packaged
#'   packaged Indiana catalog is used.
#' @return `con`, invisibly.
#' @export
initialize_bird_db <- function(con, seed_path = NULL) {
  seed <- load_species_seed(seed_path)

  DBI::dbWithTransaction(con, {
    DBI::dbExecute(con, paste(
      "CREATE TABLE IF NOT EXISTS species (",
      "species_code VARCHAR PRIMARY KEY,",
      "common_name VARCHAR NOT NULL,",
      "scientific_name VARCHAR NOT NULL,",
      "bird_group VARCHAR NOT NULL,",
      "status_note VARCHAR NOT NULL,",
      "brief_description VARCHAR NOT NULL",
      ")"
    ))
    DBI::dbExecute(con,
      "ALTER TABLE species ADD COLUMN IF NOT EXISTS brief_description VARCHAR DEFAULT ''"
    )
    DBI::dbExecute(con, "CREATE SEQUENCE IF NOT EXISTS sightings_id_seq START 1")
    DBI::dbExecute(con, paste(
      "CREATE TABLE IF NOT EXISTS sightings (",
      "sighting_id BIGINT PRIMARY KEY DEFAULT nextval('sightings_id_seq'),",
      "species_code VARCHAR NOT NULL REFERENCES species(species_code),",
      "observed_at TIMESTAMP NOT NULL,",
      "location VARCHAR NOT NULL,",
      "county VARCHAR NOT NULL,",
      "notes VARCHAR,",
      "photo_reference VARCHAR,",
      "created_at TIMESTAMP NOT NULL DEFAULT current_timestamp",
      ")"
    ))
    DBI::dbExecute(con,
      "CREATE INDEX IF NOT EXISTS sightings_observed_at_idx ON sightings(observed_at)"
    )

    # The original seed used one compound scrub-jay row. Migrate that code to
    # California Scrub-Jay so existing sightings remain valid; the seed loop
    # then adds the separate Woodhouse's Scrub-Jay row.
    old_jay <- DBI::dbGetQuery(con,
      "SELECT species_code FROM species WHERE species_code = 'APHELOCOMA_SP'")
    if (nrow(old_jay)) {
      DBI::dbExecute(con,
        "UPDATE sightings SET species_code = 'APHELOCOMA_CALIFORNICA' WHERE species_code = 'APHELOCOMA_SP'")
      DBI::dbExecute(con,
        "UPDATE species SET species_code = 'APHELOCOMA_CALIFORNICA', common_name = 'California Scrub-Jay', scientific_name = 'Aphelocoma californica' WHERE species_code = 'APHELOCOMA_SP'")
    }

    for (i in seq_len(nrow(seed))) {
      existing <- DBI::dbGetQuery(con,
        "SELECT species_code FROM species WHERE scientific_name = ? LIMIT 1",
        params = list(seed$scientific_name[[i]]))
      if (nrow(existing)) {
        DBI::dbExecute(con, paste(
          "UPDATE species SET common_name = ?, bird_group = ?, status_note = ?,",
          "brief_description = ? WHERE species_code = ?"
        ), params = list(seed$common_name[[i]], seed$bird_group[[i]],
                         seed$status_note[[i]], seed$brief_description[[i]],
                         existing$species_code[[1]]))
      } else {
        DBI::dbExecute(con, paste(
          "INSERT INTO species (species_code, common_name, scientific_name,",
          "bird_group, status_note, brief_description) VALUES (?, ?, ?, ?, ?, ?)"
        ), params = unname(as.list(seed[i, , drop = FALSE])))
      }
    }
  })

  invisible(con)
}

#' Add a personal bird sighting
#'
#' @param con An initialized bird tracker DBI connection.
#' @param species_code Species identifier from [list_species()].
#' @param observed_at Date-time of observation; coercible to `POSIXct`.
#' @param location Human-readable place name.
#' @param county Indiana county name.
#' @param notes Optional notes.
#' @param photo_reference Optional local path or URL. The app stores only this
#'   reference; it does not copy or upload the image.
#' @return The new integer sighting ID.
#' @export
add_sighting <- function(con, species_code, observed_at, location, county,
                         notes = "", photo_reference = "") {
  species_code <- validate_required_text(species_code, "Species")
  location <- validate_required_text(location, "Location")
  county <- validate_required_text(county, "County")
  observed_at <- as.POSIXct(observed_at, tz = "America/Indiana/Indianapolis")
  if (length(observed_at) != 1L || is.na(observed_at)) {
    stop("Observation date/time must be valid.", call. = FALSE)
  }
  exists <- DBI::dbGetQuery(
    con, "SELECT count(*) AS n FROM species WHERE species_code = ?",
    params = list(species_code)
  )$n[[1]]
  if (exists != 1) stop("Species code is not in the catalog.", call. = FALSE)

  result <- DBI::dbGetQuery(con, paste(
    "INSERT INTO sightings",
    "(species_code, observed_at, location, county, notes, photo_reference)",
    "VALUES (?, ?, ?, ?, ?, ?) RETURNING sighting_id"
  ), params = list(
    species_code, observed_at, location, county,
    normalize_optional_text(notes), normalize_optional_text(photo_reference)
  ))
  as.integer(result$sighting_id[[1]])
}

#' List species in the reference catalog
#'
#' @param con An initialized bird tracker DBI connection.
#' @param search Optional case-insensitive search across common and scientific
#'   names only. Use `bird_group` and `status_note` for the other filters.
#' @param bird_group Optional exact bird-group filter.
#' @param status_note Optional exact status filter.
#' @return A data frame ordered by common name.
#' @export
list_species <- function(con, search = "", bird_group = "", status_note = "") {
  search <- normalize_optional_text(search)
  bird_group <- normalize_optional_text(bird_group)
  status_note <- normalize_optional_text(status_note)
  sql <- paste(
    "SELECT species_code, common_name, scientific_name, bird_group, status_note,",
    "brief_description",
    "FROM species WHERE 1 = 1"
  )
  params <- list()
  if (!is.na(search)) {
    sql <- paste(sql, "AND (lower(common_name) LIKE '%' || lower(?) || '%'",
                 "OR lower(scientific_name) LIKE '%' || lower(?) || '%')")
    params <- c(params, list(search, search))
  }
  if (!is.na(bird_group)) {
    sql <- paste(sql, "AND bird_group = ?")
    params <- c(params, list(bird_group))
  }
  if (!is.na(status_note)) {
    sql <- paste(sql, "AND status_note = ?")
    params <- c(params, list(status_note))
  }
  sql <- paste(sql, "ORDER BY common_name")
  if (length(params)) DBI::dbGetQuery(con, sql, params = params) else DBI::dbGetQuery(con, sql)
}

#' List personal bird sightings
#'
#' @param con An initialized bird tracker DBI connection.
#' @param species_code Optional exact species filter.
#' @param county Optional exact county filter.
#' @param start_date,end_date Optional inclusive date bounds.
#' @return A data frame ordered newest first.
#' @export
list_sightings <- function(con, species_code = "", county = "",
                           start_date = NULL, end_date = NULL) {
  species_code <- normalize_optional_text(species_code)
  county <- normalize_optional_text(county)
  start_date <- normalize_date(start_date, "start_date")
  end_date <- normalize_date(end_date, "end_date")
  if (!is.null(start_date) && !is.null(end_date) && start_date > end_date) {
    stop("start_date must be on or before end_date.", call. = FALSE)
  }
  sql <- paste(
    "SELECT s.sighting_id, sp.common_name, sp.scientific_name, s.observed_at,",
    "s.location, s.county, s.notes, s.photo_reference",
    "FROM sightings s JOIN species sp USING (species_code)",
    "WHERE 1 = 1"
  )
  params <- list()
  if (!is.na(species_code)) {
    sql <- paste(sql, "AND s.species_code = ?")
    params <- c(params, list(species_code))
  }
  if (!is.na(county)) {
    sql <- paste(sql, "AND s.county = ?")
    params <- c(params, list(county))
  }
  if (!is.null(start_date)) {
    sql <- paste(sql, "AND CAST(s.observed_at AS DATE) >= ?")
    params <- c(params, list(start_date))
  }
  if (!is.null(end_date)) {
    sql <- paste(sql, "AND CAST(s.observed_at AS DATE) <= ?")
    params <- c(params, list(end_date))
  }
  sql <- paste(sql, "ORDER BY s.observed_at DESC, s.sighting_id DESC")
  if (length(params)) DBI::dbGetQuery(con, sql, params = params) else DBI::dbGetQuery(con, sql)
}

#' Summarize a personal birding database
#'
#' @param con An initialized bird tracker DBI connection.
#' @return A list with `total_sightings`, `distinct_species`, and `recent`.
#' @export
dashboard_summary <- function(con, recent_limit = 5L) {
  recent_limit <- as.integer(recent_limit)
  if (length(recent_limit) != 1L || is.na(recent_limit) || recent_limit < 1L) {
    stop("recent_limit must be a positive integer.", call. = FALSE)
  }
  counts <- DBI::dbGetQuery(con, paste(
    "SELECT count(*) AS total_sightings,",
    "count(DISTINCT species_code) AS distinct_species FROM sightings"
  ))
  recent <- DBI::dbGetQuery(con, paste(
    "SELECT s.species_code, sp.common_name, s.observed_at, s.location, s.county",
    "FROM sightings s JOIN species sp USING (species_code)",
    "ORDER BY s.observed_at DESC, s.sighting_id DESC LIMIT ?"
  ), params = list(recent_limit))
  list(
    total_sightings = as.integer(counts$total_sightings[[1]]),
    distinct_species = as.integer(counts$distinct_species[[1]]),
    recent = recent
  )
}

format_observation_time <- function(value,
                                    tz = "America/Indiana/Indianapolis") {
  if (inherits(value, "POSIXt")) {
    parsed <- as.POSIXct(value, tz = tz)
  } else {
    parsed <- as.POSIXct(value, origin = "1970-01-01", tz = tz)
  }
  format(parsed, "%b %d, %Y %I:%M %p", tz = tz, usetz = FALSE)
}

set_sighting_photo <- function(con, sighting_id, photo_reference) {
  affected <- DBI::dbExecute(con,
    "UPDATE sightings SET photo_reference = ? WHERE sighting_id = ?",
    params = list(validate_required_text(photo_reference, "Photo path"), as.integer(sighting_id))
  )
  if (affected != 1L) stop("Sighting was not found for photo update.", call. = FALSE)
  invisible(sighting_id)
}

validate_required_text <- function(value, label) {
  if (length(value) != 1L || is.na(value) || !nzchar(trimws(value))) {
    stop(paste0(label, " is required."), call. = FALSE)
  }
  trimws(as.character(value))
}

normalize_optional_text <- function(value) {
  if (is.null(value) || length(value) == 0L || is.na(value[[1]]) ||
      !nzchar(trimws(as.character(value[[1]])))) return(NA_character_)
  trimws(as.character(value[[1]]))
}

normalize_date <- function(value, label) {
  if (is.null(value) || length(value) == 0L || is.na(value[[1]]) ||
      !nzchar(as.character(value[[1]]))) return(NULL)
  parsed <- as.Date(value[[1]])
  if (is.na(parsed)) stop(paste(label, "must be a valid date."), call. = FALSE)
  parsed
}
