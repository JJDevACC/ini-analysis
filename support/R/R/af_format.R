#' Create a single PI AF CSV row
#'
#' Builds one row conforming to the PI Asset Framework bulk import CSV format.
#'
#' @param parent Parent path in the AF hierarchy (backslash-separated).
#' @param name Name of the element or attribute.
#' @param object_type One of `"Element"` or `"Attribute"`.
#' @param template AF template name (default `""`).
#' @param value Attribute value (default `""`).
#'
#' @return A single-row data frame with columns `Selected(x)`, `Parent`,
#'   `Name`, `ObjectType`, `Template`, `AttributeValue`.
#'
#' @keywords internal
af_row <- function(parent, name, object_type, template = "", value = "") {
  data.frame(
    `Selected(x)` = "x",
    Parent = parent,
    Name = name,
    ObjectType = object_type,
    Template = template,
    AttributeValue = value,
    check.names = FALSE,
    stringsAsFactors = FALSE
  )
}
