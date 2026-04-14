variable "name" {
  type = string
}

variable "roles" {
  type = list(string)
}

variable "provider_config" {
  type = object({
    token     = string
    cloud_id  = string
    folder_id = string
    zone      = string
  })
}
