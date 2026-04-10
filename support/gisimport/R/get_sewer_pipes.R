get_sewer_pipes <- function(update=FALSE, folder="G:/Financial Services/Corporate Planning/Master GIS Folder/SDE Extracts") {
  message("
  # SUBTYPE
  # 1  Collection Main
  # 2  Effluent Main
  # 3  Force Main
  # 4  Low Pressure Main
  # 5  Sludge Main
  # 6  Trunk Main
  # 7  Vacuum Main
  # 8  Collection Lateral
  # 9  Low Pressure Lateral
  # 10 Vacuum Lateral
  # 11 Plant Pipe
  # 12 Assumed Pipe
  # 13 Pump Influent Piping (FS/SP only)
  # 14 Pump Discharge Piping
  # 15 Station Influent Piping (BPS only)
  # 16 Station Discharge Piping
  # 17 Backup Pump Influent Piping
  # 18 Backup Pump Discharge Piping
  # 19 Vacuum Pump Influent Piping
  # 20 Vacuum Pump Discharge Piping")

  if(!file.exists("data/sewer_pipes.RData") | update) {
    sde_filename <- file.path(folder, "Sewer.gdb")

    layer_name <- get_latest_layer(sde_filename, "Sewer_Pipe")

    sewer_pipes <- sf::st_read(sde_filename, layer_name) |>
      sf::st_zm() %>%
      multicurve_to_multilinestring()

    save(sewer_pipes, file="data/sewer_pipes.RData")
  } else { load("data/sewer_pipes.RData")}

  sewer_pipes
}
