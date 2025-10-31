Excellente question 💥 — et très pertinente si tu utilises **Sanic + Sanic-Ext + Pydantic**, car tu veux que ton **Swagger UI (/docs)** affiche clairement :

* les **valeurs par défaut**,
* les **champs obligatoires / facultatifs**,
* et éventuellement les **valeurs autorisées** (enums).

Bonne nouvelle : ✅ **Pydantic gère tout ça automatiquement** — il suffit de déclarer tes champs correctement, et Sanic-Ext les expose dans l’OpenAPI/Swagger.

---

## 🧩 1️⃣ Exemple de base avec valeurs par défaut

```python
from sanic import Sanic, Blueprint
from sanic_ext import Extend, validate
from pydantic import BaseModel, Field
from typing import Optional

app = Sanic("vdb_api")
Extend(app)

class VdbRequest(BaseModel):
    name: str = Field(..., description="Nom du VDB (obligatoire)")
    region: str = Field("AMER", description="Région cible", examples=["AMER", "APAC", "ENEA"])
    technology: str = Field(..., description="Type de technologie", examples=["ORACLE", "MSSQL", "POSTGRESQL"])
    encryption: Optional[str] = Field(None, description="Méthode d'encryption", examples=["tde", "ckms"])

vdb_bp = Blueprint("vdb", url_prefix="/vdbs")

@vdb_bp.post("/")
@validate(json=VdbRequest)
async def create_vdb(request, body: VdbRequest):
    return {"status": "ok", "region": body.region}

app.blueprint(vdb_bp)
```

### ✅ Dans le Swagger UI :

Tu verras :

* `region` affiché avec **valeur par défaut "AMER"**
* `name` et `technology` marqués comme **requis**
* `encryption` marqué comme **optionnel (nullable)**
* des exemples pour chaque champ

---

## 🧭 2️⃣ Comment ça marche

* `Field(default=...)` ou `=` → valeur par défaut visible dans Swagger.
* `Field(..., ...)` (avec des points de suspension) → champ obligatoire.
* `description="..."` → texte d’aide dans Swagger.
* `examples=["..."]` → montre des suggestions dans Swagger.
* `Optional[...]` → Swagger affiche `nullable: true`.

---

## ⚙️ 3️⃣ Exemple plus complet avec enums + valeur par défaut

Tu peux aussi **forcer la liste des valeurs possibles** (comme un menu déroulant Swagger).

```python
from enum import Enum

class RegionEnum(str, Enum):
    AMER = "AMER"
    APAC = "APAC"
    ENEA = "ENEA"

class TechEnum(str, Enum):
    ORACLE = "ORACLE"
    MSSQL = "MSSQL"
    POSTGRESQL = "POSTGRESQL"

class VdbRequest(BaseModel):
    name: str = Field(..., description="Nom du VDB")
    region: RegionEnum = Field(RegionEnum.AMER, description="Région cible par défaut")
    technology: TechEnum = Field(..., description="Type de base de données source")
    encryption: Optional[str] = Field(None, description="Type d'encryption", examples=["tde", "ckms"])
```

🟢 Dans Swagger :

* `region` apparaîtra comme un **dropdown ("AMER", "APAC", "ENEA")**
* `"AMER"` sera **pré-sélectionné par défaut**
* `encryption` sera optionnel avec suggestions

---

## 🧱 4️⃣ Pour améliorer la clarté dans Swagger

Tu peux aussi préciser le comportement global :

```python
app.config.OAS_UI_DEFAULT = "swagger"     # ou "redoc"
app.config.OAS_UI_DEFAULT_MODEL_EXPAND_DEPTH = 3
app.config.OAS_UI_DEFAULT_MODEL_RENDERING = "example"
```

Et ajouter des **exemples de requête complets** :

```python
class VdbRequest(BaseModel):
    name: str = Field(..., example="vdb_demo")
    region: str = Field("AMER", example="AMER")
    technology: str = Field(..., example="ORACLE")
    encryption: Optional[str] = Field(None, example="tde")
```

➡️ Swagger affichera alors directement un exemple JSON complet prêt à être testé.

---

## ✅ En résumé

| Objectif          | Syntaxe à utiliser              | Effet Swagger                     |
| :---------------- | :------------------------------ | :-------------------------------- |
| Champ obligatoire | `Field(..., ...)`               | Marqué **required**               |
| Valeur par défaut | `Field("AMER", ...)`            | Affichée dans le champ par défaut |
| Exemple           | `Field(..., example="...")`     | Montre un exemple dans Swagger    |
| Enum              | `class MyEnum(str, Enum)`       | Menu déroulant                    |
| Description       | `Field(..., description="...")` | Tooltip dans Swagger              |

---

Souhaites-tu que je te génère un **exemple Swagger complet** (avec GET + POST, enums, valeurs par défaut et validateurs hérités) pour ton projet Sanic ?
👉 Comme une base prête à copier-coller.
