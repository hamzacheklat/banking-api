Excellente question 👌 — oui, **c’est tout à fait possible** d’avoir **une seule classe de base** (par exemple `OpenAPIModel`)
qui peut générer aussi bien la section **`parameters`** (pour les query params) que **`requestBody`** (pour le body JSON).

Tu décides ensuite, selon le contexte, si tu veux l’utiliser comme `query`, `json`, ou les deux.

Voici une version **ultra simple**, propre et réutilisable 👇

---

### 🧩 Classe unique `OpenAPIModel`

```python
from typing import Any, Dict, List
from pydantic import BaseModel

class OpenAPIModel(BaseModel):
    """Base model to generate OpenAPI parameters or requestBody automatically."""

    @classmethod
    def openapi_parameters(cls, in_: str = "query") -> List[Dict[str, Any]]:
        """Generate OpenAPI 'parameters' for query/path/header params."""
        schema = cls.model_json_schema()
        props = schema.get("properties", {})
        required = schema.get("required", [])
        params = []
        for name, prop in props.items():
            param = {
                "name": name,
                "in": in_,
                "required": name in required,
                "schema": {"type": prop.get("type", "string")},
                "description": prop.get("description", name),
            }
            if "default" in prop:
                param["example"] = prop["default"]
            params.append(param)
        return params

    @classmethod
    def openapi_request_body(cls, description: str = "", required: bool = True) -> Dict[str, Any]:
        """Generate OpenAPI 'requestBody' for JSON input."""
        return {
            "description": description or cls.__name__,
            "required": required,
            "content": {
                "application/json": {"schema": cls.model_json_schema()}
            },
        }
```

---

### 💡 Exemple d’utilisation

```python
from sanic import Sanic
from sanic.response import json
from sanic_ext import Extend, validate
from pydantic import Field

app = Sanic("vdb_api")
Extend(app)


class VdbQuery(OpenAPIModel):
    verbose: bool = Field(False, description="Retourner des infos détaillées")
    limit: int = Field(10, description="Nombre maximum de VDBs")


class VdbBody(OpenAPIModel):
    name: str = Field(..., description="Nom de la VDB")
    note: str = Field(None, description="Note optionnelle")


@app.post("/vdbs")
@validate(query=VdbQuery, json=VdbBody)
@app.extend.openapi(
    parameters=VdbQuery.openapi_parameters(),
    requestBody=VdbBody.openapi_request_body(description="Créer une VDB"),
    response={
        "description": "VDB créée",
        "content": {
            "application/json": {
                "schema": {"type": "object", "properties": {"ok": {"type": "boolean"}}}
            }
        },
    },
)
async def create_vdb(request, query: VdbQuery, body: VdbBody):
    return json({"ok": True, "name": body.name, "verbose": query.verbose})
```

---

### ✅ Avantages :

* Une seule classe à maintenir (`OpenAPIModel`)
* Compatible avec Pydantic v2 (`model_json_schema`)
* Peut générer les deux (`parameters`, `requestBody`)
* Supporte descriptions, required, defaults
* 100 % compatible avec Sanic + `@app.extend.openapi`

---

Souhaites-tu que cette classe gère aussi **les modèles imbriqués** (nested models) correctement dans `parameters` (par ex. `filter.size`, `filter.version`) ?
👉 Je peux te donner une version qui **aplatit** les champs imbriqués pour les query params.
