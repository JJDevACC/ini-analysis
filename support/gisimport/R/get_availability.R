get_availability <- function(folder="G:/Financial Services/Corporate Planning/Master GIS Folder/SDE Extracts") {

  sde_filename <- file.path(folder)

  layer_name <- get_latest_layer(sde_filename, "Availability")

  sf::st_read(sde_filename, layer_name)
}
