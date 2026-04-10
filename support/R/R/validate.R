#' @keywords internal
pumps <- 1:4

#' @keywords internal
pump_tag_types <- c("RUN", "FRQ", "RSPD", "CSPD")

#' Validate all pump tag combinations against the PI Web API
#'
#' Generates 16 tag candidates per station (4 pumps x 4 types: RUN, FRQ, RSPD,
#' CSPD) and checks each against the PI Web API.
#'
#' @param df_ A data frame with columns `CMMS_ASSET_ID`, `STREET_NAME`,
#'   `STREET_NUMBER`, and `PI_TAG`.
#'
#' @return A data frame of valid tags with columns `CMMS_ASSET_ID`,
#'   `STREET_NAME`, `STREET_NUMBER`, `PI_TAG`, `name` (e.g. `"p1run"`),
#'   and `value` (the full tag path).
#'
#' @importFrom dplyr select mutate filter
#' @importFrom tidyr crossing
#' @keywords internal
check_all_pump_tags <- function(df_) {
  base <- df_ %>%
    dplyr::select("CMMS_ASSET_ID", "STREET_NAME", "STREET_NUMBER", "PI_TAG") %>%
    dplyr::mutate(PI_TAG = paste0(.data$PI_TAG, "_"))

  combos <- expand.grid(pump = pumps, type = pump_tag_types, stringsAsFactors = FALSE)

  tmp <- base %>%
    tidyr::crossing(combos) %>%
    dplyr::mutate(name = paste0("p", .data$pump, tolower(.data$type))) %>%
    dplyr::mutate(value = paste0(.data$PI_TAG, "P", .data$pump, .data$type)) %>%
    dplyr::select("CMMS_ASSET_ID", "STREET_NAME", "STREET_NUMBER", "PI_TAG", "name", "value")

  n <- nrow(tmp)
  message("Checking ", n, " pump tags...")
  tmp$bad_tag <- NA
  for (i in seq_len(n)) {
    if (i %% 500 == 0) message("  ", i, "/", n)
    tmp$bad_tag[i] <- is.null(safe_get_webid(tmp$value[i]))
  }

  tmp %>% dplyr::filter(.data$bad_tag == FALSE)
}

#' Identify stations with multiple pumps or VFD speed control
#'
#' Analyzes SCADA history to detect stations that have more than 2 active pumps
#' or variable frequency drive (VFD) control. Values above 60 are treated as
#' outliers. CSPD, RSPD, and FRQ tags with values above 35 indicate VFD
#' control.
#'
#' @param raw_ A data frame of SCADA time series data with a `datetime` column
#'   and one column per tag (as returned by [get_scada_history()]).
#'
#' @return A data frame with columns `station`, `pump` (max pump number),
#'   `vfd_control` (logical), and `PI_TAG`.
#'
#' @seealso \code{vignette("technical-reference")} for VFD detection
#'   thresholds and pump count business rules.
#'
#' @importFrom tidyr pivot_longer
#' @importFrom dplyr mutate filter group_by summarize select
#' @importFrom stringr str_detect str_remove_all str_sub str_replace str_replace_all
#' @importFrom stats quantile sd
#' @keywords internal
check_multiple_pumps_or_vfd_control <- function(raw_) {
  raw_ %>%
    tidyr::pivot_longer(-"datetime") %>%
    # >60 is sensor error: RUN is 0/1, motor freq caps at 60 Hz
    dplyr::mutate(value = ifelse(.data$value > 60, NA, .data$value)) %>%
    # speed/freq >35 indicates active VFD modulation (vs. 0 or ~60 for constant-speed)
    dplyr::filter(
      (.data$value > 35 & stringr::str_detect(.data$name, "CSPD$|RSPD$|FRQ$"))
      |
      (!stringr::str_detect(.data$name, "CSPD$|RSPD$|FRQ$"))
    ) %>%
    dplyr::group_by(.data$name) %>%
    dplyr::summarize(
      mn = min(.data$value, na.rm = TRUE),
      mu = mean(.data$value, na.rm = TRUE),
      p95 = stats::quantile(.data$value, na.rm = TRUE, probs = 0.95),
      mx = max(.data$value, na.rm = TRUE),
      sd = stats::sd(.data$value, na.rm = TRUE)
    ) %>%
    dplyr::filter(!is.na(.data$sd)) %>%
    # sd > 0 means the tag value changed at least once in 7 days (not flatlined)
    dplyr::filter(.data$sd > 0) %>%
    dplyr::filter(.data$mn >= 0) %>%
    dplyr::mutate(station = stringr::str_remove_all(.data$name, "_P.*$")) %>%
    dplyr::mutate(pump = stringr::str_remove_all(.data$name, "^.*_P")) %>%
    dplyr::mutate(pump = stringr::str_sub(.data$pump, 1, 1)) %>%
    dplyr::mutate(control = stringr::str_remove_all(.data$name, "^.*_P.")) %>%
    dplyr::mutate(control = ifelse(stringr::str_detect(.data$control, "CSPD|RSPD|FRQ"), 1, 0)) %>%
    dplyr::group_by(.data$station) %>%
    dplyr::summarize(pump = max(.data$pump), control = sum(.data$control)) %>%
    dplyr::mutate(vfd_control = .data$control > 0) %>%
    dplyr::select(-"control") %>%
    dplyr::mutate(pump = as.numeric(.data$pump)) %>%
    # flag stations that need special handling (VFD or >2 pumps)
    dplyr::filter(.data$vfd_control | .data$pump > 2) %>%
    dplyr::mutate(PI_TAG = stringr::str_replace_all(.data$station, "\\.", "\\:")) %>%
    dplyr::mutate(PI_TAG = stringr::str_replace(.data$PI_TAG, "\\:[:digit:]$", "-1")) %>%
    dplyr::mutate(PI_TAG = toupper(.data$PI_TAG))
}
