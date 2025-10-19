Parfait — je te donne un **projet complet** (backend Python + ingestion Confluence + pgvector + LLM via `litellm`) + **frontend Angular minimal** pour interroger le RAG.
J’ai pris en compte ta contrainte : **utiliser le même style `litellm` que dans ta photo** pour la génération. Les embeddings sont réalisés **localement** (sentence-transformers) pour rester en interne (recommandé pour BNP). Tu peux remplacer l’embedding par un service externe si tu as une garantie entreprise.

> ⚠️ Ne colle **aucune clé** publique ici. Mets les secrets dans un `.env` sur ton infra interne.

---

## Arborescence proposée

```
rag-litellm/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ config.py
│  │  ├─ db.py
│  │  ├─ embedder.py
│  │  ├─ ingest_confluence.py
│  │  ├─ rag.py
│  │  └─ litellm_client.py
│  ├─ requirements.txt
│  └─ init_db.sql
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

# BACKEND — code complet

Crée `backend/app/` et place ces fichiers.

### `requirements.txt`

```
fastapi
uvicorn[standard]
sqlalchemy
psycopg-binary
pgvector
sentence-transformers
transformers
torch   # ou torch-cpu
python-dotenv
pdfplumber
python-multipart
pydantic
tqdm
atlassian-python-api
requests
litellm   # package montré sur ta photo (assumé installé)
```

---

### `.env` (exemple, **NE PAS COMMIT**)

```
DATABASE_URL=postgresql://user:password@localhost:5432/ragdb
CONFLUENCE_URL=https://wiki.cib.echonet
CONFLUENCE_USERNAME=ton_user
CONFLUENCE_PASSWORD=ton_password
CONFLUENCE_SPACE=IV2
DATA_DIR=./wiki_IV2  # optionnel si ingestion fichier local
LOCAL_EMB_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBED_DIM=384
CHUNK_SIZE=800
CHUNK_OVERLAP=100

# Litellm config (si tu utilises endpoint interne)
LITELLM_API_BASE=https://ai4devs.group.echonet/api/v1
LITELLM_MODEL=mistral/codestral-latest
LITELLM_API_KEY= # mettre si nécessaire (ou utilise truststore)
```

---

### `init_db.sql`

Exécute sur ta Postgres interne (une fois).

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS docs (
    id SERIAL PRIMARY KEY,
    source TEXT,
    content TEXT,
    metadata JSONB,
    embedding vector(384)
);

CREATE INDEX IF NOT EXISTS idx_docs_embedding ON docs USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    session_id TEXT,
    role TEXT,
    content TEXT,
    created_at TIMESTAMP DEFAULT now()
);
```

> Ajuste `384` si tu changes de modèle d’embeddings.

---

### `config.py`

```python
import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
CONFLUENCE_PASSWORD = os.getenv("CONFLUENCE_PASSWORD")
CONFLUENCE_SPACE = os.getenv("CONFLUENCE_SPACE", "IV2")

DATA_DIR = os.getenv("DATA_DIR", "./wiki_IV2")
LOCAL_EMB_MODEL = os.getenv("LOCAL_EMB_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBED_DIM = int(os.getenv("EMBED_DIM", "384"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))

# litellm
LITELLM_API_BASE = os.getenv("LITELLM_API_BASE")
LITELLM_MODEL = os.getenv("LITELLM_MODEL", "mistral/codestral-latest")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", "")
```

---

### `db.py`

```python
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker
from pgvector.sqlalchemy import Vector
import config

engine = create_engine(config.DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
metadata = MetaData()

docs = Table(
    "docs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("source", Text),
    Column("content", Text),
    Column("metadata", JSONB),
    Column("embedding", Vector(dim=config.EMBED_DIM))
)

conversations = Table(
    "conversations",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("session_id", Text),
    Column("role", Text),
    Column("content", Text),
)
```

---

### `embedder.py`

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
    """
    texts: list[str] -> list[list[float]] (float32)
    """
    model = get_model()
    embs = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return [e.astype(np.float32).tolist() for e in embs]
```

---

### `litellm_client.py`

(Utilise l’API `litellm` comme dans ta photo — si dans ton infra tu as un endpoint interne, on l’utilise)

```python
from litellm import completion
import config
import os

# Optional: inject truststore / proxy handling as in image
# import truststore
# truststore.inject_into_ssl()

