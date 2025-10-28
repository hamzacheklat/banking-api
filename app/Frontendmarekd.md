Parfait 🔥 — donc on pivote le projet **RAG Confluence → RAG Flow Monitoring**
👉 même architecture, mais les **données ne viennent plus de Confluence**, elles viennent de ta **base MongoDB `vanish_flows`** (ou autre source de logs).

Le but :

* Ingestion des **flows / logs** dans **ChromaDB** (vectorisé via SentenceTransformer).
* Question en langage naturel : *“Quels flux ont échoué cette nuit ?”*, *“Combien de micro-ondes ont tourné dans la prod CIB ?”*
* Réponse générée par **LiteLLM** avec contexte des logs pertinents.
* Le tout s’affiche proprement en **Markdown** côté Angular (coloration, blocs code, etc.).

---

# ⚙️ Nouvelle arborescence

```
rag-flow-monitoring/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ config.py
│  │  ├─ embedder.py
│  │  ├─ mongo_ingest.py   ← ingestion Mongo vanish_flows
│  │  ├─ rag.py
│  │  ├─ litellm_client.py
│  │  └─ vector_store.py
│  ├─ requirements.txt
│  └─ .env.example
└─ frontend-angular/
   └─ src/app/
       ├─ services/api.service.ts
       └─ chat/
           ├─ chat.component.ts
           ├─ chat.component.html
           └─ chat.component.css
```

---

## 🧠 BACKEND

### `.env.example`

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB=flowdb
MONGO_COLLECTION=vanish_flows

CHROMA_DB_DIR=./chroma_db

LOCAL_EMB_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=500
CHUNK_OVERLAP=50

LITELLM_API_BASE=https://ai4devs.group.echonet/api/v1
LITELLM_MODEL=mistral/codestral-latest
LITELLM_API_KEY=
```

---

### `app/config.py`

```python
import os
from dotenv import load_dotenv
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "flowdb")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "vanish_flows")

CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./chroma_db")

