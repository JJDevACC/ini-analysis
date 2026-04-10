get_tags <- function(tags, start_time="*-7d", end_time="*", freq="1d") {
  PI_HOST_NAME = "MASTERPIAPP.corp.jea.com/piwebapi/"

  headers <- c(
    'X-Requested-With' = 'PIWebApiWrapper'
    , 'Accept' = 'application/xml;'
  )

  tmp <- httr::GET(""
                   , config = httr::config(ssl_verifypeer = FALSE)
                   , httr::authenticate(
                          user = Sys.getenv("UID")
                        , password = Sys.getenv("PWD")
                        , type = "gssnegotiate"#"basic"#
                   )
                   , httr::add_headers(headers)
                   , scheme="https"
                   , hostname=paste0(PI_HOST_NAME, "streamsets")
                   , path="/interpolated"
                   , query=append(
                     tags,
                     list(
                           #webId=tags
                           startTime=start_time
                         , endTime=end_time
                         , interval=freq
                     ))
  )


  # Convert JSON response to R list and extract "Items" only
  raw <- jsonlite::fromJSON(rawToChar(tmp$content))
  data <- raw$Items

  return(data)
}


