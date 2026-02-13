Très bonne question — et oui, **là on touche le point critique** 👍
Je te réponds **clairement + proprement**, sans piège.

---

## ❓ Ta situation

* **4 serveurs**
* **5 APIs par serveur**
* chaque API = Sanic
* multi-workers
* Prometheus multiprocess
* `/dev/shm` (RAM)

---

## ❗ Question

> **Est-ce qu’il faut le même fichier (répertoire multiprocess) pour toutes les APIs ?**

---

# ❌ Réponse courte

**NON. SURTOUT PAS.**

👉 **1 API = 1 répertoire multiprocess dédié**

Sinon tu vas :

* mélanger les métriques
* casser les compteurs
* avoir des séries incohérentes
* rendre Prometheus inutilisable

---

# ✅ Architecture correcte (recommandée)

### Par serveur :

```
/dev/shm/prometheus/
├── ckms/
├── delphix/
├── globals/
├── precheck/
└── databases/
```

---

## 🧱 Principe

Chaque API :

```
PROMETHEUS_MULTIPROC_DIR=/dev/shm/prometheus/<api_name>
```

👉 isolation **par API**
👉 workers propres
👉 agrégation correcte

---

## 🛠️ Mise en place concrète

### 1️⃣ Créer les dossiers (1 fois)

```bash
mkdir -p /dev/shm/prometheus/{ckms,delphix,globals,precheck,databases}
chmod -R 777 /dev/shm/prometheus
```

---

### 2️⃣ systemd (exemple ckms)

```ini
[Service]
Environment="PROMETHEUS_MULTIPROC_DIR=/dev/shm/prometheus/ckms"
ExecStart=/data/microservices/ckms/current/.venv/bin/python3.12 \
  -m sanic app.apis.ckms.server:create_app \
  --factory --workers=4 --port=10010
```

---

### 3️⃣ Code API (identique pour toutes)

👉 **Même code**
👉 **Pas de config différente**
👉 l’isolation est faite **par env var**

```python
registry = CollectorRegistry()
multiprocess.MultiProcessCollector(registry)
```

---

## 🧠 Et avec 4 serveurs ?

👉 Chaque serveur a son `/dev/shm` local
👉 donc **aucun conflit inter-serveur**
👉 Prometheus verra :

```
api=ckms
instance=server1
instance=server2
instance=server3
instance=server4
```

---

## 📊 Prometheus config (propre)

```yaml
- job_name: "ckms"
  static_configs:
    - targets:
        - srv1:10010
        - srv2:10010
        - srv3:10010
        - srv4:10010
```

Même chose pour chaque API.

---

## ⚠️ ERREURS classiques à éviter

❌ un seul `/dev/shm/prom` pour tout
❌ partager un dossier entre APIs
❌ nettoyage manuel en runtime
❌ Gauge.set()
❌ labels dynamiques (`pid`, `worker_id`)

---

## 🧹 Nettoyage safe (au redémarrage)

Optionnel mais propre :

```python
from prometheus_client import multiprocess
multiprocess.mark_process_dead(os.getpid())
```

---

# 🎯 TL;DR final

```
4 serveurs
5 APIs
→ 20 répertoires multiprocess
→ 100% safe
→ métriques propres
```

👉 **Même code partout**
👉 **Config par env**
👉 **Aucune refonte**

---

Si tu veux, je peux :

* te faire un **template systemd standard**
* te donner un **naming convention clean**
* te fournir une **checklist prod**
* t’aider à migrer progressivement sans downtime

Dis-moi 🔥
