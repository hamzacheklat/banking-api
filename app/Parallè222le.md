Voici **le modèle exact** pour exécuter **plusieurs requêtes Oracle en parallèle** avec `asyncio.gather`, sachant que **`oracledb` n’est pas async**.
Donc on doit utiliser **asyncio + ThreadPoolExecutor** pour paralléliser les appels bloquants Oracle.

---

# ✅ Solution propre : exécuter plusieurs requêtes en parallèle avec `asyncio.gather`

### 👉 Fonction bloquante (appel Oracle normal)

```python
import oracledb

def run_query_sync(sql: str, user: str, password: str, dsn: str):
    conn = oracledb.connect(user=user, password=password, dsn=dsn)
    cur = conn.cursor()
    cur.execute(sql)
    result = cur.fetchall()
    cur.close()
    conn.close()
    return result
```

---

# 👉 Version asynchrone (qui exécute le bloc Oracle dans un thread)

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=10)   # nombre de requêtes en parallèle

async def run_query(sql: str, user: str, password: str, dsn: str):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        run_query_sync,
        sql,
        user,
        password,
        dsn
    )
```

---

# 🎯 Utilisation : exécuter plusieurs requêtes AWR en parallèle

```python
async def run_many_queries():
    queries = [
        "SELECT * FROM v$instance",
        "SELECT * FROM v$database",
        "SELECT count(*) FROM dba_objects",
    ]

    tasks = [
        run_query(q, "scott", "tiger", "mydb")
        for q in queries
    ]

    results = await asyncio.gather(*tasks)
    return results
```

---

# ▶️ Lancer

```python
if __name__ == "__main__":
    result = asyncio.run(run_many_queries())
    for i, r in enumerate(result):
        print(f"Résultat {i+1} :", r)
```

---

# 📌 Adapté à ton code AWR

Tu peux envoyer **plusieurs rapports AWR en parallèle**, par exemple pour plusieurs snapshots :

```python
async def get_awr_async(begin_snap, end_snap, dbid, inst, user, pwd, dsn):
    sql = (
        AWR_QUERY
        .replace("{begin_snap}", str(begin_snap))
        .replace("{end_snap}", str(end_snap))
        .replace("{dbid}", str(dbid))
        .replace("{instance_number}", str(inst))
    )
    return await run_query(sql, user, pwd, dsn)
```

---

# 📌 Ensuite :

```python
async def get_all_awrs():
    tasks = [
        get_awr_async(100, 110, dbid=1234, inst=1, user="u", pwd="p", dsn="db"),
        get_awr_async(110, 120, dbid=1234, inst=1, user="u", pwd="p", dsn="db"),
        get_awr_async(120, 130, dbid=1234, inst=1, user="u", pwd="p", dsn="db"),
    ]

    reports = await asyncio.gather(*tasks)
    return reports
```

---

# 📌 Résultat : **toutes les requêtes Oracle partent en parallèle**, vitesse ×3 à ×10

`asyncio.gather` te donne une liste : chaque élément correspond au résultat d’une requête.

---

# 💬 Si tu veux, je peux :

✅ Modifier **directement ton fichier `tuning_advisor_manual.py`**
✅ Adapter ta fonction `get_awr_report()` en version async
✅ Ajouter une file de threads optimisée pour Oracle

Souhaites-tu une version *complète* basée sur le code qui apparaît sur ta capture ?
