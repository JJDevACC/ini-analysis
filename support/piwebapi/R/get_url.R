get_url <- function(url__) {

  authType="gssnegotiate"#"basic"

  validateSSL=0L

  headers <- c(
    'X-Requested-With' = 'PIWebApiWrapper'
    , 'Accept' = 'application/xml;'
  )

  tmp <- httr::GET(url__
                   , config = httr::config(ssl_verifypeer = validateSSL)
                   , httr::authenticate(
                         user=Sys.getenv("UID")
                       , password=Sys.getenv("PWD")
                       , type=authType
                     )
                   , httr::add_headers(headers)
                   #, verbose() # used for debugging response
  )

  export <- jsonlite::fromJSON(rawToChar(tmp$content))

  return(export$Items)
}
