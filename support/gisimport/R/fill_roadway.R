library(sf)
library(tidyverse)
library(units)

#' Fill narrow gaps between polygons (typically roads/rights-of-way)
#'
#' Identifies and fills narrow gaps between polygon features that likely represent
#' roads or rights-of-way. Uses buffer expansion/contraction to bridge gaps, then
#' filters results to avoid filling artifacts or inappropriately large areas.
#'
#' @param shp sf object containing polygon geometries
#' @return sf object with roadway gaps filled and geometry simplified
#' @examples
#'   shp <- sf::st_read("gis", "test1")
#'
#'   fill_roadway(shp) %>% plot(lwd=2)
#'
#'   fill_roadway(shp) %>%
#'     st_cast("POINT") %>%
#'     plot(lwd=2, add=TRUE)
#'
#'   plot(shp
#'      , col=rgb(0.125,0.125,0.125,0.125)
#'      , border=rgb(0.25,0.25,0.25,0.25)
#'      , lty=3
#'      , add=TRUE)
fill_roadway <- function(shp, MIN_GAP_AREA_ACRE = 0.1, MAX_GAP_WIDTH_METER = 100, POINT_REDUCTION_TOLERANCE_METER = 20) {

  shp <- shp %>% st_geometry()

  # Distance tolerance in meters for vertex reduction in final step
  # Smooths polygon boundaries while preserving overall shape accuracy
  #POINT_REDUCTION_TOLERANCE_METER = 20

  # Maximum roadway gap width in meters that will be filled
  # Determines which spaces between parcels get bridged by buffering
  #MAX_GAP_WIDTH_METER = 100

  # Area threshold in acres for meaningful roadway gaps
  # Only fills gaps larger than this to avoid slivers and artifacts
  #MIN_GAP_AREA_ACRE <- 0.1

  shp %>%
    # Step 1: Expand and contract into single polygon
    st_buffer(MAX_GAP_WIDTH_METER) %>%
    st_union() %>%
    st_buffer(-MAX_GAP_WIDTH_METER) %>%
    st_geometry() %>%

    # Step 2: Identify right-of-way gaps
    st_difference(shp %>% st_union()) %>%
    st_collection_extract() %>%
    #st_cast("POLYGON") %>%
    st_as_sf() %>%

    # Step 3: Remove slivers and buffer artifacts
    mutate(area=units::set_units(st_area(.), "acre")) %>%
    filter(area>units::set_units(MIN_GAP_AREA_ACRE, "acre")) %>%
    st_geometry() %>%
    st_union() %>%

    # step 4: Add right-of-way to parcel polygon
    rbind(shp %>% st_as_sf()) %>%
    st_union() %>%

    # Step 5: Simplify geometry
    st_simplify(dTolerance = POINT_REDUCTION_TOLERANCE_METER)
}

