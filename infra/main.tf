module "network" {
  source          = "./modules/network"
  network_name    = var.yc_network_name
  subnet_name     = var.yc_subnet_name
  subnet_range    = var.yc_subnet_range
  provider_config = var.yc_config
}

module "iam_cluster" {
  source          = "./modules/iam"
  name            = var.yc_service_account_name
  provider_config = var.yc_config
  roles = [
    "k8s.clusters.agent",
    "vpc.publicAdmin",
    "load-balancer.admin"
  ]
}

module "iam_node" {
  source          = "./modules/iam"
  name            = var.yc_node_service_account_name
  provider_config = var.yc_config
  roles = [
    "container-registry.images.puller",
    "logging.writer",
    "monitoring.editor",
    "vpc.publicAdmin"
  ]
}


module "k8s" {
  source                  = "./modules/k8s"
  cluster_name            = var.yc_k8s_cluster_name
  k8s_version             = var.yc_k8s_version
  node_group_name         = var.yc_k8s_node_group_name
  zone                    = var.yc_config.zone
  network_id              = module.network.network_id
  subnet_id               = module.network.subnet_id
  cluster_service_account = module.iam_cluster.service_account_id
  node_service_account    = module.iam_node.service_account_id
  ssh_public_key_path     = var.yc_ssh_public_key_path
  node_cores              = var.yc_k8s_node_cores
  node_memory             = var.yc_k8s_node_memory
  node_disk_size          = var.yc_k8s_node_disk_size
  node_initial_count      = var.yc_k8s_node_initial_count
  node_min_count          = var.yc_k8s_node_min_count
  node_max_count          = var.yc_k8s_node_max_count
}

# locals {
#   yc_k8s_cluster_id = module.k8s.cluster_id
# }


resource "null_resource" "update_env" {
  provisioner "local-exec" {
    interpreter = ["/usr/bin/env", "bash", "-lc"]
    command     = <<EOT
      set -eu
      ENV_FILE="../.env"
      touch "$ENV_FILE"
      
      YC_K8S_CLUSTER_ID='${module.k8s.cluster_id}'
      if grep -q "^YC_K8S_CLUSTER_ID=" "$ENV_FILE"; then
        sed -i "s|^YC_K8S_CLUSTER_ID=.*|YC_K8S_CLUSTER_ID=$YC_K8S_CLUSTER_ID|" "$ENV_FILE"
      else
        echo "YC_K8S_CLUSTER_ID=$YC_K8S_CLUSTER_ID" >> "$ENV_FILE"
      fi
    EOT
  }
  triggers = {
    cluster_id = module.k8s.cluster_id  # перезапустит только при изменении ID
  }
  depends_on = [
    module.k8s,
    module.network
  ]
}
