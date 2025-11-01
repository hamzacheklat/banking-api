Excellente question 🔥 — et **très importante** pour que ton ingestion soit rapide et efficace (surtout avec un historique d’un an de flows).

👉 Actuellement, ton script `mongo_ingest.py` **réindexe toute la collection Mongo** à chaque exécution, ce qui est coûteux.
Tu veux au contraire **insérer seulement les nouveaux documents (les plus récents)** non encore présents dans ton index Chroma.

---

## 🎯 Objectif

➡️ Lors d’un `ingest_vanish_flows()`, on ne veut **indexer que les nouveaux documents** depuis la **dernière date connue** dans Chroma (ou depuis un `_id` qu’on garde en cache).

---

## ✅ Voici une version mise à jour de `app/mongo_ingest.py`

avec **ingestion incrémentale** basée sur la date (ou `_id`) :

```python
# app/mongo_ingest.py
from pymongo import MongoClient
from tqdm import tqdm
import uuid, json, os
from embedder import embed_texts
from vector_store import get_vanish_collection
import config
from datetime import datetime


LAST_INDEX_FILE = "./last_ingested.txt"


def json_to_text(document: dict) -> str:
    """
    Convertit un document Mongo en texte lisible pour l'embedding.
    """
    safe_doc = {}
    for k, v in document.items():
        if isinstance(v, (dict, list)):
            safe_doc[k] = json.dumps(v, ensure_ascii=False)
        elif isinstance(v, (str, int, float, bool)) or v is None:
            safe_doc[k] = v
        else:
            safe_doc[k] = str(v)
    return "\n".join([f"{k}: {v}" for k, v in safe_doc.items()])


def get_last_ingested_date():
    """
    Récupère la dernière date d’ingestion connue depuis un fichier.
    """
    if not os.path.exists(LAST_INDEX_FILE):
        return None
    with open(LAST_INDEX_FILE, "r", encoding="utf-8") as f:
        return f.read().strip() or None


def save_last_ingested_date(date_str):
    """
    Sauvegarde la dernière date d’ingestion pour la prochaine exécution.
    """
    with open(LAST_INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(date_str or "")


def ingest_vanish_flows(incremental: bool = True, sample_limit: int = None):
    """
    Ingestion MongoDB → Chroma, en mode incrémental si activé.
    """
    print("🚀 Ingestion MongoDB → Chroma (collection vanish_flows)")

    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    mongo_col = db["vanish_flows"]
    chroma_col = get_vanish_collection()

    last_date = get_last_ingested_date() if incremental else None
    query = {}

    if last_date:
        print(f"🕒 Ingestion incrémentale depuis {last_date}")
        query = {"DATE": {"$gt": last_date}}

    cursor = mongo_col.find(query).sort("DATE", 1)
    if sample_limit:
        cursor = cursor.limit(sample_limit)

    docs, ids, metas = [], [], []
    newest_date = last_date

    for doc in tqdm(cursor, desc="Traitement vanish_flows"):
        text = json_to_text(doc)
        docs.append(text)
        ids.append(str(uuid.uuid4()))
        metas.append({
            "_id": str(doc.get("_id")),
            "DATE": str(doc.get("DATE")),
            "FLOW": doc.get("FLOW"),
            "TASK": doc.get("TASK"),
            "JOB_ID": doc.get("JOB_ID"),
        })

        # garder la plus récente
        date_str = str(doc.get("DATE"))
        if date_str and (not newest_date or date_str > newest_date):
            newest_date = date_str

    if not docs:
        print("✅ Aucune nouvelle donnée à indexer.")
        return

    print(f"🧠 Embedding de {len(docs)} nouveaux documents...")
    embeddings = embed_texts(docs)

    chroma_col.add(
        ids=ids,
        documents=docs,
        embeddings=embeddings,
        metadatas=metas
    )

    # Sauvegarde du dernier timestamp
    if newest_date:
        save_last_ingested_date(newest_date)
        print(f"📅 Dernière date indexée mise à jour : {newest_date}")

    print(f"✅ {len(docs)} nouveaux documents indexés dans Chroma.")


if __name__ == "__main__":
    ingest_vanish_flows(incremental=True)
```

---

## 🧩 Explication

| Étape                                  | Description                                                  |
| -------------------------------------- | ------------------------------------------------------------ |
| `get_last_ingested_date()`             | Lit la dernière date déjà indexée depuis `last_ingested.txt` |
| `query = {"DATE": {"$gt": last_date}}` | Ne récupère que les documents plus récents                   |
| `save_last_ingested_date()`            | Met à jour le fichier une fois l’ingestion terminée          |
| `incremental=True`                     | Active/désactive le mode incrémental facilement              |

---

### 🧠 Exemple d’usage :

```bash
python app/mongo_ingest.py
```

➡️ Première exécution → indexe tout
➡️ Fichier `last_ingested.txt` créé, ex :

```
2025-10-29T23:59:00
```

➡️ Exécution suivante → n’ingère **que les nouveaux jobs** après cette date.

---

## 💡 Variante (par `_id` au lieu de date)

Si tes documents Mongo n’ont pas toujours une `DATE`, tu peux aussi te baser sur `ObjectId` :

```python
query = {"_id": {"$gt": ObjectId(last_id)}}
```

et sauvegarder `last_id` dans le même fichier.

---

## 🧠 Bonus (pour un RAG ultra-propre)

Tu peux aussi ajouter un **index Mongo sur `DATE`** :

```bash
db.vanish_flows.createIndex({ DATE: 1 })
```

👉 pour accélérer énormément les requêtes incrémentales.

---

Souhaites-tu que je t’ajoute aussi la **version “scheduling automatique”** (exécution toutes les heures via `cron` ou `schedule` Python) pour cette ingestion incrémentale ?
Ça permettrait d’alimenter ton RAG en continu sans rien faire manuellement.
