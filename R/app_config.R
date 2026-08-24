#' Access application configuration
#'
#' @param value Name of the configuration value.
#' @param config Active configuration profile.
#' @param use_parent Logical; passed to `golem::get_golem_config()`.
#' @return A configuration value.
#' @keywords internal
get_golem_config <- function(value, config = Sys.getenv("R_CONFIG_ACTIVE", "default"),
                             use_parent = TRUE) {
  getter <- utils::getFromNamespace("get_golem_config", "golem")
  getter(value = value, config = config, use_parent = use_parent)
}

