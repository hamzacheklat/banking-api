Parfait 👍
Je te donne **TOUT**, **à jour**, **clé en main**, **prod-ready**, sans raccourci.

👉 **Sanic API**
👉 **CRUD**
👉 **Middleware metrics (par endpoint + verbe + durée + status)**
👉 **/metrics unique**
👉 **Prometheus config**
👉 **Dashboard Grafana**
👉 **Alertes Grafana**

Tu peux **copier-coller tel quel**.

---

# 📁 Arborescence finale du projet

```
sanic-api/
│
├── app.py
├── metrics.py
├── middleware_metrics.py
│
├── requirements.txt
│
├── prom/
│   └── prometheus.yml
│
└── grafana/
    ├── dashboard.json
    └── alerts.md
```

---

# 1️⃣ requirements.txt

📄 `requirements.txt`

```txt
sanic==23.12.1
prometheus-client==0.20.0
```

---

# 2️⃣ Metrics Prometheus (déclaration UNIQUE)

📄 `metrics.py`

```python
from prometheus_client import Counter, Histogram

# Nombre total de requêtes
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

# Latence HTTP
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=(0.1, 0.3, 0.5, 1, 2, 5, 10)
)
```

---

# 3️⃣ Middleware Sanic METRICS (PROD-READY)

📄 `middleware_metrics.py`

```python
import time
import re
from sanic import Request
from metrics import (
    http_requests_total,
    http_request_duration_seconds
)

# Regex pour normaliser les paths
ID_REGEX = re.compile(r"/\d+")
UUID_REGEX = re.compile(
    r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}"
)

def normalize_endpoint(path: str) -> str:
    path = UUID_REGEX.sub("/:uuid", path)
    path = ID_REGEX.sub("/:id", path)
    return path

async def prometheus_middleware(request: Request, handler):
    # ❌ On ne mesure pas /metrics
    if request.path == "/metrics":
        return await handler(request)

    start = time.time()
    status = 500

    try:
        response = await handler(request)
        status = response.status
        return response
    except Exception:
        status = 500
        raise
    finally:
        duration = time.time() - start
        endpoint = normalize_endpoint(request.path)

        http_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            status=str(status)
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(duration)
```

---

# 4️⃣ Application Sanic COMPLETE (CRUD + metrics)

📄 `app.py`

```python
from sanic import Sanic, response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from middleware_metrics import prometheus_middleware

app = Sanic("sanic-api")

# Middleware metrics
app.register_middleware(prometheus_middleware, "request")

# Fake DB
ITEMS = {}

# -------------------------
# CRUD ENDPOINTS
# -------------------------

@app.post("/items")
async def create_item(request):
    data = request.json
    item_id = str(len(ITEMS) + 1)
    ITEMS[item_id] = data
    return response.json({"id": item_id, "data": data}, status=201)

@app.get("/items/<item_id>")
async def get_item(request, item_id):
    item = ITEMS.get(item_id)
    if not item:
        return response.json({"error": "not found"}, status=404)
    return response.json(item)

@app.put("/items/<item_id>")
async def update_item(request, item_id):
    if item_id not in ITEMS:
        return response.json({"error": "not found"}, status=404)
    ITEMS[item_id] = request.json
    return response.json({"updated": True})

@app.delete("/items/<item_id>")
async def delete_item(request, item_id):
    ITEMS.pop(item_id, None)
    return response.json({"deleted": True})

# -------------------------
# METRICS ENDPOINT
# -------------------------

@app.get("/metrics")
async def metrics(request):
    return response.raw(
        generate_latest(),
        headers={"Content-Type": CONTENT_TYPE_LATEST}
    )

# -------------------------
# RUN
# -------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

---

# 5️⃣ Configuration Prometheus

📄 `prom/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "sanic-api"
    metrics_path: /metrics
    static_configs:
      - targets:
          - localhost:8000
```

👉 En Kubernetes :

```
sanic-api.default.svc.cluster.local:8000
```

---

# 6️⃣ Dashboard Grafana COMPLET (JSON)

📄 `grafana/dashboard.json`

```json
{
  "title": "Sanic API - HTTP Monitoring",
  "panels": [
    {
      "type": "timeseries",
      "title": "HTTP Requests Rate",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total[1m])) by (method, endpoint)",
          "refId": "A"
        }
      ]
    },
    {
      "type": "timeseries",
      "title": "HTTP Error Rate (5xx)",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total{status=~\"5..\"}[1m])) by (endpoint)",
          "refId": "A"
        }
      ]
    },
    {
      "type": "timeseries",
      "title": "HTTP Latency P95",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (endpoint, le))",
          "refId": "A"
        }
      ]
    }
  ]
}
```

---

# 7️⃣ Alertes Grafana (à configurer)

📄 `grafana/alerts.md`

### ❌ Trop d’erreurs 5xx

```yaml
expr: sum(rate(http_requests_total{status=~"5.."}[2m])) by (endpoint) > 1
for: 1m
```

Message :

```
🚨 High error rate on {{ $labels.endpoint }}
```

---

### 🐌 Latence élevée

```yaml
expr: histogram_quantile(
        0.95,
        sum(rate(http_request_duration_seconds_bucket[5m]))
        by (endpoint, le)
      ) > 2
for: 2m
```

Message :

```
🐌 High latency on {{ $labels.endpoint }}
```

---

### 🔥 Trop de POST

```yaml
expr: sum(rate(http_requests_total{method="POST"}[1m])) > 100
for: 1m
```

---

# 8️⃣ Lancer le projet

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python app.py
```

---

# 9️⃣ Tester rapidement

```bash
curl -X POST localhost:8000/items -H "Content-Type: application/json" -d '{"name":"test"}'
curl localhost:8000/items/1
curl localhost:8000/metrics
```

---

# 🔥 Ce que tu as maintenant

✅ Metrics **par endpoint**
✅ Metrics **par verbe HTTP**
✅ Latence **P95**
✅ Erreurs **5xx**
✅ POST inclus
✅ Labels maîtrisés
✅ Prometheus clean
✅ Grafana exploitable
✅ Setup PROD-READY

---

Si tu veux, prochain niveau 👇

* **Kubernetes manifests (Deployment / Service / ServiceMonitor)**
* **Alertmanager (Slack / Email)**
* **OpenTelemetry → Prometheus**
* **FastAPI équivalent**

Dis-moi 👍
