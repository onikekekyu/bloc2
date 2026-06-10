"""
DAG Airflow - Pipeline d'analyse de Terms & Conditions
2Long2Read : Claude AI → MongoDB → Prometheus → Grafana
"""
import pendulum
from datetime import timedelta
from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

default_args = {
    "owner": "2long2read",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "email_on_failure": False,
}

with DAG(
    dag_id="cgu_analysis_pipeline",
    default_args=default_args,
    description="Pipeline CGU : Health Check → Claude AI → MongoDB → Prometheus → Grafana",
    schedule=None,
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
    tags=["2long2read", "production"],
    params={
        "source_name": "spotify",
        "task_id": None,
        "text_content": "",
    },
) as dag:

    # ── Task 1 : Vérifier que l'infrastructure est disponible ─────────────────

    def check_api_health():
        import requests
        resp = requests.get(
            "http://api-service.default.svc.cluster.local:8000/health",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"[CHECK] API={data['status']}, MongoDB={data.get('mongodb', 'unknown')}")
        assert data.get("status") == "healthy", f"API unhealthy: {data}"
        return data

    check_environment = PythonOperator(
        task_id="check_environment",
        python_callable=check_api_health,
        execution_timeout=timedelta(minutes=1),
    )

    # ── Task 2 : Lancer le worker Claude AI via KubernetesPodOperator ─────────

    run_analysis = KubernetesPodOperator(
        task_id="run_cgu_analysis",
        name="cgu-worker",
        namespace="default",
        image="2long2read-worker:latest",
        image_pull_policy="IfNotPresent",
        cmds=["bash", "-c"],
        arguments=[
            "echo \"$TC_CONTENT\" | python /app/worker.py"
            " --task-id \"{{ dag_run.conf.get('task_id') or run_id | replace(':', '-') | replace('+', '-') }}\""
            " --source-name \"{{ dag_run.conf.get('source_name', 'spotify') }}\""
            " --use-stdin"
        ],
        env_vars={
            "MONGO_HOSTNAME": "mongo-service.default.svc.cluster.local",
            "MONGO_PORT": "27017",
            "ANTHROPIC_API_KEY": "{{ var.value.get('ANTHROPIC_API_KEY', '') }}",
            "TC_CONTENT": "{{ dag_run.conf.get('text_content', '') }}",
        },
        get_logs=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        service_account_name="airflow-worker-launcher",
        startup_timeout_seconds=300,
        execution_timeout=timedelta(minutes=15),
    )

    # ── Task 3 : Synchroniser les métriques MongoDB → Prometheus ──────────────

    def sync_prometheus(**context):
        import requests
        resp = requests.get(
            "http://api-service.default.svc.cluster.local:8000/api/v1/sync-metrics",
            timeout=30,
        )
        resp.raise_for_status()
        stats = resp.json()
        print(f"[SYNC] Métriques synchronisées : {stats['stats']} (total={stats['total']})")
        return stats

    sync_metrics = PythonOperator(
        task_id="sync_metrics",
        python_callable=sync_prometheus,
        provide_context=True,
        execution_timeout=timedelta(minutes=2),
    )

    # ── Task 4 : Rapport final depuis MongoDB ─────────────────────────────────

    def generate_final_report(**context):
        from pymongo import MongoClient

        client = MongoClient(
            "mongodb://mongo-service.default.svc.cluster.local:27017",
            serverSelectionTimeoutMS=10000,
        )
        db = client.too_long_to_read
        latest = db.analytic_reports.find_one(
            {"status": "completed"},
            sort=[("_id", -1)],
        )
        if not latest:
            raise ValueError("Aucune analyse complétée trouvée dans MongoDB")

        scores = latest["report"].get("risk_scores", {})
        clauses = latest["report"].get("dangerous_clauses", [])
        summary = latest["report"].get("executive_summary", {})

        print("=" * 55)
        print("  PIPELINE 2Long2Read — RAPPORT FINAL")
        print("=" * 55)
        print(f"  Source    : {latest.get('source_name', 'unknown')}")
        print(f"  Task ID   : {latest.get('task_id', 'unknown')}")
        print(f"  Verdict   : {summary.get('overall_verdict', 'N/A')}")
        print()
        print("  SCORES DE RISQUE :")
        for k, v in scores.items():
            bar = "█" * (v // 10) + "░" * (10 - v // 10)
            print(f"    {k:25s} {bar} {v}/100")
        print()
        print(f"  Clauses dangereuses : {len(clauses)}")
        print("=" * 55)

        return {
            "source": latest.get("source_name"),
            "overall_risk": scores.get("overall"),
            "clauses_count": len(clauses),
        }

    final_report = PythonOperator(
        task_id="final_report",
        python_callable=generate_final_report,
        provide_context=True,
        execution_timeout=timedelta(minutes=2),
    )

    # ── Dépendances ───────────────────────────────────────────────────────────

    check_environment >> run_analysis >> sync_metrics >> final_report
