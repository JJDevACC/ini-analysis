impute_avg <- function(value, z = -qnorm((1-0.95)/2), n=3, p=0.2) {
  value.old <- value

  mu <- mean(value, na.rm=TRUE)
  sd <- sd(value, na.rm=TRUE)

  value[is.na(value)] <- mu
  value[value>(mu+z*sd)] <- mu
  value[value<(mu-z*sd)] <- mu

  value_ <- stats::filter(value, rep(1/n, n), sides=2)
  value_[is.na(value_)] <- mu

  value[abs(1-value/value_)>(p)] <- value_[abs(1-value/value_)>(p)]

  plot(value.old, col="red", type="l", lty=2, xlab="", ylab="value")
  lines(value)

  return(value)
}