def generate_with_litellm(messages, temperature=0.2, max_tokens=1024):
    """
    messages: list of dicts like {"role": "user", "content": "..."}
    Retourne: texte généré (str)
    """
    # Si ton instance litellm nécessite env var, configure-le
    if config.LITELLM_API_KEY:
        os.environ["LITELLM_API_KEY"] = config.LITELLM_API_KEY

    # Selon ta version de litellm, l'appel peut différer — voici un usage similaire à ta photo.
    resp = completion(
        model=config.LITELLM_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        api_base=config.LITELLM_API_BASE
    )
    # response shape dépend de la lib; sur ta photo: response['choices'][0]['message']['content']
    try:
        return resp['choices'][0]['message']['content']
    except Exception:
        # fallback: str(resp)
        return str(resp)
```

---

### `ingest_confluence.py`

(Récupère les pages Confluence du space `IV2`, chunk et insère dans Postgres)

```python
from atlassian import Confluence
from pathlib import Path
import config
from embedder import embed_texts
from db import engine, docs
from sqlalchemy import insert
from tqdm import tqdm
import html
import re

def html_to_text(html_content):
    # simple cleanup: remove tags
    text = re.sub(r'<[^>]+>', ' ', html_content)
    text = html.unescape(text)
    return ' '.join(text.split())

def fetch_pages_from_space():
    confluence = Confluence(
        url=config.CONFLUENCE_URL,
        username=config.CONFLUENCE_USERNAME,
        password=config.CONFLUENCE_PASSWORD
    )
    # get all pages in the space
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
    all_chunks = []
    metadatas = []
    sources = []
    for p in pages:
        chunks = chunk_text(p['text'])
        for c in chunks:
            all_chunks.append(c)
            metadatas.append({"page_id": p['id'], "title": p['title']})
            sources.append(f"confluence:{p['id']}:{p['title'][:60]}")

    batch = 128
    with engine.begin() as conn:
        for i in tqdm(range(0, len(all_chunks), batch)):
            batch_texts = all_chunks[i:i+batch]
            embs = embed_texts(batch_texts)
            rows = []
            for j, text in enumerate(batch_texts):
                rows.append({
                    "source": sources[i+j],
                    "content": text,
                    "metadata": metadatas[i+j],
                    "embedding": embs[j]
                })
            conn.execute(insert(docs), rows)
    print("Ingestion Confluence terminée.")

if __name__ == "__main__":
    ingest_confluence()
```

---

### `rag.py`

(recherche pgvector + construction du prompt + génération via `litellm_client`)

```python
from db import engine
from sqlalchemy import text
from embedder import embed_texts
import config
from litellm_client import generate_with_litellm
from datetime import datetime

def pgvector_search(query_embedding, top_k=5):
    stmt = text("""
    SELECT id, source, content, metadata
    FROM docs
    ORDER BY embedding <-> :q
    LIMIT :k
    """)
    with engine.connect() as conn:
        rows = conn.execute(stmt, {"q": query_embedding, "k": top_k}).fetchall()
        return [dict(r) for r in rows]

def build_messages(query, contexts):
    system = {
        "role": "system",
        "content": (
            "Tu es un assistant interne sécurisé. Réponds uniquement à partir des CONTEXT fournis "
            "et n'invente pas d'informations. Si l'information n'est pas disponible, dis le clairement."
        )
    }
    context_text = "\n\n---\n\n".join([f"Source: {c['source']}\n{c['content']}" for c in contexts])
    user = {
        "role": "user",
        "content": f"CONTEXT:\n{context_text}\n\nQUESTION: {query}\n\nRÉPONSE (en français):"
    }
    return [system, user]

