#' Title
#'
#' @param TAG a list of PI tags
#' @param start_time a date-time object (lubridate format)
#' @param end_time a date-time object (lubridate format)
#' @param freq return resolution ("1m", "1h", "1d", etc... )
#' @param isWebID boolean, TRUE if TAG is a WebID
#'
#' @return data.frame
#' @export
#'
#' @examples
#' tags <- c("wwl:east:bra10477B_REALTMMETFLO")
#'
#' get_sampled_multi(tags, mdy("12/16/2021"), mdy("1/31/2022"))
get_sampled_multi <- function(TAG, start_time="*-7d", end_time="*", freq="1m", isWebID=FALSE) {
  #browser()
  START <- start_time
  END <- end_time

  MAX_ITEMS = 150000*0.9
  MAX_TAGS = 50

  tag_split <- split(TAG, ceiling(seq_along(TAG)/MAX_TAGS))

  for (i in seq_along(tag_split)) {
    items <- as.numeric(END-START)*1440*length(tag_split[[i]])

    max_minutes <- floor(MAX_ITEMS/length(tag_split[[i]]))

    dt_seq <- seq(as_datetime(START), as_datetime(END), "min")

    dt_split <- split(dt_seq, ceiling(seq_along(dt_seq)/(max_minutes)))

    for (j in seq_along(dt_split)) {
      tmp_ <- get_sampled(tag_split[[i]]
                          , start_time=min(dt_split[[j]])
                          , end_time=max(dt_split[[j]])
                          , freq=freq
                          , isWebID
      )


      ifelse(j > 1
             , tmp <- dplyr::union(tmp, tmp_)
             , tmp <- tmp_
      )

    } # for j

    ifelse(i > 1
           , export_ <- dplyr::full_join(export_, tmp, by=c("datetime"="datetime"))
           , export_ <- tmp
    )

    rm(tmp)
  } # for i

  return(export_)

}
