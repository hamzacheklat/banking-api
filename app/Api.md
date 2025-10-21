Parfait 🔥
Voici une **version complète et cohérente** de ton projet **RAG (Confluence + Chroma + LiteLLM + Angular 16)**.
Tu auras **tous les fichiers backend et frontend** prêts à copier dans ton repo.

> ⚙️ **Objectif** : RAG interne, ingestion Confluence, embeddings locaux, stockage Chroma, génération via `litellm`, interface Angular 16 minimaliste.

---

# 🧱 ARBORESCENCE GLOBALE

```
rag-litellm/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ config.py
│  │  ├─ embedder.py
│  │  ├─ ingest_confluence.py
│  │  ├─ rag.py
│  │  ├─ litellm_client.py
│  │  └─ vector_store.py
│  ├─ requirements.txt
│  └─ .env.example
└─ frontend-angular/
   ├─ package.json
   └─ src/
      └─ app/
          ├─ app.module.ts
          ├─ services/api.service.ts
          └─ chat/
              ├─ chat.component.ts
              ├─ chat.component.html
              └─ chat.component.css
```

---

# 🧠 BACKEND COMPLET (Chroma + Confluence + litellm)

## `backend/requirements.txt`

```txt
fastapi
uvicorn[standard]
chromadb
sentence-transformers
transformers
torch
python-dotenv
pdfplumber
python-multipart
pydantic
tqdm
atlassian-python-api
requests
litellm
```

---

## `.env.example`

```env
# General
CHROMA_DB_DIR=./chroma_db

# Confluence
CONFLUENCE_URL=https://wiki.cib.echonet
CONFLUENCE_USERNAME=ton_user
CONFLUENCE_PASSWORD=ton_password
CONFLUENCE_SPACE=IV2

# Embeddings
LOCAL_EMB_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=800
CHUNK_OVERLAP=100

# LiteLLM
LITELLM_API_BASE=https://ai4devs.group.echonet/api/v1
LITELLM_MODEL=mistral/codestral-latest
LITELLM_API_KEY=
```

---

## `app/config.py`

```python
import os
from dotenv import load_dotenv
load_dotenv()

# Chroma
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./chroma_db")

# Confluence
CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
CONFLUENCE_PASSWORD = os.getenv("CONFLUENCE_PASSWORD")
CONFLUENCE_SPACE = os.getenv("CONFLUENCE_SPACE", "IV2")

# Embeddings
LOCAL_EMB_MODEL = os.getenv("LOCAL_EMB_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))

# litellm
LITELLM_API_BASE = os.getenv("LITELLM_API_BASE")
LITELLM_MODEL = os.getenv("LITELLM_MODEL", "mistral/codestral-latest")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", "")
```

---

## `app/vector_store.py`

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
        metadata={"description": "Documents Confluence IV2"},
        embedding_function=None
    )
```

---

## `app/embedder.py`

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

## `app/litellm_client.py`

```python
from litellm import completion
import config
import os

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

## `app/ingest_confluence.py`

```python
from atlassian import Confluence
import config
from embedder import embed_texts
from vector_store import get_collection
from tqdm import tqdm
import html, re, uuid

def html_to_text(html_content):
    text = re.sub(r'<[^>]+>', ' ', html_content)
    text = html.unescape(text)
    return ' '.join(text.split())

def fetch_pages_from_space():
    confluence = Confluence(
        url=config.CONFLUENCE_URL,
        username=config.CONFLUENCE_USERNAME,
        password=config.CONFLUENCE_PASSWORD
    )
    start = 0
    limit = 50
    pages = []
    while True:
        res = confluence.get_all_pages_from_space(config.CONFLUENCE_SPACE, start=start, limit=limit, expand='body.storage')
        if not res:
            break
        for p in res:
            content = p.get('body', {}).get('storage', {}).get('value', '')
            text = html_to_text(content)
            pages.append({
                "id": p.get('id'),
                "title": p.get('title'),
                "text": text
            })
        start += limit
        if len(res) < limit:
            break
    return pages

def chunk_text(text, size=config.CHUNK_SIZE, overlap=config.CHUNK_OVERLAP):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i+size])
        if chunk.strip():
            chunks.append(chunk)
        i += size - overlap
    return chunks

def ingest_confluence():
    pages = fetch_pages_from_space()
    collection = get_collection()

    all_chunks, metadatas, ids = [], [], []
    for p in pages:
        chunks = chunk_text(p["text"])
        for c in chunks:
            all_chunks.append(c)
            metadatas.append({"page_id": p["id"], "title": p["title"]})
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
    print("✅ Ingestion Confluence terminée dans ChromaDB")

if __name__ == "__main__":
    ingest_confluence()
```

---

## `app/rag.py`