def answer_query(query, top_k=5):
    q_emb = embed_texts([query])[0]
    contexts = pgvector_search(q_emb, top_k=top_k)
    messages = build_messages(query, contexts)
    answer = generate_with_litellm(messages)
    return {
        "answer": answer,
        "contexts": contexts,
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

### `main.py` (FastAPI)

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ingest_confluence import ingest_confluence
from rag import answer_query
import db

app = FastAPI(title="RAG - pgvector - litellm")

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

# FRONTEND — Angular (minimal)

Place sous `frontend-angular/src/app/`

### `package.json` (squelette — crée projet via `ng new` idéalement)

```json
{
  "name": "rag-angular",
  "version": "0.0.1",
  "dependencies": {
    "@angular/core": "^15.0.0",
    "@angular/common": "^15.0.0",
    "@angular/forms": "^15.0.0",
    "@angular/platform-browser": "^15.0.0",
    "@angular/platform-browser-dynamic": "^15.0.0",
    "rxjs": "^7.0.0",
    "zone.js": "~0.12.0"
  }
}
```

---

### `app.module.ts`

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

### `services/api.service.ts`

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

### `chat/chat.component.ts`

```ts
import { Component } from '@angular/core';
import { ApiService } from '../services/api.service';

interface Message { role: string; content: string; timestamp?: string; }

@Component({
  selector: 'app-chat',
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css']
})
export class ChatComponent {
  sessionId = 'session-1';
  input = '';
  messages: Message[] = [];

  constructor(private api: ApiService) {}

  send() {
    if (!this.input.trim()) return;
    const q = this.input;
    this.messages.push({ role: 'user', content: q });
    this.input = '';
    this.api.query(this.sessionId, q, 5).subscribe({
      next: (res) => {
        this.messages.push({ role: 'assistant', content: res.answer, timestamp: res.timestamp });
        // Optionally show contexts
        console.log('contexts', res.contexts);
      },
      error: (err) => {
        this.messages.push({ role: 'assistant', content: 'Erreur: ' + (err.error?.detail || err.message) });
      }
    });
  }

  runIngest() {
    this.api.ingestConfluence().subscribe({
      next: () => alert('Ingestion lancée'),
      error: (e) => alert('Erreur ingestion: ' + e.message)
    });
  }
}
```

---

### `chat/chat.component.html`

```html
<div class="chat-container">
  <h2>RAG Chat - IV2</h2>
  <div class="controls">
    <button (click)="runIngest()">Ingest Confluence (IV2)</button>
  </div>

  <div class="messages">
    <div *ngFor="let m of messages" [ngClass]="{'user': m.role=='user','assistant': m.role=='assistant'}">
      <b>{{m.role}}:</b> <span [innerText]="m.content"></span>
      <div class="ts" *ngIf="m.timestamp">{{m.timestamp}}</div>
    </div>
  </div>

  <div class="controls">
    <input [(ngModel)]="input" (keyup.enter)="send()" placeholder="Pose ta question..." />
    <button (click)="send()">Envoyer</button>
  </div>
</div>
```

### `chat/chat.component.css`

```css
.chat-container { width: 800px; margin: 20px auto; font-family: Arial, sans-serif; }
.controls { margin-bottom: 10px; }
.messages { height: 420px; overflow: auto; border: 1px solid #ddd; padding: 12px; background:#fff; }
.user { text-align: right; margin: 8px 0; }
.assistant { text-align: left; margin: 8px 0; }
input { width: 70%; padding: 8px; }
button { padding: 8px 12px; margin-left: 8px; }
.ts { font-size: 0.75em; color: gray; }
```

---

## Déploiement / run (résumé)

1. **Postgres** (interne) : installe `pgvector` et exécute `init_db.sql`.
2. **Variables** : crée un `.env` sécurisé avec credentials Confluence, DB, litellm endpoint si nécessaire.
3. **Installer deps** : `pip install -r requirements.txt` dans `backend/`.
4. **Ingestion Confluence** (local) : `python -m ingest_confluence` ou via endpoint POST `/ingest_confluence`.
5. **Lancer backend** : `uvicorn main:app --host 0.0.0.0 --port 8000`.
6. **Frontend** : crée projet Angular (`ng new`), place files et `ng serve`.

---

## Remarques sécurité (BNP)

* Tout doit être déployé **dans ton réseau interne**.
* **Litellm** : si ton endpoint est externe, évite de l’utiliser pour données sensibles. Préfère un endpoint TGI interne ou instance litellm accessible en intranet.
* **Confluence** : stocke cred dans vault (Hashi, Azure Key Vault) et n’expose pas le `.env`.
* **Logs** : masque PII dans logs.
* **Accès API** : protège le backend (auth JWT / mTLS) avant de le rendre accessible.

---

Si tu veux, je peux maintenant (sans étape supplémentaire) :

* Te fournir le `docker-compose.yml` qui orchestre **Postgres (pgvector)** + **backend** + **optionnel : TGI** (si tu veux héberger un LLM local) ; **ou**
* Adapter le client `litellm_client.py` si ton endpoint interne a une forme différente (par ex. il s’attend à `prompt=` au lieu de `messages=`).

Dis-moi lequel tu veux **tout de suite** et je te le donne directement (docker-compose ou adaptation endpoint).
