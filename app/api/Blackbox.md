Parfait 👍
On va faire **STG et PRD bien séparés**, **proprement**, **sans dupliquer inutilement**, et **100 % compatible avec ton archi actuelle**.
C’est exactement ce qu’un reviewer infra attend.

Je te donne **tout** :

* où mettre les fichiers
* ce qui change entre STG / PRD
* Prometheus
* Grafana dashboard
* alertes

---

# 🧱 1️⃣ PRINCIPE (clair et simple)

👉 **Un seul Blackbox Exporter déployé**
👉 **Deux jobs Prometheus distincts** :

* `blackbox-health-emea-stg`
* `blackbox-health-emea-prd`

👉 La séparation **STG / PRD se fait dans Prometheus**, pas dans l’exporter
👉 C’est **la bonne pratique officielle Prometheus**

---

# 📁 2️⃣ STRUCTURE FINALE (chez toi)

```
k8s/manifests/prometheus/
├── prometheus-region/
│   ├── base/
│   │   └── configs/
│   │       └── prometheus.yaml
│   └── overlays/
│       ├── stg/
│       │   └── prometheus-patch.yaml
│       └── prd/
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

📌

* **Blackbox = commun**
* **STG / PRD = overlays Prometheus**

---

# 📦 3️⃣ BLACKBOX EXPORTER (COMMUN)

👉 **AUCUN changement** entre STG / PRD

### `exporters/blackbox/base/configmap.yaml`

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

### `deployment.yaml`

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

### `service.yaml`

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

# 📡 4️⃣ PROMETHEUS – BASE (COMMUN)

📄 `prometheus-region/base/configs/prometheus.yaml`

⚠️ **PAS d’URLs ici**
Juste la base Prometheus.

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

# 🌍 5️⃣ PROMETHEUS STG

📄 `prometheus-region/overlays/stg/prometheus-patch.yaml`

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
      - job_name: "blackbox-health-emea-stg"
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

# 🌍 6️⃣ PROMETHEUS PRD

📄 `prometheus-region/overlays/prd/prometheus-patch.yaml`

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
      - job_name: "blackbox-health-emea-prd"
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

📌

* **URLs séparées**
* **jobs séparés**
* **alertes séparables**
* **aucune ambiguïté STG / PRD**

---

# 📊 7️⃣ DASHBOARD GRAFANA (STG + PRD)

👉 **Un seul dashboard**, filtré par job.

### Variable Grafana

**Variable :** `job`

```promql
label_values(probe_success, job)
```

---

### Panels (PROMQL)

#### 🟢 Disponibilité

```promql
probe_success{job="$job"}
```

#### ⏱ Latence

```promql
probe_duration_seconds{job="$job"}
```

#### 🌐 HTTP Code

```promql
probe_http_status_code{job="$job"}
```

👉 Tu switches STG / PRD avec un dropdown.

---

# 🚨 8️⃣ ALERTES GRAFANA (SÉPARÉES)

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

## 🟠 PRD – Latence élevée

```promql
probe_duration_seconds{job="blackbox-health-emea-prd"} > 1
```

---

# ✅ 9️⃣ POURQUOI CETTE ARCHI EST EXCELLENTE

✅ séparation claire STG / PRD
✅ un seul exporter
✅ zéro duplication infra
✅ simple à maintenir
✅ clean en revue d’archi
✅ scalable plus tard
✅ bank-grade

---

## 🔜 Tu veux aller encore plus loin ?

Je peux t’ajouter :

* 🔐 headers d’auth par env
* 📅 alerte expiration TLS
* 📄 README d’audit
* 🧠 justification formelle d’archi
* 🔄 migration progressive Python → Blackbox

Dis-moi 👌
