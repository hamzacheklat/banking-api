from pymongo import MongoClient
from tqdm import tqdm
import uuid, json, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from embedder import embed_texts
from vector_store import get_vanish_collection
import config


def json_to_text(document: dict) -> str:
    """
    Convertit un document Mongo (dict) en texte lisible pour l'embedding.
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


def process_batch(batch, chroma_col):
    texts = [json_to_text(doc) for doc in batch]
    ids = [str(uuid.uuid4()) for _ in batch]
    metas = [{"_id": str(doc.get("_id"))} for doc in batch]
    embeddings = embed_texts(texts)
    chroma_col.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metas)
    return len(batch)


def ingest_vanish_flows(batch_size=100, max_workers=4, sample_limit=None):
    """
    Ingestion rapide et parallélisée MongoDB → Chroma (collection vanish_flows).
    """
    print("🚀 Ingestion MongoDB → Chroma (vanish_flows optimisée)")

    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    mongo_col = db["vanish_flows"]
    chroma_col = get_vanish_collection()

    cursor = mongo_col.find()
    if sample_limit:
        cursor = cursor.limit(sample_limit)

    total_indexed = 0
    start_time = time.time()
    batch = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for doc in tqdm(cursor, desc="Lecture MongoDB"):
            batch.append(doc)
            if len(batch) >= batch_size:
                futures.append(executor.submit(process_batch, batch, chroma_col))
                batch = []
        if batch:
            futures.append(executor.submit(process_batch, batch, chroma_col))

        for f in as_completed(futures):
            total_indexed += f.result()

    print(f"✅ {total_indexed} documents indexés en {time.time() - start_time:.1f}s")


if __name__ == "__main__":
    ingest_vanish_flows(batch_size=200, max_workers=6)
