write_sewer_pipes_icm <- function() {

  all_pipes <- get_sewer_pipes(TRUE)

  all_pipes |>
    dplyr::filter(FAC_STATE=="INS") |>
    dplyr::mutate(utility=case_when(
      SUBTYPE == 1 ~ "Collection Main"
      , SUBTYPE == 2 ~ "Effluent Main"
      , SUBTYPE == 3 ~ "Force Main"
      , SUBTYPE == 4 ~ "Low Pressure Main"
      , SUBTYPE == 5 ~ "Sludge Main"
      , SUBTYPE == 6 ~ "Trunk Main"
      , SUBTYPE == 7 ~ "Vacuum Main"
      , SUBTYPE == 8 ~ "Collection Lateral"
      , SUBTYPE == 9 ~ "Low Pressure Lateral"
      , SUBTYPE == 10 ~ "Vacuum Lateral"
      , SUBTYPE == 11 ~ "Plant Pipe"
      , SUBTYPE == 12 ~ "Assumed Pipe"
    )) |>
    dplyr::filter(
        SUBTYPE==1 |
        SUBTYPE==3 |
        SUBTYPE==4 |
        SUBTYPE==6 |
        SUBTYPE==12
    ) |>
    dplyr::select(
      OWNER = FAC_OWNER
      , STATE = FAC_STATE
      , CMMS = CMMS_ASSET_ID
      , DIA = PIPE_SIZE
      , CLASS = PIPE_CLASS
      , MATL = PIPE_MATERIAL_ABV
      , SUBTYPE
      , INVT_US = US_PIPE_INVERT_ELEVATION
      , INVT_DS = DS_PIPE_INVERT_ELEVATION
      , SLOPE
      , LINK_P = HYPERLINK_PRIMARY
      , LINK_S = HYPERLINK_SECONDARY
      , LINK_M = HYPERLINK_MAINTENANCE
      , LINK_R = REHAB_HYPERLINK
      , UTIL = utility
      , AVAIL = AVAIL_NUM
    ) -> tmp

  tmp |>
    dplyr::filter(
        SUBTYPE==1 |
        SUBTYPE==6
    ) |>
    sf::st_transform(st_crs(2236)) |>
    sf::st_write("E:/GIS Depot/Pipes/Gravity.shp"
                    , driver="ESRI Shapefile"
                    , append=FALSE)

  tmp |>
    dplyr::filter(
        SUBTYPE==3 |
        SUBTYPE==4 |
        SUBTYPE==12
    ) |>
    sf::st_transform(st_crs(2236)) |>
    sf::st_write("E:/GIS Depot/Pipes/Forcemain.shp"
                    , driver="ESRI Shapefile"
                    , append=FALSE)
}
