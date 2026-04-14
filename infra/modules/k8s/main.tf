resource "yandex_kubernetes_cluster" "cluster" {
  name        = var.cluster_name
  description = "MLOps managed Kubernetes cluster"
  network_id  = var.network_id

  master {
    version = var.k8s_version

    zonal {
      zone      = var.zone
      subnet_id = var.subnet_id
    }

    public_ip = true
  }

  service_account_id      = var.cluster_service_account
  node_service_account_id = var.node_service_account

  release_channel = "REGULAR"

  network_policy_provider = "CALICO"
}

resource "yandex_kubernetes_node_group" "nodes" {
  cluster_id  = yandex_kubernetes_cluster.cluster.id
  name        = var.node_group_name
  description = "Worker nodes for MLOps app"
  version     = var.k8s_version

  instance_template {
    platform_id = "standard-v3"

    network_interface {
      subnet_ids = [var.subnet_id]
      nat        = true
    }

    resources {
      memory = var.node_memory
      cores  = var.node_cores
    }

    boot_disk {
      type = "network-hdd"
      size = var.node_disk_size
    }

    scheduling_policy {
      preemptible = false
    }

    metadata = {
      ssh-keys = "ubuntu:${file(var.ssh_public_key_path)}"
    }
  }

  scale_policy {
    auto_scale {
      min     = var.node_min_count
      max     = var.node_max_count
      initial = var.node_initial_count
    }
  }


  allocation_policy {
    location {
      zone = var.zone
    }
  }

  maintenance_policy {
    auto_repair  = true
    auto_upgrade = true
  }
}
