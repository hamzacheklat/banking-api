Parfait 👍 ça me donne une info clé.

Si dans **`sanic_testing`** tu ne peux importer que `TestManager`, ça veut dire que tu es sur une version récente où l’API a changé.

Dans les versions modernes de Sanic + sanic-testing :

👉 `SanicTestClient` n’est plus exposé directement comme avant
👉 On utilise **`TestManager`** pour attacher le client à l’app

---

# ✅ Solution propre avec TestManager

Voici comment faire maintenant :

```python
from sanic_testing import TestManager

@pytest.fixture
def ckms_app():
    from app.apis.ckms.server import create_app
    app = create_app()
    TestManager(app)  # attache le client de test
    return app


@pytest.fixture
def ckms_client(ckms_app):
    return ckms_app.test_client
```

Et ensuite dans ton test :

```python
def test_something(ckms_client):
    _, response = ckms_client.get("/metrics")
    assert response.status == 200
```

---

# 🎯 Pourquoi ça marche

`TestManager(app)` injecte dynamiquement :

```python
app.test_client
```

Donc plus besoin d’importer `SanicTestClient` directement.

---

# 🧠 Pourquoi ton ancien import ne marche plus

Avant :

```python
from sanic.testing import SanicTestClient
```

Maintenant :

* Le module `sanic.testing` n’existe plus
* `SanicTestClient` n’est plus exposé comme API publique
* `TestManager` est la nouvelle interface officielle

---

# 🔥 Alternative moderne (encore mieux)

Si tu es en async (ce qui est recommandé avec Sanic moderne) :

```python
@pytest.mark.asyncio
async def test_metrics(ckms_app):
    request, response = await ckms_app.asgi_client.get("/metrics")
    assert response.status == 200
```

👉 Pas besoin de `TestManager`
👉 Plus rapide
👉 Plus clean
👉 100% compatible Sanic 23+

---

# 🏆 Recommandation senior

Si ton projet est récent :

👉 utilise `asgi_client`
👉 évite `SanicTestClient`
👉 évite les hacks `sys.path.append`

---

Si tu me dis ta version exacte de Sanic (`pip show sanic`),
je te donne la version parfaite adaptée à ton setup 👌
