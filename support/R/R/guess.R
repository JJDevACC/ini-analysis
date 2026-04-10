#' @keywords internal
grids <- c("north", "east", "south", "west", "nassau", "stjohns")

#' @keywords internal
tag_suffixes <- c("", "B", "-1")

#' Guess PI tag names from street address data
#'
#' For assets with missing or invalid PI tags, builds candidate tag names from
#' the common format, then validates each against the PI Web API.
#'
#' @details
#' Candidate format: `wwl:{grid}:{first 3 chars of street}{address}{suffix}_P1RUN`
#'
#' Tries all combinations of [grids] and [tag_suffixes], stopping at the first
#' valid match per asset to minimize API calls.
#'
#' @param df A data frame with columns `STREET_NAME`, `STREET_NUMBER`, and
#'   `CMMS_ASSET_ID`.
#'
#' @return A data frame with columns `CMMS_ASSET_ID` and `PI_TAG`. `PI_TAG`
#'   is `NA` for assets where no valid tag could be guessed.
#'
#' @seealso \code{vignette("technical-reference")} for tag naming convention,
#'   suffix meanings, and search order.
#'
#' @importFrom stringr str_remove_all str_remove
#' @keywords internal
guess_tag_name <- function(df) {
  if (nrow(df) == 0) {
    return(data.frame(CMMS_ASSET_ID = character(), PI_TAG = character()))
  }

  candidates <- df %>%
    dplyr::mutate(CODE = stringr::str_remove_all(.data$STREET_NAME, "[:space:]")) %>%
    dplyr::mutate(CODE = substr(.data$CODE, 1, 3)) %>%
    dplyr::mutate(CODE = paste0(.data$CODE, .data$STREET_NUMBER))

  results <- data.frame(CMMS_ASSET_ID = character(), PI_TAG = character())
  n <- nrow(candidates)
  message("Guessing tag names for ", n, " assets...")

  for (i in seq_len(n)) {
    if (i %% 10 == 0) message("  ", i, "/", n)
    asset_id <- candidates$CMMS_ASSET_ID[i]
    street_name <- candidates$STREET_NAME[i]
    street_number <- candidates$STREET_NUMBER[i]
    code <- candidates$CODE[i]
    found <- FALSE

    for (suffix in tag_suffixes) {
      if (found) break
      for (grid in grids) {
        tag_candidate <- paste0("wwl:", grid, ":", code, suffix, "_P1RUN")
        webid <- safe_get_webid(tag_candidate)
        if (!is.null(webid)) {
          base_tag <- stringr::str_remove(tag_candidate, "_P1RUN$")
          results <- rbind(results, data.frame(
            CMMS_ASSET_ID = asset_id,
            STREET_NAME = street_name,
            STREET_NUMBER = street_number,
            PI_TAG = base_tag
          ))
          found <- TRUE
          break
        }
      }
    }

    if (!found) {
      results <- rbind(results, data.frame(
        CMMS_ASSET_ID = asset_id,
        STREET_NAME = street_name,
        STREET_NUMBER = street_number,
        PI_TAG = NA
      ))
    }
  }

  results
}

#' Guess tag names for all flagged assets
#'
#' Driver function that applies [guess_tag_name()] to assets flagged as
#' `"Missing Data (NA)"` or `"Bad Tag"`. All tags are normalized to uppercase.
#'
#' @param ls_check A data frame of bad-tag rows from [check_tags()], containing
#'   only `"Missing Data (NA)"` and `"Bad Tag"` rows.
#'
#' @return A data frame with columns `CMMS_ASSET_ID` and `PI_TAG`.
#'
#' @importFrom dplyr mutate
#' @keywords internal
guess_tag_name_from_df <- function(ls_check) {
  guess_tag_name(ls_check) %>%
    dplyr::mutate(PI_TAG = toupper(.data$PI_TAG))
}
