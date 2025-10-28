import os
import uuid
from tqdm import tqdm
from embedder import embed_texts
from vector_store import get_collection

# Extensions de code ou config pertinentes
ALLOWED_EXTENSIONS = [
    ".py", ".js", ".ts", ".java", ".json", ".yaml", ".yml",
    ".html", ".css", ".xml", ".sql", ".sh", ".ini", ".cfg",
    ".env", ".md", ".txt"
]

def is_text_file(filename):
    _, ext = os.path.splitext(filename)
    return ext.lower() in ALLOWED_EXTENSIONS

def read_file_safe(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        try:
            with open(path, "r", encoding="latin-1") as f:
                return f.read()
        except Exception:
            return None

def ingest_codebase(root_dir="./", collection_name="codebase", batch_size=1000):
    collection = get_collection()
    docs, metadatas, ids = [], [], []

    # 🔍 On parcourt les fichiers
    for root, _, files in os.walk(root_dir):
        for file in files:
            if not is_text_file(file):
                continue
            path = os.path.join(root, file)
            text = read_file_safe(path)
            if not text or len(text.strip()) < 20:
                continue

            rel_path = os.path.relpath(path, root_dir)
            ids.append(str(uuid.uuid4()))
            docs.append(text)
            metadatas.append({
                "source": "codebase",
                "path": rel_path
            })

    total = len(docs)
    print(f"📁 {total} fichiers à indexer depuis {root_dir}")

    if total == 0:
        print("⚠️ Aucun fichier trouvé, ingestion ignorée.")
        return

    # 🔄 Insertion par batchs pour éviter l’erreur Chroma
    for i in tqdm(range(0, total, batch_size), desc="🚀 Ingestion codebase par batch"):
        batch_docs = docs[i:i+batch_size]
        batch_meta = metadatas[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        embs = embed_texts(batch_docs)
        collection.add(
            ids=batch_ids,
            documents=batch_docs,
            embeddings=embs,
            metadatas=batch_meta
        )

    print(f"✅ Ingestion codebase terminée ({total} fichiers indexés par lots de {batch_size})")

if __name__ == "__main__":
    ingest_codebase("./mon_projet")
