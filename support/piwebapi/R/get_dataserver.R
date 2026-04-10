get_dataserver <- function(servername, pi_server, pi_tag) {
  loc <- "dataservers/"

  url_ <- paste0(servername, loc)

  data <- get_url(url_)
  index <- which(toupper(data$Name)==toupper(pi_server))

  ifelse(sum(index)>0
         , webID <- data$WebId[index]
         , stop("Not a valid PI server")
  )

  query <- "/points?namefilter="

  url_ <- paste0(url_, webID, query, pi_tag)

  return(url_)
}
