Parfait 👍
Je te refais **une version CLEAN, SIMPLE et COHÉRENTE de A à Z**, sans bruit, **STG / PRD bien séparés**, exactement comme on le ferait en prod.

Je pars sur **Blackbox Exporter + Prometheus + Grafana**, **EMEA only**.

---

# 🎯 OBJECTIF FINAL

* ✅ Surveiller `/health` des APIs **STG** et **PRD**
* ✅ Séparation claire **STG / PRD**
* ✅ **Un seul Blackbox Exporter**
* ✅ Prometheus Region qui scrape
* ✅ Dashboard Grafana + alertes
* ✅ Zéro code custom

---

# 🧱 1️⃣ ARCHITECTURE (DÉFINITIVE)

Dans ton repo :

```
k8s/manifests/prometheus/
├── prometheus-region/
│   ├── base/
│   │   └── configs/
│   │       └── prometheus.yaml
│   └── overlays/
│       ├── stg/
│       │   ├── kustomization.yaml
│       │   └── prometheus-patch.yaml
│       └── prd/
│           ├── kustomization.yaml
│           └── prometheus-patch.yaml
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

# 📦 2️⃣ BLACKBOX EXPORTER (COMMUN STG / PRD)

## `exporters/blackbox/base/configmap.yaml`

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

## `exporters/blackbox/base/deployment.yaml`

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

## `exporters/blackbox/base/service.yaml`

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

## `exporters/blackbox/base/kustomization.yaml`

```yaml
resources:
  - configmap.yaml
  - deployment.yaml
  - service.yaml
```

---

# 📡 3️⃣ PROMETHEUS – BASE (COMMUN)

## `prometheus-region/base/configs/prometheus.yaml`

⚠️ **PAS de STG / PRD ici**

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets:
          - localhost:9090
```

---

# 🌍 4️⃣ PROMETHEUS STG

## `prometheus-region/overlays/stg/prometheus-patch.yaml`

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

## `prometheus-region/overlays/stg/kustomization.yaml`

```yaml
bases:
  - ../../base
```

---

# 🌍 5️⃣ PROMETHEUS PRD

## `prometheus-region/overlays/prd/prometheus-patch.yaml`

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

## `prometheus-region/overlays/prd/kustomization.yaml`

```yaml
bases:
  - ../../base
```

---

# 📊 6️⃣ DASHBOARD GRAFANA (UN SEUL)

## Variable Grafana

**Nom** : `job`

```promql
label_values(probe_success, job)
```

---

## Panels

### 🟢 Disponibilité

```promql
probe_success{job="$job"}
```

---

### ⏱ Latence

```promql
probe_duration_seconds{job="$job"}
```

---

### 🌐 HTTP Status Code

```promql
probe_http_status_code{job="$job"}
```

---

# 🚨 7️⃣ ALERTES GRAFANA

## 🔴 STG – API DOWN

```promql
probe_success{job="blackbox-health-emea-stg"} == 0
```

* for: `2m`
* severity: `warning`

---

## 🔴 PRD – API DOWN

```promql
probe_success{job="blackbox-health-emea-prd"} == 0
```

* for: `1m`
* severity: `critical`

---

## 🟠 PRD – API lente

```promql
probe_duration_seconds{job="blackbox-health-emea-prd"} > 1
```

---

# ✅ 8️⃣ POURQUOI C’EST LA BONNE SOLUTION

✅ STG / PRD **clairement séparés**
✅ exporter unique
✅ Prometheus propre
✅ facile à maintenir
✅ validable en revue d’archi
✅ zéro code
✅ scalable plus tard

---

Si tu veux, prochaine étape possible :

* 🔐 ajouter headers d’auth
* 📅 alerte expiration TLS
* 📄 README d’archi prêt audit
* 🧠 argumentaire pour comité infra

Dis-moi 👍
