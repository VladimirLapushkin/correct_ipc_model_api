variable "yc_config" {
  type = object({
    token     = string
    cloud_id  = string
    folder_id = string
    zone      = string
  })
  sensitive = true
}

variable "yc_network_name" {
  type    = string
  default = "mlops-network"
}

variable "yc_subnet_name" {
  type    = string
  default = "mlops-subnet"
}

variable "yc_subnet_range" {
  type    = string
  default = "10.10.0.0/24"
}

variable "yc_service_account_name" {
  type    = string
  default = "mlops-k8s-cluster-sa"
}

variable "yc_node_service_account_name" {
  type    = string
  default = "mlops-k8s-node-sa"
}

variable "yc_k8s_cluster_name" {
  type    = string
  default = "mlops-k8s"
}

variable "yc_k8s_version" {
  type    = string
  default = "1.30"
}

variable "yc_k8s_node_group_name" {
  type    = string
  default = "mlops-k8s-nodes"
}

variable "yc_k8s_node_cores" {
  type    = number
  default = 2
}

variable "yc_k8s_node_memory" {
  type    = number
  default = 8
}

variable "yc_k8s_node_initial_count" {
  type    = number
  default = 2
}

variable "yc_k8s_node_min_count" {
  type    = number
  default = 2
}

variable "yc_k8s_node_max_count" {
  type    = number
  default = 4
}


variable "yc_k8s_node_disk_size" {
  type    = number
  default = 30
}



variable "yc_ssh_public_key_path" {
  type = string
}
