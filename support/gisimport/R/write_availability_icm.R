write_availability_icm <- function() {

  loa <- get_availability()

  loa |>
    dplyr::select(
        AVAILNUM
    ) |>
    sf::st_transform(st_crs(2236)) |>
    sf::st_write("E:/GIS Depot/Pipes/Avail.shp"
                 , driver="ESRI Shapefile"
                 , append=FALSE)

}
