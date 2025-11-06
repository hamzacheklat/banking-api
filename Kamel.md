Super — je fais la modification complète pour que l’ingestion **n’aille plus sur Confluence** mais lise **2 pages de wiki locales** (ou plus si tu veux), et je remplace **ChromaDB** par **PostgreSQL + pgvector**.

Je te fournis ci-dessous les fichiers backend modifiés à remplacer dans `backend/app/`. Ils sont prêts à coller dans ton repo — j’ai aussi inclus les changements à `requirements.txt` et des instructions d’usage.

> Remarque importante : PostgreSQL doit avoir l’extension `pgvector` activée (commande SQL: `CREATE EXTENSION IF NOT EXISTS vector;`). Tu peux le faire dans ta base avant d’exécuter l’app.

---

# ✅ Résumé des changements

* Suppression de la dépendance Confluence/Chroma.
* Nouvelle ingestion depuis des fichiers locaux (HTML / Markdown / TXT) présents dans un dossier local ou listés via la variable d’environnement `LOCAL_WIKI_PAGES` (séparés par des virgules).
* Stockage des embeddings dans une table `documents` PostgreSQL avec colonne `embedding` de type `vector` (pgvector).
* Recherche vectorielle via l’opérateur `<->` (similarité) dans Postgres.
* Fichiers modifiés fournis : `requirements.txt`, `config.py`, `vector_store.py`, `ingest_local_wiki.py` (remplace ingest_confluence), `rag.py`, `main.py`.

---

## `backend/requirements.txt` (remplace l’ancien)

```txt
fastapi
uvicorn[standard]
sentence-transformers
transformers
torch
python-dotenv
pdfplumber
python-multipart
pydantic
tqdm
requests
litellm

# Postgres + pgvector
psycopg2-binary
SQLAlchemy>=1.4
pgvector
```

---

## `backend/app/config.py`

```python
import os
from dotenv import load_dotenv
load_dotenv()

# Postgres / pgvector
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://postgres:password@localhost:5432/ragdb")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))  # adapter si tu changes de modèle

# Local wiki pages (comma separated filenames relative to LOCAL_WIKI_DIR)
LOCAL_WIKI_DIR = os.getenv("LOCAL_WIKI_DIR", "./local_wiki")
LOCAL_WIKI_PAGES = os.getenv("LOCAL_WIKI_PAGES", "page1.html,page2.html")

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

## `backend/app/vector_store.py`

```python
# PostgreSQL + pgvector vector store via SQLAlchemy
import json
import uuid
from sqlalchemy import create_engine, Column, String, Text, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import IntegrityError
from pgvector.sqlalchemy import Vector
import config
from typing import List, Dict

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, index=True)  # uuid str
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True)
    embedding = Column(Vector(dimensions=config.EMBEDDING_DIM), nullable=False)

