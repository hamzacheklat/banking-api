Tu as raison de chercher à améliorer la lisibilité et la clarté de cette API. Le payload actuel est trop générique et demande de connaître toute la structure interne pour effectuer des actions simples comme fermer un produit ou bloquer une API. Décomposer les actions en plusieurs endpoints rend l'API plus intuitive, surtout si les actions sont fréquentes.

---

### 🔄 **Rappel de l’existant (tel que sur l’image)**

* Endpoint : `PATCH /globals/product_action/{product_name}/{status}`
* Paramètres dans le body :

```json
{
  "action_name": "create",
  "region": "",
  "env": "",
  "reason": "",
  "ecosystems_to_open": [],
  "ecosystems_to_close": [],
  "block_api": ""
}
```

---

## ✅ Proposition de refactoring par endpoints (selon ta demande)

### 📌 Endpoint 1 : Fermer un produit

Ferme totalement le produit dans une région + env pour une action spécifique.

```
PATCH /globals/product_action/{product_name}/close
```

**Body** :

```json
{
  "action_name": "create",
  "region": "eu-west-1",
  "env": "prod"
}
```

---

### 📌 Endpoint 2 : Ouvrir/fermer l’API du produit

Contrôle du flag `block_api`.

```
PATCH /globals/product_action/{product_name}/api_access
```

**Body** :

```json
{
  "action_name": "create",
  "region": "eu-west-1",
  "env": "prod",
  "block_api": "open"  // ou "close"
}
```

---

### 📌 Endpoint 3 : Fermer un ou plusieurs écosystèmes du produit

```
PATCH /globals/product_action/{product_name}/close_ecosystems
```

**Body** :

```json
{
  "action_name": "create",
  "region": "eu-west-1",
  "env": "prod",
  "ecosystems_to_close": ["eco1", "eco2"]
}
```

---

### 📌 Endpoint 4 : Ouvrir un ou plusieurs écosystèmes du produit

```
PATCH /globals/product_action/{product_name}/open_ecosystems
```

**Body** :

```json
{
  "action_name": "create",
  "region": "eu-west-1",
  "env": "prod",
  "ecosystems_to_open": ["eco3", "eco4"]
}
```

---

## 🧠 Alternative de modélisation (plus RESTful)

Si tu préfères éviter des verbes comme `close`, `open`, etc. dans l’URL, tu peux normaliser les endpoints REST comme suit :

### Exemple :

```
PATCH /globals/product_action/{product_name}/status
```

**Avec le body suivant** :

```json
{
  "action_name": "create",
  "region": "eu-west-1",
  "env": "prod",
  "status": "closed", // ou "open"
  "target": "product" // ou "api", "ecosystem"
  "ecosystems": ["eco1"]
}
```

---

## ✅ Avantages de ta proposition multi-endpoints :

* Lisibilité
* Simplicité d’appel
* Validation plus facile de la payload par endpoint
* Moins d’erreurs côté client

---

Souhaites-tu que je te rédige les définitions Swagger/OpenAPI correspondantes à ces endpoints ?
