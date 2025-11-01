Excellent réflexe 👏 — c’est **exactement ce qu’il faut faire** pour les gros volumes MongoDB (comme ton historique d’un an).

Faire les embeddings **par batchs** (ex. 5 000 docs à la fois) :

* ✅ évite la surcharge mémoire GPU/CPU
* ✅ rend l’ingestion plus stable (même si tu interromps le process, tu gardes ton avancement)
* ✅ permet d’afficher des stats intermédiaires

Voici donc ton fichier **`app/mongo_ingest.py` complet, à jour**, avec :

* batching intelligent (`batch_size=5000`)
* ingestion incrémentale
* log clair à chaque batch
* compatibilité totale avec ton RAG actuel

---

## 📄 `app/mongo_ingest.py`

```python
# app/mongo_ingest.py
from pymongo import MongoClient
from tqdm import tqdm
import uuid
import json
from embedder import embed_texts
from vector_store import get_vanish_collection
import config
import time


# ==========================================================
# 🧩 Formatage du document
# ==========================================================
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


# ==========================================================
# ⚙️ Ingestion principale avec batch
# ==========================================================
def ingest_vanish_flows(sample_limit: int = None, batch_size: int = 5000, incremental: bool = True):
    """
    Ingestion MongoDB → Chroma (avec batching).
    - batch_size : nombre de documents traités par batch
    - incremental : évite de retraiter les documents déjà indexés
    """
    print("🚀 Ingestion MongoDB → Chroma (collection vanish_flows)")
    print(f"⚙️ Mode incrémental : {incremental} | Batch size = {batch_size}")

    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    mongo_col = db["vanish_flows"]
    chroma_col = get_vanish_collection()

    # Lecture Mongo
    cursor = mongo_col.find().sort("_id", 1)
    if sample_limit:
        cursor = cursor.limit(sample_limit)

    # Extraction des IDs déjà indexés
    existing_ids = set()
    if incremental:
        try:
            existing_data = chroma_col.get()
            existing_ids = {meta["_id"] for meta in existing_data.get("metadatas", []) if "_id" in meta}
            print(f"📦 {len(existing_ids)} documents déjà présents dans Chroma.")
        except Exception:
            print("ℹ️ Collection Chroma vide (aucun index existant).")

    batch_docs, batch_ids, batch_metas = [], [], []
    total_added, total_skipped = 0, 0
    start_time = time.time()

    # Parcours Mongo
    for i, doc in enumerate(tqdm(cursor, desc="Lecture Mongo")):
        doc_id = str(doc.get("_id"))

        if incremental and doc_id in existing_ids:
            total_skipped += 1
            continue

        text = json_to_text(doc)
        batch_docs.append(text)
        batch_ids.append(str(uuid.uuid4()))
        batch_metas.append({
            "_id": doc_id,
            "DATE": str(doc.get("DATE", "")),
            "FLOW": doc.get("FLOW", ""),
            "TASK": doc.get("TASK", ""),
            "JOB_ID": doc.get("JOB_ID", ""),
            "STATUS": doc.get("STATUS", "")
        })

        # Traitement par batch
        if len(batch_docs) >= batch_size:
            _process_batch(chroma_col, batch_docs, batch_ids, batch_metas)
            total_added += len(batch_docs)
            batch_docs, batch_ids, batch_metas = [], [], []

    # Reste à traiter
    if batch_docs:
        _process_batch(chroma_col, batch_docs, batch_ids, batch_metas)
        total_added += len(batch_docs)

    elapsed = round(time.time() - start_time, 2)
    print(f"\n✅ Ingestion terminée en {elapsed}s")
    print(f"🧠 {total_added} documents ajoutés à Chroma")
    print(f"⏭️ {total_skipped} documents ignorés (déjà indexés)")


# ==========================================================
# 🔁 Fonction interne de traitement d’un batch
# ==========================================================
def _process_batch(chroma_col, docs, ids, metas):
    """
    Gère un batch complet : embedding + ajout à Chroma.
    """
    print(f"\n🧩 Traitement d’un batch de {len(docs)} documents...")
    embeddings = embed_texts(docs)
    chroma_col.add(ids=ids, documents=docs, embeddings=embeddings, metadatas=metas)
    print(f"✅ Batch ajouté ({len(docs)} docs).")


# ==========================================================
# 🚀 CLI
# ==========================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingestion vanish_flows → Chroma (avec batchs)")
    parser.add_argument("--limit", type=int, default=None, help="Nombre maximum de documents à ingérer")
    parser.add_argument("--batch", type=int, default=5000, help="Taille d’un batch (par défaut: 5000)")
    parser.add_argument("--full", action="store_true", help="Forcer ingestion complète (ignore les docs déjà indexés)")
    args = parser.parse_args()

    ingest_vanish_flows(sample_limit=args.limit, batch_size=args.batch, incremental=not args.full)
```

---

## 🚀 Exemples d’usage

### 🔹 Ingestion incrémentale par batch de 5000

```bash
python app/mongo_ingest.py
```

### 🔹 Ingestion complète (rebuild)

```bash
python app/mongo_ingest.py --full
```

### 🔹 Ingestion limitée (ex. 10 000 docs par batch de 2000)

```bash
python app/mongo_ingest.py --limit 10000 --batch 2000
```

---

## ⚡ Avantages de cette version

| ✅ Atout                  | Description                              |
| ------------------------ | ---------------------------------------- |
| **Batch configurable**   | Évite toute surcharge mémoire            |
| **Progression claire**   | Barre `tqdm` + logs par batch            |
| **Incrémental**          | Ignore les `_id` déjà indexés            |
| **Résilient**            | Si coupé, tu peux relancer sans doublons |
| **Statistiques finales** | Nombre ajouté / ignoré / durée totale    |

---

Souhaites-tu que je te fasse aussi une **version parallèle multithread**
(pour accélérer les embeddings en batchs de 5 000, surtout si tu as >100 000 flows) ?
Je peux le faire avec `ThreadPoolExecutor` sans que ça touche à la logique principale.
