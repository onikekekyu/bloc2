# 2Long2Read — Analyseur de CGU avec Claude AI

**Système d'analyse automatique de Terms & Conditions : Claude AI analyse les clauses abusives, MongoDB stocke les résultats, Prometheus collecte les métriques, Grafana les visualise, Airflow orchestre le tout sur Kubernetes.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INFRASTRUCTURE (Terraform)                  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Kubernetes (Docker Desktop)               │  │
│  │                                                              │  │
│  │  ┌─────────┐    ┌──────────┐    ┌───────────┐              │  │
│  │  │ Airflow │───▶│  Worker  │───▶│  MongoDB  │              │  │
│  │  │ (DAG)   │    │(Claude AI│    │           │              │  │
│  │  └─────────┘    └──────────┘    └─────┬─────┘              │  │
│  │                                       │                     │  │
│  │  ┌─────────┐    ┌──────────┐          │                    │  │
│  │  │ Grafana │◀───│Prometheus│◀──────── │ /sync-metrics      │  │
│  │  │         │    │          │    ┌─────▼─────┐              │  │
│  │  └─────────┘    └──────────┘    │  FastAPI  │              │  │
│  │                                 │  /metrics │              │  │
│  │                                 └───────────┘              │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Stack technique

| Composant | Technologie | Rôle |
|---|---|---|
| Orchestration | Apache Airflow 2.10.3 (Helm) | Pipeline DAG |
| Worker / IA | Python + Anthropic Claude Sonnet | Analyse des CGU |
| Stockage | MongoDB 7.0 | Documents JSON enrichis |
| API | FastAPI + Uvicorn | REST API + exposition métriques |
| Monitoring | Prometheus + Grafana (kube-prometheus-stack) | Observabilité |
| Conteneurs | Docker + Kubernetes | Déploiement |
| IaC | Terraform + Kubernetes YAML + Helm | Infrastructure as Code |
| CI/CD | GitHub Actions | Build + validation syntaxe |

---

## Structure du projet

```
.
├── docker/                        # Dockerfiles
│   ├── Dockerfile                 # Image API FastAPI
│   └── Dockerfile.worker          # Image Worker Claude AI
│
├── k8s/                           # Manifestes Kubernetes
│   ├── infra.yaml                 # MongoDB (avec PVC)
│   ├── app.yaml                   # API + Worker deployments
│   ├── airflow-dags-pv.yaml       # PersistentVolume pour les DAGs
│   ├── rbac-airflow.yaml          # RBAC pour KubernetesPodOperator
│   └── prometheus-servicemonitor.yaml
│
├── terraform/                     # Infrastructure as Code
│   ├── main.tf                    # Namespaces, secrets, Helm releases
│   ├── variables.tf
│   └── outputs.tf
│
├── dags/                          # DAGs Airflow
│   └── cgu_analysis_dag.py        # Pipeline principal (4 tasks)
│
├── scripts/                       # Scripts utilitaires
│   ├── run_worker.sh              # Lancer une analyse localement
│   ├── access_grafana.sh          # Port-forward Grafana
│   └── analyze_spotify.sh         # Lancer un worker pod K8s
│
├── config/
│   ├── companies_config.json      # Liste des 50 entreprises cibles
│   └── grafana_spotify_dashboard.json
│
├── docs/
│   └── data_model.md              # ERD MongoDB + schéma en étoile Prometheus
│
├── raw_data/                      # Textes T&C bruts
│   ├── spotify_tc.txt
│   └── anthropic_tc.txt
│
├── main.py                        # API FastAPI
├── worker.py                      # Worker CLI (analysis runner)
├── ai_analyzer.py                 # Intégration Claude AI
├── airflow-values.yaml            # Config Helm Airflow (minimal)
├── frontend.html                  # Interface web
└── requirements.txt
```

---

## Prérequis

- **Docker Desktop** avec Kubernetes activé
- **kubectl** et **Helm** installés
- **Terraform >= 1.0** installé
- **Python 3.11+**
- **Une clé API Anthropic** (Claude AI)

```bash
docker --version && kubectl version --client && helm version && terraform version
```

---

## Déploiement

### Option A — Terraform (recommandé)

```bash
cd terraform/

# Initialiser les providers
terraform init

# Vérifier le plan
terraform plan -var="anthropic_api_key=sk-ant-..."

# Déployer (namespaces + secrets + Prometheus + Airflow)
terraform apply -var="anthropic_api_key=sk-ant-..."
```

Terraform provisionne automatiquement :
- Les namespaces `monitoring` et `airflow`
- Le secret Kubernetes pour la clé API
- Prometheus + Grafana via Helm
- Airflow 2.10.3 via Helm

### Option B — Déploiement manuel étape par étape

#### 1. Clé API Anthropic

```bash
kubectl create secret generic claude-api-key-secret \
  --from-literal=ANTHROPIC_API_KEY="sk-ant-..."
```

#### 2. Images Docker

```bash
docker build -t 2long2read-api:latest -f docker/Dockerfile .
docker build -t 2long2read-worker:latest -f docker/Dockerfile.worker .
```

#### 3. MongoDB + API

```bash
kubectl apply -f k8s/infra.yaml
kubectl wait --for=condition=ready pod -l app=mongo --timeout=120s
kubectl apply -f k8s/app.yaml
kubectl get pods
```

#### 4. Prometheus + Grafana

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace --wait --timeout 5m
kubectl apply -f k8s/prometheus-servicemonitor.yaml
```

#### 5. Airflow

```bash
helm repo add apache-airflow https://airflow.apache.org
helm repo update
kubectl create namespace airflow
kubectl apply -f k8s/airflow-dags-pv.yaml   # Mettre à jour le path dans ce fichier
kubectl apply -f k8s/rbac-airflow.yaml
helm install airflow apache-airflow/airflow \
  --namespace airflow -f airflow-values.yaml --timeout 10m --wait
```

---

## Utilisation

### Analyser un fichier de CGU (local)

```bash
# Activer l'environnement Python
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Port-forward MongoDB
kubectl port-forward svc/mongo-service 27017:27017 &

# Lancer l'analyse
./scripts/run_worker.sh raw_data/spotify_tc.txt spotify
```

### Via l'API

```bash
kubectl port-forward svc/api-service 8000:8000 &

# Soumettre une analyse
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "<texte des CGU>", "source_name": "spotify"}'

