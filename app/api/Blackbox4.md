Parfait, merci pour la capture 👍
Ton arborescence est **saine** et **très proche de ce qu’on veut**. On va **s’intégrer dedans**, pas la casser.

Je vais faire ça **pas à pas**, en mode **STG only**, testable immédiatement.

---

# 🧠 Ce que tu as DÉJÀ (important)

D’après ton screenshot :

```
prometheus/
├── base/
│   ├── configs/
│   │   └── prometheus.yaml   👈 CONFIG PROM
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── kustomization.yaml
│
└── exporters/
    └── blackbox/
        └── base/
            ├── configmap.yaml
            ├── deployment.yaml
            ├── service.yaml
            └── kustomization.yaml
```

👉 **C’est PARFAIT**
👉 Il manque juste **le lien entre Prometheus et Blackbox**

---

# 🎯 OBJECTIF IMMÉDIAT

1. **Déployer Blackbox**
2. **Ajouter le scrape Blackbox dans Prometheus**
3. **Tester en STG**
4. **Zéro impact PRD**

---

# ✅ 1️⃣ DÉPLOYER BLACKBOX EXPORTER (SI PAS ENCORE FAIT)

Depuis la racine de ton repo :

```bash
kubectl apply -k prometheus/exporters/blackbox/base
```

Vérifie :

```bash
kubectl get pods | grep blackbox
kubectl get svc | grep blackbox
```

---

## Test rapide Blackbox (avant Prometheus)

```bash
kubectl port-forward svc/blackbox-exporter 9115:9115
```

Puis :

👉 navigateur ou curl :

```
http://localhost:9115/probe?target=https://google.com&module=http_2xx
```

Si tu vois des métriques → ✅ Blackbox OK

---

# 📡 2️⃣ MODIFIER LA CONFIG PROMETHEUS (POINT CLÉ)

👉 **Tout se passe ici**
📄 `prometheus/base/configs/prometheus.yaml`

### 🔴 AVANT (simplifié)

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

### 🟢 APRÈS – AJOUT BLACKBOX STG EMEA

👉 **Tu AJOUTES**, tu ne remplaces rien.

```yaml
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

📌

* STG only
* EMEA only
* Aucun PRD touché

---

# 🔁 3️⃣ APPLIQUER SANS CASSER

## Dry-run (OBLIGATOIRE)

```bash
kubectl apply -k prometheus/base --dry-run=server
```

👉 Vérifie :

* ConfigMap `prometheus-config`
* **pas d’erreur**

---

## Apply réel

```bash
kubectl apply -k prometheus/base
```

---

## Reload Prometheus (si nécessaire)

Selon ton setup :

```bash
kubectl rollout restart deployment prometheus
```

(ou le nom exact de ton deployment Prometheus)

---

# 🔍 4️⃣ TESTER DANS PROMETHEUS

Va dans l’UI Prometheus :

### Status → Targets

Tu dois voir :

```
blackbox-health-emea-stg    UP
```

---

### Test requêtes

```promql
probe_success
```

Tu dois voir :

```
job="blackbox-health-emea-stg"
```

---

# 📊 5️⃣ TESTER DANS GRAFANA

Dans Grafana :

### Panel simple – disponibilité

```promql
probe_success{job="blackbox-health-emea-stg"}
```

Si ça s’affiche → 🎉 c’est gagné

---

# 🚨 6️⃣ TEST DE PANNE (RECOMMANDÉ)

Pour valider les alertes :

👉 change temporairement une URL :

```yaml
- https://does-not-exist.stg.emea.example.com/health
```

Puis :

```bash
kubectl apply -k prometheus/base
```

Tu dois voir :

* Target DOWN
* `probe_success = 0`

👉 rollback ensuite

---

# 🧠 POURQUOI CETTE MÉTHODE EST SAFE

✅ Tu touches **un seul fichier**
✅ Pas d’overlay PRD
✅ Pas de code
✅ Rollback simple (git revert)
✅ Validable en 10 min

---

# 🔜 ÉTAPES SUIVANTES (quand tu veux)

Je peux te guider pour :

* séparer **STG / PRD via overlays**
* ajouter **headers d’auth**
* alerte TLS expiration
* exporter les dashboards en JSON
* rédiger un **README / runbook banque**

👉 Dis-moi ce que tu veux faire ensuite 👌
