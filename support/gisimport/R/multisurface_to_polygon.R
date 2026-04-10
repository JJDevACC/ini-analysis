multisurface_to_polygon <- function(shp) {

  # Remove only MULTICURVE type
  sample_set <- shp %>%
    dplyr::filter(sf::st_geometry_type(shp)=="MULTISURFACE")

  if(nrow(sample_set) > 0 ) {

      # Extract just the geometry
      sample_set_geom <- sample_set$SHAPE[] |> sf::st_as_sf()

      # Extract just the data
      sample_set_data <- sample_set |> sf::st_drop_geometry()

      #initialize list
      l <- list()

      j <- 1
    #  for (j in 1:length(sample_set_geom_i_list)) {
        # re-build the numerical matrix as a LINESTRING
        nn <- length(sample_set_geom$x[[j]][[1]][[1]])

        use <- data.frame(x=numeric(), y=numeric())

        for (i in 1:nn) {
          pt <- unlist(sample_set_geom$x[[j]][[1]][[1]][i])

          n <- length(pt)

          x <- 1:(n/2)
          y <- (n/2+1):n

          xx <- pt[x]
          yy <- pt[y]

          use_ <- data.frame(x=xx, y=yy)
          use <- rbind(use, use_)
        }

        l[[j]] <-
          sf::st_as_sf(
            use
            , coords=c("x","y")
            , crs=st_crs(shp)
          ) %>%
          st_combine() %>%
          st_cast("POLYGON")

          # Add Data to the Geometry (for each row)
          sf::st_set_geometry(
            sample_set_data[1,]
            , l[[1]]
          ) %>%
          sf::st_set_crs(sf::st_crs(shp))

  } else {shp}
}

