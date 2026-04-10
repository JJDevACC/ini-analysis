.libPaths("G:/Financial Services/Corporate Planning/Hydraulic Model Files/RWD/4-0")
library(devtools)
library(lubridate)
load_all()

Sys.setenv("UID"="/Jonedc")

#source("r/_def.R")

tag <- "wwl:South:OLD4193B_STPRESSINL"

tags <- get_webid(tag)
testthat::expect_equal(class(tags), "character")
# URL:
# https://masterpiapp.corp.jea.com/piwebapi/dataservers/F1DSAAAAAAAAAAAAAAAAAAAdogTUFTVEVSUEk/points?namefilter=wwl:South:OLD4193B_STPRESSINL

tmp <- get_tags(tags)
testthat::expect_equal(class(tmp), "data.frame")

head(tmp)

library(lubridate)

#tags <- c("wwl:bra10477b_realtmmetflo")

start_time = ymd(today()) - days(7)
end_time = ymd(today())

tmp <- get_sampled(tag, start_time, end_time)
testthat::expect_equal(class(tmp), "data.frame")

tags <- c("wwl:east:bra10477b_realtmmetflo", "wwl:South:OLD4193B_STPRESSINL")

tmp <- get_sampled_multi(tags, start_time, end_time)


freq="1d"
tmp <- get_sampled(tag, start_time, end_time, "1d")
testthat::expect_equal(class(tmp), "data.frame")



get_sampled_multi(tags
                  , ymd(today()-days(90))
                  , ymd_hms(now())
)

# -------------------------------------------------------------------------

tag <- c("wwl:South:OLD4193B_STPRESSINL", "wwl:South:OLD4193B_STPRESSOUT")

tags <- list()
for (i in seq_along(tag)) {
  tags <- append(tags, get_webid(tag[i]))
}

names(tags) <- rep("webid", length(tag))

start_time = ymd(today()) - days(7)
end_time = ymd(today())
freq="1d"

headers <- c(
  'X-Requested-With' = 'PIWebApiWrapper'
  , 'Accept' = 'application/xml;'
)

tmp <- httr::GET(""
                 , config = httr::config(ssl_verifypeer = TRUE)
                 , httr::authenticate(
                     user = Sys.getenv("UID")
                   , password = Sys.getenv("PWD")
                   , type = "basic"#gssnegotiate"
                 )
                 , httr::add_headers(headers)
                 , scheme="https"
                 , hostname=paste0(PI_HOST_NAME, "streamsets")
                 , path="/interpolated"
                 , query=append(tags,
                   list(
                     #webId=tags
                      startTime=start_time
                     , endTime=end_time
                     , interval=freq
                   ))
)


# -------------------------------------------------------------------------

get_sampled(tag)
