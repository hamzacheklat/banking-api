Parfait 💪 on va en faire un **decorator générique propre**, réutilisable dans tous tes jobs, avec la DB en paramètre.

Objectif :

```python
@job_db("oracle")
def run_job():
    engines = NginModelController.dump_many(NginModelController.all())
```

ou même :

```python
@job_db("iv2")
def compute():
    ...
```

---

# ✅ Décorateur `@job_db`

## 📦 job_context.py

```python
from functools import wraps
from database import DatabasesConfig
from request import _current_request, JobRequest


def job_db(db_name: str):
    """
    Decorator to initialize a database session context
    for non-HTTP jobs (cron, batch, worker, etc.)

    Usage:
        @job_db("oracle")
        def my_job():
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            db_config = DatabasesConfig(db_name)
            session = db_config.get_session()

            token = _current_request.set(JobRequest(session))

            try:
                return func(*args, **kwargs)
            finally:
                try:
                    session.close()
                finally:
                    _current_request.reset(token)

        return wrapper

    return decorator
```

---

# ✅ Usage dans tes jobs

```python
from job_context import job_db


@job_db("oracle")
def run_oracle_job():
    engines = NginModelController.dump_many(NginModelController.all())
    print(engines)


@job_db("iv2")
def run_iv2_job():
    ...
```

---

# 🔥 Bonus : version compatible méthodes de classe

Si ton job est dans une classe :

```python
class DelphixCrawlerJob:

    @job_db("oracle")
    def execute(self):
        engines = NginModelController.dump_many(NginModelController.all())
```

→ Ça marche sans modification.

---

# 🧠 Bonus PRO : version avec commit automatique

Si tu veux auto-commit :

```python
def job_db(db_name: str, auto_commit: bool = False):

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            db_config = DatabasesConfig(db_name)
            session = db_config.get_session()

            token = _current_request.set(JobRequest(session))

            try:
                result = func(*args, **kwargs)

                if auto_commit:
                    session.commit()

                return result

            except Exception:
                session.rollback()
                raise

            finally:
                session.close()
                _current_request.reset(token)

        return wrapper
    return decorator
```

Usage :

```python
@job_db("oracle", auto_commit=True)
def my_write_job():
    ...
```

---

# 🏆 Résultat

✔ Multi database
✔ Réutilisable
✔ Thread safe
✔ Middleware compatible
✔ Aucun refactor de tes modèles
✔ Plug & play

---

Si tu veux, je peux aussi te faire la version :

* 🔁 async
* 🧠 multi-DB dans un même job
* 📦 context manager `with job_db("oracle"):`
* 🛡 version avec logging automatique des erreurs

Tu es sur une archi propre là 👌
