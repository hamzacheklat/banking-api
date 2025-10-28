Parfait 🙌
Voici une structure **complète, propre et prête à l’emploi** pour ton cas :
➡️ une **seule collection Mongo (`vanish_flows`)**
➡️ une **seule collection Chroma (`mongo_vanish_flows`)**
➡️ un **RAG** simple basé sur `litellm`
➡️ tout organisé dans le dossier `app/`.

---

## 📁 Structure finale

```
app/
├── config.py
├── vector_store.py
├── embedder.py
├── mongo_ingest.py
└── rag.py
```

---

## ⚙️ `app/config.py`

```python
import os

# MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "my_database")

# Chroma
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./chroma_data")

# LLM (Litellm)
LITELLM_MODEL = os.getenv("LITELLM_MODEL", "mistral:latest")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", "")
```

---

## 💾 `app/vector_store.py`

```python
import chromadb
from chromadb.config import Settings
import config

# Initialisation du client Chroma
chroma_client = chromadb.Client(
    Settings(
        persist_directory=config.CHROMA_DB_DIR,
        anonymized_telemetry=False
    )
)

def get_vanish_collection():
    """
    Retourne la collection Chroma utilisée pour vanish_flows.
    """
    return chroma_client.get_or_create_collection(
        name="mongo_vanish_flows",
        metadata={
            "description": "Index vectoriel pour la collection Mongo vanish_flows"
        },
        embedding_function=None
    )
```

---

## 🧠 `app/embedder.py`

```python
from sentence_transformers import SentenceTransformer
import numpy as np

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model

def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return np.array(embeddings).tolist()
```

---

## 🚀 `app/mongo_ingest.py`

```python
from pymongo import MongoClient
from tqdm import tqdm
import uuid, json
from embedder import embed_texts
from vector_store import get_vanish_collection
import config


def json_to_text(document: dict) -> str:
    """
    Convertit un document Mongo (dict) en texte lisible et stable pour l'embedding.
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


def ingest_vanish_flows(sample_limit: int = None):
    """
    Ingestion spécifique à la collection Mongo vanish_flows.
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

    for doc in tqdm(cursor, desc="Traitement vanish_flows"):
        text = json_to_text(doc)
        docs.append(text)
        ids.append(str(uuid.uuid4()))
        metas.append({"_id": str(doc.get("_id"))})

    if not docs:
        print("⚠️ Aucune donnée à indexer dans vanish_flows")
        return

    print(f"🧠 Embedding de {len(docs)} documents...")
    embeddings = embed_texts(docs)

    chroma_col.add(
        ids=ids,
        documents=docs,
        embeddings=embeddings,
        metadatas=metas
    )

    print(f"✅ {len(docs)} documents indexés dans Chroma (mongo_vanish_flows)")


if __name__ == "__main__":
    ingest_vanish_flows(sample_limit=1000)
```

---

## 💬 `app/rag.py`

```python
from embedder import embed_texts
from vector_store import get_vanish_collection
from litellm_client import generate_with_litellm
from datetime import datetime

def answer_query(query: str, top_k: int = 8):
    q_emb = embed_texts([query])[0]
    col = get_vanish_collection()

    res = col.query(query_embeddings=[q_emb], n_results=top_k)

    if not res["documents"] or not res["documents"][0]:
        return {"answer": "Aucun résultat trouvé.", "contexts": []}

    results = list(zip(res["documents"][0], res["metadatas"][0]))
    context_text = "\n---\n".join([r[0] for r in results])

    messages = [
        {"role": "system", "content": "Tu es un assistant d'analyse des flux vanish. Interprète les données et identifie les causes probables des anomalies."},
        {"role": "user", "content": f"CONTEXT:\n{context_text}\n\nQUESTION:\n{query}\nRéponds en français."}
    ]

    answer = generate_with_litellm(messages)
    return {
        "answer": answer,
        "contexts": [{"content": r[0], "meta": r[1]} for r in results],
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

Souhaites-tu que je te fournisse aussi le petit fichier `app/litellm_client.py` (pour que `generate_with_litellm` fonctionne directement) ?
Je peux te le donner en version prête avec ton modèle Mistral.
