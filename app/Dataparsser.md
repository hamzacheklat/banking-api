Parfait ✅ — tu veux donc que ton décorateur accepte des retours du style :

```python
return {"name": "foo"}, 201
```

…et que ce soit **le code HTTP** qui soit pris en compte, **sans l’ajouter dans le modèle** (c’est-à-dire qu’on ne le valide pas via Pydantic, juste on le passe au `json()`).

Voici la version **idéale** du décorateur pour ton besoin 👇

---

## ⚙️ `@validate_response(model)` — version avec support du code HTTP uniquement

```python
from functools import wraps
from pydantic import ValidationError
from sanic.response import json
from sanic import HTTPResponse

def validate_response(model):
    """
    Valide la réponse d'un endpoint Sanic via Pydantic.
    Le handler peut retourner :
      - dict → status=200
      - (dict, int) → status personnalisé
      - HTTPResponse → inchangé
    """
    def decorator(handler):
        @wraps(handler)
        async def wrapper(request, *args, **kwargs):
            result = await handler(request, *args, **kwargs)

            # Si la route renvoie déjà une réponse Sanic (ex: redirect, file, etc.)
            if isinstance(result, HTTPResponse):
                return result

            # Gestion (data, status)
            if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], int):
                data, status_code = result
            else:
                data, status_code = result, 200

            # Validation via Pydantic
            try:
                validated = model(**data)
            except ValidationError as e:
                return json({
                    "error": "Response validation failed",
                    "details": e.errors(),
                }, status=500)

            # Sérialisation JSON + code HTTP
            return json(validated.model_dump(), status=status_code)

        return wrapper
    return decorator
```

---

## 🧩 Exemple d’utilisation

```python
from sanic import Sanic
from sanic_ext import Extend, validate
from pydantic import BaseModel

app = Sanic("vdb_api")
Extend(app)

class VdbResponse(BaseModel):
    name: str
    status: str

class PatchVdbBody(BaseModel):
    name: str

@app.patch("/vdbs/<vdb_name>")
@validate(json=PatchVdbBody)
@validate_response(VdbResponse)
async def patch_vdb(request, body: PatchVdbBody, vdb_name: str):
    if vdb_name == "new":
        # Création → 201
        return {"name": body.name, "status": "CREATED"}, 201

    # Cas normal → 200
    return {"name": body.name, "status": "UPDATED"}
```

✅ **Résultat :**

* `return {...}` → HTTP 200
* `return {...}, 201` → HTTP 201
* `return json(...)` → inchangé
* Si la réponse ne correspond pas à `VdbResponse`, tu obtiens :

  ```json
  {
    "error": "Response validation failed",
    "details": [...]
  }
  ```

---

## ⚙️ Exemple avec modèle imbriqué

```python
from typing import Optional

class Details(BaseModel):
    size: int
    version: str

class VdbResponse(BaseModel):
    name: str
    status: str
    details: Optional[Details]

@app.get("/vdbs/<vdb_name>")
@validate_response(VdbResponse)
async def get_vdb(request, vdb_name: str):
    return {
        "name": vdb_name,
        "status": "READY",
        "details": {"size": 1024, "version": "1.0.0"}
    }
```

💡 Si `details.version` ou `details.size` ne respecte pas le type → validation automatique échoue.

---

Souhaites-tu que je te montre une version **multi-support** (qui gère aussi les réponses `List[Model]`, genre `return [{"id": 1}, {"id": 2}]`), tout en gardant cette logique de code HTTP ?
