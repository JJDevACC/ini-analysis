#' @details
#' Smallest wetwell area to support a duplex is 5 ft diameter -> 19.6 ft^2
#' @keywords internal
MIN_WETWELL_AREA <- pi * 5^2 / 4

#' @details
#' Typical wetwell area for JEA station is 8 ft diameter -> 50.3 ft^2.
#' Used as default if diameter data is missing.
#' @keywords internal
DEFAULT_WETWELL_AREA <- pi * 8^2 / 4

#' Build PI tag master list from GIS data
#'
#' Main pipeline entry point (Step 1). Loads lift station data from GIS,
#' validates tags, guesses missing tag names, and exports to CSV
#'
#' @details
#' Pipeline steps:
#' 1. Load GIS lift station data via [get_ls_from_gis()]
#' 2. Classify and validate tags via [check_tags()]
#' 3. Guess missing/bad tag names via [guess_tag_name_from_df()]
#' 4. Join corrected tags with original GIS data
#' 6. Filter to valid lift stations
#'    (i.e. `CMMS_ASSET_ID` starting with `"LS"` or `"BPS"`)
#' 7. Export to `data/pi_tag_master_list.csv` OR
#'    user-defined path (`outfile` argument)
#'
#' Prints warnings for duplicate `CMMS_ASSET_ID`s and `PI_TAG`s.
#'
#' @param verbose Logical. If `TRUE` (default), prints export summary,
#'   duplicate counts, and a data glimpse to the console.
#' @param log_path Character. Optional path to a log file. If provided, the
#'   export summary is appended to the file with a timestamp.
#'
#' @return A named list (invisibly) with elements:
#'   \describe{
#'     \item{export}{The exported data frame.}
#'     \item{n_rows}{Number of rows exported.}
#'     \item{outfile}{Path the CSV was written to.}
#'     \item{dup_asset_ids}{Data frame of duplicate `CMMS_ASSET_ID` counts.}
#'     \item{dup_pi_tags}{Data frame of duplicate `PI_TAG` counts.}
#'   }
#'
#' @seealso \code{vignette("usage-guide")} for step-by-step instructions,
#'   \code{vignette("technical-reference")} for prerequisites and data file
#'   requirements.
#'
#' @importFrom dplyr full_join select distinct filter count
#' @importFrom stringr str_detect
#' @importFrom utils write.csv
#' @export
validate_gis <- function(outfile = "out/pi_tag_master_list.csv",
                         verbose = TRUE,
                         log_path = NULL) {

  ls <- get_ls_from_gis()
  # TODO: Manually Adding Tag, revise to make without '_' default
  ls_check <- check_tags(ls)
  ls_ <- guess_tag_name_from_df(
    ls_check[ls_check$levelName %in% c("Missing Data (NA)", "Bad Tag"), ]
  )

  export <-
    # Join corrected tags back to original GIS data
    ls_ %>%
    dplyr::full_join(ls %>% filter(!CMMS_ASSET_ID %in% ls_$CMMS_ASSET_ID), by = "CMMS_ASSET_ID") %>%
    mutate(STREET_NAME=ifelse(is.na(STREET_NAME.y), STREET_NAME.x, STREET_NAME.y)) %>%
    dplyr::select(-c(STREET_NAME.x, STREET_NAME.y)) %>%
    mutate(STREET_NUMBER=ifelse(is.na(STREET_NUMBER.y), STREET_NUMBER.x, STREET_NUMBER.y)) %>%
    dplyr::select(-c(STREET_NUMBER.x, STREET_NUMBER.y)) %>%
    mutate(PI_TAG=ifelse(is.na(PI_TAG.y), PI_TAG.x, PI_TAG.y)) %>%
    dplyr::select(-c(PI_TAG.x, PI_TAG.y)) %>%
    dplyr::distinct() %>%

    # Filter to valid lift stations based Asset ID
    dplyr::filter(stringr::str_detect(.data$CMMS_ASSET_ID, "^LS|^BPS"))

  # Export PI Tags to CSV
  export %>% utils::write.csv(outfile, row.names = FALSE)

  # Build feedback on export, summary, and dups
  dup_asset_ids <- export %>% dplyr::count(.data$CMMS_ASSET_ID) %>% dplyr::filter(.data$n > 1)
  dup_pi_tags   <- export %>% dplyr::count(.data$PI_TAG)        %>% dplyr::filter(.data$n > 1)

  summary_text <- sprintf(
    "[%s] Exported %d rows to %s | Dup CMMS_ASSET_IDs: %d | Dup PI_TAGs: %d\n",
    Sys.time(), nrow(export), outfile, nrow(dup_asset_ids), nrow(dup_pi_tags)
  )

  if (verbose) {
    message(summary_text)
    message("Duplicate CMMS_ASSET_IDs:")
    print(dup_asset_ids)
    message("Duplicate PI_TAGs:")
    print(dup_pi_tags)
    dplyr::glimpse(export)
  }

  if (!is.null(log_path)) {
    cat(summary_text, file = log_path, append = TRUE)
  }

  save(export, file="data/validate_gis.RData")

  message("Exported ", nrow(export), " rows to ", outfile)
}