```python
from embedder import embed_texts
from vector_store import get_collection
from litellm_client import generate_with_litellm
from datetime import datetime

def chroma_search(query_embedding, top_k=5):
    collection = get_collection()
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
    docs = []
    for i in range(len(results["ids"][0])):
        docs.append({
            "id": results["ids"][0][i],
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i]
        })
    return docs

def build_messages(query, contexts):
    system = {
        "role": "system",
        "content": (
            "Tu es un assistant interne sécurisé. Réponds uniquement à partir des CONTEXT fournis "
            "et n'invente pas d'informations. Si l'information n'est pas disponible, dis-le clairement."
        )
    }
    context_text = "\n\n---\n\n".join([
        f"Source: {c['metadata'].get('title', 'N/A')}\n{c['content']}"
        for c in contexts
    ])
    user = {
        "role": "user",
        "content": f"CONTEXT:\n{context_text}\n\nQUESTION: {query}\n\nRÉPONSE (en français):"
    }
    return [system, user]

def answer_query(query, top_k=5):
    q_emb = embed_texts([query])[0]
    contexts = chroma_search(q_emb, top_k=top_k)
    messages = build_messages(query, contexts)
    answer = generate_with_litellm(messages)
    return {
        "answer": answer,
        "contexts": contexts,
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

## `app/main.py`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ingest_confluence import ingest_confluence
from rag import answer_query

app = FastAPI(title="RAG - ChromaDB - litellm")

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

@app.post("/query")
def query(q: QueryIn):
    try:
        out = answer_query(q.query, top_k=q.top_k)
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

# 🧩 FRONTEND — Angular 16 minimal

## `frontend-angular/package.json`

```json
{
  "name": "rag-angular",
  "version": "0.0.1",
  "private": true,
  "dependencies": {
    "@angular/animations": "^16.0.0",
    "@angular/common": "^16.0.0",
    "@angular/compiler": "^16.0.0",
    "@angular/core": "^16.0.0",
    "@angular/forms": "^16.0.0",
    "@angular/platform-browser": "^16.0.0",
    "@angular/platform-browser-dynamic": "^16.0.0",
    "@angular/router": "^16.0.0",
    "rxjs": "^7.8.0",
    "tslib": "^2.5.0",
    "zone.js": "~0.13.0"
  },
  "devDependencies": {
    "@angular-devkit/build-angular": "^16.0.0",
    "@angular/cli": "^16.0.0",
    "@angular/compiler-cli": "^16.0.0",
    "typescript": "~5.0.4"
  }
}
```

---

## `src/app/app.module.ts`

```ts
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { ChatComponent } from './chat/chat.component';

@NgModule({
  declarations: [ChatComponent],
  imports: [BrowserModule, HttpClientModule, FormsModule],
  bootstrap: [ChatComponent]
})
export class AppModule {}
```

---

## `src/app/services/api.service.ts`

```ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ApiService {
  base = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  query(sessionId: string, query: string, top_k = 5): Observable<any> {
    return this.http.post(`${this.base}/query`, { session_id: sessionId, query, top_k });
  }

  ingestConfluence(): Observable<any> {
    return this.http.post(`${this.base}/ingest_confluence`, {});
  }
}
```

---

## `src/app/chat/chat.component.ts`

```ts
import { Component } from '@angular/core';
import { ApiService } from '../services/api.service';

interface Message {
  role: string;
  content: string;
  timestamp?: string;
}

@Component({
  selector: 'app-chat',
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css']
})
export class ChatComponent {
  sessionId = 'session-1';
  input = '';
  messages: Message[] = [];
  loading = false;

  constructor(private api: ApiService) {}

  send() {
    if (!this.input.trim() || this.loading) return;
    const q = this.input.trim();
    this.messages.push({ role: 'user', content: q });
    this.input = '';
    this.loading = true;

    this.api.query(this.sessionId, q, 5).subscribe({
      next: (res) => {
        this.messages.push({
          role: 'assistant',
          content: res.answer,
          timestamp: res.timestamp
        });
        this.loading = false;
      },
      error: (err) => {
        this.messages.push({
          role: 'assistant',
          content: 'Erreur: ' + (err.error?.detail || err.message)
        });
        this.loading = false;
      }
    });
  }

  runIngest() {
    if (this.loading) return;
    this.loading = true;
    this.api.ingestConfluence().subscribe({
      next: () => {
        alert('Ingestion terminée.');
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

## `src/app/chat/chat.component.html`

```html
<div class="chat-container">
  <h2>RAG Chat - IV2 (Angular 16)</h2>

  <div class="controls">
    <button (click)="runIngest()" [disabled]="loading">
      🔄 Ingest Confluence
    </button>
  </div>

  <div class="messages">
    <div
      *ngFor="let m of messages"
      [ngClass]="{ user: m.role === 'user', assistant: m.role === 'assistant' }"
    >
      <b>{{ m.role }}:</b>
      <span [innerText]="m.content"></span>
      <div class="ts" *ngIf="m.timestamp">{{ m.timestamp }}</div>
    </div>
  </div>

  <div class="controls">
    <input
      [(ngModel)]="input"
      (keyup.enter)="send()"
      [disabled]="loading"
      placeholder="Pose ta question..."
    />
    <button (click)="send()" [disabled]="loading || !input.trim()">Envoyer</button>
  </div>

  <div *ngIf="loading" class="loader">⏳ Traitement...</div>
</div>
```

---

## `src/app/chat/chat.component.css`

```css
.chat-container {
  width: 800px;
  margin: 30px auto;
  font-family: 'Segoe UI', sans-serif;
}

.controls {
  margin-bottom: 10px;
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
  margin: 8px 0;
  color: #1e88e5;
}

.assistant {
  text-align: left;
  margin: 8px 0;
  color: #2e7d32;
}

input {
  width: 70%;
  padding: 8px;
}

button {
  padding: 8px 12px;
  margin-left: 8px;
}

.ts {
  font-size: 0.75em;
  color: gray;
}

.loader {
  margin-top: 8px;
  color: #ff9800;
}
```

---

# ▶️ DÉMARRAGE RAPIDE

### 1️⃣ Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 2️⃣ Frontend Angular 16

```bash
cd frontend-angular
npm install
ng serve --port 4200
```

👉 Accède à : [http://localhost:4200](http://localhost:4200)
(le backend tourne sur [http://localhost:8000](http://localhost:8000))

---

Souhaites-tu que je te rajoute maintenant un **`docker-compose.yml`** qui lance :

* `backend (FastAPI)`
* `chromadb` (serveur persistant)
* `frontend (Angular 16 avec nginx)`
  ?
  Cela permet un déploiement interne prêt à exécuter (`docker-compose up -d`).
