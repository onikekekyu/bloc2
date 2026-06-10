output "monitoring_namespace" {
  description = "Namespace where Prometheus + Grafana are deployed"
  value       = kubernetes_namespace.monitoring.metadata[0].name
}

output "airflow_namespace" {
  description = "Namespace where Airflow is deployed"
  value       = kubernetes_namespace.airflow.metadata[0].name
}

output "grafana_url" {
  description = "Access Grafana via port-forward: kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80"
  value       = "http://localhost:3000"
}

output "airflow_url" {
  description = "Access Airflow UI via port-forward: kubectl port-forward -n airflow svc/airflow-webserver 8080:8080"
  value       = "http://localhost:8080"
}