# Récupérer le rapport
curl http://localhost:8000/api/v1/report/<task_id>

# Synchroniser les métriques vers Prometheus
curl http://localhost:8000/api/v1/sync-metrics
```

### Via Airflow (orchestration complète)

```bash
# Accéder à Airflow UI
kubectl port-forward -n airflow svc/airflow-webserver 8080:8080 &
# http://localhost:8080  (admin / admin)
```

Le DAG `cgu_analysis_pipeline` exécute 4 tasks :
1. `check_environment` — vérifie la santé de l'API et MongoDB
2. `run_cgu_analysis` — lance le worker Claude AI via `KubernetesPodOperator`
3. `sync_metrics` — synchronise MongoDB → Prometheus
4. `final_report` — affiche le rapport depuis MongoDB

Déclencher avec `dag_run.conf` :
```json
{
  "source_name": "spotify",
  "task_id": "spotify-demo-001",
  "text_content": "<texte des CGU>"
}
```

### Accéder à Grafana

```bash
./scripts/access_grafana.sh
# http://localhost:3000  (admin / prom-operator)
```

Importer le dashboard : `config/grafana_spotify_dashboard.json`

Requêtes PromQL utiles :
```promql
# Score de risque global
cgu_last_risk_score{source_name="spotify"}

# Scores par catégorie
cgu_data_privacy_score
cgu_termination_risk_score
cgu_legal_protection_score
cgu_transparency_score

# Nombre de clauses dangereuses
cgu_problematic_clauses
```

---

## Modèle de données

Le modèle complet est documenté dans [`docs/data_model.md`](docs/data_model.md), incluant :
- ERD de la collection MongoDB `analytic_reports`
- Schéma en étoile des métriques Prometheus
- Flux de données end-to-end

### Exemple de document MongoDB

```json
{
  "task_id": "spotify-20250601-143022",
  "source_name": "spotify",
  "status": "completed",
  "report": {
    "metadata": { "company_name": "Spotify", "word_count": 8432 },
    "executive_summary": {
      "overall_verdict": "Concerning",
      "one_liner": "Spotify retains broad rights over user content with limited recourse"
    },
    "risk_scores": {
      "overall": 72,
      "data_privacy": 65,
      "user_rights": 78,
      "termination_risk": 75,
      "legal_protection": 82,
      "transparency": 58
    },
    "dangerous_clauses": [
      {
        "type": "LEGAL",
        "severity": "CRITICAL",
        "title": "Mandatory arbitration clause",
        "summary": "Waives right to class action lawsuits"
      }
    ]
  }
}
```

---

## Résultats — Spotify T&C

| Dimension | Score | Niveau |
|---|---|---|
| Score global | 72/100 | Préoccupant |
| Confidentialité des données | 65/100 | Préoccupant |
| Droits utilisateur | 78/100 | Élevé |
| Risque de résiliation | 75/100 | Élevé |
| Protection légale | 82/100 | Élevé |
| Transparence | 58/100 | Préoccupant |

**10 clauses problématiques détectées**, dont :
- Arbitrage obligatoire (CRITIQUE) — pas de recours collectifs
- Licence mondiale irrévocable sur le contenu utilisateur
- Résiliation sans remboursement ni préavis
- Limitation de responsabilité à 30 $

---

## Commandes utiles

```bash
# État de l'infrastructure
kubectl get pods --all-namespaces

# Logs de l'API
kubectl logs -f deployment/api-deployment

# Logs du Worker
kubectl logs -f deployment/worker-deployment

# Vérifier MongoDB
kubectl exec deployment/mongo-deployment -- \
  mongosh too_long_to_read --eval "db.analytic_reports.countDocuments()"

# Redémarrer un composant
kubectl rollout restart deployment/api-deployment
```

---

## CI/CD

Le pipeline GitHub Actions se déclenche à chaque push sur `main` et effectue :

1. **Validation syntaxe Python** — `main.py`, `worker.py`, `ai_analyzer.py`, `dags/cgu_analysis_dag.py`
2. **Build image API** — `docker/Dockerfile`
3. **Build image Worker** — `docker/Dockerfile.worker`

```
Push → GitHub Actions → py_compile ✓ → docker build API ✓ → docker build Worker ✓
```

Les images ne sont pas poussées sur un registry (Docker Hub optionnel via secrets `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN`).

---

## Dépannage

**MongoDB inaccessible**
```bash
kubectl get pods -l app=mongo
kubectl logs deployment/mongo-deployment
```

**Métriques à 0 dans Grafana**
```bash
# 1. Vérifier qu'une analyse existe dans MongoDB
kubectl exec deployment/mongo-deployment -- \
  mongosh too_long_to_read --eval "db.analytic_reports.countDocuments({status:'completed'})"
# 2. Re-synchroniser
curl http://localhost:8000/api/v1/sync-metrics
```

**Images Docker introuvables**
```bash
docker images | grep 2long2read
# Si absent, reconstruire :
docker build -t 2long2read-api:latest -f docker/Dockerfile .
docker build -t 2long2read-worker:latest -f docker/Dockerfile.worker .
kubectl rollout restart deployment/api-deployment deployment/worker-deployment
```
