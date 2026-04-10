# Convert MULTICURVE to MULTILINESTRING
multicurve_to_multilinestring <- function(shp) {
  # Remove only MULTICURVE type
  sample_set <- shp %>%
    dplyr::filter(sf::st_geometry_type(shp)=="MULTICURVE")

  # Extract just the geometry
  sample_set_geom <- sample_set$SHAPE[] |> sf::st_as_sf()

  # Extract just the data
  sample_set_data <- sample_set |> sf::st_drop_geometry()

  # Initialize a blank spatial object
  export <- sample_set |> dplyr::slice(0)|> sf::st_transform(st_crs(shp))

  for (i in 1:nrow(sample_set)) {
    # decompose the MULTICURVE geometry (for each row) into a numerical matrix
    sample_set_geom_i_list <- unlist(sample_set_geom$x[[i]], recursive = FALSE)

    #initialize list
    l <- list()

    for (j in 1:length(sample_set_geom_i_list)) {
      # re-build the numerical matrix as a LINESTRING
      l[[j]] <- sf::st_linestring(sample_set_geom_i_list[[j]][])
    }

    export_ <-
      # Add Data to the Geometry (for each row)
      sf::st_set_geometry(
        sample_set_data[i,]
        , st_multilinestring(l) |> sf::st_sfc()
      ) %>%
      sf::st_set_crs(sf::st_crs(export))

    export <- rbind(export, export_)
  }

  excluded_set <-
    shp |>
    filter(!st_geometry_type(shp)=="MULTICURVE")

  rbind(excluded_set, export |> rename(SHAPE=geometry))
}