#' Validate an edited PI tag master list (Step 1b)
#'
#' Reads `data/pi_tag_master_list.csv` (or a user-supplied path), classifies
#' each tag, and validates against the PI Web API via [check_tags()]. Use
#' this after manually editing the CSV produced by [validate_gis()] to confirm
#' that your corrections are recognised by PI.
#'
#' @param infile Path to the CSV to validate.
#'   Defaults to `"data/pi_tag_master_list.csv"`.
#'
#' @return A data frame of rows still needing correction (return value of
#'   [check_tags()]), invisibly. The tag-classification tree is printed as a
#'   side-effect.
#'
#' @seealso [validate_gis()] to generate the initial master list,
#'   [build_af()] for the next pipeline step.
#'
#' @importFrom utils read.csv
#' @export
validate_csv <- function(infile = "out/pi_tag_master_list.csv") {
  ls <- utils::read.csv(infile, colClasses = "character")
  invisible(check_tags(ls))
}

#' Build PI AF import data (Step 2)
#'
#' Reads `data/pi_tag_master_list.csv` (output of [validate_gis()]),
#' validates all pump tag combinations, identifies multi-pump and VFD stations,
#' checks for lead setpoint tags, and exports the AF import file.
#'
#' @details
#' Pipeline steps:
#' 1. Read master list, filter to `WWL:` tags
#' 2. Validate all pump tag combinations via [check_all_pump_tags()]
#' 3. Pull 7-day SCADA history via [get_scada_history()]
#' 4. Identify multi-pump/VFD stations via
#'    [check_multiple_pumps_or_vfd_control()]
#' 5. Exclude stations with >2 pumps
#' 6. Check for `_WLLEADSP` lead setpoint tags
#' 7. Join plant/basin ([get_ls_by_plant()]) and pipe diameter
#'    ([get_dia_by_ls()]) data
#' 8. Assign AF template: `_cte_leadsp` (with setpoint) or `_cte_lead`
#'    (without)
#' 9. Normalize pipe diameter (minimum [MIN_WETWELL_AREA], default
#'    [DEFAULT_WETWELL_AREA])
#' 10. Export to `data/pi_af_import.csv`
#'
#' @return A data frame with columns `BASIN`, `STATION_NAME`,
#'   `CMMS_ASSET_ID`, `PI_TAG`, `Dia`, `TEMPLATE`.
#'
#' @seealso \code{vignette("usage-guide")} for step-by-step instructions,
#'   \code{vignette("technical-reference")} for template assignment rules,
#'   pipe diameter normalization, and station exclusion criteria.
#'
#' @importFrom dplyr filter mutate left_join select
#' @importFrom stringr str_detect str_remove
#' @importFrom utils read.csv write.csv View
#' @export
build_af <- function(infile= "out/pi_tag_master_list.csv", outfile = "out/pi_af_import.csv") {
  df <- utils::read.csv(infile, colClasses = "character") %>%
    dplyr::filter(stringr::str_detect(.data$PI_TAG, "^WWL:"))

  tags <- check_all_pump_tags(df)
  save(tags, file="data/check_all_pump_tags.RData")
  raw <- get_scada_history(tags)
  save(raw, file="data/get_scada_history.RData")
  vfd <- check_multiple_pumps_or_vfd_control(raw)
  save(vfd, file="data/check_multiple_pumps_or_vfd_control.RData")

  # Exclude >2 pumps: CTE flow model assumes lead/lag (2-pump) configuration
  multi_pump <- vfd %>% dplyr::filter(.data$pump > 2)
  use_df <- df %>% dplyr::filter(!.data$PI_TAG %in% multi_pump$PI_TAG)
  save(use_df, file="data/not_multi_pump.RData")

  # Check for lead setpoint tags
  tmp <- use_df %>% dplyr::mutate(PI_TAG = paste0(.data$PI_TAG, "_WLLEADSP"))
  tmp$bad_tag <- NA
  n <- nrow(tmp)
  message("Checking ", n, " lead setpoint tags...")
  for (i in seq_along(tmp$PI_TAG)) {
    if (i %% 50 == 0) message("  ", i, "/", n)
    tmp$bad_tag[i] <- is.null(safe_get_webid(tmp$PI_TAG[i]))
  }
  save(tmp, file="data/check_lead_setpoint_tag.RData")

  ls_by_plant <- get_ls_by_plant()
  dia_by_ls <- get_dia_by_ls()

  export <- use_df %>%
    dplyr::left_join(tmp %>% dplyr::select("CMMS_ASSET_ID", "bad_tag"), by = "CMMS_ASSET_ID") %>%
    dplyr::left_join(ls_by_plant, by = c("CMMS_ASSET_ID" = "CMMS_ASSET")) %>%
    dplyr::left_join(dia_by_ls, by = "CMMS_ASSET_ID") %>%
    dplyr::mutate(PI_TAG = stringr::str_remove(.data$PI_TAG, "^WWL:")) %>%
    dplyr::mutate(STATION_NAME = paste0(toupper(.data$STREET_NAME), " - ", .data$STREET_NUMBER)) %>%
    # bad_tag = TRUE means no _WLLEADSP tag exists -> use _cte_lead template
    dplyr::mutate(TEMPLATE = ifelse(.data$bad_tag, "_cte_lead", "_cte_leadsp")) %>%
    dplyr::mutate(AREA_FT2 = ifelse(is.na(.data$AREA_FT2), DEFAULT_WETWELL_AREA, .data$AREA_FT2)) %>%
    dplyr::mutate(AREA_FT2 = ifelse(.data$AREA_FT2 < MIN_WETWELL_AREA, MIN_WETWELL_AREA, .data$AREA_FT2))
    dplyr::select("BASIN", "STATION_NAME", "CMMS_ASSET_ID", "PI_TAG", "AREA_FT2", "TEMPLATE")

  export %>% utils::write.csv(outfile, row.names = FALSE)
  message("Exported ", nrow(export), " rows to ", outfile)
}

