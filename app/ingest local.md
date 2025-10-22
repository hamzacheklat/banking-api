Parfait ! 🔥 Si tu n’as pas accès à Confluence, on peut tout à fait tester ton RAG **en local avec ton dossier de code Python**. L’idée :

1. On va **scanner tes fichiers `.py`** dans ton dossier.
2. On va créer les embeddings avec **SentenceTransformers**.
3. On stocke tout dans **ChromaDB**.
4. On pose des questions sur ton code via le RAG et **LiteLLM**.

Je te propose un exemple de **nouvel ingesteur local** (`ingest_local_code.py`) pour remplacer `ingest_confluence.py` :

---

## `app/ingest_local_code.py`

```python
import os
import uuid
from embedder import embed_texts
from vector_store import get_collection
from tqdm import tqdm

CODE_EXTENSIONS = [".py"]

def read_files_from_dir(root_dir):
    files_content = []
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            if any(f.endswith(ext) for ext in CODE_EXTENSIONS):
                path = os.path.join(dirpath, f)
                with open(path, "r", encoding="utf-8") as file:
                    files_content.append({
                        "path": path,
                        "content": file.read()
                    })
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

def ingest_local_code(root_dir="./local_code"):
    files = read_files_from_dir(root_dir)
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
    print("✅ Ingestion du code Python terminée dans ChromaDB")

if __name__ == "__main__":
    ingest_local_code("./local_code")
```

---

### 🔹 Points clés :

1. Crée un dossier `backend/local_code/` et mets-y ton code Python.
2. Lance l’ingestion :

```bash
python app/ingest_local_code.py
```

3. Ensuite, tu peux interroger ton RAG via l’endpoint `/query` comme avant.
   Exemple de questions :

* “Quels sont les modules Python définis dans mon projet ?”
* “Où est définie la fonction `answer_query` ?”
* “Quels endpoints FastAPI existent dans ce code ?”

---

Si tu veux, je peux te **mettre à jour `main.py`** pour avoir un **endpoint `/ingest_local_code`** à côté de `/ingest_confluence`, et garder tout compatible avec Angular pour tester le front.

Veux‑tu que je fasse ça ?
