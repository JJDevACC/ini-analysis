get_end <- function(tag_vector, username="", password="", authType="gssnegotiate", validateSSL=0L, isWebID=FALSE) {
  # tag_vector <- tmp1$apo_tag
  # username=""
  # password=""
  # authType="gssnegotiate"
  # validateSSL=0L

  # Get webID for each element in vector as a list
  # tags <- list()
  # for (i in seq_along(tag_vector)) {
  #   tags <- append(tags, get_webid(tag_vector[i]))
  # }
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
  names(tags) <- rep("webid", length(tags))


  headers <- c(
    'X-Requested-With' = 'PIWebApiWrapper'
    , 'Accept' = 'application/xml;'
  )

  for (i in seq_along(tags)) {

    use <- httr::GET(""
                     , config = httr::config(ssl_verifypeer = validateSSL)
                     , authenticate(user=username, password=password, type=authType)
                     , add_headers(headers)
                     , authenticate("", "", "gssnegotiate")
                     , scheme="https"
                     , hostname=paste0(PI_HOST_NAME, "streams/", tags[i])
                     , path="/end"
                     #, query=data$WebId[1]
    )

    # Convert JSON response to R list and extract "Items" only
    raw <- fromJSON(rawToChar(use$content))
    #browser()
    tmp_ <- ifelse(length(raw$Value)==1, raw$Value, raw$Value$Value)


    ifelse(i > 1
           , tmp <- c(tmp, tmp_)
           , tmp <- tmp_
    )

  }


  return(tmp)
}
