# Modèle de données — 2Long2Read

## Vue d'ensemble

Le projet utilise deux couches de données complémentaires :
- **MongoDB** (stockage opérationnel) : documents JSON enrichis par Claude AI
- **Prometheus** (stockage métrique) : séries temporelles pour la surveillance et la visualisation Grafana

---

## ERD — Collection MongoDB `analytic_reports`

```
┌──────────────────────────────────────────────────────────┐
│                    analytic_reports                      │
├──────────────────────────────────────────────────────────┤
│ _id            ObjectId   PK                             │
│ task_id        String     UUID unique par analyse        │
│ source_name    String     ex: "spotify", "google"        │
│ status         Enum       pending | in_progress |        │
│                           completed | failed             │
│ error_message  String?    présent si status=failed       │
│                                                          │
│ ┌─ report (Object) ──────────────────────────────────┐  │
│ │                                                    │  │
│ │  ┌─ metadata ────────────────────────────────┐    │  │
│ │  │  company_name     String                  │    │  │
│ │  │  language         String                  │    │  │
│ │  │  word_count        Int                    │    │  │
│ │  │  reading_time_min  Int                    │    │  │
│ │  │  last_updated      String                 │    │  │
│ │  │  document_type     String                 │    │  │
│ │  └────────────────────────────────────────────┘   │  │
│ │                                                    │  │
│ │  ┌─ executive_summary ───────────────────────┐    │  │
│ │  │  one_liner         String                 │    │  │
│ │  │  key_takeaways     String[]               │    │  │
│ │  │  overall_verdict   Enum                   │    │  │
│ │  │     User Friendly | Standard |            │    │  │
│ │  │     Concerning | Highly Problematic       │    │  │
│ │  └────────────────────────────────────────────┘   │  │
│ │                                                    │  │
│ │  ┌─ risk_scores ─────────────────────────────┐    │  │
│ │  │  overall            Int  (0-100)           │    │  │
│ │  │  data_privacy       Int  (0-100)           │    │  │
│ │  │  user_rights        Int  (0-100)           │    │  │
│ │  │  termination_risk   Int  (0-100)           │    │  │
│ │  │  legal_protection   Int  (0-100)           │    │  │
│ │  │  transparency       Int  (0-100)           │    │  │
│ │  └────────────────────────────────────────────┘   │  │
│ │                                                    │  │
│ │  ┌─ key_flags ───────────────────────────────┐    │  │
│ │  │  data_sharing_third_party  Boolean        │    │  │
│ │  │  data_selling              Boolean        │    │  │
│ │  │  ip_rights_transfer        Boolean        │    │  │
│ │  │  content_monitoring        Boolean        │    │  │
│ │  │  termination_without_notice Boolean       │    │  │
│ │  │  forced_arbitration        Boolean        │    │  │
│ │  │  class_action_waiver       Boolean        │    │  │
│ │  │  unilateral_changes        Boolean        │    │  │
│ │  └────────────────────────────────────────────┘   │  │
│ │                                                    │  │
│ │  dangerous_clauses  DangerousClause[]  (0-N)       │  │
│ │  sections_breakdown Section[]          (0-N)       │  │
│ │  action_items       ActionItem[]       (0-N)       │  │
│ │  readability        Object                         │  │
│ │  comparison_to_industry Object                     │  │
│ └────────────────────────────────────────────────────┘  │
│                                                          │
│ ┌─ meta (Object) ────────────────────────────────────┐  │
│ │  source_name       String                          │  │
│ │  analyzed_at       ISODate                         │  │
│ │  raw_text_length   Int                             │  │
│ │  analyzer_version  String                          │  │
│ └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### Sous-document : `DangerousClause`

```
┌──────────────────────────────────────────────┐
│  DangerousClause                             │
├──────────────────────────────────────────────┤
│  id           String   identifiant unique    │
│  type         Enum     DATA_PRIVACY |        │
│                        USER_RIGHTS |         │
│                        TERMINATION |         │
│                        LEGAL | CONTENT       │
│  severity     Enum     LOW | MEDIUM |        │
│                        HIGH | CRITICAL       │
│  title        String                         │
│  summary      String                         │
│  exact_quote  String                         │
│  user_impact  String                         │
│  recommendation String                       │
└──────────────────────────────────────────────┘
```

---

## Schéma en étoile — Métriques Prometheus

Le schéma en étoile Prometheus place **l'analyse CGU** comme fait central, avec les dimensions `source_name` et `severity` comme axes de filtrage.

```
                    ┌──────────────────────┐
                    │   FAIT CENTRAL       │
                    │   cgu_analysis       │
                    │                      │
                    │  • risk_score        │
                    │  • clause_count      │
                    │  • analysis_duration │
                    │  • timestamp         │
                    └──────────┬───────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  DIM: Source     │  │  DIM: Catégorie  │  │  DIM: Sévérité   │
│                  │  │                  │  │                  │
│  source_name     │  │  data_privacy    │  │  LOW             │
│  "spotify"       │  │  user_rights     │  │  MEDIUM          │
│  "google"        │  │  termination     │  │  HIGH            │
│  "anthropic"     │  │  legal           │  │  CRITICAL        │
│  ...             │  │  transparency    │  │                  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

### Métriques exportées (`/metrics`)

| Métrique | Type | Labels | Description |
|---|---|---|---|
| `cgu_analyses_total` | Counter | `source_name` | Nb d'analyses soumises via API |
| `cgu_analyses_count` | Gauge | `source_name` | Nb d'analyses complétées (MongoDB) |
| `cgu_last_risk_score` | Gauge | `source_name` | Dernier score de risque global (0-100) |
| `cgu_data_privacy_score` | Gauge | `source_name` | Score confidentialité des données |
| `cgu_user_rights_score` | Gauge | `source_name` | Score droits utilisateur |
| `cgu_termination_risk_score` | Gauge | `source_name` | Score risque de résiliation |
| `cgu_legal_protection_score` | Gauge | `source_name` | Score protection légale |
| `cgu_transparency_score` | Gauge | `source_name` | Score transparence |
| `cgu_problematic_clauses` | Gauge | `source_name` | Nb de clauses problématiques |
| `cgu_risk_score` | Histogram | — | Distribution des scores (buckets: 0,20,40,60,80,100) |
| `cgu_analysis_duration_seconds` | Histogram | — | Durée d'analyse (buckets: 5,10,15,30,60,120s) |

---

## Flux de données

```
raw_data/*.txt
      │
      ▼
  Worker (Python)
  ai_analyzer.py
  Claude Sonnet API
      │
      ▼ JSON structuré
  MongoDB
  too_long_to_read.analytic_reports
      │
      ▼ /api/v1/sync-metrics
  FastAPI
  /metrics (Prometheus format)
      │
      ▼ scrape toutes les 30s
  Prometheus
      │
      ▼ datasource
  Grafana Dashboard
```
