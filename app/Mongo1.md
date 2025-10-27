Parfait 🔥
On va donc mettre à jour ton **backend RAG pour Flow Monitoring** avec :

* ingestion directe depuis MongoDB,
* embeddings **`intfloat/multilingual-e5-small`**,
* vectorisation dans **ChromaDB**,
* endpoint `/query` pour poser des questions sur les erreurs,
* et tout ça prêt à tourner (CPU friendly 💨).

---

# 🧱 Nouvelle arborescence

```
flow-rag/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ config.py
│  │  ├─ mongo_ingest.py
│  │  ├─ embedder.py
│  │  ├─ vector_store.py
│  │  ├─ rag.py
│  │  └─ litellm_client.py
│  ├─ requirements.txt
│  └─ .env.example
└─ frontend/
   └─ (optionnel plus tard)
```

---

# ⚙️ `backend/requirements.txt`

```txt
fastapi
uvicorn[standard]
pymongo
chromadb
sentence-transformers
torch
numpy
python-dotenv
tqdm
litellm
```

---

# 🧩 `.env.example`

```env
# MongoDB
MONGO_URI=mongodb://user:pass@localhost:27017/
MONGO_DB=flow_monitoring
MONGO_COLLECTION=flows

# Chroma
CHROMA_DB_DIR=./chroma_db

# Embeddings
LOCAL_EMB_MODEL=intfloat/multilingual-e5-small

# LiteLLM
LITELLM_API_BASE=https://ai4devs.group.echonet/api/v1
LITELLM_MODEL=mistral/codestral-latest
LITELLM_API_KEY=
```

---

# 📘 `app/config.py`

```python
import os
from dotenv import load_dotenv
load_dotenv()

# Mongo
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "flow_monitoring")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "flows")

# Chroma
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./chroma_db")

# Embeddings
LOCAL_EMB_MODEL = os.getenv("LOCAL_EMB_MODEL", "intfloat/multilingual-e5-small")

# LiteLLM
LITELLM_API_BASE = os.getenv("LITELLM_API_BASE")
LITELLM_MODEL = os.getenv("LITELLM_MODEL", "mistral/codestral-latest")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", "")
```

---

# 🧠 `app/embedder.py`

```python
from sentence_transformers import SentenceTransformer
import numpy as np
import config

_model = None

def get_model():
    global _model
    if _model is None:
        print(f"🧩 Chargement du modèle embedding : {config.LOCAL_EMB_MODEL}")
        _model = SentenceTransformer(config.LOCAL_EMB_MODEL)
    return _model

def embed_texts(texts):
    model = get_model()
    embs = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return [e.astype(np.float32).tolist() for e in embs]
```

---

# 🗄️ `app/vector_store.py`

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
        name="flow_logs",
        metadata={"description": "Monitoring des flows et erreurs"},
        embedding_function=None
    )
```

---

# 🧾 `app/mongo_ingest.py`

```python
from pymongo import MongoClient
from tqdm import tqdm
import uuid
from embedder import embed_texts
from vector_store import get_collection
import config

def fetch_monitoring_data():
    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    col = db[config.MONGO_COLLECTION]

    data = list(col.find({}))  # à adapter selon ton filtre (ex: date)
    return data

def format_record(record):
    return (
        f"Pipeline: {record.get('pipeline_name', 'N/A')}\n"
        f"Techno: {record.get('tech', 'N/A')}\n"
        f"Status: {record.get('status', 'N/A')}\n"
        f"Erreur: {record.get('error_message', '')}\n"
        f"Date: {record.get('timestamp', '')}"
    )

def ingest_mongo():
    print("🚀 Début ingestion Mongo → ChromaDB")
    records = fetch_monitoring_data()
    collection = get_collection()

    docs, ids, metas = [], [], []

    for r in tqdm(records):
        docs.append(format_record(r))
        ids.append(str(uuid.uuid4()))
        metas.append({
            "tech": r.get("tech"),
            "status": r.get("status"),
            "pipeline": r.get("pipeline_name"),
            "timestamp": r.get("timestamp")
        })

    if not docs:
        print("⚠️ Aucune donnée trouvée à ingérer.")
        return

    print(f"🧠 Embedding de {len(docs)} documents...")
    embeddings = embed_texts(docs)

    collection.add(
        ids=ids,
        documents=docs,
        embeddings=embeddings,
        metadatas=metas
    )

    print("✅ Ingestion Mongo terminée avec succès !")

if __name__ == "__main__":
    ingest_mongo()
```

---

# 💬 `app/litellm_client.py`

```python
from litellm import completion
import config, os

def generate_with_litellm(messages, temperature=0.2, max_tokens=1024):
    if config.LITELLM_API_KEY:
        os.environ["LITELLM_API_KEY"] = config.LITELLM_API_KEY

    resp = completion(
        model=config.LITELLM_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        api_base=config.LITELLM_API_BASE
    )

    try:
        return resp['choices'][0]['message']['content']
    except Exception:
        return str(resp)
```

---

# 🧩 `app/rag.py`

```python
from embedder import embed_texts
from vector_store import get_collection
from litellm_client import generate_with_litellm
from datetime import datetime

def answer_query(query, top_k=8):
    q_emb = embed_texts([query])[0]
    collection = get_collection()
    results = collection.query(query_embeddings=[q_emb], n_results=top_k)

    contexts = []
    for i in range(len(results["ids"][0])):
        contexts.append({
            "content": results["documents"][0][i],
            "meta": results["metadatas"][0][i]
        })

    context_text = "\n---\n".join([c["content"] for c in contexts])
    messages = [
        {
            "role": "system",
            "content": (
                "Tu es un assistant de monitoring interne. "
                "Analyse les logs et explique les causes ou tendances observées "
                "à partir des CONTEXT fournis. Sois synthétique et factuel."
            )
        },
        {
            "role": "user",
            "content": f"CONTEXT:\n{context_text}\n\nQUESTION:\n{query}\n\nRéponds en français."
        }
    ]

    answer = generate_with_litellm(messages)
    return {
        "answer": answer,
        "contexts": contexts,
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

# ⚡ `app/main.py`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mongo_ingest import ingest_mongo
from rag import answer_query

app = FastAPI(title="Flow Monitoring RAG")

class QueryIn(BaseModel):
    query: str
    top_k: int = 8

@app.post("/ingest_mongo")
def run_ingest_mongo():
    try:
        ingest_mongo()
        return {"status": "ok", "message": "Ingestion Mongo terminée"}
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

# ▶️ Lancement

### 1️⃣ Installation

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
```

### 2️⃣ Ingestion initiale

```bash
python app/mongo_ingest.py
```

### 3️⃣ Démarrer l’API

```bash
uvicorn app.main:app --reload --port 8000
```

### 4️⃣ Tester

```bash
curl -X POST http://localhost:8000/query \
    -H "Content-Type: application/json" \
    -d '{"query": "Quelles technos ont échoué hier ?"}'
```

---

# 🧩 Étape suivante (optionnelle)

Quand tu seras prêt, on pourra ajouter :

* 🔁 une tâche automatique quotidienne d’ingestion + résumé,
* 📊 un petit dashboard Angular pour visualiser les anomalies,
* 🔔 envoi Slack/email du rapport matinaux.

---

Souhaites-tu que je te prépare **le code du rapport automatique quotidien (tâche cron ou FastAPI background)** à partir de cette base ?
Il générerait chaque matin une synthèse RAG (“état des erreurs, tendances, technos impactées”) et l’enverrait dans Slack.
