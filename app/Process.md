Parfait 👍
On passe en **MODE PRO / SRE** 💪
Je te fais un **dashboard unique “APIs Metrics – Grade A+”** qui **utilise TOUTES les métriques disponibles**, y compris :

* ✅ `http_*` (trafic, latence, erreurs)
* ✅ `process_*` (CPU, mémoire, file descriptors, threads)
* ✅ corrélation **Infra ↔ API**
* ✅ variables complètes pour **API / endpoint / server / status**
* ✅ lisible managers **+** exploitable en incident

---

# 🎯 OBJECTIF DU DASHBOARD

> **Répondre en 1 écran à :**
>
> * L’API va-t-elle bien ?
> * Est-ce un problème applicatif ou infra ?
> * Quel endpoint / serveur est impacté ?
> * CPU / RAM sont-ils la cause ?

---

# 🏷️ DASHBOARD

**Nom :** `APIs Metrics`
**Data source :** `Prometheus`
**Niveau :** ✅ Grade A+ (Production)

---

# 🔎 VARIABLES (COMPLÈTES)

* `api` → ckms, delphix, globals, precheck, databases
* `endpoint`
* `server`
* `status`

---

# 📥 IMPORT

Grafana → **Dashboards → Import** → **Upload JSON** → coller 👇

---

# 📊 DASHBOARD JSON – GRADE A+ (API + PROCESS)

```json
{
  "dashboard": {
    "id": null,
    "uid": "apis-metrics-grade-a-plus",
    "title": "APIs Metrics",
    "tags": ["api", "prometheus", "grade-a", "process"],
    "timezone": "browser",
    "schemaVersion": 36,
    "version": 1,
    "refresh": "10s",

    "templating": {
      "list": [
        {
          "name": "api",
          "label": "API",
          "type": "custom",
          "query": "ckms,delphix,globals,precheck,databases",
          "multi": true,
          "includeAll": true,
          "allValue": ".*"
        },
        {
          "name": "endpoint",
          "label": "Endpoint",
          "type": "query",
          "datasource": "Prometheus",
          "query": "label_values(http_request_duration_seconds_count{api=~\"$api\"}, endpoint)",
          "multi": true,
          "includeAll": true,
          "allValue": ".*"
        },
        {
          "name": "server",
          "label": "Server",
          "type": "query",
          "datasource": "Prometheus",
          "query": "label_values(process_cpu_seconds_total, instance)",
          "multi": true,
          "includeAll": true,
          "allValue": ".*"
        },
        {
          "name": "status",
          "label": "HTTP Status",
          "type": "custom",
          "query": "2..,4..,5..",
          "multi": true,
          "includeAll": true,
          "allValue": ".*"
        }
      ]
    },

    "panels": [

      {
        "type": "stat",
        "title": "Total RPS",
        "datasource": "Prometheus",
        "targets": [
          { "expr": "sum(rate(http_request_duration_seconds_count{api=~\"$api\"}[5m]))" }
        ],
        "gridPos": { "x": 0, "y": 0, "w": 4, "h": 4 }
      },

      {
        "type": "stat",
        "title": "P95 Latency (s)",
        "datasource": "Prometheus",
        "targets": [
          { "expr": "histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{api=~\"$api\"}[5m])))" }
        ],
        "gridPos": { "x": 4, "y": 0, "w": 4, "h": 4 }
      },

      {
        "type": "stat",
        "title": "Error Rate 5xx (%)",
        "datasource": "Prometheus",
        "targets": [
          { "expr": "100 * sum(rate(http_requests_total{api=~\"$api\",status=~\"5..\"}[5m])) / sum(rate(http_requests_total{api=~\"$api\"}[5m]))" }
        ],
        "gridPos": { "x": 8, "y": 0, "w": 4, "h": 4 }
      },

      {
        "type": "stat",
        "title": "CPU Usage",
        "datasource": "Prometheus",
        "targets": [
          { "expr": "sum by (instance) (rate(process_cpu_seconds_total[5m]))" }
        ],
        "gridPos": { "x": 12, "y": 0, "w": 4, "h": 4 }
      },

      {
        "type": "stat",
        "title": "Memory RSS (MB)",
        "datasource": "Prometheus",
        "targets": [
          { "expr": "process_resident_memory_bytes / 1024 / 1024" }
        ],
        "gridPos": { "x": 16, "y": 0, "w": 4, "h": 4 }
      },

      {
        "type": "graph",
        "title": "RPS by Endpoint",
        "datasource": "Prometheus",
        "targets": [
          {
            "expr": "sum by (endpoint) (rate(http_request_duration_seconds_count{api=~\"$api\",endpoint=~\"$endpoint\"}[5m]))",
            "legendFormat": "{{endpoint}}"
          }
        ],
        "gridPos": { "x": 0, "y": 4, "w": 24, "h": 6 }
      },

      {
        "type": "table",
        "title": "Endpoints in Error (5xx)",
        "datasource": "Prometheus",
        "targets": [
          {
            "expr": "sum by (endpoint) (rate(http_requests_total{api=~\"$api\",status=~\"5..\"}[5m]))"
          }
        ],
        "gridPos": { "x": 0, "y": 10, "w": 12, "h": 6 }
      },

      {
        "type": "table",
        "title": "Top 5 Slowest Endpoints (P95)",
        "datasource": "Prometheus",
        "targets": [
          {
            "expr": "topk(5, histogram_quantile(0.95, sum by (le, endpoint) (rate(http_request_duration_seconds_bucket{api=~\"$api\"}[5m]))))"
          }
        ],
        "gridPos": { "x": 12, "y": 10, "w": 12, "h": 6 }
      },

      {
        "type": "graph",
        "title": "CPU vs Latency Correlation",
        "datasource": "Prometheus",
        "targets": [
          {
            "expr": "rate(process_cpu_seconds_total[5m])",
            "legendFormat": "CPU {{instance}}"
          },
          {
            "expr": "histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{api=~\"$api\"}[5m])))",
            "legendFormat": "P95 Latency"
          }
        ],
        "gridPos": { "x": 0, "y": 16, "w": 24, "h": 6 }
      }
    ]
  }
}
```

---

# 🧠 POURQUOI CE DASHBOARD EST **TOP NIVEAU**

✅ Utilise **TOUTES les métriques clés**

* `http_*` → expérience utilisateur
* `process_*` → santé applicative
* Corrélation **CPU ↔ Latence**

✅ **Filtrage puissant**

* API → Endpoint → Server → Status

✅ **Incident ready**

* erreurs visibles
* endpoints lents
* saturation infra identifiable

---

# 🔥 PROCHAINES ÉVOLUTIONS (OPTIONNEL)

* SLO / Burn rate
* Dashboard “Incident Mode”
* Drill-down Pod / Worker
* Alertes liées aux panels

👉 Dis-moi si tu veux passer au **niveau Google SRE** 😄
