get_service_area <- function(plant_name=NA) {
  folder <- "G:/Financial Services/Corporate Planning/Master GIS Folder/SDE Extracts"
  sde_filename <- file.path(folder, "Sewer.gdb")

  #sde_filename <- file.path(folder, "Service Area.gdb")

  layer_name <- get_latest_layer(sde_filename, "Sewer_Service_Area")
  if(is.na(plant_name)) {
    st_read(sde_filename, layer_name, quiet = TRUE) %>%
      st_drop_geometry() %>%
      distinct(NAME)
  } else {

    service_area <- st_read(sde_filename, layer_name, promote_to_multi = FALSE) %>%
      filter(str_detect(NAME, plant_name))
    # [1] "Arlington East" "Ponte Vedra"    "Ponce De Leon"  "Cedar Bay"
    # [5] "Southwest"      "Mandarin"       "Monterey"       "Blacks Ford"
    # [9] "JCP"            "Nassau"         "Buckman"

    service_area
  }
}


