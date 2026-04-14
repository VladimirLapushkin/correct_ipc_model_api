variable "network_name" {
  type = string
}

variable "subnet_name" {
  type = string
}

variable "subnet_range" {
  type = string
}

variable "provider_config" {
  type = object({
    token     = string
    cloud_id  = string
    folder_id = string
    zone      = string
  })
}
