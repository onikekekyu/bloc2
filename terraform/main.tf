terraform {
  required_version = ">= 1.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
}

provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = var.kube_context
}

provider "helm" {
  kubernetes {
    config_path    = var.kubeconfig_path
    config_context = var.kube_context
  }
}

# ── Namespaces ──────────────────────────────────────────────────────────────

resource "kubernetes_namespace" "monitoring" {
  metadata {
    name = "monitoring"
    labels = {
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
}

resource "kubernetes_namespace" "airflow" {
  metadata {
    name = "airflow"
    labels = {
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
}

# ── Secrets ─────────────────────────────────────────────────────────────────

resource "kubernetes_secret" "claude_api_key" {
  metadata {
    name      = "claude-api-key-secret"
    namespace = "default"
  }
  data = {
    ANTHROPIC_API_KEY = var.anthropic_api_key
  }
}

# ── Prometheus + Grafana (kube-prometheus-stack) ─────────────────────────────

resource "helm_release" "monitoring" {
  name       = "monitoring"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  namespace  = kubernetes_namespace.monitoring.metadata[0].name
  version    = "65.0.0"
  timeout    = 600

  set {
    name  = "grafana.adminPassword"
    value = var.grafana_password
  }

  set {
    name  = "prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues"
    value = "false"
  }

  depends_on = [kubernetes_namespace.monitoring]
}

# ── Airflow ──────────────────────────────────────────────────────────────────

resource "helm_release" "airflow" {
  name       = "airflow"
  repository = "https://airflow.apache.org"
  chart      = "airflow"
  namespace  = kubernetes_namespace.airflow.metadata[0].name
  version    = "1.15.0"
  timeout    = 600

  values = [file("${path.module}/../airflow-values.yaml")]

  depends_on = [kubernetes_namespace.airflow]
}
