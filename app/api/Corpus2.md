Parfait ! Voici un **script complet pour indexer ton `rag_corpus` avec LiteLLM + Chroma**, prêt à copier dans `backend/index_rag_corpus_chroma.py`.

---

## `index_rag_corpus_chroma.py` — LiteLLM version

```python
# backend/index_rag_corpus_chroma.py
import glob
import os
from dotenv import load_dotenv
import chromadb
from litellm import LLM

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
CORPUS_DIR = os.getenv("CORPUS_DIR", "./rag_corpus")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "oracle_rag_docs")

# LiteLLM config
LITE_API_BASE = os.getenv("LITE_API_BASE")
LITE_API_KEY = os.getenv("LITE_API_KEY")
LITE_MODEL = os.getenv("LITE_MODEL", "gpt-4.1-mini")

llm = LLM(
    model=LITE_MODEL,
    api_base=LITE_API_BASE,
    api_key=LITE_API_KEY
)

# Chroma persistent client
client = chromadb.PersistentClient(path=CHROMA_PATH)

def embed_text(text: str) -> list[float]:
    """Generate embedding vector using LiteLLM."""
    resp = llm.embed([text])
    return resp[0]

# Collection
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embed_text
)

def index_corpus():
    files = glob.glob(os.path.join(CORPUS_DIR, "*.txt"))
    docs, ids = [], []

    for i, fpath in enumerate(files):
        with open(fpath, "r", encoding="utf-8") as f:
            docs.append(f.read())
            ids.append(f"doc_{i}")

    if docs:
        collection.add(documents=docs, ids=ids)
        print(f"[OK] Indexed {len(docs)} documents into Chroma collection '{COLLECTION_NAME}'.")
    else:
        print("[WARN] No .txt files found in corpus directory.")

if __name__ == "__main__":
    index_corpus()
```

---

### 🔹 Instructions

1. Mets tous tes `.txt` dans `backend/rag_corpus/`.
2. Vérifie `.env` :

```env
CORPUS_DIR=./rag_corpus
CHROMA_PATH=./chroma_db
COLLECTION_NAME=oracle_rag_docs
LITE_API_BASE=http://localhost:11434/v1
LITE_API_KEY=sk-lite-xxxx
LITE_MODEL=gpt-4.1-mini
```

3. Lance l’indexation :

```bash
cd backend
source .venv/bin/activate
python index_rag_corpus_chroma.py
```

> ✅ Chaque fichier `.txt` sera ajouté à Chroma, avec des embeddings générés **via LiteLLM**.

---

Si tu veux, je peux aussi te fournir **une version du backend complet qui appelle ce RAG automatiquement** pour chaque analyse, de façon “plug & play” avec LiteLLM, sans OpenAI du tout.

Veux‑tu que je fasse ça ?
