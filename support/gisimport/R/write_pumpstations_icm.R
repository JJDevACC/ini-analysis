write_pumpstations_icm <- function() {

  ps <- get_pumpstations()

  ps |>
    dplyr::filter(FAC_STATE=="INS") |>
    dplyr::filter(SUBTYPE==1) |>
    dplyr::filter(str_detect(CMMS_ASSET_ID , "^LS-")) |>
    dplyr::select(
      CODE = S_COMMON_NAME
      , STREET = STREET_NAME
      , NUMBER = STREET_NUMBER
      , LINK = HYPERLINK
      , CMMS = CMMS_ASSET_ID
      , PI_TAG
      , GIS_NAME = GIS_STREET_NAME
      , AVAIL = AVAIL_NUM
    ) |>
    sf::st_transform(st_crs(2236)) |>
    sf::st_write("E:/GIS Depot/Pipes/Stations.shp"
                    , driver="ESRI Shapefile"
                    , append=FALSE)

  ps |>
    dplyr::filter(FAC_STATE=="INS") |>
    dplyr::filter(SUBTYPE==1) |>
    dplyr::filter(is.na(str_detect(CMMS_ASSET_ID, "^LS"))) |>
    dplyr::select(
      CODE = S_COMMON_NAME
      , STREET = STREET_NAME
      , NUMBER = STREET_NUMBER
      , LINK = HYPERLINK
      , CMMS = CMMS_ASSET_ID
      , PI_TAG
      , GIS_NAME = GIS_STREET_NAME
    ) |>
    sf::st_transform(st_crs(2236)) |>
    sf::st_write("E:/GIS Depot/Pipes/Private.shp"
                    , driver="ESRI Shapefile"
                    , append=FALSE)
}
