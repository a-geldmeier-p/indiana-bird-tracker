# Rebuild the packaged catalog from authoritative source snapshots.
#
# Occurrence scope: Indiana DNR Birds of Indiana list (revised September 2021).
# Taxonomy/range enrichment: Cornell Lab eBird/Clements Checklist v2025.
# Retrieval date for the packaged snapshot: 2026-08-18.

dnr_path <- file.path("work", "indiana-dnr-birds.html")
clements_path <- file.path("work", "clements_v2025.csv")
output_path <- file.path("inst", "extdata", "indiana_bird_catalog.csv")

dnr_url <- paste0(
  "https://secure.in.gov/dnr/fish-and-wildlife/nongame-and-endangered-wildlife/",
  "birds/birds-of-indiana-list/"
)
clements_url <- paste0(
  "https://www.birds.cornell.edu/clementschecklist/wp-content/uploads/2025/10/",
  "Clements_v2025-October-2025.csv?download=1"
)

dir.create("work", showWarnings = FALSE)
if (!file.exists(dnr_path)) utils::download.file(dnr_url, dnr_path, mode = "wb")
if (!file.exists(clements_path)) {
  utils::download.file(clements_url, clements_path, mode = "wb",
    headers = c("User-Agent" = "Mozilla/5.0", "Referer" = paste0(
      "https://www.birds.cornell.edu/clementschecklist/introduction/updateindex/",
      "october-2025/2025-citation-checklist-downloads/"
    )))
}

stopifnot(file.exists(dnr_path), file.exists(clements_path))

clean_html <- function(value) {
  value <- gsub("(?is)<[^>]+>", "", value, perl = TRUE)
  replacements <- c(
    "&nbsp;" = " ", "&amp;" = "&", "&#39;" = "'", "&rsquo;" = "'",
    "&ldquo;" = "\"", "&rdquo;" = "\"", "&ndash;" = "-", "&mdash;" = "-"
  )
  for (from in names(replacements)) value <- gsub(from, replacements[[from]], value, fixed = TRUE)
  trimws(gsub("[[:space:]]+", " ", value))
}

html <- paste(readLines(dnr_path, warn = FALSE, encoding = "UTF-8"), collapse = "\n")
table <- sub("(?is).*?<table id=\"dnrtable\">", "", html, perl = TRUE)
table <- sub("(?is)</table>.*", "", table, perl = TRUE)
rows <- regmatches(table, gregexpr("(?is)<tr.*?</tr>", table, perl = TRUE))[[1]]

records <- list()
family_scientific <- NA_character_
bird_group <- NA_character_
for (row in rows) {
  cells <- regmatches(row, gregexpr("(?is)<td.*?</td>", row, perl = TRUE))[[1]]
  if (!length(cells)) next
  values <- vapply(cells, clean_html, character(1))
  if (grepl("Family:", values[[1]], fixed = TRUE)) {
    family_scientific <- sub("^Family: ([^ (]+).*$", "\\1", values[[1]])
    bird_group <- sub("^.*\\((.*)\\)$", "\\1", values[[1]])
    if (identical(bird_group, values[[1]])) bird_group <- family_scientific
    next
  }
  if (length(values) == 3L) {
    records[[length(records) + 1L]] <- data.frame(
      common_name = values[[1]], scientific_name = values[[2]],
      dnr_status = values[[3]], family_scientific = family_scientific,
      bird_group = bird_group, stringsAsFactors = FALSE
    )
  }
}
dnr <- do.call(rbind, records)
stopifnot(nrow(dnr) > 400L)

clements <- read.csv(clements_path, check.names = FALSE, stringsAsFactors = FALSE,
                     encoding = "UTF-8")
clements <- clements[clements$category == "species", ]
match_index <- match(dnr$common_name, clements[["English name"]])
scientific_name <- clements[["scientific name"]][match_index]
scientific_name[is.na(scientific_name)] <- dnr$scientific_name[is.na(scientific_name)]

status_labels <- c(
  "-" = "No special state or federal status code shown",
  "SC" = "Indiana Special Concern", "SE" = "Indiana State Endangered",
  "FT" = "Federally Threatened", "FE" = "Federally Endangered",
  "FC" = "Federal Candidate", "X" = "Exotic or introduced"
)
status_note <- unname(status_labels[dnr$dnr_status])
status_note[is.na(status_note)] <- paste("Indiana DNR status", dnr$dnr_status[is.na(status_note)])

range <- clements$range[match_index]
range[is.na(range) | !nzchar(range)] <- "Range context unavailable in the matched Cornell record."
brief <- paste0(
  tools::toTitleCase(dnr$bird_group), ". Range: ", range,
  " Indiana listing: ", status_note, "."
)

make_code <- function(scientific_name) {
  code <- toupper(gsub("[^A-Za-z0-9]+", "_", scientific_name))
  sub("_+$", "", code)
}

seed <- data.frame(
  species_code = vapply(scientific_name, make_code, character(1)),
  common_name = dnr$common_name,
  scientific_name = scientific_name,
  bird_group = tools::toTitleCase(dnr$bird_group),
  status_note = status_note,
  brief_description = brief,
  stringsAsFactors = FALSE
)
stopifnot(!anyDuplicated(seed$species_code), !anyDuplicated(seed$scientific_name))
seed <- seed[order(seed$common_name), ]
write.csv(seed, output_path, row.names = FALSE, na = "", fileEncoding = "UTF-8")

cat("Indiana DNR species:", nrow(seed), "\n")
cat("Matched to Cornell species by common name:", sum(!is.na(match_index)), "\n")
cat("Unmatched DNR taxa:", sum(is.na(match_index)), "\n")
if (anyNA(match_index)) print(dnr[is.na(match_index), c("common_name", "scientific_name")])
