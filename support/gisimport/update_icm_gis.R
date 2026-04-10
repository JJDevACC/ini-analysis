.libPaths("G:/Financial Services/Corporate Planning/Hydraulic Model Files/RWD/4-0")

suppressMessages(library(sf))
suppressMessages(library(tidyverse))
suppressMessages(library(devtools))

load_all("G:/Financial Services/Corporate Planning/Hydraulic Model Files/R Library/gisimport/R")
setwd("G:/Financial Services/Corporate Planning/Hydraulic Model Files/R Library/gisimport/")


message("==============================================================")
message("🚀 Starting: Update GIS files (typical runtime = 5 mins)")
message("==============================================================")

tick <- Sys.time()


message("")
message("🔄 Step 1 of 4: Downloading manhole features...")
message("--------------------------------------------------------------")

write_manholes_icm()



message("")
message("🔄 Step 2 of 4: Downloading pumpstation features...")
message("--------------------------------------------------------------")


write_pumpstations_icm()



message("")
message("🔄 Step 3 of 4: Downloading pipeline features...")
message("--------------------------------------------------------------")


write_sewer_pipes_icm()


message("")
message("🔄 Step 4 of 4: Downloading availability features...")
message("--------------------------------------------------------------")

write_availability_icm()


message("")
message("✅ All downloads complete.")
message("--------------------------------------------------------------")
message(paste0("⏱️ Total runtime: ", round(Sys.time() - tick, 1), " minutes."))
message("==============================================================")


