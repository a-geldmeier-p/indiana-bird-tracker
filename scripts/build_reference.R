args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L) stop("Usage: Rscript scripts/build_reference.R SITE_DIR")

site_dir <- args[[1L]]
rd_files <- sort(list.files("man", pattern = "\\.Rd$", full.names = TRUE))
if (!length(rd_files)) stop("No Roxygen .Rd files found in man/")

reference_dir <- file.path(site_dir, "reference")
dir.create(reference_dir, recursive = TRUE, showWarnings = FALSE)
package_name <- read.dcf("DESCRIPTION", fields = "Package")[[1L]]
topics <- tools::file_path_sans_ext(basename(rd_files))
titles <- character(length(rd_files))

for (i in seq_along(rd_files)) {
  rendered <- tempfile(fileext = ".html")
  suppressWarnings(tools::Rd2HTML(
    rd_files[[i]], out = rendered, package = package_name,
    no_links = TRUE, standalone = TRUE
  ))
  html <- paste(readLines(rendered, warn = FALSE, encoding = "UTF-8"), collapse = "\n")
  unlink(rendered)

  start <- regexpr("<main>", html, fixed = TRUE)[[1L]]
  end <- regexpr("</main>", html, fixed = TRUE)[[1L]]
  if (start < 0L || end <= start) stop("Could not extract R help page: ", rd_files[[i]])
  body <- substr(html, start + nchar("<main>"), end - 1L)
  heading <- regmatches(body, regexpr("<h2>[^<]+</h2>", body, perl = TRUE))
  titles[[i]] <- if (length(heading) && nzchar(heading)) {
    sub("</h2>$", "", sub("^<h2>", "", heading))
  } else topics[[i]]

  writeLines(c(
    "---", "layout: default", paste0("title: ", topics[[i]]),
    "section: reference", "---", "{% raw %}", body, "{% endraw %}"
  ), file.path(reference_dir, paste0(topics[[i]], ".html")), useBytes = TRUE)
}

links <- sprintf("- [`%s`](%s.html): %s", topics, topics, titles)
writeLines(c(
  "---", "layout: default", "title: Function documentation",
  "section: reference", "---", "# Function documentation", "",
  "Generated from the package's Roxygen documentation (`man/*.Rd`).", "", links
), file.path(reference_dir, "index.md"), useBytes = TRUE)

message("Built ", length(rd_files), " function documentation pages.")
