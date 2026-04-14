output "cluster_id" {
  value = yandex_kubernetes_cluster.cluster.id
}

output "cluster_name" {
  value = yandex_kubernetes_cluster.cluster.name
}

output "external_v4_endpoint" {
  value = yandex_kubernetes_cluster.cluster.master[0].external_v4_endpoint
}

output "cluster_ca_certificate" {
  value = yandex_kubernetes_cluster.cluster.master[0].cluster_ca_certificate
}
