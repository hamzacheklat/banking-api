Parfait 👍
Je vais te donner **exactement ce que tu dois mettre** dans :

* `middleware/`
* `service/`
* `config/`
* `view/`

👉 Et **pour les 3 bases : Oracle, Mongo, Sybase**
Avec une structure simple et propre, adaptée à ton code actuel.

---

# 🧩 **STRUCTURE RECOMMANDÉE (simple & propre)**

```
app/
 ├── config/
 │     └── config.py
 │
 ├── middleware/
 │     ├── oracle_middleware.py
 │     ├── mongo_middleware.py
 │     └── sybase_middleware.py
 │
 ├── services/
 │     ├── oracle_service.py
 │     ├── mongo_service.py
 │     └── sybase_service.py
 │
 ├── views/
 │     ├── oracle_view.py
 │     ├── mongo_view.py
 │     └── sybase_view.py
 │
 └── __init__.py
server.py
```

Tout est regroupé par **type** (middleware, services, views) → plus simple.

---

# 📌 **1) CONFIG**

Fichier : `app/config/config.py`

```python
# Oracle
ORACLE_DB_URL = "oracle+cx_oracle://user:pass@host:1521/ORCL"

# MongoDB
MONGO_URI = "mongodb://localhost:27017"

# Sybase (pymssql)
SYBASE_HOST = "sybase-host"
SYBASE_USER = "sa"
SYBASE_PASSWORD = "password"
SYBASE_DB = "mydb"
SYBASE_PORT = 5000
```

---

# 📌 **2) MIDDLEWARE**

Les middlewares créent et gèrent les connexions aux bases.

---

## 🔷 Oracle — `app/middleware/oracle_middleware.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

def init_oracle_session(request):
    request.ctx.db = request.app.ctx.OracleSession()

def close_oracle_session(request, response):
    db = request.ctx.db
    try:
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

def register_oracle(app):
    engine = create_engine(app.config.ORACLE_DB_URL)
    app.ctx.OracleSession = scoped_session(sessionmaker(bind=engine))

    app.register_middleware(init_oracle_session, "request")
    app.register_middleware(close_oracle_session, "response")
```

---

## 🟩 Mongo — `app/middleware/mongo_middleware.py`

```python
from pymongo import MongoClient

def register_mongo(app):

    @app.listener("before_server_start")
    def init_mongo(app, loop):
        app.ctx.mongo = MongoClient(app.config.MONGO_URI)

    @app.listener("after_server_stop")
    def close_mongo(app, loop):
        app.ctx.mongo.close()
```

---

## 🟧 Sybase (pymssql) — `app/middleware/sybase_middleware.py`

```python
import pymssql

def register_sybase(app):

    @app.listener("before_server_start")
    def init_sybase(app, loop):
        app.ctx.sybase = pymssql.connect(
            server=app.config.SYBASE_HOST,
            user=app.config.SYBASE_USER,
            password=app.config.SYBASE_PASSWORD,
            database=app.config.SYBASE_DB,
            port=app.config.SYBASE_PORT
        )

    @app.listener("after_server_stop")
    def close_sybase(app, loop):
        app.ctx.sybase.close()
```

---

# 📌 **3) SERVICES**

Les services contiennent **la logique métier** et **les requêtes**.

---

## 🔷 Oracle — `app/services/oracle_service.py`

```python
class OracleService:

    @staticmethod
    def get_backups(session):
        sql = """
        SELECT STATUS, INPUT_BYTES, OUTPUT_BYTES
        FROM V$RMAN_BACKUP_JOB_DETAILS
        """
        rows = session.execute(sql).fetchall()
        return [dict(r) for r in rows]
```

---

## 🟩 Mongo — `app/services/mongo_service.py`

```python
class MongoService:

    @staticmethod
    def get_users(app):
        collection = app.ctx.mongo["mydb"]["users"]
        return list(collection.find({}, {"_id": 0}))
```

---

## 🟧 Sybase — `app/services/sybase_service.py`

```python
class SybaseService:

    @staticmethod
    def get_reports(app):
        conn = app.ctx.sybase
        cursor = conn.cursor(as_dict=True)
        cursor.execute("SELECT id, name, created_at FROM reports")
        return cursor.fetchall()
```

---

# 📌 **4) VIEWS (endpoints)**

---

## 🔷 Oracle — `app/views/oracle_view.py`

```python
from sanic import Blueprint, json
from app.services.oracle_service import OracleService

bp_oracle = Blueprint("oracle", url_prefix="/oracle")

@bp_oracle.get("/backups")
def get_backups(request):
    data = OracleService.get_backups(request.ctx.db)
    return json(data)
```

---

## 🟩 Mongo — `app/views/mongo_view.py`

```python
from sanic import Blueprint, json
from app.services.mongo_service import MongoService

bp_mongo = Blueprint("mongo", url_prefix="/mongo")

@bp_mongo.get("/users")
def get_users(request):
    data = MongoService.get_users(request.app)
    return json(data)
```

---

## 🟧 Sybase — `app/views/sybase_view.py`

```python
from sanic import Blueprint, json
from app.services.sybase_service import SybaseService

bp_sybase = Blueprint("sybase", url_prefix="/sybase")

@bp_sybase.get("/reports")
def get_reports(request):
    data = SybaseService.get_reports(request.app)
    return json(data)
```

---

# 📌 **5) INIT GLOBAL**

Fichier : `app/__init__.py`

```python
from app.middleware.oracle_middleware import register_oracle
from app.middleware.mongo_middleware import register_mongo
from app.middleware.sybase_middleware import register_sybase

from app.views.oracle_view import bp_oracle
from app.views.mongo_view import bp_mongo
from app.views.sybase_view import bp_sybase

def init_app(app):
    register_oracle(app)
    register_mongo(app)
    register_sybase(app)

    app.blueprint(bp_oracle)
    app.blueprint(bp_mongo)
    app.blueprint(bp_sybase)
```

---

# 📌 **6) server.py**

```python
from sanic import Sanic
from app import init_app

app = Sanic("MyAPI")
app.update_config("app/config/config.py")

init_app(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

---

# 🎉 Résultat final

### Oracle

`GET /oracle/backups`

### Mongo

`GET /mongo/users`

### Sybase

`GET /sybase/reports`

---

# 💬 Tu veux que je t’en fasse une **version exactement adaptée à tes fichiers actuels** (ceux en screenshot) ?

Si oui → envoie-moi juste **ta structure actuelle** (liste des dossiers/fichiers).
