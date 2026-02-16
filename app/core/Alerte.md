Voici un **dashboard Grafana clair, lisible et utile en production**, avec des titres **en anglais**, organisé comme un dashboard SRE moderne.

Il est structuré en 4 sections :

1. Traffic
2. Errors
3. Latency
4. System

Puis je te donne les **alerts Prometheus** prêtes à l’emploi.

---

# 📊 Grafana Dashboard – “API Production Overview”

Dans Grafana :

* Dashboards → Import
* Coller le JSON ci-dessous
* Choisir ta datasource Prometheus

## Dashboard JSON

```json
{
  "title": "API Production Overview",
  "schemaVersion": 36,
  "version": 1,
  "refresh": "10s",
  "panels": [
    {
      "type": "row",
      "title": "Traffic"
    },
    {
      "type": "stat",
      "title": "Requests per Second",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total[1m]))"
        }
      ],
      "gridPos": { "h": 4, "w": 6, "x": 0, "y": 1 }
    },
    {
      "type": "stat",
      "title": "In-Progress Requests",
      "targets": [
        {
          "expr": "sum(http_requests_in_progress)"
        }
      ],
      "gridPos": { "h": 4, "w": 6, "x": 6, "y": 1 }
    },
    {
      "type": "graph",
      "title": "Requests per Endpoint",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total[1m])) by (endpoint)"
        }
      ],
      "gridPos": { "h": 8, "w": 12, "x": 12, "y": 1 }
    },

    {
      "type": "row",
      "title": "Errors"
    },
    {
      "type": "stat",
      "title": "Error Rate (%)",
      "targets": [
        {
          "expr": "sum(rate(http_requests_5xx_total[5m])) / sum(rate(http_requests_total[5m])) * 100"
        }
      ],
      "gridPos": { "h": 4, "w": 6, "x": 0, "y": 10 }
    },
    {
      "type": "stat",
      "title": "4xx Rate",
      "targets": [
        {
          "expr": "sum(rate(http_requests_4xx_total[5m]))"
        }
      ],
      "gridPos": { "h": 4, "w": 6, "x": 6, "y": 10 }
    },
    {
      "type": "stat",
      "title": "5xx Rate",
      "targets": [
        {
          "expr": "sum(rate(http_requests_5xx_total[5m]))"
        }
      ],
      "gridPos": { "h": 4, "w": 6, "x": 12, "y": 10 }
    },
    {
      "type": "graph",
      "title": "Errors per Endpoint",
      "targets": [
        {
          "expr": "sum(rate(http_requests_5xx_total[5m])) by (endpoint)"
        }
      ],
      "gridPos": { "h": 8, "w": 12, "x": 0, "y": 14 }
    },

    {
      "type": "row",
      "title": "Latency"
    },
    {
      "type": "graph",
      "title": "Latency p50",
      "targets": [
        {
          "expr": "histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))"
        }
      ],
      "gridPos": { "h": 6, "w": 8, "x": 0, "y": 23 }
    },
    {
      "type": "graph",
      "title": "Latency p95",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))"
        }
      ],
      "gridPos": { "h": 6, "w": 8, "x": 8, "y": 23 }
    },
    {
      "type": "graph",
      "title": "Latency p99",
      "targets": [
        {
          "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))"
        }
      ],
      "gridPos": { "h": 6, "w": 8, "x": 16, "y": 23 }
    },

    {
      "type": "row",
      "title": "System"
    },
    {
      "type": "graph",
      "title": "CPU Usage",
      "targets": [
        {
          "expr": "rate(process_cpu_seconds_total[1m])"
        }
      ],
      "gridPos": { "h": 6, "w": 12, "x": 0, "y": 30 }
    },
    {
      "type": "graph",
      "title": "Memory Usage",
      "targets": [
        {
          "expr": "process_resident_memory_bytes"
        }
      ],
      "gridPos": { "h": 6, "w": 12, "x": 12, "y": 30 }
    }
  ]
}
```

---

# 🚨 Alertes Prometheus prêtes pour production

Fichier : `alerts.yml`

```yaml
groups:
  - name: api-production
    rules:

      # ========================
      # Availability
      # ========================
      - alert: APIInstanceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "API instance down"
          description: "Instance {{ $labels.instance }} is not responding"

      # ========================
      # Errors
      # ========================
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_5xx_total[5m]))
          /
          sum(rate(http_requests_total[5m]))
          > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate"
          description: "Error rate > 5% for 2 minutes"

      - alert: ErrorSpike
        expr: sum(rate(http_requests_5xx_total[1m])) > 5
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Error spike detected"

      # ========================
      # Latency
      # ========================
      - alert: HighLatencyP95
        expr: |
          histogram_quantile(
            0.95,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
          ) > 1
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "High latency p95"
          description: "p95 latency above 1 second"

      - alert: CriticalLatencyP99
        expr: |
          histogram_quantile(
            0.99,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
          ) > 3
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Critical latency p99"
          description: "p99 latency above 3 seconds"

      # ========================
      # Resource usage
      # ========================
      - alert: HighMemoryUsage
        expr: process_resident_memory_bytes > 1e9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"

      - alert: HighCPUUsage
        expr: rate(process_cpu_seconds_total[1m]) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage"
```

---

# 🧭 Alertmanager minimal (Slack ou email)

`alertmanager.yml`

```yaml
route:
  receiver: default
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 1h

receivers:
  - name: default
    email_configs:
      - to: ops@yourcompany.com
        from: alertmanager@yourcompany.com
        smarthost: smtp:587
        auth_username: user
        auth_password: pass
```

---

# Ce dashboard te permet de voir immédiatement

En moins de 5 secondes :

* Si l’API reçoit du trafic
* Si elle a des erreurs
* Si elle est lente
* Si elle consomme trop de ressources

C’est exactement le type de dashboard utilisé en prod (SRE style).

---

Si tu veux, je peux maintenant te fournir :

* un **docker-compose complet** (Prometheus + Grafana + Alertmanager)
* un **dashboard encore plus avancé** (multi-service, multi-instance)
* un **dashboard orienté métier** pour ton pipeline Cinego.
