#' Title
#'
#' @return dataframe
#' @export
#'
#' @examples
#' \dontrun{ list_cmms_attributes() }
list_cmms_attributes <- function() {
  # PI_HOST_NAME = "MASTERPIDVAPP.corp.jea.com/piwebapi"
  # PI_SERVER_NAME ="MASTERPIDVAPP"
  # ASSET_DATABASE = "Development-W-WW-Planning"
  PI_HOST_NAME = "MASTERPIAPP.corp.jea.com/piwebapi"
  PI_SERVER_NAME ="MASTERPIAPP"
  ASSET_DATABASE = "W-WW Planning"

  username=Sys.getenv("UID")
  password=Sys.getenv("PWD")
  authType="gssnegotiate"
  validateSSL=TRUE

  headers <- c(
      'X-Requested-With' = 'PIWebApiWrapper'
    , 'Accept' = 'application/xml;'
  )

  # Get PI AF Asset Server WebID

  resp <- httr::GET(""
                    , config = httr::config(ssl_verifypeer = validateSSL)
                    , httr::authenticate(user=username, password=password, type=authType)
                    , httr::add_headers(headers)
                    , scheme = "https"
                    , hostname = PI_HOST_NAME
                    , path = list("assetservers")
                    , query = list(name=PI_SERVER_NAME, selectedFields="WebId")
  )

  content <- jsonlite::fromJSON(rawToChar(resp$content))

  webid <- content$WebId
  #webid <- "F1RSjAUtRSZlRE6pGfVjyglICATUFTVEVSUElEVkFQUA"

  # Get WWSP Asset Database WebID

  resp <- httr::GET(""
                    , config = httr::config(ssl_verifypeer = validateSSL)
                    , httr::authenticate(user=username, password=password, type=authType)
                    , httr::add_headers(headers)
                    , scheme = "https"
                    , hostname = PI_HOST_NAME
                    , path = list("assetservers", webid, "assetdatabases")
  )

  content <- jsonlite::fromJSON(rawToChar(resp$content))

  webid <- content$Items$WebId[content$Items$Name==ASSET_DATABASE]
  #webid <- "F1RDjAUtRSZlRE6pGfVjyglICAyDzz-0IkqEKKEi6SHeNyRwTUFTVEVSUElEVkFQUFxERVZFTE9QTUVOVC1XLVdXLVBMQU5OSU5H"
  # Get Asset ID WebID

  resp <- httr::GET(""
                    , config = httr::config(ssl_verifypeer = validateSSL)
                    , httr::authenticate(user=username, password=password, type=authType)
                    , httr::add_headers(headers)
                    , scheme = "https"
                    , hostname = PI_HOST_NAME
                    , path = list("assetdatabases", webid, "elementattributes")
                    , query = list(attributeNameFilter="CMMS Asset ID"
                                   , elementTemplate="-Liftstation"
                                   , searchFullHierarchy="true"
                                   , maxCount=10000
                    )
  )

  content <- jsonlite::fromJSON(rawToChar(resp$content))

  tmp <- content$Items$WebId

  #export <- NULL

  # Get Asset ID Value from WebID

  for (i in seq_along(tmp)) {

    resp <- httr::GET(""
                      , config = httr::config(ssl_verifypeer = validateSSL)
                      , httr::authenticate(user=username, password=password, type=authType)
                      , httr::add_headers(headers)
                      , scheme = "https"
                      , hostname = PI_HOST_NAME
                      , path = list("streams", tmp[i], "end")
                      , query = list(selectedFields="Value")
    )

    content <- jsonlite::fromJSON(rawToChar(resp$content))

    export_ <- data.frame(cmms=content$Value, webid=tmp[i])

    ifelse(i==1
           , export <- export_
           , export <- rbind(export, export_)
    )
  }

  # Get Parent Element

  for (i in seq_along(tmp)) {

    resp <- httr::GET(""
                      , config = httr::config(ssl_verifypeer = validateSSL)
                      , httr::authenticate(user=username, password=password, type=authType)
                      , httr::add_headers(headers)
                      , scheme = "https"
                      , hostname = PI_HOST_NAME
                      , path = list("attributes", export$webid[i])
                      , query = list(selectedFields="Links.Element")
    )

    content <- jsonlite::fromJSON(rawToChar(resp$content))

    element_ <- data.frame(url_element=content$Links$Element)

    ifelse(i==1
           , element <- element_
           , element <- rbind(element, element_)
    )
  }

  export <- cbind(export, element)

  # Get Parent Element WebID

  #i <- sample(seq_along(tmp), 1)
  for (i in seq_along(tmp)) {
    resp <- httr::GET(export$url_element[i]
                      , config = httr::config(ssl_verifypeer = validateSSL)
                      , httr::authenticate(user=username, password=password, type=authType)
                      , httr::add_headers(headers)
                      , query = list(selectedFields="Links.Attributes")
    )

    content <- jsonlite::fromJSON(rawToChar(resp$content))

    attribute_ <- data.frame(url_attribute=content$Links$Attributes)

    ifelse(i==1
           , attribute <- attribute_
           , attribute <- rbind(attribute, attribute_)
    )
  }

  export <- cbind(export, attribute)

  # Get Parent ID Attributes WebID

  for (i in seq_along(tmp)) {

    resp <- httr::GET(export$url_attribute[i]
                      , config = httr::config(ssl_verifypeer = validateSSL)
                      , httr::authenticate(user=username, password=password, type=authType)
                      , httr::add_headers(headers)
                      , query = list(selectedFields="Items.Name;Items.WebId")
    )

    content <- jsonlite::fromJSON(rawToChar(resp$content))

    df_ <- as.list(content$Items$WebId)
    names(df_) <- content$Items$Name
    df_ <- data.frame(cmms=export$cmms[i], df_)

    ifelse(i==1
           , df <- df_
           , df <- rbind(df, df_)
    )
  }

  df
}
