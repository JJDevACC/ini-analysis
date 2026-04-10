get_latest_layer <- function(fpath, expression) {
  sf::st_layers(fpath) -> tmp
  #layer_names <- tmp$name[stringr::str_detect(tmp$name, expression)]
  layer_names <- tmp$name[grepl(expression, tmp$name)]
  layer_names <- layer_names[length(layer_names)]
  layer_names
}
