Parfait ✔️
Tu veux **UNE SEULE classe `DatabaseConfig`** dans `core/database_config.py` qui :

### 🎯 **Gère toutes tes APIs**

* ckms
* delphix
* global
* databases *(qui contient Oracle, Sybase, Mongo)*

### 🚫 Mais attention :

Tu ne veux PAS mélanger :

* les **APIs** (ckms, delphix, global)
  avec
* les **bases réelles** (oracle, sybase, mongo)

Donc ta classe doit être capable de faire :

```
DatabaseConfig("ckms")        -> charge la config spécifique de l’API CKMS
DatabaseConfig("delphix")     -> charge la config DELPHIX
DatabaseConfig("global")      -> charge la config GLOBAL

DatabaseConfig("oracle")      -> charge Oracle
DatabaseConfig("sybase")      -> charge Sybase
DatabaseConfig("mongo")       -> charge Mongo
```

**Une seule classe qui sait tout gérer**
✔ propre
✔ extensible
✔ compatible middleware
✔ sans casser ton architecture

---

# 🔥 Voici la version FINALE et UNIFIÉE de ton fichier

# 📌 `core/database_config.py`

💡 **C’est EXACTEMENT ce que tu veux : gérer toutes les APIs depuis un seul fichier.**

```python
from sqlalchemy import create_engine
from pymongo import MongoClient
import pymssql
from utils import Singleton


class DatabaseConfig(Singleton):
    """
    DatabaseConfig gère toutes les APIs :
    - ckms, delphix, global → bases SQL propres à chaque API
    - oracle, sybase, mongo → API databases
    """

    _initialized = False

    def __init__(self, name=None):
        if not self._initialized:
            self.name = name
            self.connection = self._load_connection()
            self._initialized = True

    def _load_connection(self):

        # --- API DATABASES (Oracle / Sybase / Mongo) ---
        if self.name == "oracle":
            from core.settings.oracle_settings import OracleSettings
            cfg = OracleSettings()
            return create_engine(cfg.URI)

        if self.name == "sybase":
            from core.settings.sybase_settings import SybaseSettings
            cfg = SybaseSettings()
            return pymssql.connect(
                server=cfg.HOST,
                user=cfg.USER,
                password=cfg.PASSWORD,
                database=cfg.DB,
                port=cfg.PORT
            )

        if self.name == "mongo":
            from core.settings.mongo_settings import MongoSettings
            cfg = MongoSettings()
            return MongoClient(cfg.URI)

        # --- AUTRES APIs : CKMS, DELPHIX, GLOBAL ---
        if self.name == "ckms":
            from core.settings.ckms_settings import CKMSSettings
            cfg = CKMSSettings()
            return create_engine(cfg.URI)

        if self.name == "delphix":
            from core.settings.delphix_settings import DelphixSettings
            cfg = DelphixSettings()
            return create_engine(cfg.URI)

        if self.name == "global":
            from core.settings.global_settings import GlobalSettings
            cfg = GlobalSettings()
            return create_engine(cfg.URI)

        raise ValueError(f"[DatabaseConfig] Base inconnue : {self.name}")

    def get(self):
        """Retourne la connexion (SQLAlchemy, MongoClient ou Sybase)."""
        return self.connection
```

---

# 🎉 Ce que tu obtiens maintenant

## ✔ UNE SEULE classe pour TOUT gérer

* les DB réelles : oracle, sybase, mongo
* les APIs séparées : ckms, delphix, global

## ✔ Aucun doublon

## ✔ Architecture propre

## ✔ Compatible middleware

## ✔ Compatible singleton

## ✔ Appels uniformes :

### 👉 Pour CKMS API

```python
db = DatabaseConfig("ckms").get()
```

### 👉 Pour DELPHIX API

```python
db = DatabaseConfig("delphix").get()
```

### 👉 Pour GLOBAL API

```python
db = DatabaseConfig("global").get()
```

### 👉 Pour API DATABASES (automatique via middleware)

* `/databases/oracle/*` → Oracle
* `/databases/sybase/*` → Sybase
* `/databases/mongo/*` → Mongo

---

# 💬 Prochaine étape ?

Je peux te fournir :

✔ Tous les fichiers `settings/*.py` propres (Oracle, Sybase, Mongo, CKMS, Delphix, Global)
✔ Le middleware final pour chaque API
✔ L’arborescence complète
✔ Les endpoints déjà câblés

Dis-moi ce que tu veux 👉
