.libPaths("G:/Financial Services/Corporate Planning/Hydraulic Model Files/RWD/4-0")

packages <- c(
  "data.tree",
  "dplyr",
  "lubridate",
  "piwebapi",
  "gisimport",
  "purrr",
  "sf",
  "stats",
  "stringr",
  "tidyr",
  "utils"
)

lapply(packages, library, character.only = TRUE)

library(devtools)

load_all("R")

validate_gis()

# check exported CSV and manually correct NA values
validate_csv()

# Takes a long time
build_af()

export_af()
