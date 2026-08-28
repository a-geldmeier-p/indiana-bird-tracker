required_files <- c("README.md", "NEWS.md", "USER_GUIDE.md", "WORKFLOW_INVENTORY.md", "docs/playwright/manifest.yml")
missing <- required_files[!file.exists(required_files)]
if (length(missing)) stop("Missing documentation files: ", paste(missing, collapse = ", "))

guide <- readLines("USER_GUIDE.md", warn = FALSE)
inventory <- readLines("WORKFLOW_INVENTORY.md", warn = FALSE)
contract <- readLines(".github/agents/workflow-contract.yml", warn = FALSE)
manifest <- readLines("docs/playwright/manifest.yml", warn = FALSE)

workflow_rows <- grep("^  [a-z0-9_]+:$", contract)
workflow_ids <- sub("^  ([a-z0-9_]+):$", "\\1", contract[workflow_rows])
workflow_headings <- vapply(workflow_rows, function(row) {
  candidates <- contract[seq.int(row + 1L, min(length(contract), row + 4L))]
  value <- grep("^    guide_heading:", candidates, value = TRUE)
  if (!length(value)) stop("Workflow contract is missing guide_heading after: ", contract[[row]])
  trimws(sub("^    guide_heading:", "", value[[1]]))
}, character(1))

for (heading in workflow_headings) {
  if (!any(grepl(paste0("^## ", heading, "$"), guide))) stop("Missing guide heading: ", heading)
}
for (id in grep("stable_ids", contract, value = TRUE)) {
  ids <- sub(".*stable_ids:[[:space:]]*", "", id)
  ids <- gsub("[", "", ids, fixed = TRUE)
  ids <- gsub("]", "", ids, fixed = TRUE)
  ids <- trimws(unlist(strsplit(ids, ",")))
  for (stable_id in ids) if (!any(grepl(stable_id, inventory, fixed = TRUE))) stop("Inventory is missing stable ID: ", stable_id)
}
for (workflow in workflow_ids) {
  marker <- paste0("- id: ", workflow)
  index <- which(grepl(marker, manifest, fixed = TRUE))
  if (!length(index)) stop("Manifest is missing workflow: ", workflow)
  end <- c(grep("^  - id:", manifest), length(manifest) + 1L)
  block_end <- min(end[end > index[[1]]]) - 1L
  block <- manifest[seq.int(index[[1]], block_end)]
  placeholder <- grep("video_placeholder:", block, value = TRUE)
  placeholder <- if (length(placeholder)) {
    gsub('^.*video_placeholder:[[:space:]]*"|"$', "", placeholder[[1]])
  } else character()
  has_video <- any(grepl(paste0('id="tutorial-', workflow, '"'), guide, fixed = TRUE)) ||
    any(grepl(paste0("docs/playwright/artifacts/", workflow, ".webm"), guide, fixed = TRUE))
  has_placeholder <- length(placeholder) && any(grepl(placeholder, guide, fixed = TRUE))
  if (!has_video && !has_placeholder) {
    stop("Guide is missing a video or placeholder for workflow: ", workflow)
  }
}

message("Documentation checks passed.")
