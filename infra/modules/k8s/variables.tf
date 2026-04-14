variable "cluster_name" {
  type = string
}

variable "k8s_version" {
  type = string
}

variable "node_group_name" {
  type = string
}

variable "zone" {
  type = string
}

variable "network_id" {
  type = string
}

variable "subnet_id" {
  type = string
}

variable "cluster_service_account" {
  type = string
}

variable "node_service_account" {
  type = string
}

variable "ssh_public_key_path" {
  type = string
}

variable "node_cores" {
  type = number
}

variable "node_memory" {
  type = number
}

variable "node_disk_size" {
  type = number
}

variable "node_initial_count" {
  type = number
}

variable "node_min_count" {
  type = number
}

variable "node_max_count" {
  type = number
}
