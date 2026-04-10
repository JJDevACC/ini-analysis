#' @keywords internal
tag_cols <- c("STREET_NAME", "STREET_NUMBER", "CMMS_ASSET_ID", "PI_TAG")

#' Safe wrapper around [get_webid()]
#'
#' Returns `NULL` instead of raising an error when a tag is not found.
#' (https://purrr.tidyverse.org/reference/possibly.html)
#'
#' @param ... Arguments passed to [get_webid()].
#' @return A web ID string, or `NULL` if the tag does not exist.
#' @keywords internal
safe_get_webid <- purrr::possibly(piwebapi::get_webid, otherwise = NULL)

#' Retrieve lift station data from GIS
#'
#' Downloads pump station features from GIS via gisimport package,
#' then filters#' to in-service JEA lift stations with an CMMS asset ID
#'
#' @details
#' Filters applied:
#' - `FAC_STATE == "INS"` (in-service only)
#' - `CMMS_ASSET_ID` is not `NA`
#' - `SUBTYPE == 1` (lift stations)
#'
#' @return A data frame with columns: `STREET_NAME`, `STREET_NUMBER`,
#'   `CMMS_ASSET_ID`, `PI_TAG`.
#'
#' @importFrom sf st_drop_geometry
#' @importFrom dplyr filter select
#' @keywords internal
get_ls_from_gis <- function() {
  #load_gis_ps() %>% # TODO UPDATE to current gisimport function for pump stations
    gisimport::get_pumpstations() %>%
    sf::st_drop_geometry() %>%
    dplyr::filter(.data$FAC_STATE == "INS") %>%
    dplyr::filter(!is.na(.data$CMMS_ASSET_ID)) %>%
    dplyr::filter(.data$SUBTYPE == 1) %>%
    dplyr::select(dplyr::all_of(tag_cols))
}

#' Load plant/basin assignments for lift stations
#'
#' Reads the lookup table from `data/ls_by_plant.RData`.
#'
#' @return A data frame with at least column `CMMS_ASSET`.
#'
#' @note TODO: Replace with computed lookup from GIS/CMMS source.
#' @keywords internal
get_ls_by_plant <- function() {
  message("Get pumpstation based in GIS Spatial Join")
  # TODO make call to arcpy
  read.csv("data/ls_by_basin.csv") %>%
    dplyr::select(CMMS_ASSET, TR_PLANT=TR_PLANT) %>%
    mutate(TR_PLANT=toupper(TR_PLANT)) %>%
    mutate(TR_PLANT=ifelse(TR_PLANT=="BLACKS FORD/GREENLAND", "GREENLAND", TR_PLANT)) %>%
    filter(!TR_PLANT=="") %>%
    mutate(BASIN=TR_PLANT)
}

#' Load pipe diameter data for lift stations
#'
#' Reads the lookup table from `data/dia_by_ls.RData`.
#'
#' @return A data frame with at least columns `CMMS_ASSET_ID` and `Dia`.
#'
#' @note TODO: Replace with computed lookup from GIS/CMMS source.
#' @keywords internal
get_dia_by_ls <- function() {

  message("Get list of tags in PI AF")
  # Download Existing Wetwell Area from AF
  df <- piwebapi::list_cmms_attributes()

  message("Check value in each tag")
  wetwell_area <- data.frame(CMMS_ASSET_ID=character(), AREA_FT2=numeric())
  for (i in seq_along(df$CMMS.Asset.ID)) {
    CMMS_ASSET_ID <- df$cmms[i]
    AREA_FT2 <- piwebapi::get_sampled_multi(df$Wetwell.Area[i], ymd(today()), ymd(today()), "1d", TRUE)$Wetwell.Area[1]

    wetwell_area <- rbind(wetwell_area, data.frame(CMMS_ASSET_ID, AREA_FT2))
  }
  save(wetwell_area, file="data/get_dia_by_ls.RData")

  message("Get tags from GIS")
  # TODO make call to arcpy
  # Download Existing Wetwell Area from GIS
  ww <- read.csv("data/wetwell.csv") %>%
    dplyr::select(CMMS_ASSET_ID=EQUIPMEN_1, DIA=WETWELL__1)

  message("Consolidate AF and GIS")
  # Compare AF and GIS, then use best guess
  check <-
    ww %>%
    mutate(DIA=ifelse(DIA<5, NA, DIA)) %>%
    mutate(AREA_FT2_=round(pi * DIA * DIA / 4,2)) %>%
    left_join(wetwell_area, by="CMMS_ASSET_ID") %>%
    mutate(AREA_FT2__=ifelse(is.na(AREA_FT2), AREA_FT2_, AREA_FT2))

  check %>%
    mutate(diff=round((abs(AREA_FT2-AREA_FT2_)/AREA_FT2)*100,2)) %>%
    mutate(AREA_FT2__=ifelse(diff>1&!is.na(diff), AREA_FT2_, AREA_FT2__)) %>%
    dplyr::select(CMMS_ASSET_ID, AREA_FT2=AREA_FT2__)

}

#' Retrieve SCADA history for pump tags
#'
#' Pulls sampled SCADA data for the specified tags over the last `NUM_DAYS`
#' days, excluding P1RUN and P2RUN summary tags.
#'
#' @param tags_ A data frame with columns `name` and `value`, where `value`
#'   contains the full PI tag path.
#' @param NUM_DAYS Number of days of history to retrieve (default 7).
#'
#' @return A data frame with a `datetime` column and one column per tag.
#'
#' @importFrom dplyr filter
#' @importFrom stringr str_detect
#' @importFrom lubridate today days
#' @keywords internal
get_scada_history <- function(tags_, NUM_DAYS = 7) {
  tmp <- tags_ %>%
    dplyr::filter(!.data$name %in% c("p1run", "p2run"))

  message("Checking ", NUM_DAYS, " days of SCADA History on ", nrow(tmp), " tags")
  piwebapi::get_sampled_multi(
    tmp$value,
    lubridate::today() - lubridate::days(NUM_DAYS),
    lubridate::today()
  )
}
