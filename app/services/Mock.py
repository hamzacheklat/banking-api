Parfait 👍 là on n’est plus sur un import circulaire.

L’erreur est maintenant :

```
ValueError: env PROMETHEUS_MULTIPROC_DIR is not set or not a directory
```

Elle vient de :

```python
multiprocess.MultiProcessCollector(self._registry)
```

👉 En environnement de test, la variable d’environnement
`PROMETHEUS_MULTIPROC_DIR` n’est pas définie.

---

# 🎯 Pourquoi ça casse en test ?

`MultiProcessCollector` exige :

```bash
PROMETHEUS_MULTIPROC_DIR=/some/existing/folder
```

En prod (gunicorn, uvicorn workers) elle est définie.
En pytest → elle ne l’est pas → exception.

---

# ✅ Solution propre pour les tests

On va **mocker MultiProcessCollector**.

---

# 🔥 Corrige ton test comme ceci

Remplace :

```python
with patch("prometheus_client.CollectorRegistry") as mock_registry:
```

Par :

```python
with patch("utils.metrics.CollectorRegistry") as mock_registry, \
     patch("utils.metrics.multiprocess.MultiProcessCollector"):
```

⚠️ On patch **dans le module où c’est utilisé**, pas dans `prometheus_client`.

---

# ✅ Version corrigée de ton test singleton

```python
def test_singleton_init_called_once(mock_logger):
    with patch("utils.metrics.CollectorRegistry") as mock_registry, \
         patch("utils.metrics.multiprocess.MultiProcessCollector"):

        collector1 = MetricsCollector(mock_logger)
        collector2 = MetricsCollector(mock_logger)

        assert collector1 is collector2
        assert mock_registry.call_count == 1
```

---

# 🧠 Pourquoi ça marche ?

Parce qu’on empêche :

```python
multiprocess.MultiProcessCollector(self._registry)
```

d’exécuter son vrai code (qui exige la variable d’env).

---

# 🚀 Alternative (moins propre)

Ajouter dans le test :

```python
import os
import tempfile

@pytest.fixture(autouse=True)
def setup_prometheus_env():
    tmp_dir = tempfile.mkdtemp()
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = tmp_dir
    yield
    del os.environ["PROMETHEUS_MULTIPROC_DIR"]
```

Mais franchement, pour un test unitaire → mock > env réel.

---

# 🎯 Recommandation clean architecture

Encore mieux : dans ton code production :

```python
if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
    multiprocess.MultiProcessCollector(self._registry)
```

Comme ça tes tests n’auront jamais besoin de mocker ça.

---

# 📌 Résumé

Ton problème actuel n’est PAS le singleton.

C’est :

```
MultiProcessCollector exige PROMETHEUS_MULTIPROC_DIR
```

👉 Mock-le dans les tests.

---

Si tu veux, je peux te donner :

* 🔥 Version totalement isolée (100% unit test pur)
* 🧪 Version test d’intégration Prometheus
* 🏗️ Refacto propre pour rendre MetricsCollector testable sans patch

Dis-moi ce que tu préfères 😉
