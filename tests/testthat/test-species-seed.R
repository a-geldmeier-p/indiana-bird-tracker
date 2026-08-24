test_that("the sourced Indiana catalog is valid and searchable", {
  con <- local_bird_db()
  all_species <- list_species(con)
  expect_equal(nrow(all_species), 425)
  expect_equal(nrow(all_species), length(unique(all_species$species_code)))
  expect_contains(list_species(con, "cardinal")$common_name, "Northern Cardinal")
  expect_true(all(list_species(con, bird_group = "Woodpeckers")$bird_group == "Woodpeckers"))
  expect_true(all(list_species(con, status_note = "Indiana State Endangered")$status_note ==
                    "Indiana State Endangered"))
  expect_equal(nrow(list_species(con, "endangered")), 0)
  expect_true(all(nzchar(all_species$brief_description)))
})

test_that("initialization is idempotent", {
  con <- local_bird_db()
  before <- nrow(list_species(con))
  initialize_bird_db(con)
  expect_equal(nrow(list_species(con)), before)
})

test_that("initialization migrates an older species table without duplicating taxa", {
  con <- bird_db_connect(":memory:")
  withr::defer(DBI::dbDisconnect(con, shutdown = TRUE))
  DBI::dbExecute(con, paste(
    "CREATE TABLE species (species_code VARCHAR PRIMARY KEY, common_name VARCHAR NOT NULL,",
    "scientific_name VARCHAR NOT NULL, bird_group VARCHAR NOT NULL, status_note VARCHAR NOT NULL)"
  ))
  DBI::dbExecute(con,
    "INSERT INTO species VALUES ('NOCA', 'Northern Cardinal', 'Cardinalis cardinalis', 'Cardinals', 'old')"
  )
  initialize_bird_db(con)
  expect_equal(nrow(list_species(con)), 425)
  cardinal <- list_species(con, "Northern Cardinal")
  expect_equal(cardinal$species_code, "NOCA")
  expect_true(nzchar(cardinal$brief_description))
})
