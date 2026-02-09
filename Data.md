Top, merci pour le screenshot — il est **très parlant** 👍
La bonne nouvelle : **ta conf Prometheus + Blackbox est correcte**.
Le **DOWN** vient **presque sûrement du endpoint lui-même**, pas de Prometheus.

On va diagnostiquer ça **méthodiquement**, comme en prod.

---

# 🔎 Ce que dit exactement ton écran

On voit :

* **job** : `blackbox-health-emea-stg`
* **module** : `http_2xx`
* **target** :

  ```
  https://database-services-stg.xmp.net.intra/databases/health
  ```
* **endpoint blackbox** :

  ```
  http://blackbox-exporter.monitoring.svc.cluster.local:9115/probe
  ```
* **State** : ❌ **DOWN**

👉 Donc :
➡️ Prometheus arrive bien à joindre **Blackbox**
➡️ Blackbox arrive bien à essayer l’URL
➡️ MAIS le check HTTP **échoue**

---

# 🧠 Règle clé Blackbox (très importante)

Le module `http_2xx` signifie :

> **Le endpoint doit retourner un code HTTP 2xx (200–299)**

❌ Sinon → `probe_success = 0` → **DOWN**

---

# 🧪 1️⃣ Test IMMÉDIAT à faire (le plus important)

Depuis **n’importe où** (ton poste, un pod, un bastion) :

```bash
curl -i https://database-services-stg.xmp.net.intra/databases/health
```

👉 Dis-moi exactement ce que tu obtiens, mais voici les cas classiques 👇

---

# ❌ CAUSES LES PLUS FRÉQUENTES (99% du temps)

## 🔴 1️⃣ Le endpoint retourne **401 / 403**

Très courant en banque.

Exemple :

```
HTTP/1.1 401 Unauthorized
```

➡️ Blackbox considère ça comme **DOWN**

### ✅ Solution

Ajouter un **header d’auth**.

---

## 🔴 2️⃣ Le endpoint retourne **302 / 301**

Exemple :

```
HTTP/1.1 302 Found
Location: /login
```

➡️ `http_2xx` = ❌ DOWN

### ✅ Solution

Autoriser les redirects dans Blackbox.

---

## 🔴 3️⃣ Certificat TLS non trusté

Très fréquent en `.intra`.

Logs Blackbox typiques :

```
x509: certificate signed by unknown authority
```

### ✅ Solution

Désactiver la vérification TLS (en STG uniquement).

---

## 🔴 4️⃣ Endpoint répond lentement (>5s)

Timeout Blackbox :

```
context deadline exceeded
```

### ✅ Solution

Augmenter le timeout.

---

# 🛠️ 2️⃣ CORRECTION PROPRE (LA BONNE)

On va **adapter Blackbox**, pas Prometheus.

## ➕ Modifier le module Blackbox

📄 `prometheus/exporters/blackbox/base/configmap.yaml`

### 🔴 AVANT

```yaml
modules:
  http_2xx:
    prober: http
    timeout: 5s
    http:
      method: GET
```

---

### 🟢 APRÈS (version STG safe)

```yaml
modules:
  http_2xx:
    prober: http
    timeout: 10s
    http:
      method: GET
      follow_redirects: true
      tls_config:
        insecure_skip_verify: true
      headers:
        Accept: application/json
```

📌

* `follow_redirects` → gère 302
* `insecure_skip_verify` → certs internes
* `timeout: 10s` → endpoints lents

---

## 🔁 Appliquer la modif

```bash
kubectl apply -k prometheus/exporters/blackbox/base
kubectl rollout restart deployment blackbox-exporter
```

---

# 🔍 3️⃣ RE-TEST IMMÉDIAT

Dans Prometheus → **Status → Targets**

Tu dois voir :

```
blackbox-health-emea-stg   UP
```

Et en PromQL :

```promql
probe_success
```

➡️ valeur = `1`

---

# 🧪 4️⃣ Debug fin (si encore DOWN)

Port-forward Blackbox :

```bash
kubectl port-forward svc/blackbox-exporter 9115:9115
```

Puis teste exactement ce que Prometheus fait :

```
http://localhost:9115/probe?target=https://database-services-stg.xmp.net.intra/databases/health&module=http_2xx
```

➡️ **Lis les métriques**, tu verras clairement :

* `probe_http_status_code`
* `probe_ssl_last_chain_expiry_timestamp_seconds`
* `probe_duration_seconds`
* `probe_failed_due_to_regex`

---

# 🧠 Conclusion claire

👉 **Ta stack est bien montée**
👉 **Prometheus fonctionne**
👉 **Blackbox fonctionne**
👉 Le DOWN vient de :

* auth ❌
* redirect ❌
* TLS ❌
* timeout ❌

Et **pas** d’un problème Kubernetes.

---

## 🔜 Prochaine étape (si tu veux)

Je peux t’aider à :

* 🔐 gérer **Authorization header**
* 🔑 mTLS
* 🔥 différencier STG (TLS off) / PRD (TLS strict)
* 🚨 créer les alertes finales PRD
* 📊 finaliser le dashboard Grafana

Dis-moi ce que retourne ton `curl -i`, et on ajuste en 2 minutes 👌
