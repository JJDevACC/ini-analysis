#' @keywords internal
tag_cols <- c("STREET_NAME", "STREET_NUMBER", "CMMS_ASSET_ID", "PI_TAG")

#' Classify PI tags into quality categories
#'
#' Normalizes all tags (stripping any trailing `_`) and validates them in a
#' single pass against the PI Web API using [safe_get_webid()].
#'
#' @param ls A data frame of lift stations with at least the columns in
#'   [tag_cols].
#'
#' @return A named list with five data frames:
#'   \describe{
#'     \item{all_stations}{All input rows}
#'     \item{na_tags}{Rows where `PI_TAG` is `NA`}
#'     \item{none_tags}{Rows where `PI_TAG` contains `"NONE"`}
#'     \item{valid_tags}{Rows that passed PI Web API validation}
#'     \item{bad_tags}{Rows that failed PI Web API validation}
#'   }
#'
#' @seealso \code{vignette("technical-reference")} for classification
#'   categories and validation method.
#'
#' @importFrom dplyr filter select mutate
#' @importFrom stringr str_detect str_remove_all str_replace str_remove
#' @keywords internal
classify_tags <- function(ls) {
  all_stations <- ls %>%
    dplyr::select(dplyr::all_of(tag_cols))

  # Tags marked NONE
  none_tags <- ls %>%
    dplyr::filter(stringr::str_detect(.data$PI_TAG, "NONE")) %>%
    dplyr::select(dplyr::all_of(tag_cols))

  # NA Tags
  na_tags <- ls %>%
    dplyr::filter(is.na(.data$PI_TAG)) %>%
    dplyr::select(dplyr::all_of(tag_cols))

  # All remaining tags — normalize then validate in one pass
  candidates <- ls %>%
    dplyr::filter(!is.na(.data$PI_TAG) & !stringr::str_detect(.data$PI_TAG, "NONE")) %>%
    dplyr::select(dplyr::all_of(tag_cols)) %>%
    dplyr::mutate(PI_TAG = stringr::str_remove_all(.data$PI_TAG, " ")) %>%
    dplyr::mutate(PI_TAG = stringr::str_replace(.data$PI_TAG, "-\\*", "")) %>%
    dplyr::mutate(PI_TAG = stringr::str_remove_all(.data$PI_TAG, "\r|\n")) %>%
    dplyr::mutate(PI_TAG = stringr::str_remove(.data$PI_TAG, "_$"))

  candidates$bad_tag <- FALSE
  n <- nrow(candidates)
  if (n > 0) message("Checking ", n, " tags...")
  for (i in seq_along(candidates$PI_TAG)) {
    if (i %% 100 == 0) message("  ", i, "/", n)
    candidates$bad_tag[i] <- is.null(safe_get_webid(paste0(candidates$PI_TAG[i], "_P1RUN")))
  }

  list(
    all_stations = all_stations,
    na_tags = na_tags,
    none_tags = none_tags,
    valid_tags = candidates %>% dplyr::filter(!.data$bad_tag),
    bad_tags = candidates %>% dplyr::filter(.data$bad_tag)
  )
}

#' Print a tree-formatted summary of tag classification
#'
#' Displays a hierarchical breakdown of tag categories with counts and
#' percentages, using [data.tree::Node].
#'
#' @param categories A list returned by [classify_tags()].
#'
#' @return Invisibly returns the [data.tree::Node] tree (called for its
#'   side-effect of printing).
#'
#' @importFrom data.tree Node
#' @export
print_tag_summary <- function(categories) {
  total <- nrow(categories$all_stations)
  pct <- function(n) paste0("(", round(n / total * 100, 1), "%)")

  tree <- data.tree::Node$new("Pump Stations", matches = total, pct = "")
  tree$AddChild("Missing Data (NA)",
    matches = nrow(categories$na_tags), pct = pct(nrow(categories$na_tags)))
  tree$AddChild("No SCADA",
    matches = nrow(categories$none_tags), pct = pct(nrow(categories$none_tags)))
  tree$AddChild("Valid Tag",
    matches = nrow(categories$valid_tags), pct = pct(nrow(categories$valid_tags)))
  tree$AddChild("Bad Tag",
    matches = nrow(categories$bad_tags), pct = pct(nrow(categories$bad_tags)))

  print(tree, "matches", "pct")
}

#' Classify tags and return rows that need correction
#'
#' Wrapper that calls [classify_tags()] and [print_tag_summary()], then returns
#' a combined data frame of NA and bad-tag rows for downstream processing by
#' [guess_tag_name_from_df()].
#'
#' @param ls A data frame of lift stations (see [classify_tags()]).
#'
#' @return A data frame with columns `STREET_NAME`, `STREET_NUMBER`,
#'   `CMMS_ASSET_ID`, `PI_TAG`, and `levelName` indicating the category.
#'
#' @importFrom dplyr select mutate
#' @export
check_tags <- function(ls) {
  categories <- classify_tags(ls)
  print_tag_summary(categories)

  na_tags <- categories$na_tags
  na_tags$levelName <- "Missing Data (NA)"
  na_tags$bad_tag <- NA

  bad <- categories$bad_tags
  bad$levelName <- "Bad Tag"

  rbind(na_tags, bad) %>%
    dplyr::select(-"bad_tag") %>%
    dplyr::mutate(PI_TAG = ifelse(.data$levelName == "Bad Tag", NA, toupper(.data$PI_TAG)))
}
