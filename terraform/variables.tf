variable "kubeconfig_path" {
  description = "Path to the kubeconfig file"
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "Kubernetes context to use (e.g. docker-desktop, minikube)"
  type        = string
  default     = "docker-desktop"
}

variable "anthropic_api_key" {
  description = "Anthropic API key for Claude AI (stored as K8s secret)"
  type        = string
  sensitive   = true
}

variable "grafana_password" {
  description = "Grafana admin password"
  type        = string
  default     = "prom-operator"
  sensitive   = true
}
