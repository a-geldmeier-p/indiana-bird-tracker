# The contract, not a fixed list of module-name prefixes, is authoritative.
contract <- readLines(".github/agents/workflow-contract.yml", warn = FALSE)
inventory <- paste(readLines("WORKFLOW_INVENTORY.md", warn = FALSE), collapse = "\n")
stable_rows <- grep("^    stable_ids:", contract, value = TRUE)
if (!length(stable_rows)) stop("Workflow contract has no stable IDs.")
stable_ids <- unique(trimws(unlist(strsplit(
  gsub("]", "", gsub("[", "", sub("^    stable_ids:[[:space:]]*", "", stable_rows), fixed = TRUE), fixed = TRUE),
  ",", fixed = TRUE
))))
missing <- stable_ids[!vapply(stable_ids, grepl, logical(1), x = inventory, fixed = TRUE)]
if (length(missing)) stop("Update WORKFLOW_INVENTORY.md for: ", paste(missing, collapse = ", "))
message("Workflow inventory covers all contracted stable IDs.")
