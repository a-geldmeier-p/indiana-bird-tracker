args <- commandArgs(trailingOnly = TRUE)
if (!length(args) || !nzchar(args[[1]])) stop("Usage: Rscript scripts/update_news.R 'Concise change summary'")
news <- readLines("NEWS.md", warn = FALSE)
entry <- paste0("- ", format(Sys.Date()), ": ", args[[1]])
if (entry %in% news) quit(status = 0)
anchor <- which(grepl("^#|^##", news))[1]
writeLines(append(news, entry, after = anchor), "NEWS.md")
