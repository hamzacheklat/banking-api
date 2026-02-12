Parfait — ton setup est déjà très solide 👍
On va maintenant **le rendre production-grade** :

✅ alertes prêtes à déployer
✅ persistance Prometheus (backup + restart safe)
✅ dashboard Grafana JSON
✅ alert rules JSON Grafana

Je te donne **du concret prêt à coller**.

---

# ✅ 1️⃣ Sauvegarde + persistance Prometheus (critique en prod)

Tu as déjà un PVC — bien 👍 — mais ça protège **uniquement contre un restart Pod**, pas :

* corruption disque
* suppression PVC
* cluster crash

👉 On ajoute **snapshot automatique Prometheus**.

---

## 🔹 Activer l’API snapshot Prometheus

Dans le deployment :

```yaml
args:
  - "--storage.tsdb.path=/prometheus"
  - "--storage.tsdb.retention.time=15d"
  - "--web.enable-admin-api"
```

---

## 🔹 CronJob Kubernetes — snapshot automatique

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: prometheus-backup
spec:
  schedule: "0 */6 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: snapshot
            image: curlimages/curl
            command:
            - sh
            - -c
            - |
              curl -X POST http://prometheus:9090/api/v1/admin/tsdb/snapshot
          restartPolicy: OnFailure
```

👉 Snapshot toutes les 6h.

---

## 🔹 (Option recommandé prod)

Monter un volume externe :

```
/prometheus/snapshots → S3 / NFS / backup system
```

---

# 🚨 2️⃣ Alertes Prometheus (rules YAML)

👉 À mettre dans un ConfigMap `alerts.yaml`.

---

## 🔥 API DOWN

```yaml
groups:
- name: api-health
  rules:

  - alert: APIDown
    expr: up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "API down"
      description: "An API endpoint is unreachable"
```

---

## 🔥 Trop d’erreurs

```yaml
  - alert: HighErrorRate
    expr: |
      (
        sum(rate(http_requests_total{status=~"5.."}[5m]))
        /
        sum(rate(http_requests_total[5m]))
      ) > 0.05
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High error rate"
      description: "More than 5% errors"
```

---

## 🔥 API lente

```yaml
  - alert: HighLatency
    expr: |
      histogram_quantile(
        0.95,
        sum by (le) (
          rate(http_request_duration_seconds_bucket[5m])
        )
      ) > 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "API latency high"
      description: "P95 latency > 2s"
```

---

## 🔥 Saturation (in flight)

```yaml
  - alert: HighInflightRequests
    expr: http_requests_in_flight > 100
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "Too many in-flight requests"
```

---

# 📊 3️⃣ Dashboard Grafana — JSON prêt à importer

👉 Import → JSON → coller ceci.

{
"title": "API Overview",
"schemaVersion": 39,
"panels": [
{
"type": "timeseries",
"title": "Requests/sec",
"targets": [
{
"expr": "sum(rate(http_requests_total[1m]))"
}
]
},
{
"type": "timeseries",
"title": "5xx Errors/sec",
"targets": [
{
"expr": "sum(rate(http_requests_total{status=~"5.."}[1m]))"
}
]
},
{
"type": "timeseries",
"title": "Error Rate %",
"targets": [
{
"expr": "(sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))) * 100"
}
]
},
{
"type": "timeseries",
"title": "Latency P95",
"targets": [
{
"expr": "histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))"
}
]
},
{
"type": "timeseries",
"title": "Requests in Flight",
"targets": [
{
"expr": "http_requests_in_flight"
}
]
}
]
}

---

# 🚨 4️⃣ Alertes Grafana — JSON provisioning

👉 À placer dans `/etc/grafana/provisioning/alerting/api-alerts.json`

{
"apiVersion": 1,
"groups": [
{
"name": "API Alerts",
"folder": "API",
"interval": "1m",
"rules": [
{
"title": "High Error Rate",
"condition": "A",
"data": [
{
"refId": "A",
"expr": "(sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))) > 0.05"
}
]
},
{
"title": "API Down",
"condition": "A",
"data": [
{
"refId": "A",
"expr": "up == 0"
}
]
},
{
"title": "High Latency",
"condition": "A",
"data": [
{
"refId": "A",
"expr": "histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m]))) > 2"
}
]
}
]
}
]
}

---

# ✅ Résultat final — architecture robuste

```
API metrics
    ↓
Prometheus (PVC + snapshots)
    ↓
Grafana dashboards + alerting email
```

✔ restart safe
✔ sauvegardes
✔ alertes prod
✔ dashboard prêt

---

Si tu veux, je peux te faire ensuite :

👉 Alertmanager config email Slack
👉 Dashboard par endpoint
👉 SLO/SLA monitoring
👉 autoscaling basé sur metrics
👉 federation multi clusters

Dis-moi ce que tu veux next.
