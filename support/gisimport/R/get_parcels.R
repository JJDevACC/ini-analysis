get_parcels <- function(update=FALSE, folder="") {

  if(!file.exists("data/parcels.RData") | update) {

    parcels <-
    rbind(
      shp <- sf::st_read("E:/GIS Depot/Parcels/Duval/2025-08-08", "duval") %>%
        dplyr::select(RE=RE)
      ,
      shp <- sf::st_read("E:/GIS Depot/Parcels/stjohns/2025-08-08", "stjohns") %>%
        dplyr::select(RE=PIN)
      ,
      shp <- sf::st_read("E:/GIS Depot/Parcels/nassau/2025-08-08", "nassau") %>%
        dplyr::select(RE=PIN)
    )

    save(sewer_pipes, file="data/parcels.RData")
  } else { load("data/parcels.RData")}

  parcels

}
