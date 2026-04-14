output "network_id" {
  value = module.network.network_id
}

output "subnet_id" {
  value = module.network.subnet_id
}

output "cluster_id" {
  value = module.k8s.cluster_id
}

output "cluster_name" {
  value = module.k8s.cluster_name
}

output "cluster_external_v4_endpoint" {
  value = module.k8s.external_v4_endpoint
}

output "cluster_ca_certificate" {
  value     = module.k8s.cluster_ca_certificate
  sensitive = true
}
