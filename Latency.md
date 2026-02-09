Parfait.
Je te donne **TOUT**, prêt à poser dans ton repo, **EMEA only**, **sans Docker custom**, **compatible avec ta structure actuelle Prometheus + Kustomize**.
Tu peux quasiment **copier / coller**.

Je pars sur ces hypothèses (dis-moi si un nom diffère) :

* namespace : `monitoring`
* Prometheus qui scrape : `prometheus-region`
* environnements : `stg` et `prd`
* une seule région : **EMEA**

---

# 🧱 1️⃣ Arborescence À AJOUTER

À la racine de `manifests/prometheus/` :

```
exporters/
└── health-exporter/
    ├── base/
    │   ├── configmap.yaml
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   └── kustomization.yaml
    └── overlays/
        ├── stg/
        │   └── kustomization.yaml
        └── prd/
            └── kustomization.yaml
```

---

# 🐍 2️⃣ Script Python (metrics Prometheus)

📄 **`exporters/health-exporter/base/configmap.yaml`**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: health-exporter-script
  namespace: monitoring
data:
  health_exporter.py: |
    import os
    import time
    import requests
    from http.server import BaseHTTPRequestHandler, HTTPServer

    ENV = os.getenv("ENV", "stg")

    APIS = {
        "stg": {
            "data-api": "https://data.stg.emea.example.com/health",
            "billing-api": "https://billing.stg.emea.example.com/health",
        },
        "prd": {
            "data-api": "https://data.prd.emea.example.com/health",
            "billing-api": "https://billing.prd.emea.example.com/health",
        },
    }[ENV]

    TIMEOUT = 5


    def collect_metrics():
        lines = []

        for api, url in APIS.items():
            try:
                start = time.time()
                r = requests.get(url, timeout=TIMEOUT)
                elapsed = int((time.time() - start) * 1000)

                data = r.json()
                status = 1 if data.get("status") == "Healthy" else 0

                lines.append(f'api_health_status{{api="{api}"}} {status}')
                lines.append(f'api_response_time_ms{{api="{api}"}} {elapsed}')

                if "database" in data:
                    for db, info in data["database"].items():
                        db_status = 1 if info.get("status") == "Healthy" else 0
                        db_rt = info.get("response_time", 0)

                        lines.append(
                            f'db_health_status{{api="{api}",db="{db}"}} {db_status}'
                        )
                        lines.append(
                            f'db_response_time_ms{{api="{api}",db="{db}"}} {db_rt}'
                        )

            except Exception:
                lines.append(f'api_health_status{{api="{api}"}} 0')

        return "\n".join(lines) + "\n"


    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/metrics":
                metrics = collect_metrics()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.end_headers()
                self.wfile.write(metrics.encode())


    HTTPServer(("0.0.0.0", 9100), Handler).serve_forever()
```

👉 Tu peux modifier les URLs **sans toucher au reste**.

---

# 🚀 3️⃣ Deployment du health-exporter

📄 **`exporters/health-exporter/base/deployment.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: health-exporter
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: health-exporter
  template:
    metadata:
      labels:
        app: health-exporter
    spec:
      containers:
        - name: health-exporter
          image: python:3.11-slim
          command: ["sh", "-c"]
          args:
            - |
              pip install --no-cache-dir requests && \
              python /app/health_exporter.py
          ports:
            - containerPort: 9100
          env:
            - name: ENV
              value: stg   # surchargé en overlay
          volumeMounts:
            - name: script
              mountPath: /app
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 200m
              memory: 128Mi
      volumes:
        - name: script
          configMap:
            name: health-exporter-script
```

---

# 🌐 4️⃣ Service Kubernetes

📄 **`exporters/health-exporter/base/service.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: health-exporter
  namespace: monitoring
spec:
  selector:
    app: health-exporter
  ports:
    - name: metrics
      port: 9100
      targetPort: 9100
```

---

# 🧩 5️⃣ Kustomization base

📄 **`exporters/health-exporter/base/kustomization.yaml`**

```yaml
resources:
  - configmap.yaml
  - deployment.yaml
  - service.yaml
```

---

# 🌍 6️⃣ Overlays STG / PRD

## STG

📄 **`exporters/health-exporter/overlays/stg/kustomization.yaml`**

```yaml
bases:
  - ../../base

patches:
  - target:
      kind: Deployment
      name: health-exporter
    patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/env/0/value
        value: stg
```

---

## PRD

📄 **`exporters/health-exporter/overlays/prd/kustomization.yaml`**

```yaml
bases:
  - ../../base

patches:
  - target:
      kind: Deployment
      name: health-exporter
    patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/env/0/value
        value: prd
```

---

# 📡 7️⃣ Prometheus – AJOUT DU SCRAPE

Dans **TON** Prometheus EMEA :

📄 `prometheus-region/base/configs/prometheus.yaml`

👉 Ajoute **à la fin** de `scrape_configs` :

```yaml
  - job_name: "health-exporter-emea"
    scrape_interval: 15s
    metrics_path: /metrics
    static_configs:
      - targets:
          - health-exporter.monitoring.svc.cluster.local:9100
```

---

# 📊 8️⃣ Métriques disponibles (PROMQL)

### API status

```promql
api_health_status
```

### API latency

```promql
api_response_time_ms
```

### DB status

```promql
db_health_status
```

### DB latency

```promql
db_response_time_ms
```

---

# 🚨 9️⃣ Alertes Grafana (recommandé)

### API down (2 min)

```promql
api_health_status == 0
```

### API lente (>1s)

```promql
api_response_time_ms > 1000
```

---

# ✅ 10️⃣ Checklist finale

✔ aucun Dockerfile
✔ aucune image custom
✔ compatible Kustomize
✔ EMEA only
✔ STG / PRD propre
✔ scalable plus tard
✔ validable en revue d’archi

---

## 🔜 Tu veux que je fasse quoi ensuite ?

* 📊 **Dashboard Grafana JSON prêt à importer**
* 🔐 **Ajout auth / token**
* 🧪 **Retries / circuit breaker**
* 📝 **README d’archi (banque-friendly)**

Dis-moi, et on continue proprement 👌