# Engine & session
engine = create_engine(config.POSTGRES_URL, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def init_db():
    # create table if not exists
    Base.metadata.create_all(bind=engine)

def add_documents(ids: List[str], documents: List[str], embeddings: List[List[float]], metadatas: List[Dict]):
    """
    Adds a batch of documents to Postgres.
    """
    init_db()
    session = SessionLocal()
    objs = []
    for i, doc in enumerate(documents):
        did = ids[i] if ids and len(ids) > i else str(uuid.uuid4())
        meta = metadatas[i] if metadatas and len(metadatas) > i else {}
        emb = embeddings[i]
        objs.append(Document(id=did, content=doc, metadata=meta, embedding=emb))
    try:
        session.add_all(objs)
        session.commit()
    except IntegrityError:
        session.rollback()
        # try upsert: replace existing
        for o in objs:
            session.merge(o)
        session.commit()
    finally:
        session.close()

def query_vector(query_embedding: List[float], top_k: int = 5):
    """
    Perform similarity search using pgvector's <-> operator.
    Returns list of dicts with id, content, metadata.
    """
    init_db()
    # We use raw SQL for ORDER BY embedding <-> :vec
    from sqlalchemy import text
    # Convert to pgvector literal using array notation: pgvector python adapter will handle lists if using SQLAlchemy bind
    sql = text("""
        SELECT id, content, metadata
        FROM documents
        ORDER BY embedding <-> :vec
        LIMIT :k
    """)
    # Use execution with parameters. SQLAlchemy + psycopg2 + pgvector adapter accepts Python list as :vec
    session = SessionLocal()
    try:
        res = session.execute(sql, {"vec": query_embedding, "k": top_k}).fetchall()
        docs = []
        for row in res:
            docs.append({
                "id": row[0],
                "content": row[1],
                "metadata": row[2]
            })
        return docs
    finally:
        session.close()
```

> Remarque : `pgvector` adapte automatiquement les listes Python si la connexion utilise `psycopg2` et `pgvector` est installé. Assure-toi que l’extension `vector` est activée sur ta DB.

---

## `backend/app/ingest_local_wiki.py` (remplace `ingest_confluence.py`)

```python
import os, re, html, uuid
from tqdm import tqdm
import config
from embedder import embed_texts
from vector_store import add_documents
from pathlib import Path

def html_to_text(html_content):
    text = re.sub(r'<[^>]+>', ' ', html_content)
    text = html.unescape(text)
    return ' '.join(text.split())

def read_file(path: Path):
    text = path.read_text(encoding='utf-8', errors='ignore')
    if path.suffix.lower() in ['.html', '.htm']:
        return html_to_text(text)
    else:
        # .md or .txt or unknown: minimal cleanup
        return ' '.join(text.split())

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

def ingest_local_wiki():
    """
    Ingest pages specified by LOCAL_WIKI_PAGES (comma separated names) in LOCAL_WIKI_DIR
    If not found, ingests all .html/.md/.txt files in LOCAL_WIKI_DIR.
    """
    base = Path(config.LOCAL_WIKI_DIR)
    if not base.exists():
        raise FileNotFoundError(f"LOCAL_WIKI_DIR not found: {base}")

    pages_list = [p.strip() for p in config.LOCAL_WIKI_PAGES.split(",") if p.strip()]
    files = []

    if pages_list:
        for name in pages_list:
            p = base / name
            if p.exists():
                files.append(p)
            else:
                # try with extensions
                for ext in ['.html', '.md', '.txt']:
                    q = base / (name + ext)
                    if q.exists():
                        files.append(q)
                        break
    if not files:
        # fallback: take html/md/txt files
        files = list(base.glob("*.html")) + list(base.glob("*.md")) + list(base.glob("*.txt"))

    if not files:
        raise FileNotFoundError("Aucun fichier wiki trouvé pour ingestion.")

    all_chunks, metadatas, ids = [], [], []
    for f in files:
        text = read_file(f)
        chunks = chunk_text(text)
        for c in chunks:
            all_chunks.append(c)
            metadatas.append({"source_file": str(f.name)})
            ids.append(str(uuid.uuid4()))

    batch = 128
    for i in tqdm(range(0, len(all_chunks), batch)):
        batch_texts = all_chunks[i:i+batch]
        batch_ids = ids[i:i+batch]
        batch_meta = metadatas[i:i+batch]
        embs = embed_texts(batch_texts)
        add_documents(batch_ids, batch_texts, embs, batch_meta)

    print("✅ Ingestion locale terminée (Postgres + pgvector).")

if __name__ == "__main__":
    ingest_local_wiki()
```

---

## `backend/app/rag.py` (pette adaptation pour utiliser vector_store.query_vector)

```python
from embedder import embed_texts
from vector_store import query_vector
from litellm_client import generate_with_litellm
from datetime import datetime

def chroma_search(query_embedding, top_k=5):
    # renamed function body to use Postgres vector search
    docs = query_vector(query_embedding, top_k=top_k)
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
        f"Source: {c.get('metadata', {}).get('source_file', c.get('metadata', {}).get('title','N/A'))}\n{c['content']}"
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

## `backend/app/main.py` (mise à jour des imports et endpoints)

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ingest_local_wiki import ingest_local_wiki
from rag import answer_query

app = FastAPI(title="RAG - Postgres(pgvector) - litellm")

class QueryIn(BaseModel):
    session_id: str = "default"
    query: str
    top_k: int = 5

@app.post("/ingest_local_wiki")
def run_ingest_local():
    try:
        ingest_local_wiki()
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

> Note : j’ai renommé l’endpoint d’ingest en `/ingest_local_wiki`. Si tu préfères garder `/ingest_confluence`, dis-le et je fais la redirection.

---

## Variables d’environnement importantes (`.env`)

Ajoute/édite ces variables dans ton `.env` :

```env
POSTGRES_URL=postgresql://postgres:password@db:5432/ragdb
EMBEDDING_DIM=384

LOCAL_WIKI_DIR=./local_wiki
LOCAL_WIKI_PAGES=page1.html,page2.html

LOCAL_EMB_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=800
CHUNK_OVERLAP=100

LITELLM_API_BASE=...
LITELLM_MODEL=...
LITELLM_API_KEY=...
```

---

## Instructions rapides d’utilisation (local)

1. Prépare un dossier `backend/local_wiki/` et mets-y `page1.html` et `page2.html` (ou modifie `LOCAL_WIKI_PAGES`).
2. Assure-toi que Postgres est up et que l’extension `vector` est activée :

   * connecte-toi à la DB et exécute : `CREATE EXTENSION IF NOT EXISTS vector;`
3. Installer dépendances :

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # ou crée .env avec les variables ci-dessus
```

4. Lancer l’app :

```bash
uvicorn app.main:app --reload --port 8000
```

5. Appels :

* `POST /ingest_local_wiki` → ingère les pages locales dans Postgres.
* `POST /query` → même interface qu’avant.

---

## Points d’attention (à lire)

* `EMBEDDING_DIM` doit correspondre à la dimension de sortie de ton modèle d’embeddings (MiniLM-L6-v2 → 384).
* Vérifie que PostgreSQL ait l’extension `pgvector` activée.
* Le driver `psycopg2-binary` + `pgvector` gèrent la sérialisation des vecteurs passés depuis Python. Si tu rencontres une erreur de type, dis-moi l’erreur exacte et j’adapte le binding.
* Si tu veux ingestion directe depuis des fichiers `.confluence` exportés ou autre format, on peut ajouter des parseurs spécifiques.

---

Si tu veux, j’adapte aussi :

* le frontend Angular pour appeler `POST /ingest_local_wiki` (actuellement il appelait `/ingest_confluence`) — je peux modifier `ApiService.ingestConfluence()` et le texte du bouton.
* créer un `docker-compose.yml` incluant Postgres (avec pgvector), backend et frontend.

Dis-moi ce que tu veux en priorité (adapter frontend + docker-compose ?), et je te fournis les fichiers immédiatement.
