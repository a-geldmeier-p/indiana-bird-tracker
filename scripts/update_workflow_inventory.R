# Rebuild guard: current workflow labels and IDs must remain documented.
source_files <- list.files("R", pattern = "\\.R$", full.names = TRUE)
source_text <- paste(vapply(source_files, paste, character(1), collapse = "\n"), collapse = "\n")
inventory <- paste(readLines("WORKFLOW_INVENTORY.md", warn = FALSE), collapse = "\n")
ids <- unique(unlist(regmatches(source_text, gregexpr('"[A-Za-z0-9_-]+"', source_text))))
ids <- gsub('"', "", ids)
relevant <- ids[grepl("^(species|record|sightings|dashboard|main)-", ids)]
missing <- relevant[!vapply(relevant, grepl, logical(1), x = inventory, fixed = TRUE)]
if (length(missing)) stop("Update WORKFLOW_INVENTORY.md for: ", paste(missing, collapse = ", "))
message("Workflow inventory is current.")
