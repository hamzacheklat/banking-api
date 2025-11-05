Parfait ✅ — tu veux donc pouvoir faire quelque chose comme :

```python
from sanic_ext import openapi

@app.get("/vdbs")
@openapi.parameter(VdbQuery.openapi_parameters())
@openapi.response(VdbResponse.openapi_response())
async def get_vdbs(...):
    ...
```

Autrement dit :
👉 **une seule classe de base** (`OpenAPIModel`)
👉 capable de générer facilement :

* les **parameters** pour OpenAPI (`@openapi.parameter(...)`)
* les **requestBody** pour les endpoints POST/PATCH
* les **responses** (schéma de réponse JSON)

Voici une version **propre, simple et compatible avec `sanic-ext`** 👇

---

### ⚙️ Classe unique `OpenAPIModel` (minimaliste + compatible sanic-ext)

```python
from typing import Any, Dict, List
from pydantic import BaseModel

class OpenAPIModel(BaseModel):
    """
    Classe de base unique pour générer :
      - openapi_parameters() → pour @openapi.parameter(...)
      - openapi_request_body() → pour @openapi.body(...)
      - openapi_response() → pour @openapi.response(...)
    """

    # ----------- PARAMETERS -----------
    @classmethod
    def openapi_parameters(cls, in_: str = "query") -> List[Dict[str, Any]]:
        """Génère une liste de paramètres OpenAPI pour sanic-ext."""
        schema = cls.model_json_schema()
        props = schema.get("properties", {})
        required = schema.get("required", [])
        params = []
        for name, prop in props.items():
            params.append({
                "name": name,
                "in": in_,
                "required": name in required,
                "schema": {"type": prop.get("type", "string")},
                "description": prop.get("description", name),
                "example": prop.get("default", None),
            })
        return params

    # ----------- BODY -----------
    @classmethod
    def openapi_request_body(cls, description: str = "", required: bool = True) -> Dict[str, Any]:
        """Génère un requestBody compatible OpenAPI (application/json)."""
        return {
            "description": description or f"{cls.__name__} body",
            "required": required,
            "content": {"application/json": {"schema": cls.model_json_schema()}},
        }

    # ----------- RESPONSE -----------
    @classmethod
    def openapi_response(cls, description: str = "", status: int = 200) -> Dict[str, Any]:
        """Génère un schéma de réponse pour @openapi.response()."""
        return {
            "status": status,
            "description": description or f"{cls.__name__} response",
            "content": {"application/json": {"schema": cls.model_json_schema()}},
        }
```

---

### 💡 Exemple complet avec `sanic-ext`

```python
from sanic import Sanic
from sanic.response import json
from sanic_ext import Extend, openapi
from pydantic import Field

app = Sanic("vdb_api")
Extend(app)

# ---- Modèles hérités ----
class VdbQuery(OpenAPIModel):
    verbose: bool = Field(False, description="Retourner des informations détaillées")
    limit: int = Field(10, description="Nombre maximal de résultats")

class VdbBody(OpenAPIModel):
    name: str = Field(..., description="Nom de la VDB")
    note: str = Field(None, description="Note optionnelle")

class VdbResponse(OpenAPIModel):
    name: str
    status: str


# ---- Route exemple ----
@app.post("/vdbs")
@openapi.parameter(*VdbQuery.openapi_parameters())
@openapi.body(**VdbBody.openapi_request_body(description="Corps de la requête"))
@openapi.response(**VdbResponse.openapi_response(description="Réponse VDB créée", status=201))
async def create_vdb(request):
    body = request.json
    return json({"name": body["name"], "status": "CREATED"}, status=201)
```

---

### ✅ Résumé :

| Méthode                   | Utilisation               | Pour                   |
| ------------------------- | ------------------------- | ---------------------- |
| `.openapi_parameters()`   | `@openapi.parameter(...)` | Query / Path params    |
| `.openapi_request_body()` | `@openapi.body(...)`      | Corps de requête       |
| `.openapi_response()`     | `@openapi.response(...)`  | Schéma de réponse JSON |

---

Souhaites-tu que cette classe **gère aussi les modèles imbriqués** (nested models) dans les réponses, avec `$ref` correct pour OpenAPI ?
(ex : `details: DetailsModel` à l’intérieur d’un `VdbResponse`)
