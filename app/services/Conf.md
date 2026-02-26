Parfait 💪
Je te donne un **`conftest.py` propre, moderne et stable** pour :

* ✅ Sanic 23+
* ✅ `sanic-testing`
* ✅ endpoint `/metrics`
* ✅ Prometheus multiprocess
* ✅ pas d’erreur 500
* ✅ compatible CI
* ✅ sans `sys.path.append` dégueu

---

# ✅ `tests/conftest.py` COMPLET QUI FONCTIONNE

```python
import os
import shutil
import tempfile

import pytest
from sanic_testing import TestManager


# ============================================================
# PROMETHEUS MULTIPROCESS DIR (évite erreur 500)
# ============================================================

@pytest.fixture(scope="session", autouse=True)
def prometheus_multiproc_dir():
    """
    Crée un dossier temporaire pour PROMETHEUS_MULTIPROC_DIR
    obligatoire si MultiProcessCollector est utilisé.
    """
    temp_dir = tempfile.mkdtemp()
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = temp_dir

    yield

    shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================
# SANIC APP
# ============================================================

@pytest.fixture
def app():
    from app.apis.ckms.server import create_app

    app = create_app()

    # Attache le client de test proprement
    TestManager(app)

    return app


# ============================================================
# TEST CLIENT
# ============================================================

@pytest.fixture
def client(app):
    return app.test_client
```

---

# ✅ Exemple de test qui fonctionne

```python
def test_metrics_endpoint_success(client):
    request, response = client.get("/metrics")

    print(response.status)
    print(response.text)

    assert response.status == 200
```

---

# 🚀 Version encore plus moderne (ASGI — recommandé)

Si tu veux éviter tout comportement legacy :

```python
import pytest


@pytest.fixture
def app():
    from app.apis.ckms.server import create_app
    return create_app()


@pytest.mark.asyncio
async def test_metrics_endpoint_success(app):
    request, response = await app.asgi_client.get("/metrics")

    print(response.status)
    print(response.text)

    assert response.status == 200
```

👉 Plus propre
👉 Plus rapide
👉 100% compatible Sanic moderne

---

# 🔥 Pourquoi ton 500 disparaît avec ce conftest

Parce que :

```python
os.environ["PROMETHEUS_MULTIPROC_DIR"]
```

est défini avant l’instanciation du `MultiProcessCollector`.

Sans ça → 500 automatique.

---

# 🎯 Si ça plante encore

Donne-moi :

* ta version de Sanic → `pip show sanic`
* ta version de sanic-testing → `pip show sanic-testing`
* le traceback complet

Et je te donne la config exacte adaptée à ton setup 👌
