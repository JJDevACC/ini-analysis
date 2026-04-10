get_pumpstations <- function(folder="G:/Financial Services/Corporate Planning/Master GIS Folder/SDE Extracts") {

  sde_filename <- file.path(folder, "Sewer.gdb")

  layer_name <- get_latest_layer(sde_filename, "Pump_Station")

  sf::st_read(sde_filename, layer_name)
}
