Parfait 🔥 ! Je vais te fournir **tout le backend mis à jour pour ton RAG** : ingestion Confluence + ingestion code local avec **CodeT5 embeddings**, prêt à brancher dans ton projet.

On va garder la structure existante, juste remplacer l’embedder et ajouter le nouvel ingesteur local pour le code.

---

# 🧠 1️⃣ Backend – Arborescence

```
backend/
├─ app/
│  ├─ main.py
│  ├─ config.py
│  ├─ embedder.py        # Nouveau embedder avec CodeT5
│  ├─ ingest_confluence.py
│  ├─ ingest_local_code.py   # Nouveau : ingestion code local
│  ├─ rag.py
│  ├─ litellm_client.py
│  └─ vector_store.py
├─ requirements.txt
└─ .env.example
```

---

# 2️⃣ `.env.example`

```env
# General
CHROMA_DB_DIR=./chroma_db

# Confluence
CONFLUENCE_URL=https://wiki.cib.echonet
CONFLUENCE_USERNAME=ton_user
CONFLUENCE_PASSWORD=ton_password
CONFLUENCE_SPACE=IV2

# Embeddings
LOCAL_EMB_MODEL=Salesforce/codet5-base
CHUNK_SIZE=800
CHUNK_OVERLAP=100

# LiteLLM
LITELLM_API_BASE=https://ai4devs.group.echonet/api/v1
LITELLM_MODEL=mistral/codestral-latest
LITELLM_API_KEY=
```

---

# 3️⃣ `embedder.py` (CodeT5 embeddings)

```python
from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F
import numpy as np

MODEL_NAME = "Salesforce/codet5-base"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)

def embed_texts(texts):
    embeddings = []
    for text in texts:
        inputs = tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )
        with torch.no_grad():
            outputs = model(**inputs)
            token_embeddings = outputs.last_hidden_state
            attention_mask = inputs['attention_mask'].unsqueeze(-1).expand(token_embeddings.size()).float()
            summed = torch.sum(token_embeddings * attention_mask, 1)
            counts = torch.clamp(attention_mask.sum(1), min=1e-9)
            vector = (summed / counts).squeeze()
            vector = F.normalize(vector, p=2, dim=0)
            embeddings.append(vector.cpu().numpy().astype(np.float32))
    return embeddings
```

---

# 4️⃣ `vector_store.py`

```python
import chromadb
from chromadb.config import Settings
import config

chroma_client = chromadb.Client(
    Settings(
        persist_directory=config.CHROMA_DB_DIR,
        anonymized_telemetry=False
    )
)

def get_collection():
    return chroma_client.get_or_create_collection(
        name="docs",
        metadata={"description": "Documents Confluence + Code"},
        embedding_function=None
    )
```

---

# 5️⃣ `ingest_local_code.py` (nouveau)

```python
import os
import uuid
from tqdm import tqdm
from embedder import embed_texts
from vector_store import get_collection

# Extensions de code à indexer
CODE_EXTENSIONS = [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".html", ".css", ".json"]

def read_code_files(base_path="./src"):
    code_files = []
    for root, _, files in os.walk(base_path):
        for f in files:
            if any(f.endswith(ext) for ext in CODE_EXTENSIONS):
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as file:
                        content = file.read()
                        code_files.append({"path": path, "content": content})
                except Exception as e:
                    print(f"⚠️ Erreur lecture {path}: {e}")
    return code_files

def chunk_code(text, max_lines=40, overlap=5):
    lines = text.splitlines()
    chunks = []
    i = 0
    while i < len(lines):
        chunk = "\n".join(lines[i:i+max_lines])
        if chunk.strip():
            chunks.append(chunk)
        i += max_lines - overlap
    return chunks

def ingest_local_code(base_path="./src"):
    files = read_code_files(base_path)
    collection = get_collection()
    all_chunks, metadatas, ids = [], [], []

    print(f"📂 {len(files)} fichiers trouvés dans {base_path}")

    for f in files:
        chunks = chunk_code(f["content"])
        for chunk in chunks:
            all_chunks.append(chunk)
            metadatas.append({"path": f["path"]})
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
    print("✅ Ingestion du code source terminée.")
```

---

# 6️⃣ `main.py` (ajout route ingestion code)

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ingest_confluence import ingest_confluence
from ingest_local_code import ingest_local_code
from rag import answer_query

app = FastAPI(title="RAG - ChromaDB - LiteLLM + CodeT5")

class QueryIn(BaseModel):
    session_id: str = "default"
    query: str
    top_k: int = 5

@app.post("/ingest_confluence")
def run_ingest_confluence():
    try:
        ingest_confluence()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest_local_code")
def run_ingest_local_code():
    try:
        ingest_local_code("./src")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
def query(q: QueryIn):
    try:
        out = answer_query(q.query, top_k=q.top_k)
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

# 7️⃣ Utilisation

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

* `/ingest_confluence` → ingérer Confluence
* `/ingest_local_code` → ingérer ton code local (`./src`)
* `/query` → poser des questions au RAG

---

💡 Avec ce setup :

* CodeT5 gère **les embeddings du code Python/JS/TS**
* Tu peux faire **RAG hybride** (Confluence + code source)
* Tout est compatible avec **ChromaDB + LiteLLM**

---

Si tu veux, je peux maintenant te fournir **la version frontend Angular mise à jour pour afficher le Markdown et la source du code correctement** pour tes réponses du RAG.

Veux‑tu que je fasse ça ?
