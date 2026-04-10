#' Get WebID
#'
#' Primary use case is to determine if a tag exists
#'
#' @param pi_tag
#' @param pi_server
#' @param servername
#' @param is_data_server
#'
#' @return
#' @export
#'
#' @examples
#'   get_webid("wwl:stjohns:wam213_stpwp")
get_webid <- function(pi_tag
                      , pi_server="masterpi"
                      #, servername = "https://MASTERPIDVAPP.corp.jea.com/piwebapi/"
                      , servername = "https://MASTERPIAPP.corp.jea.com/piwebapi/"
                      , is_data_server=TRUE
) {

  if(length(pi_tag)>1) {stop("get_webid: ")}


  ifelse(is_data_server
         , url__ <- get_dataserver(servername, pi_server, pi_tag)
         , url__ <- get_assetserver()
  )


  export <- get_url(url__)

  # add error checking for bad pi tag or pi tag not found

  return(export$WebId)
}