LOCAL_EMB_MODEL = os.getenv("LOCAL_EMB_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

LITELLM_API_BASE = os.getenv("LITELLM_API_BASE")
LITELLM_MODEL = os.getenv("LITELLM_MODEL", "mistral/codestral-latest")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", "")
```

---

### `app/vector_store.py`

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
        metadata={"description": "Flow monitoring vanish_flows logs"},
        embedding_function=None
    )
```

---

### `app/embedder.py`

```python
from sentence_transformers import SentenceTransformer
import numpy as np
import config

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(config.LOCAL_EMB_MODEL)
    return _model

def embed_texts(texts):
    model = get_model()
    embs = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return [e.astype(np.float32).tolist() for e in embs]
```

---

### `app/mongo_ingest.py`

```python
from pymongo import MongoClient
from tqdm import tqdm
import uuid
from vector_store import get_collection
from embedder import embed_texts
import config

def connect_mongo():
    client = MongoClient(config.MONGO_URI)
    return client[config.MONGO_DB][config.MONGO_COLLECTION]

def fetch_flows():
    coll = connect_mongo()
    return list(coll.find({}, {"_id": 0}))

def format_flow(flow):
    parts = []
    for k, v in flow.items():
        if v:
            parts.append(f"{k}: {v}")
    return "\n".join(parts)

def ingest_mongo_flows():
    docs = fetch_flows()
    collection = get_collection()

    all_texts, ids, metas = [], [], []
    for d in docs:
        text = format_flow(d)
        if len(text.strip()) == 0:
            continue
        all_texts.append(text)
        ids.append(str(uuid.uuid4()))
        metas.append({"source": "mongo_vanish_flows"})

    batch = 128
    for i in tqdm(range(0, len(all_texts), batch)):
        batch_texts = all_texts[i:i+batch]
        batch_ids = ids[i:i+batch]
        batch_meta = metas[i:i+batch]
        embs = embed_texts(batch_texts)
        collection.add(
            ids=batch_ids,
            documents=batch_texts,
            embeddings=embs,
            metadatas=batch_meta
        )
    print(f"✅ {len(all_texts)} flows indexés dans ChromaDB")

if __name__ == "__main__":
    ingest_mongo_flows()
```

---

### `app/rag.py`

```python
from embedder import embed_texts
from vector_store import get_collection
from litellm_client import generate_with_litellm
from datetime import datetime
import markdown

def chroma_search(query_embedding, top_k=5):
    col = get_collection()
    res = col.query(query_embeddings=[query_embedding], n_results=top_k)
    docs = []
    for i in range(len(res["ids"][0])):
        docs.append({
            "id": res["ids"][0][i],
            "content": res["documents"][0][i],
            "metadata": res["metadatas"][0][i]
        })
    return docs

def build_messages(query, contexts):
    ctx_text = "\n\n---\n\n".join([c["content"] for c in contexts])
    system = {
        "role": "system",
        "content": "Tu es un assistant d'observabilité des flux. Tu analyses les logs vanish_flows et donnes des réponses concises et techniques, en format Markdown."
    }
    user = {
        "role": "user",
        "content": f"Voici des logs:\n{ctx_text}\n\nQuestion: {query}\nRéponds en Markdown clair."
    }
    return [system, user]

def answer_query(query, top_k=5):
    q_emb = embed_texts([query])[0]
    ctx = chroma_search(q_emb, top_k)
    msgs = build_messages(query, ctx)
    answer = generate_with_litellm(msgs)
    return {
        "answer": markdown.markdown(answer),
        "contexts": ctx,
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

### `app/main.py`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mongo_ingest import ingest_mongo_flows
from rag import answer_query

app = FastAPI(title="RAG Flow Monitoring")

class QueryIn(BaseModel):
    query: str
    top_k: int = 5

@app.post("/ingest_mongo")
def run_ingest():
    try:
        ingest_mongo_flows()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
def query(q: QueryIn):
    try:
        return answer_query(q.query, q.top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 🧩 FRONTEND (Angular)

### `src/app/chat/chat.component.ts`

```ts
import { Component } from '@angular/core';
import { ApiService } from '../services/api.service';
import { marked } from 'marked';

@Component({
  selector: 'app-chat',
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css']
})
export class ChatComponent {
  query = '';
  messages: any[] = [];
  loading = false;

  constructor(private api: ApiService) {}

  send() {
    if (!this.query.trim() || this.loading) return;
    const q = this.query.trim();
    this.messages.push({ role: 'user', content: q });
    this.query = '';
    this.loading = true;

    this.api.query('default', q, 5).subscribe({
      next: (res) => {
        this.messages.push({
          role: 'assistant',
          content: marked(res.answer),
          timestamp: res.timestamp
        });
        this.loading = false;
      },
      error: (err) => {
        this.messages.push({
          role: 'assistant',
          content: '❌ ' + (err.error?.detail || err.message)
        });
        this.loading = false;
      }
    });
  }

  ingestMongo() {
    if (this.loading) return;
    this.loading = true;
    this.api.ingestMongo().subscribe({
      next: () => {
        alert('✅ Ingestion Mongo terminée.');
        this.loading = false;
      },
      error: (e) => {
        alert('Erreur ingestion: ' + e.message);
        this.loading = false;
      }
    });
  }
}
```

---

### `src/app/chat/chat.component.html`

```html
<div class="chat-container">
  <h2>Flow Monitoring RAG 🔍</h2>

  <button (click)="ingestMongo()" [disabled]="loading">🔄 Re-ingest MongoDB</button>

  <div class="messages">
    <div
      *ngFor="let m of messages"
      [ngClass]="{ user: m.role === 'user', assistant: m.role === 'assistant' }"
    >
      <b>{{ m.role }}:</b>
      <div class="msg-content" [innerHTML]="m.content"></div>
      <div class="ts" *ngIf="m.timestamp">{{ m.timestamp }}</div>
    </div>
  </div>

  <input
    [(ngModel)]="query"
    placeholder="Pose une question sur les flux..."
    (keyup.enter)="send()"
  />
  <button (click)="send()" [disabled]="loading">Envoyer</button>

  <div *ngIf="loading" class="loader">⏳ Analyse...</div>
</div>
```

---

### `src/app/chat/chat.component.css`

```css
.chat-container {
  width: 800px;
  margin: 30px auto;
  font-family: 'Segoe UI', sans-serif;
}

.messages {
  height: 420px;
  overflow-y: auto;
  border: 1px solid #ddd;
  padding: 12px;
  background: #fafafa;
  border-radius: 10px;
}

.user {
  text-align: right;
  color: #1e88e5;
  margin: 8px 0;
}

.assistant {
  text-align: left;
  color: #2e7d32;
  margin: 8px 0;
}

.msg-content {
  display: inline-block;
  text-align: left;
  background: #f5f5f5;
  border-radius: 8px;
  padding: 6px 10px;
  white-space: pre-wrap;
}

code {
  background: #eee;
  padding: 2px 5px;
  border-radius: 4px;
}

pre {
  background: #f0f0f0;
  padding: 10px;
  border-radius: 8px;
  overflow-x: auto;
}

.loader {
  margin-top: 8px;
  color: #ff9800;
}
```

---

Souhaites-tu que je t’ajoute un **`docker-compose.yml`** qui lance :

* le backend (FastAPI),
* un conteneur MongoDB avec `vanish_flows`,
* un conteneur `chromadb`,
* et ton frontend Angular (build + nginx) ?
