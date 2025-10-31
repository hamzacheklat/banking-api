Parfait ! Voici un exemple complet pour un **POST** avec **Blueprint**, **validation Pydantic du body**, **validation de la réponse avec code HTTP variable**, et **modèles imbriqués**.

---

## ⚙️ Exemple POST avec Blueprint

```python
from sanic import Sanic, Blueprint
from sanic_ext import Extend, validate
from pydantic import BaseModel
from typing import Optional
from sanic.response import json

app = Sanic("vdb_api")
Extend(app)

# -----------------------------
# Modèles Pydantic
# -----------------------------
class AdditionalSettings(BaseModel):
    aps_pre_masking: Optional[dict] = None
    aps_post_masking: Optional[dict] = None
    dev_post_masking: Optional[dict] = None
    managed_account: Optional[list[str]] = []

class VdbRequest(BaseModel):
    name: str
    da_branch: Optional[str] = "origin/master"
    oracle_size: Optional[str] = None
    additional_settings: Optional[AdditionalSettings] = None

class VdbResponse(BaseModel):
    name: str
    status: str
    additional_settings: Optional[AdditionalSettings] = None

# -----------------------------
# Décorateur validate_response
# -----------------------------
def validate_response(model):
    from functools import wraps
    from pydantic import ValidationError
    from sanic import HTTPResponse

    def decorator(handler):
        @wraps(handler)
        async def wrapper(request, *args, **kwargs):
            result = await handler(request, *args, **kwargs)

            if isinstance(result, HTTPResponse):
                return result

            if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], int):
                data, status_code = result
            else:
                data, status_code = result, 200

            try:
                validated = model(**data)
            except ValidationError as e:
                return json({
                    "error": "Response validation failed",
                    "details": e.errors(),
                }, status=500)

            return json(validated.model_dump(), status=status_code)
        return wrapper
    return decorator

# -----------------------------
# Blueprint
# -----------------------------
vdb_bp = Blueprint("vdb", url_prefix="/vdbs")

# -----------------------------
# POST endpoint
# -----------------------------
@vdb_bp.post("/")
@validate(json=VdbRequest)          # Validation du body
@validate_response(VdbResponse)     # Validation de la réponse
async def create_vdb(request, body: VdbRequest):
    # Ici on pourrait créer le VDB dans la DB
    # Retour 201 si création, 200 sinon
    status = "CREATED" if body.name.startswith("new") else "UPDATED"
    code = 201 if status == "CREATED" else 200

    response = {
        "name": body.name,
        "status": status,
        "additional_settings": body.additional_settings
    }

    return response, code

# -----------------------------
# Registration du Blueprint
# -----------------------------
app.blueprint(vdb_bp)
```

---

### ✅ Fonctionnalités couvertes

1. `@validate(json=VdbRequest)` :

   * Valide automatiquement le body JSON selon ton modèle Pydantic.
   * Retourne 400 si le JSON ne correspond pas.

2. `@validate_response(VdbResponse)` :

   * Valide la réponse (dict ou dict+code) via Pydantic.
   * Retourne 500 si la réponse est invalide.
   * Permet de retourner `(dict, code)` pour gérer 200/201/… dynamiquement.

3. **Modèle imbriqué** (`AdditionalSettings`) :

   * Validé automatiquement à l’intérieur de la réponse et de la requête.

4. **Blueprint supporté** :

   * OpenAPI doc automatique via Sanic‑Ext (`/docs`).

---

Si tu veux, je peux te préparer **un blueprint complet GET + POST + PATCH** avec tous les modèles imbriqués, validation input et output, et retour de code HTTP variable, **prêt à l’emploi pour ton projet**.

Veux‑tu que je fasse ça ?
