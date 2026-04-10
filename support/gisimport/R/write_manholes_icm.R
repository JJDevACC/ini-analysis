write_manholes_icm <- function() {

  Sewer_Manholes <- get_manholes(TRUE)

  Sewer_Manholes |>
    dplyr::filter(FAC_STATE=="INS") |>
    dplyr::select(
        OWNER = FAC_OWNER
      , STATE = FAC_STATE
      , CMMS = CMMS_ASSET_ID
      , RIM = RIM_ELEVATION
      , DIA = MANHOLE_SIZE
      , TYPE = MANHOLE_TYPE
      , MATL = MATERIAL
      , SUBTYPE
      , PS = RECEIVING_PUMPSTATION
      , AVAIL = AVAIL_NUM
    ) -> tmp

  tmp |>
    sf::st_transform(st_crs(2236)) |>
    sf::st_write("E:/GIS Depot/Pipes/Manholes.shp"
                 , driver="ESRI Shapefile"
                 , append=FALSE)
}
