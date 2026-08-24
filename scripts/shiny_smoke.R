root <- tempfile("bird-tracker-")
dir.create(root)
db <- file.path(root, "birds.duckdb")
photos <- file.path(root, "photos")
refs <- file.path(root, "references")
port <- httpuv::randomPort()

if (.Platform$OS.type == "windows") {
  stop("The CI smoke check requires a Unix-like runner.")
}

app_process <- parallel::mcparallel({
  app <- indianabirdtracker::run_app(
    db_path = db,
    photo_library = photos,
    reference_path = refs
  )
  shiny::runApp(app, port = port, launch.browser = FALSE, quiet = TRUE)
}, silent = TRUE)
on.exit({
  tools::pskill(app_process$pid)
  parallel::mccollect(app_process, wait = FALSE)
}, add = TRUE)

url <- paste0("http://127.0.0.1:", port)
deadline <- Sys.time() + 30
last_error <- NULL
repeat {
  response <- tryCatch(curl::curl_fetch_memory(url), error = function(error) {
    last_error <<- conditionMessage(error)
    NULL
  })
  if (!is.null(response) && identical(response$status_code, 200L)) break
  if (Sys.time() >= deadline) {
    stop("Shiny smoke check did not return HTTP 200 within 30 seconds. Last error: ", last_error)
  }
  Sys.sleep(0.5)
}

message("Shiny smoke check passed.")
