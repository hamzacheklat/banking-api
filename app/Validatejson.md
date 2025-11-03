Bien sûr 👍 Voici une version **simple, claire et compacte** de `@validate_response`, compatible **Pydantic v2**, qui :

* valide la réponse (dict ou liste de dicts) avec ton modèle,
* accepte un code HTTP optionnel (`return {...}, 201`),
* ignore les réponses déjà formatées (`json(...)`, `HTTPResponse`, etc.).

---

### ✅ Version simple

```python
from functools import wraps
from pydantic import BaseModel, ValidationError
from sanic.response import json
from sanic import HTTPResponse

def validate_response(model):
    """Valide la réponse avec Pydantic (dict ou liste de dicts)."""
    def decorator(handler):
        @wraps(handler)
        async def wrapper(request, *args, **kwargs):
            result = await handler(request, *args, **kwargs)

            # Si déjà une HTTPResponse → on ne touche pas
            if isinstance(result, HTTPResponse):
                return result

            # (data, status) ou data seul
            if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], int):
                data, status = result
            else:
                data, status = result, 200

            try:
                # Si la réponse est une liste → valider chaque élément
                if isinstance(data, list):
                    validated = [model(**item).model_dump() for item in data]
                else:
                    validated = model(**data).model_dump()
            except ValidationError as e:
                return json({"error": "Response validation failed", "details": e.errors()}, status=500)

            return json(validated, status=status)
        return wrapper
    return decorator
```

---

### 🧩 Exemple d’utilisation

```python
from sanic import Sanic
from pydantic import BaseModel

app = Sanic("api")

class Item(BaseModel):
    id: int
    name: str

@app.get("/items")
@validate_response(Item)
async def get_items(request):
    return [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]

@app.post("/items")
@validate_response(Item)
async def create_item(request):
    return {"id": 3, "name": "New"}, 201
```

---

✅ Fonctionne avec :

* `return {...}` → status 200
* `return {...}, 201` → status 201
* `return [{...}, {...}]` → liste validée
* `return json(...)` → inchangé

Souhaites-tu que je te montre aussi la version **Pydantic v1** (au cas où ton projet ne soit pas encore en v2) ?
