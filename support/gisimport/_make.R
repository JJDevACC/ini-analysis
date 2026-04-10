.libPaths("G:/Financial Services/Corporate Planning/Hydraulic Model Files/RWD/4-0")

suppressMessages(library(sf))
suppressMessages(library(tidyverse))

library(devtools)

load_all()



# -------------------------------------------------------------------------





#library(usethis)
#usethis::use_pipe()

#
#
# tmp <- c(
#   "LS-000085"
#   ,"LS-000217"
#   ,"LS-000224"
#   ,"LS-000225"
#   ,"LS-000390"
#   ,"LS-000768"
#   ,"LS-000769"
#   ,"LS-002905"
#   ,"LS-003967"
#   ,"LS-004078"
# )
#
# ps <- get_pumpstations() %>%
#   #st_drop_geometry() %>%
#   filter(CMMS_ASSET_ID %in% tmp) %>%
#   dplyr::select(CMMS_ASSET_ID, STREET_NAME, STREET_NUMBER, PI_TAG)
#
# ps %>% ggplot() + geom_sf()
#
# st_write(ps, "ps.shp", driver="ESRI Shapefile")
#
# basin <-
# sf::st_read(
#     "G:/Financial Services/Corporate Planning/Planning Group/Craig/_PEC/139-02 Northwest New WRF/2025-01-22 Pumpstation Basin"
#   , "Northwest"
# )
#
# ps <-
# get_pumpstations() %>%
#   st_transform(st_crs(basin)) %>%
#   st_filter(basin) %>%
#   filter(!is.na(CMMS_ASSET_ID))
#
# basin %>% ggplot() + geom_sf() + geom_sf(data=ps)
#
# ps %>%
#   st_drop_geometry() %>%
#   dplyr::select(CMMS_ASSET_ID, STREET_NAME, STREET_NUMBER, PI_TAG) %>%
#   write_csv("deleteme.csv")
#
# st_write(ps, "ps_in_basin.shp", driver="ESRI ShapeFile")
