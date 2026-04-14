resource "kubernetes_namespace" "monitoring" {
  metadata {
    name = var.monitoring_namespace
    labels = {
      app = "monitoring"
    }
  }
}

resource "helm_release" "kube_prometheus_stack" {
  name             = "kube-prometheus-stack"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  version          = var.kube_prometheus_stack_version
  namespace        = kubernetes_namespace.monitoring.metadata[0].name
  create_namespace = false
  timeout          = 1800
  wait             = true

  values = [
    yamlencode({
      grafana = {
        adminPassword = var.grafana_admin_password
        service = {
          type = "LoadBalancer"
          port = 80
        }
      }

      alertmanager = {
        service = {
          type = "ClusterIP"
          port = 9093
        }
      }

      prometheus = {
        service = {
          type = "ClusterIP"
          port = 9090
        }
        prometheusSpec = {
          retention = "10d"
          serviceMonitorSelectorNilUsesHelmValues = false
          podMonitorSelectorNilUsesHelmValues     = false
          ruleSelectorNilUsesHelmValues           = false
        }
      }

      kubeStateMetrics = {
        enabled = true
      }

      nodeExporter = {
        enabled = true
      }
    })
  ]
}
