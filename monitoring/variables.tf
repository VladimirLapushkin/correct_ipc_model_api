variable "kubeconfig_path" {
  type        = string
  description = "Path to kubeconfig"
  default     = "~/.kube/config"
}

variable "kube_context" {
  type        = string
  description = "kubectl context for target cluster"
}

variable "monitoring_namespace" {
  type        = string
  description = "Namespace for monitoring stack"
  default     = "monitoring"
}

variable "grafana_admin_password" {
  type        = string
  description = "Grafana admin password"
  sensitive   = true
}

variable "kube_prometheus_stack_version" {
  type        = string
  description = "Helm chart version"
  default     = "65.8.1"
}
