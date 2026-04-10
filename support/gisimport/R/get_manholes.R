get_manholes <- function(update=FALSE, folder="G:/Financial Services/Corporate Planning/Master GIS Folder/SDE Extracts") {

  if(!file.exists("data/sewer_manhole.RData") | update) {
    sde_filename <- file.path(folder, "Sewer.gdb")

    layer_name <- get_latest_layer(sde_filename, "Sewer_Manhole")

    sewer_manholes <- sf::st_read(sde_filename, layer_name) |>
      sf::st_zm()

    save(sewer_manholes, file="data/sewer_manhole.RData")
  } else { load("data/sewer_manhole.RData")}

  sewer_manholes
}
