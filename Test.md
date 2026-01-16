Parfait, merci pour les screenshots — ils confirment exactement ce que je pensais 👍
Tu es **TRÈS proche** du but.

Je te fais un résumé clair :

---

## Ce que je vois sur tes captures

### 1️⃣ Tu construis bien l’URL SQLAlchemy

```python
sybase+pyodbc://SVC2ASYDATABASED:...@host:5000/inventory?driver=Adaptive Server Enterprise
```

Mais ⚠️ :
➡️ Cette méthode **est fragile** avec pyodbc + Sybase
➡️ Elle casse souvent à cause des espaces, du driver, du parsing

---

### 2️⃣ Ton `connector.create_connect_args(url)` montre :

```
'DRIVER=Adaptive Server Enterprise;Server=host,5000;Database=inventory;UID=...;PWD=...'
```

C’est **déjà très bien** 👌
Mais SQLAlchemy + Sybase est capricieux → on doit passer par un **DSN propre**

---

## Ce que je te recommande (méthode qui marche à coup sûr)

### Étape 1 — DSN ODBC

Dans `/etc/odbc.ini` :

```ini
[DBREPIV2]
Description     = SAP ASE Inventory
Driver          = Adaptive Server Enterprise
Server          = eurvli32821.xmp.net.intra
Port            = 5000
Database        = inventory
UID             = ED
PWD             = TON_MOT_DE_PASSE
UseCursor       = 1
```

---

### Étape 2 — Test ODBC pur (CRITIQUE)

Fais :

```bash
isql -v DBREPIV2 ED TON_MOT_DE_PASSE
```

Si ça ne marche pas ici → Python ne marchera pas non plus.

---

### Étape 3 — Python FINAL (simple et robuste)

```python
from sqlalchemy import create_engine
from urllib.parse import quote_plus

user = "ED"
password = quote_plus("TON_MOT_DE_PASSE")

engine = create_engine(
    "sybase+pyodbc:///?odbc_connect="
    f"DSN=DBREPIV2;UID={user};PWD={password}"
)

try:
    with engine.connect() as conn:
        result = conn.execute("select @@version")
        print(result.fetchone())
        print("✅ Connexion Sybase OK")
except Exception as e:
    print("❌ Erreur :", e)
```

---

## Pourquoi ta méthode actuelle peut poser problème

| Méthode                    | Fiabilité           |
| -------------------------- | ------------------- |
| URL directe avec `driver=` | ❌ fragile           |
| DSN ODBC                   | ✅ stable            |
| isql                       | ✅ référence absolue |

---

## Dis-moi maintenant :

Copie-colle :

### 1️⃣ Le résultat de :

```bash
isql -v DBREPIV2 ED xxx
```

### 2️⃣ L’erreur Python complète si ça échoue

Je te garantis que je te fais une connexion **fonctionnelle à 100%** au prochain message 🚀
