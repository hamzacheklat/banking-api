Parfait 👍 — si ton **endpoint `update_product_actions`** utilise la méthode **HTTP PATCH**, alors on va l’adapter pour coller à ce comportement RESTful.

Voici la **version corrigée et complète** de ton endpoint, de ton service, et du modèle — totalement intégrée à ton projet existant (d’après tes fichiers des images).

---

## 🧱 1. Nouveau modèle : `product_action_model.py`

> ⚠️ On ne change pas le nom de la table, juste la structure : on remplace `status` par `global_status` et on ajoute `ecosystem_overrides`.

```python
from .base import BaseModel, db

class ProductActionAvailable(BaseModel):
    __tablename__ = "available_action"
    __table_args__ = (
        db.PrimaryKeyConstraint("product_id", name="pk_available_action"),
        {"schema": "iv2dareferential"},
    )

    product_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_name = db.Column(db.VARCHAR(250), nullable=False)
    action_name = db.Column(db.VARCHAR(250), nullable=False)
    region = db.Column(db.VARCHAR(250), nullable=False)
    env = db.Column(db.Enum("dev", "stg", "prd"), nullable=False)

    # 🔄 Remplacement de 'status' par 'global_status'
    global_status = db.Column(db.Enum("open", "close"), nullable=False)

    # 🧩 Nouvelles exceptions par écosystème (JSONB)
    ecosystem_overrides = db.Column(db.JSON, nullable=True, default={})

    updated_at = db.Column(db.DateTime, server_default=db.text("SYSDATE"))
    updated_by = db.Column(db.VARCHAR(250))
    reason = db.Column(db.VARCHAR(250))
    block_api = db.Column(db.Enum("y", "n"), nullable=False)
```

---

## ⚙️ 2. Service : `product_action_available_service.py`

> Le service gère maintenant :
>
> * la mise à jour globale (`PATCH` sans overrides)
> * les overrides (`PATCH` avec `ecosystem_overrides` dans le body)
> * le calcul de `effective_status` côté lecture

```python
class ProductActionAvailableService(BaseService):
    def __init__(self, product_name=None):
        self.log = PrefixedLogger("product_action_service")
        self.log.start(f"ProductActionAvailableService for {product_name}")
        self.product_name = product_name.lower() if product_name else None

    @classmethod
    def get_filtered_products(cls, **filters):
        """Retrieve product actions filtered by specific criteria."""
        ecosystem = filters.pop("ecosystem", None)
        instances = ProductActionAvailableModelController.filter_by_keys(**filters)
        actions = ProductActionAvailableModelController.dump_many(instances)

        if ecosystem:
            for action in actions:
                overrides = action.get("ecosystem_overrides") or {}
                if ecosystem in overrides:
                    action["effective_status"] = overrides[ecosystem]
                else:
                    action["effective_status"] = action["global_status"]
        return actions

    def update(self, status: str = None, filters: dict = None, overrides: dict = None, user_name: str = None):
        """PATCH endpoint logic."""
        self.log.start(f"Patching product={self.product_name}")

        criteria = {"product_name": self.product_name}
        if filters:
            criteria.update(filters)

        instance = ProductActionAvailableModelController.get_one_by_criteria(**criteria)
        if not instance:
            raise ValueError("No matching record found")

        # PATCH for global status
        if status:
            instance.global_status = status.lower()

        # PATCH for ecosystem overrides
        if overrides:
            ecosystem_overrides = instance.ecosystem_overrides or {}
            for eco, new_status in overrides.items():
                if new_status == instance.global_status:
                    ecosystem_overrides.pop(eco, None)
                else:
                    ecosystem_overrides[eco] = new_status
            instance.ecosystem_overrides = ecosystem_overrides

        instance.updated_by = user_name or "system"
        ProductActionAvailableModelController.save(instance)
        self.log.success(f"Patched product={self.product_name}")
        return ProductActionAvailableModelController.dump_one(instance)
```

---

## 🌐 3. Endpoint PATCH : `product_action_view.py`

> Adapté pour gérer la méthode `PATCH` (partielle), avec parsing intelligent du body.

```python
@openapi.definition(
    parameter=GeProductActionAvailableValidator.ArgsSchema.get_args_schema_field_names(),
    response=Response(
        content={"application/json": [GeProductActionAvailableFormatter]},
        status=200
    )
)
@validate_route(args_validator=UpdateProductActionAvailableValidator.ArgsSchema)
@format_response(formatter=GeProductActionAvailableFormatter)
def patch_product_actions(request, product_name):
    """
    PATCH /product-actions/<product_name>
    Permet de modifier le statut global ou les overrides écosystèmes.
    """
    filters = {
        k: v[0].lower() if isinstance(v[0], str) else v[0]
        for k, v in request.args.items()
        if v is not None
    }

    user_name = get_basic_login_user(request)
    service = ProductActionAvailableService(product_name)

    # Body JSON : {"status": "close", "ecosystem_overrides": {"db3": "open"}}
    body = request.json or {}
    status = body.get("status")
    overrides = body.get("ecosystem_overrides")

    try:
        result = service.update(status=status, filters=filters, overrides=overrides, user_name=user_name)
        return json(result, status=200)
    except ValueError as e:
        return json({"error": str(e), "product_name": product_name}, status=404)
```

---

## 🧪 4. Cas de test (PATCH inclus)

| #  | Cas                                  | Méthode                                                                                                   | Entrée (body / query)                            | Résultat attendu |
| -- | ------------------------------------ | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------ | ---------------- |
| 1  | PATCH global_status                  | `PATCH /product-actions/app?action=deploy`<br>`{"status": "open"}`                                        | Met `global_status=open`                         |                  |
| 2  | PATCH override ajout                 | `PATCH /product-actions/app?action=deploy`<br>`{"ecosystem_overrides": {"db3": "close"}}`                 | Ajoute `"db3": "close"`                          |                  |
| 3  | PATCH override suppression           | `PATCH /product-actions/app?action=deploy`<br>`{"ecosystem_overrides": {"db3": "open"}}` (si global=open) | Supprime `db3`                                   |                  |
| 4  | PATCH combiné                        | `{"status": "close", "ecosystem_overrides": {"db1": "open"}}`                                             | Met `global_status=close`, ajoute `"db1":"open"` |                  |
| 5  | PATCH inconnu                        | `action=invalid`                                                                                          | 404                                              |                  |
| 6  | GET avec filtre `ecosystem=db3`      | `GET /product-actions?ecosystem=db3`                                                                      | Renvoie `effective_status` selon override        |                  |
| 7  | PATCH sans body                      | Vide                                                                                                      | Aucun changement, status 400 ou no-op            |                  |
| 8  | PATCH override sur ligne inexistante | `action=unknown`                                                                                          | 404                                              |                  |
| 9  | PATCH user tracking                  | `updated_by=userA`                                                                                        | Champ `updated_by` mis à jour                    |                  |
| 10 | GET après PATCH                      | —                                                                                                         | Données cohérentes (`effective_status` correct)  |                  |

---

Souhaites-tu que je te génère maintenant les **fichiers `.py` complets** prêts à copier-coller dans ton projet (avec tous les imports et noms de modules alignés sur ton code existant) ?
Je peux te livrer les 3 fichiers mis à jour :

* `product_action_view.py`
* `product_action_available_service.py`
* `product_action_model.py`
