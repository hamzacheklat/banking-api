from pymongo import MongoClient
from tqdm import tqdm
import uuid, json, math
from embedder import embed_texts
from vector_store import get_vanish_collection
import config


def json_to_text(document: dict) -> str:
    safe_doc = {}
    for k, v in document.items():
        if isinstance(v, (dict, list)):
            safe_doc[k] = json.dumps(v, ensure_ascii=False)
        elif isinstance(v, (str, int, float, bool)) or v is None:
            safe_doc[k] = v
        else:
            safe_doc[k] = str(v)
    return "\n".join([f"{k}: {v}" for k, v in safe_doc.items()])


def ingest_vanish_flows(sample_limit: int = None, batch_size: int = 5000):
    """
    Ingestion MongoDB → Chroma avec batching (évite les erreurs de max batch size).
    """
    print("🚀 Ingestion MongoDB → Chroma (collection vanish_flows)")

    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    mongo_col = db["vanish_flows"]

    chroma_col = get_vanish_collection()

    cursor = mongo_col.find()
    if sample_limit:
        cursor = cursor.limit(sample_limit)

    docs, ids, metas = [], [], []

    for doc in tqdm(cursor, desc="Préparation des documents"):
        text = json_to_text(doc)
        docs.append(text)
        ids.append(str(uuid.uuid4()))
        metas.append({"_id": str(doc.get("_id"))})

    if not docs:
        print("⚠️ Aucune donnée à indexer dans vanish_flows")
        return

    total_docs = len(docs)
    print(f"🧠 Embedding et indexation de {total_docs} documents en batchs de {batch_size}...")

    # Découpage en batchs
    num_batches = math.ceil(total_docs / batch_size)

    for i in range(num_batches):
        start = i * batch_size
        end = min((i + 1) * batch_size, total_docs)

        batch_docs = docs[start:end]
        batch_ids = ids[start:end]
        batch_metas = metas[start:end]

        print(f"📦 Batch {i + 1}/{num_batches} → {len(batch_docs)} docs")

        embeddings = embed_texts(batch_docs)

        chroma_col.add(
            ids=batch_ids,
            documents=batch_docs,
            embeddings=embeddings,
            metadatas=batch_metas
        )

    print(f"✅ {total_docs} documents indexés dans Chroma (mongo_vanish_flows)")


if __name__ == "__main__":
    ingest_vanish_flows(sample_limit=10000, batch_size=5000)
