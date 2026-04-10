get_sampled <- function(tag_vector, start_time="*-7d", end_time="*", freq="1d", isWebID=FALSE) {

  tags <- build_webID_list(tag_vector, isWebID)

  data <- get_tags(tags, start_time, end_time, freq)

  # Extract data from Items for calculation
  use <- data$Items

  j <- as.data.frame(matrix(rep(NA, nrow(use[[1]])*length(use)), ncol=length(use)))
  for (i in seq_along(use)) {
    if (is.null(ncol(use[[i]]$Value))) {
      j[,i] <- as.numeric(as.character(use[[i]]$Value)) } else {
        j[,i] <- as.numeric(as.character(use[[i]]$Value$Value)) }
  }

  # get non-numeric
  colnames(j) <- data$Name

  # Correct Timezone to Local
  datetime <- with_tz(ymd_hms(use[[1]]$Timestamp), Sys.timezone(location=TRUE))

  export <- data.frame(datetime, j)

  return(export)
}


build_webID_list <- function(tag_vector, isWebID) {

  if (!isWebID) {
    # Get webID for each element in vector as a list
    tags <- list()
    for (i in seq_along(tag_vector)) {
      tags <- append(tags, get_webid(tag_vector[i]))
    }
  } else {
    tags <- as.list(tag_vector)
  }

  # named list required for httr::GET
  names(tags) <- rep("webid", length(tag_vector))

  tags
}
