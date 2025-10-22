import os
import uuid
from embedder import embed_texts
from vector_store import get_collection
from tqdm import tqdm

def read_files_from_dir(root_dir):
    files_content = []
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            path = os.path.join(dirpath, f)
            try:
                with open(path, "rb") as file:
                    raw = file.read()
                    text = raw.decode("utf-8", errors="ignore")
                    if text.strip():
                        files_content.append({
                            "path": path,
                            "content": text
                        })
            except Exception as e:
                print(f"⚠️ Erreur lecture fichier {path}: {e}")
    return files_content

def chunk_text(text, size=800, overlap=100):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i+size])
        if chunk.strip():
            chunks.append(chunk)
        i += size - overlap
    return chunks

def ingest_local_all_files(root_dir="./local_code"):
    print(f"📂 Scan du dossier {root_dir} ...")
    files = read_files_from_dir(root_dir)
    print(f"📝 {len(files)} fichiers trouvés.")

    collection = get_collection()
    all_chunks, metadatas, ids = [], [], []

    for f in files:
        chunks = chunk_text(f["content"])
        for c in chunks:
            all_chunks.append(c)
            metadatas.append({"file_path": f["path"]})
            ids.append(str(uuid.uuid4()))

    batch = 128
    for i in tqdm(range(0, len(all_chunks), batch)):
        batch_texts = all_chunks[i:i+batch]
        batch_ids = ids[i:i+batch]
        batch_meta = metadatas[i:i+batch]
        embs = embed_texts(batch_texts)
        collection.add(
            ids=batch_ids,
            documents=batch_texts,
            embeddings=embs,
            metadatas=batch_meta
        )
    print("✅ Ingestion de tous les fichiers terminée dans ChromaDB")

if __name__ == "__main__":
    ingest_local_all_files("./local_code")
