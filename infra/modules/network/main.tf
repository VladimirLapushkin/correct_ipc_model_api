resource "yandex_vpc_network" "network" {
  name = var.network_name
}

resource "yandex_vpc_subnet" "subnet" {
  name           = var.subnet_name
  zone           = var.provider_config.zone
  network_id     = yandex_vpc_network.network.id
  v4_cidr_blocks = [var.subnet_range]
}
