from pymongo import MongoClient
from tqdm import tqdm
import uuid
import json
from datetime import datetime
from embedder import embed_texts
from vector_store import get_vanish_collection
import config

# ⚙️ Taille du batch à ajuster selon ta mémoire
BATCH_SIZE = 5000  


def json_to_text(document: dict) -> str:
    """
    Convertit un document Mongo en texte lisible et stable pour l'embedding.
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


def get_last_indexed_ids(chroma_col):
    """
    Récupère les métadonnées déjà indexées dans Chroma pour éviter les doublons.
    """
    try:
        existing = chroma_col.get(include=["metadatas"])
        existing_ids = {m["_id"] for m in existing["metadatas"] if "_id" in m}
        return existing_ids
    except Exception:
        return set()


def ingest_vanish_flows(sample_limit: int = None):
    """
    Ingestion incrémentale de la collection Mongo vanish_flows → Chroma.
    - En batchs
    - Avec métadonnées enrichies
    - Évite les doublons
    """
    print("🚀 Ingestion MongoDB → Chroma (collection vanish_flows)")

    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    mongo_col = db["vanish_flows"]

    chroma_col = get_vanish_collection()
    existing_ids = get_last_indexed_ids(chroma_col)
    print(f"🧩 {len(existing_ids)} documents déjà indexés")

    cursor = mongo_col.find()
    if sample_limit:
        cursor = cursor.limit(sample_limit)

    buffer_docs, buffer_ids, buffer_metas = [], [], []
    new_count = 0

    for doc in tqdm(cursor, desc="Traitement vanish_flows"):
        _id = str(doc.get("_id"))

        if _id in existing_ids:
            continue  # 🔁 Document déjà indexé

        # Conversion du document en texte pour l'embedding
        text = json_to_text(doc)

        # Métadonnées enrichies et nettoyées
        meta = {
            "_id": _id,
            "FLOW": doc.get("FLOW", ""),
            "TASK": doc.get("TASK", ""),
            "JOB_ID": doc.get("JOB_ID", ""),
            "START_TIME": str(doc.get("START_TIME", "")),
            "END_TIME": str(doc.get("END_TIME", "")),
            "FAILURE": doc.get("FAILURE REASON", ""),
            "WHAT_TO_DO": doc.get("WHAT TO DO?", ""),
            "ORIGIN": doc.get("ORIGIN", ""),
            "TOWER_URL": doc.get("TOWER_URL", ""),
            "ingested_at": datetime.utcnow().isoformat(),
        }

        buffer_docs.append(text)
        buffer_ids.append(str(uuid.uuid4()))
        buffer_metas.append(meta)

        # Si le batch est plein, on l'envoie dans Chroma
        if len(buffer_docs) >= BATCH_SIZE:
            process_batch(chroma_col, buffer_docs, buffer_ids, buffer_metas)
            new_count += len(buffer_docs)
            buffer_docs, buffer_ids, buffer_metas = [], [], []

    # Dernier batch
    if buffer_docs:
        process_batch(chroma_col, buffer_docs, buffer_ids, buffer_metas)
        new_count += len(buffer_docs)

    print(f"✅ Ingestion terminée : {new_count} nouveaux documents ajoutés.")


def process_batch(chroma_col, docs, ids, metas):
    """
    Gère l’ajout d’un batch dans Chroma.
    """
    print(f"📦 Traitement d’un batch de {len(docs)} documents...")
    embeddings = embed_texts(docs)

    if len(embeddings) != len(docs):
        raise ValueError("❌ Le nombre d'embeddings ne correspond pas au nombre de documents.")

    chroma_col.add(
        ids=ids,
        documents=docs,
        embeddings=embeddings,
        metadatas=metas
    )
    print("✅ Batch inséré avec succès.")


if __name__ == "__main__":
    ingest_vanish_flows(sample_limit=None)