#' Format AF import data for the PI CSV loader (Step 3)
#'
#' Reads `data/pi_af_import.csv` (output of [build_af()]) and
#' transforms it into the hierarchical CSV structure required by the PI Asset
#' Framework bulk import tool.
#'
#' @details
#' Output hierarchy:
#' ```
#' WASTEWATER
#'   +-- EST FLOW
#'         +-- {BASIN}
#'               +-- {STATION_NAME}  (Template: _Liftstation)
#'                     |-- CMMS Asset ID  (Attribute)
#'                     |-- PI Tag         (Attribute)
#'                     |-- Wetwell Area   (Attribute)
#'                     |-- cte            (Element, template varies)
#'                     +-- hrt            (Element, template: _hrt)
#' ```
#'
#' Each station produces 6 rows. Output is written to `xlsx/pi_af_loader.csv`.
#'
#' @return A data frame of the complete AF import structure (invisibly).
#'
#' @seealso \code{vignette("usage-guide")} for step-by-step instructions,
#'   \code{vignette("technical-reference")} for AF hierarchy structure.
#'
#' @importFrom dplyr distinct arrange bind_rows
#' @importFrom utils read.csv write.csv
#' @export
export_af <- function(infile = "out/pi_af_import.csv", outfile = "out/pi_af_loader.csv") {
  export <- utils::read.csv(infile, colClasses = "character")

  # Root element
  root <- af_row("WASTEWATER", "EST FLOW", "Element")

  # Basin elements
  basins <- export %>% dplyr::distinct(.data$BASIN) %>% dplyr::arrange(.data$BASIN)
  basin_rows <- lapply(basins$BASIN, function(b) {
    af_row("WASTEWATER\\EST FLOW", b, "Element")
  })

  # Station rows (6 rows per station)
  station_rows <- lapply(seq_len(nrow(export)), function(i) {
    row <- export[i, ]
    parent <- paste0("WASTEWATER\\EST FLOW\\", row$BASIN)
    station_path <- paste0(parent, "\\", row$STATION_NAME)

    rbind(
      af_row(parent, row$STATION_NAME, "Element", template = "_Liftstation"),
      af_row(station_path, "CMMS Asset ID", "Attribute", value = row$CMMS_ASSET_ID),
      af_row(station_path, "PI Tag", "Attribute", value = row$PI_TAG),
      af_row(station_path, "Wetwell Area", "Attribute", value = row$AREA_FT2),
      af_row(station_path, "cte", "Element", template = row$TEMPLATE),
      af_row(station_path, "hrt", "Element", template = "_hrt")
    )
  })

  af <- dplyr::bind_rows(root, basin_rows, station_rows)

  af %>% utils::write.csv(outfile, row.names = FALSE)
  message("Exported ", nrow(af), " rows to ", outfile)

  invisible(af)
}
