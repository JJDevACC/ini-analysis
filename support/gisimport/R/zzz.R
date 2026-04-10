.onLoad <- function(lib, pkg) {
  pkg.env <- new.env(parent = emptyenv())
  pkg.env$gis_sde_extract <- "G:/Financial Services/Corporate Planning/Master GIS Folder/SDE Extracts"
}

.onAttach <- function(lib, pkg) {

}
