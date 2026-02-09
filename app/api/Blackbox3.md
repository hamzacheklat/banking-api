Parfait 👍
Là on va faire **la version PROPRE, FINALE, bank-ready**, **STG + PRD**, **sans casser l’existant**, **en respectant TON arborescence** et **Kustomize**.

Je vais te donner :

1. ✅ **Architecture finale**
2. ✅ **Tous les fichiers (complets)**
3. ✅ **Comment déployer STG puis PRD**
4. ✅ **Comment tester**
5. ✅ **Comment rollback**

On fait ça **calmement et proprement**.

---

# 🧱 1️⃣ ARCHITECTURE FINALE (ADAPTÉE À TON REPO)

👉 On **NE TOUCHE PAS** à `prometheus/base` directement pour STG/PRD
👉 On utilise **overlays** (bonne pratique)

```
prometheus/
├── base/
│   ├── configs/
│   │   └── prometheus.yaml          # config commune
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── kustomization.yaml
│
├── overlays/
│   ├── stg/
│   │   ├── kustomization.yaml
│   │   └── prometheus-patch.yaml    # scrape STG
│   │
│   └── prd/
│       ├── kustomization.yaml
│       └── prometheus-patch.yaml    # scrape PRD
│
└── exporters/
    └── blackbox/
        └── base/
            ├── configmap.yaml
            ├── deployment.yaml
            ├── service.yaml
            └── kustomization.yaml
```

---

# 📦 2️⃣ BLACKBOX EXPORTER (COMMUN STG + PRD)

## `prometheus/exporters/blackbox/base/configmap.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: blackbox-config
  namespace: monitoring
data:
  blackbox.yml: |
    modules:
      http_2xx:
        prober: http
        timeout: 5s
        http:
          method: GET
          preferred_ip_protocol: ip4
```

---

## `prometheus/exporters/blackbox/base/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blackbox-exporter
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: blackbox-exporter
  template:
    metadata:
      labels:
        app: blackbox-exporter
    spec:
      containers:
        - name: blackbox
          image: prom/blackbox-exporter:v0.25.0
          args:
            - "--config.file=/etc/blackbox/blackbox.yml"
          ports:
            - containerPort: 9115
          volumeMounts:
            - name: config
              mountPath: /etc/blackbox
      volumes:
        - name: config
          configMap:
            name: blackbox-config
```

---

## `prometheus/exporters/blackbox/base/service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: blackbox-exporter
  namespace: monitoring
spec:
  selector:
    app: blackbox-exporter
  ports:
    - port: 9115
      targetPort: 9115
```

---

## `prometheus/exporters/blackbox/base/kustomization.yaml`

```yaml
resources:
  - configmap.yaml
  - deployment.yaml
  - service.yaml
```

---

# 📡 3️⃣ PROMETHEUS BASE (COMMUN)

## `prometheus/base/configs/prometheus.yaml`

⚠️ **AUCUNE notion STG / PRD ici**

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets:
          - localhost:9090
```

---

# 🌍 4️⃣ OVERLAY STG

## `prometheus/overlays/stg/prometheus-patch.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yaml: |
    global:
      scrape_interval: 15s

    scrape_configs:
      - job_name: prometheus
        static_configs:
          - targets:
              - localhost:9090

      - job_name: blackbox-health-emea-stg
        metrics_path: /probe
        params:
          module: [http_2xx]
        static_configs:
          - targets:
              - https://data.stg.emea.example.com/health
              - https://billing.stg.emea.example.com/health
        relabel_configs:
          - source_labels: [__address__]
            target_label: __param_target
          - source_labels: [__param_target]
            target_label: instance
          - target_label: __address__
            replacement: blackbox-exporter.monitoring.svc.cluster.local:9115
```

---

## `prometheus/overlays/stg/kustomization.yaml`

```yaml
resources:
  - ../../base

patchesStrategicMerge:
  - prometheus-patch.yaml
```

---

# 🌍 5️⃣ OVERLAY PRD

## `prometheus/overlays/prd/prometheus-patch.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yaml: |
    global:
      scrape_interval: 15s

    scrape_configs:
      - job_name: prometheus
        static_configs:
          - targets:
              - localhost:9090

      - job_name: blackbox-health-emea-prd
        metrics_path: /probe
        params:
          module: [http_2xx]
        static_configs:
          - targets:
              - https://data.prd.emea.example.com/health
              - https://billing.prd.emea.example.com/health
        relabel_configs:
          - source_labels: [__address__]
            target_label: __param_target
          - source_labels: [__param_target]
            target_label: instance
          - target_label: __address__
            replacement: blackbox-exporter.monitoring.svc.cluster.local:9115
```

---

## `prometheus/overlays/prd/kustomization.yaml`

```yaml
resources:
  - ../../base

patchesStrategicMerge:
  - prometheus-patch.yaml
```

---

# 🚀 6️⃣ DÉPLOIEMENT (SANS TOUT CASSER)

## 1️⃣ Blackbox (une seule fois)

```bash
kubectl apply -k prometheus/exporters/blackbox/base
```

---

## 2️⃣ STG (toujours en premier)

```bash
kubectl apply -k prometheus/overlays/stg --dry-run=server
kubectl apply -k prometheus/overlays/stg
```

---

## 3️⃣ Validation STG

Prometheus → **Status / Targets**

```
blackbox-health-emea-stg   UP
```

---

## 4️⃣ PRD (après validation STG)

```bash
kubectl apply -k prometheus/overlays/prd --dry-run=server
kubectl apply -k prometheus/overlays/prd
```

---

# 🧪 7️⃣ TESTS RAPIDES

### PromQL

```promql
probe_success
```

```promql
probe_duration_seconds
```

---

# 🔙 8️⃣ ROLLBACK IMMÉDIAT

```bash
kubectl rollout undo deployment prometheus
```

ou

```bash
git revert <commit>
kubectl apply -k prometheus/overlays/stg
```

---

# ✅ POURQUOI CETTE SOLUTION EST SOLIDE

✔ STG / PRD isolés
✔ Blackbox partagé
✔ Aucun code
✔ Kustomize propre
✔ Facile à auditer
✔ Bank-ready

---

## 🔜 Tu veux aller encore plus loin ?

Je peux te fournir :

* 📊 **Dashboard Grafana JSON prêt à importer**
* 🚨 **Alerting PrometheusRule**
* 🔐 **Headers d’auth / mTLS**
* 🧾 **Runbook d’exploitation**

Dis-moi ce que tu veux, on continue 💪
