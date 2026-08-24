required_files <- c("README.md", "NEWS.md", "USER_GUIDE.md", "WORKFLOW_INVENTORY.md", "docs/playwright/manifest.yml")
missing <- required_files[!file.exists(required_files)]
if (length(missing)) stop("Missing documentation files: ", paste(missing, collapse = ", "))

guide <- readLines("USER_GUIDE.md", warn = FALSE)
inventory <- readLines("WORKFLOW_INVENTORY.md", warn = FALSE)
contract <- readLines(".github/agents/workflow-contract.yml", warn = FALSE)
manifest <- readLines("docs/playwright/manifest.yml", warn = FALSE)

headings <- c("Browse the Indiana catalog", "Record a sighting", "Review and filter My Sightings", "View the dashboard")
for (heading in headings) if (!any(grepl(paste0("^## ", heading, "$"), guide))) stop("Missing guide heading: ", heading)
for (id in grep("stable_ids", contract, value = TRUE)) {
  ids <- sub(".*stable_ids:[[:space:]]*", "", id)
  ids <- gsub("[\\[\\]]", "", ids)
  ids <- trimws(unlist(strsplit(ids, ",")))
  for (stable_id in ids) if (!any(grepl(stable_id, inventory, fixed = TRUE))) stop("Inventory is missing stable ID: ", stable_id)
}
for (workflow in c("catalog", "record_sighting", "my_sightings", "dashboard")) if (!any(grepl(paste0("id: ", workflow), manifest, fixed = TRUE))) stop("Manifest is missing workflow: ", workflow)
if (sum(grepl("VIDEO PLACEHOLDER|docs/playwright/artifacts", guide)) < 4) stop("Guide must retain four video placeholders or real artifact links")

message("Documentation checks passed.")
