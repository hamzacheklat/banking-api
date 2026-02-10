Parfait 😄 Je te fais **un package complet** prêt à déployer pour ton cas :

* **FastAPI Python** → `/health` et `/metrics`
* **Prometheus YAML** → scrape les APIs
* **Grafana JSON** → dashboard multi-API
* **Alertes Grafana** → unhealthy + latence

On va prendre **3 APIs comme exemple** (`api1`, `api2`, `api3`).

---

# 1️⃣ Python FastAPI – `/health` + `/metrics`

```python
# app.py
from fastapi import FastAPI, Response
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST
import datetime
import random

app = FastAPI()

# --- Metrics ---
health_status = Gauge("api_health_status", "API health status (1=healthy, 0=unhealthy)", ["api_name"])
health_last_check = Gauge("api_health_last_check_timestamp", "Last health check timestamp", ["api_name"])
db_query_duration = Gauge("db_query_duration_seconds", "DB query duration", ["api_name", "db_type"])

# --- Simulate DB query latency ---
def simulate_db_query(api_name, db_type="oracle"):
    duration = random.uniform(0.1, 2.5)
    db_query_duration.labels(api_name=api_name, db_type=db_type).set(duration)
    return duration

# --- Health endpoint ---
@app.get("/health")
def health(api_name: str = "api1"):
    healthy = True  # remplacer par ta vraie logique
    now = datetime.datetime.utcnow()

    # Update metrics
    health_status.labels(api_name=api_name).set(1 if healthy else 0)
    health_last_check.labels(api_name=api_name).set(now.timestamp())
    simulate_db_query(api_name)  # optionnel pour latence DB

    return {"api_name": api_name, "status": "Healthy" if healthy else "Unhealthy", "time": now.isoformat() + "Z"}

# --- Metrics endpoint ---
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

✅ Cette version gère **plusieurs APIs** grâce au label `api_name`.

---

# 2️⃣ Prometheus scrape config (`prometheus.yml`)

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "fastapi_apis"
    metrics_path: /metrics
    static_configs:
      - targets:
          - api1.default.svc.cluster.local:80
          - api2.default.svc.cluster.local:80
          - api3.default.svc.cluster.local:80
```

---

# 3️⃣ Grafana dashboard JSON (exemple multi-API)

```json
{
  "annotations": {
    "list": []
  },
  "panels": [
    {
      "type": "stat",
      "title": "API Health Status",
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "api_health_status",
          "legendFormat": "{{api_name}}"
        }
      ],
      "thresholds": "0,1",
      "colorMode": "value",
      "valueMapping": [
        { "value": "1", "text": "Healthy" },
        { "value": "0", "text": "Unhealthy" }
      ]
    },
    {
      "type": "time-series",
      "title": "DB Query Duration",
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "db_query_duration_seconds",
          "legendFormat": "{{api_name}} - {{db_type}}"
        }
      ]
    },
    {
      "type": "time-series",
      "title": "Last Health Check",
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "api_health_last_check_timestamp",
          "legendFormat": "{{api_name}}"
        }
      ]
    }
  ],
  "schemaVersion": 36,
  "version": 1,
  "title": "Multi-API Health Dashboard"
}
```

---

# 4️⃣ Alerts Grafana

### 1️⃣ API Unhealthy

* **Query** :

```promql
api_health_status == 0
```

* **For** : 2 minutes
* **Severity** : Critical

### 2️⃣ API non scrappée (pas de metrics)

```promql
absent(api_health_status)
```

* **For** : 5 minutes
* **Severity** : Warning

### 3️⃣ DB query lente (>2s)

```promql
db_query_duration_seconds > 2
```

* **For** : 3 minutes
* **Severity** : Critical

---

# ✅ Résumé

* **FastAPI** → expose `/health` + `/metrics` avec labels `api_name`
* **Prometheus** → scrape tous les targets (`api1, api2, api3`)
* **Grafana** → dashboard multi-API prêt à importer
* **Alertes** → unhealthy, metrics absentes, DB lente

---

Si tu veux, je peux te fournir **un package Kubernetes complet** :

* FastAPI Deployment
* Services exposant `/metrics`
* Prometheus Deployment + ConfigMap
* Dashboard Grafana préchargé avec alertes

Ça te ferait un **setup full end-to-end** prêt à déployer pour plusieurs APIs.

Veux‑tu que je fasse ça ?
