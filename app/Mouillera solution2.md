Parfait ✅
Je te redonne **les 2 méthodes complètes**, **proprement finalisées**, prêtes à coller dans ton fichier `product_action_available_service.py` :

---

## 🔍 **Méthode `get_filtered_products()` (filters + effective_status propre)**

```python
@classmethod
def get_filtered_products(cls, **filters):
    """
    Retrieve product actions filtered by specific criteria (+ compute effective_status).
    If ecosystem is provided, compute final status considering overrides.
    """
    ecosystem = filters.pop("ecosystem", None)  # optional filter passed via query
    instances = ProductActionAvailableModelController.filter_by_keys(**filters)
    actions = ProductActionAvailableModelController.dump_many(instances)

    for action in actions:
        # Default: effective_status = global_status
        effective_status = action.get("global_status", action.get("status"))  # fallback if column still named 'status'
        overrides = action.get("ecosystem_overrides") or {}

        # If an ecosystem is provided AND exists in overrides → override takes priority
        if ecosystem and ecosystem in overrides:
            effective_status = overrides[ecosystem]

        action["effective_status"] = effective_status

    return actions
```

---

## 🔁 **Méthode `update()` (avec `status`, `ecosystems_to_open`, `ecosystems_to_close`)**

```python
def update(self, status: str = None, filters: dict = None,
           ecosystems_to_open: list = None, ecosystems_to_close: list = None,
           user_name: str = None):
    """
    Update global_status and/or ecosystem overrides.
    - If ecosystems_to_open / ecosystems_to_close both empty → only global_status is applied.
    - If override = same as global_status → override is REMOVED (clean table)
    """
    self.log.start(f"Patching product={self.product_name}")

    criteria = {}
    if self.product_name:
        criteria["product_name"] = self.product_name
    if filters:
        criteria.update(filters)

    instance = ProductActionAvailableModelController.get_one_by_criteria(**criteria)
    if not instance:
        raise ValueError(f"No matching record found for {criteria}")

    # 1️⃣ Update global status if provided
    if status:
        instance.global_status = status.lower()

    # Load existing overrides or init empty
    current_overrides = instance.ecosystem_overrides or {}

    # 2️⃣ Process ecosystems_to_open
    if ecosystems_to_open:
        for eco in ecosystems_to_open:
            if status and status.lower() == "open":
                current_overrides.pop(eco, None)  # clean if same as global
            else:
                current_overrides[eco] = "open"

    # 3️⃣ Process ecosystems_to_close
    if ecosystems_to_close:
        for eco in ecosystems_to_close:
            if status and status.lower() == "close":
                current_overrides.pop(eco, None)
            else:
                current_overrides[eco] = "close"

    # 4️⃣ If both lists empty AND status provided → clean overrides fully (global mode only)
    if (not ecosystems_to_open and not ecosystems_to_close) and status:
        current_overrides = {}

    instance.ecosystem_overrides = current_overrides
    instance.updated_by = user_name or "system"

    ProductActionAvailableModelController.save(instance)
    self.log.success(f"✅ Patched product={self.product_name}")
    return ProductActionAvailableModelController.dump_one(instance)
```

---

### 🎯 **Tu confirmes que je t’ajoute maintenant la version finale du endpoint BULK + VALIDATOR + EXEMPLE Swagger / Postman dans le prochain bloc ?**

👉 **Dis juste "go"**, et je te livre **tout le package prêt à coller et tester** 🚀
