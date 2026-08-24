root <- tempfile("bird-tracker-")
dir.create(root)
db <- file.path(root, "birds.duckdb")
photos <- file.path(root, "photos")
refs <- file.path(root, "references")
port <- httpuv::randomPort()

app_process <- callr::r_bg(
  func = function(db, photos, refs, port) {
    app <- indianabirdtracker::run_app(
      db_path = db,
      photo_library = photos,
      reference_path = refs
    )
    shiny::runApp(app, port = port, launch.browser = FALSE, quiet = TRUE)
  },
  args = list(db = db, photos = photos, refs = refs, port = port),
  libpath = .libPaths(),
  supervise = TRUE,
  stdout = "|",
  stderr = "|"
)
on.exit({
  if (app_process$is_alive()) app_process$kill()
}, add = TRUE)

url <- paste0("http://127.0.0.1:", port)
deadline <- Sys.time() + 30
last_error <- NULL
repeat {
  if (!app_process$is_alive()) app_process$get_result()
  response <- tryCatch(curl::curl_fetch_memory(url), error = function(error) {
    last_error <<- conditionMessage(error)
    NULL
  })
  if (!is.null(response) && identical(response$status_code, 200L)) break
  if (Sys.time() >= deadline) {
    stop(
      "Shiny smoke check did not return HTTP 200 within 30 seconds. Last error: ", last_error,
      "\nChild-process output:\n",
      paste(c(app_process$read_all_output(), app_process$read_all_error()), collapse = "\n")
    )
  }
  Sys.sleep(0.5)
}

message("Shiny smoke check passed.")
