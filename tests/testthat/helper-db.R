local_bird_db <- function() {
  con <- bird_db_connect(":memory:")
  initialize_bird_db(con)
  withr::defer(DBI::dbDisconnect(con, shutdown = TRUE), envir = parent.frame())
  con
}
