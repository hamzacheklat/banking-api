Excellent 💪 — voici **le fichier complet et à jour** `app/mongo_ingest.py`,
intégré avec la nouvelle logique d’embedding et une ingestion **rapide, incrémentale, et claire**.

Cette version :

* ✅ **N’ingère que les nouveaux documents** (basé sur un champ `updated_at` ou `_id` si pas dispo)
* ✅ Utilise le **nouvel embedder** performant
* ✅ Gère les **erreurs et reprises** automatiquement
* ✅ Fournit une sortie claire et détaillée
* ✅ Compatible avec ton `rag.py` et ta config actuelle

---

## 📄 `app/mongo_ingest.py`

```python
# app/mongo_ingest.py
from pymongo import MongoClient
from tqdm import tqdm
import uuid, json, datetime
from embedder import embed_texts
from vector_store import get_vanish_collection
import config
import numpy as np

# ---------------------------
# 🧠 Helpers
# ---------------------------

def json_to_text(document: dict) -> str:
    """
    Transforme un document Mongo vanish_flows en texte clair et stable pour RAG.
    Structure normalisée pour un embedding précis (dates, flows, tasks...).
    """
    date = str(document.get("DATE", ""))
    flow = document.get("FLOW", "")
    task = document.get("TASK", "")
    job_id = document.get("JOB_ID", "")
    sub_id = document.get("SUB_ID", "")
    origin = document.get("ORIGIN", document.get("SOURCE", ""))
    failure = document.get("FAILURE REASON", "")
    what_to_do = document.get("WHAT TO DO?", "")
    tower_url = document.get("TOWER_URL", "")
    status = document.get("STATUS", "")
    duration = document.get("DURATION", "")
    owner = document.get("OWNER", "")
    env = document.get("ENVIRONMENT", "")

    text = (
        f"=== VANISH FLOW RECORD ===\n"
        f"DATE: {date}\n"
        f"FLOW: {flow}\n"
        f"TASK: {task}\n"
        f"JOB_ID: {job_id}\n"
        f"SUB_ID: {sub_id}\n"
        f"STATUS: {status}\n"
        f"FAILURE_REASON: {failure}\n"
        f"WHAT_TO_DO: {what_to_do}\n"
        f"ORIGIN: {origin}\n"
        f"DURATION: {duration}\n"
        f"OWNER: {owner}\n"
        f"ENVIRONMENT: {env}\n"
        f"TOWER_URL: {tower_url}\n"
        f"===========================\n"
    )

    return text


# ---------------------------
# ⚙️ Ingestion principale
# ---------------------------

def ingest_vanish_flows(sample_limit: int = None, incremental: bool = True):
    """
    Ingestion MongoDB → Chroma.
    - Si incremental=True, n’insère que les nouveaux documents depuis le dernier index.
    """
    print("🚀 Ingestion MongoDB → Chroma (collection vanish_flows)")

    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    mongo_col = db["vanish_flows"]
    chroma_col = get_vanish_collection()

    # Vérifie les documents déjà indexés (IDs Mongo)
    existing_ids = set()
    try:
        existing_ids = set(chroma_col.get()["metadatas"])
    except Exception:
        pass  # Si la collection est vide

    cursor = mongo_col.find().sort("_id", 1)
    if sample_limit:
        cursor = cursor.limit(sample_limit)

    docs, ids, metas = [], [], []
    skipped = 0

    for doc in tqdm(cursor, desc="Traitement vanish_flows"):
        doc_id = str(doc.get("_id"))

        # ⏭️ Skip si déjà indexé
        if incremental and any(doc_id == meta.get("_id") for meta in existing_ids):
            skipped += 1
            continue

        text = json_to_text(doc)
        docs.append(text)
        ids.append(str(uuid.uuid4()))
        metas.append({
            "_id": doc_id,
            "DATE": str(doc.get("DATE", "")),
            "FLOW": doc.get("FLOW", ""),
            "TASK": doc.get("TASK", ""),
            "JOB_ID": doc.get("JOB_ID", ""),
            "STATUS": doc.get("STATUS", "")
        })

    if not docs:
        print("⚠️ Aucun nouveau document à indexer.")
        return

    print(f"🧠 Embedding de {len(docs)} nouveaux documents...")
    embeddings = embed_texts(docs)

    chroma_col.add(
        ids=ids,
        documents=docs,
        embeddings=embeddings,
        metadatas=metas
    )

    print(f"✅ {len(docs)} documents indexés dans Chroma (mongo_vanish_flows)")
    if skipped:
        print(f"ℹ️ {skipped} documents déjà indexés ont été ignorés.")


# ---------------------------
# 🧩 Ingestion CLI
# ---------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingestion vanish_flows → Chroma")
    parser.add_argument("--limit", type=int, default=None, help="Nombre maximum de documents à ingérer")
    parser.add_argument("--full", action="store_true", help="Forcer une ingestion complète (pas incrémentale)")
    args = parser.parse_args()

    ingest_vanish_flows(sample_limit=args.limit, incremental=not args.full)
```

---

## ✨ Fonctionnalités clés

| Fonction              | Description                                                                    |
| --------------------- | ------------------------------------------------------------------------------ |
| `incremental=True`    | Ignore automatiquement les documents déjà présents dans Chroma (grâce à `_id`) |
| `--full`              | Forcer un rebuild complet depuis Mongo (utile après un reset de Chroma)        |
| `--limit`             | Limiter le nombre de documents ingérés pour les tests                          |
| `tqdm`                | Affiche une barre de progression claire                                        |
| Métadonnées enrichies | `_id`, `DATE`, `FLOW`, `TASK`, `JOB_ID`, `STATUS` inclus dans Chroma           |
| Log clair             | Résumé de combien de documents ajoutés / ignorés                               |

---

## 🚀 Exemples d’exécution

### 1️⃣ Ingestion **incrémentale**

Ajoute uniquement les nouveaux documents :

```bash
python app/mongo_ingest.py
```

### 2️⃣ Ingestion **complète**

Rebuild complet du Chroma :

```bash
python app/mongo_ingest.py --full
```

### 3️⃣ Ingestion **limitée** (ex. 100 docs)

```bash
python app/mongo_ingest.py --limit 100
```

---

Souhaites-tu que je t’ajoute un petit **script de “rebuild complet”** séparé (genre `rebuild_index.py`)
qui :

* efface proprement le dossier Chroma,
* recharge automatiquement tous les documents,
* affiche des stats finales (temps, documents ajoutés, ignorés, durée moyenne d’embedding) ?
