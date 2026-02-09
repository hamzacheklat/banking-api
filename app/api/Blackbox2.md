Très bonne question 👍
On va parler **déploiement réel**, **sans tout casser**, avec **Kustomize**, **STG d’abord**, **EMEA uniquement**, et **rollback facile**.
Je te réponds comme si on était en **change window banque**.

---

# 🎯 OBJECTIF

Déployer :

* Blackbox Exporter
* Prometheus STG (avec health STG)

👉 **sans impacter PRD**
👉 **sans toucher aux autres régions**
👉 **sans redémarrer inutilement**

---

# 🧠 PRINCIPE CLÉ (à retenir)

👉 **Kustomize = overlay par overlay**
👉 Tu ne déploies **JAMAIS** `base/` directement
👉 Tu déploies **UN overlay précis** à la fois

---

# ✅ 1️⃣ PRÉREQUIS (sécurité avant tout)

Avant toute chose :

```bash
kubectl config current-context
```

⚠️ Vérifie :

* le **cluster**
* le **namespace** (`monitoring`)
* que tu es bien en **STG**

Si tu veux être safe :

```bash
kubectl config set-context --current --namespace=monitoring
```

---

# 📦 2️⃣ DÉPLOYER LE BLACKBOX EXPORTER (SAFE)

Le Blackbox Exporter est **commun STG / PRD**, mais **non intrusif**.

### Dry-run (OBLIGATOIRE)

```bash
kubectl apply -k k8s/manifests/prometheus/exporters/blackbox/base --dry-run=server
```

✔ Vérifie :

* ConfigMap
* Deployment
* Service

---

### Apply réel

```bash
kubectl apply -k k8s/manifests/prometheus/exporters/blackbox/base
```

---

### Vérification

```bash
kubectl get pods -l app=blackbox-exporter
kubectl get svc blackbox-exporter
```

Test manuel :

```bash
kubectl port-forward svc/blackbox-exporter 9115:9115
```

Puis dans ton navigateur :

```
http://localhost:9115/probe?target=https://google.com&module=http_2xx
```

👉 Si tu vois des métriques → **OK**

---

# 📡 3️⃣ DÉPLOYER PROMETHEUS STG (SANS TOUCHER PRD)

⚠️ **NE JAMAIS appliquer `base/`**

---

## Dry-run STG

```bash
kubectl apply -k k8s/manifests/prometheus/prometheus-region/overlays/stg --dry-run=server
```

👉 Vérifie :

* que **seul Prometheus STG** est impacté
* que la ConfigMap `prometheus-config` est modifiée

---

## Apply STG

```bash
kubectl apply -k k8s/manifests/prometheus/prometheus-region/overlays/stg
```

---

## Redémarrage contrôlé (si nécessaire)

Si Prometheus ne reload pas à chaud :

```bash
kubectl rollout restart deployment prometheus-region
```

📌

* pas besoin de restart PRD
* pas d’impact EMEA global

---

# 🔍 4️⃣ VALIDATION POST-DÉPLOIEMENT (OBLIGATOIRE)

### Dans Prometheus STG

Va dans :

```
Status → Targets
```

Tu dois voir :

* `blackbox-health-emea-stg` → **UP**

---

### Vérifier les métriques

Dans Prometheus :

```promql
probe_success
```

Tu dois voir :

* `job="blackbox-health-emea-stg"`

---

# 📊 5️⃣ GRAFANA (ZÉRO RISQUE)

Grafana **ne casse rien**.

1. Importer le dashboard
2. Choisir le job :

   * `blackbox-health-emea-stg`

👉 Aucun impact PRD

---

# 🚨 6️⃣ ALERTES – ACTIVER EN MODE SAFE

### Bonne pratique banque

* activer alertes **STG uniquement**
* observer 24–48h
* puis PRD

Exemple STG :

```promql
probe_success{job="blackbox-health-emea-stg"} == 0
```

Severity : `warning`

---

# 🔙 7️⃣ ROLLBACK (IMPORTANT)

Si quelque chose ne va pas :

### Revenir à l’état précédent

```bash
kubectl rollout undo deployment prometheus-region
```

Ou :

```bash
git revert <commit>
kubectl apply -k k8s/manifests/prometheus/prometheus-region/overlays/stg
```

👉 **Aucun effet PRD**

---

# 🧠 RÈGLES D’OR (pour ne jamais casser)

✅ Toujours `--dry-run=server`
✅ Toujours STG avant PRD
✅ Jamais `apply` sur `base/`
✅ Un overlay = un déploiement
✅ Vérifier `Targets` Prometheus
✅ Rollback prêt AVANT le apply

---

# 🏁 SÉQUENCE FINALE RECOMMANDÉE

```bash
# 1. Blackbox
kubectl apply -k exporters/blackbox/base

# 2. Prometheus STG
kubectl apply -k prometheus-region/overlays/stg

# 3. Vérifs
kubectl get pods
```

---

## 🔜 Tu veux aller encore plus safe ?

Je peux te donner :

* 📝 **runbook de déploiement banque**
* ✅ **check-list pre/post change**
* 🔐 **feature flag STG → PRD**
* 📄 **doc pour CAB / comité**

Dis-moi 👍
