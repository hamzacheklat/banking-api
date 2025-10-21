Parfait ✅ — voici **tout le projet complet**, proprement organisé, avec :

* 🔹 Backend **FastAPI + LangChain + LiteLLM** (RAG + mémoire de session)
* 🔹 Ingestion automatique **Confluence + Chroma/FAISS**
* 🔹 Front **Angular** simple de type “ChatGPT”
* 🔹 Gestion complète des **sessions** (contexte persistant tant que le serveur tourne)

---

# 🧱 STRUCTURE GLOBALE

```
rag-bnp-langchain/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── rag_chain.py
│   │   ├── ingest_confluence.py
│   │   ├── sessions.py
│   │   ├── config.py
│   │   └── requirements.txt
│   └── data/
│       └── vectordb/
└── frontend-angular/
    ├── src/
    │   └── app/
    │       ├── chat/
    │       │   ├── chat.component.ts
    │       │   ├── chat.component.html
    │       │   └── chat.component.css
    │       └── app.module.ts
    └── package.json
```

---

## 🧩 BACKEND

---

### 📄 `requirements.txt`

```txt
fastapi
uvicorn[standard]
langchain
langchain-community
chromadb
faiss-cpu
sentence-transformers
atlassian-python-api
apscheduler
python-dotenv
litellm
tqdm
```

---

### 📄 `config.py`

```python
import os
from dotenv import load_dotenv
load_dotenv()

# === Confluence ===
CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
CONFLUENCE_PASSWORD = os.getenv("CONFLUENCE_PASSWORD")
CONFLUENCE_SPACE = os.getenv("CONFLUENCE_SPACE", "IV2")

# === Embeddings ===
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))

# === Vector DB ===
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./data/vectordb")
VECTOR_DB_TYPE = os.getenv("VECTOR_DB_TYPE", "chroma")  # ou 'faiss'

# === LITELLM ===
LITELLM_API_BASE = os.getenv("LITELLM_API_BASE")
LITELLM_MODEL = os.getenv("LITELLM_MODEL", "mistral/codestral-latest")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", "")

# === Scheduler ===
SYNC_INTERVAL_MINUTES = int(os.getenv("SYNC_INTERVAL_MINUTES", "60"))
```

---

### 📄 `sessions.py`

```python
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.llms import LiteLLM
import config

# Dictionnaire global de sessions
_sessions = {}

def get_session(session_id: str, retriever=None):
    if session_id not in _sessions:
        print(f"[NEW SESSION] Création d'une session: {session_id}")
        llm = LiteLLM(
            model=config.LITELLM_MODEL,
            api_base=config.LITELLM_API_BASE
        )
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        chain = ConversationChain(
            llm=llm,
            memory=memory,
            verbose=False
        )
        _sessions[session_id] = {
            "chain": chain,
            "memory": memory,
            "retriever": retriever
        }
    return _sessions[session_id]

def reset_session(session_id: str):
    if session_id in _sessions:
        del _sessions[session_id]
```

---

### 📄 `ingest_confluence.py`

```python
from atlassian import Confluence
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma, FAISS
import config, re, html
from tqdm import tqdm
from apscheduler.schedulers.background import BackgroundScheduler
import os

def html_to_text(content):
    text = re.sub(r"<[^>]+>", " ", content)
    text = html.unescape(text)
    return " ".join(text.split())

def get_confluence_client():
    return Confluence(
        url=config.CONFLUENCE_URL,
        username=config.CONFLUENCE_USERNAME,
        password=config.CONFLUENCE_PASSWORD
    )

def load_confluence_pages():
    client = get_confluence_client()
    pages = client.get_all_pages_from_space(config.CONFLUENCE_SPACE, expand="body.storage")
    docs = []
    for p in tqdm(pages, desc="Lecture des pages Confluence"):
        pid, title = p["id"], p["title"]
        html_content = p.get("body", {}).get("storage", {}).get("value", "")
        text = html_to_text(html_content)
        docs.append({"page_id": pid, "title": title, "text": text})
    return docs

def chunk_documents(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP
    )
    texts, metadatas = [], []
    for d in docs:
        chunks = splitter.split_text(d["text"])
        for i, chunk in enumerate(chunks):
            texts.append(chunk)
            metadatas.append({"page_id": d["page_id"], "title": d["title"], "chunk": i})
    return texts, metadatas

def get_embeddings():
    return SentenceTransformerEmbeddings(model_name=config.EMBED_MODEL)

def build_vectorstore(texts, metadatas):
    embeddings = get_embeddings()
    os.makedirs(config.VECTOR_DB_PATH, exist_ok=True)

    if config.VECTOR_DB_TYPE.lower() == "chroma":
        db = Chroma.from_texts(
            texts=texts,
            embedding=embeddings,
            metadatas=metadatas,
            persist_directory=config.VECTOR_DB_PATH
        )
        db.persist()
    elif config.VECTOR_DB_TYPE.lower() == "faiss":
        db = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
        db.save_local(config.VECTOR_DB_PATH)
    print("[✅] Ingestion terminée et base vectorielle mise à jour.")

def ingest_confluence():
    print("[SYNC] Démarrage de l’ingestion Confluence…")
    docs = load_confluence_pages()
    texts, metadatas = chunk_documents(docs)
    build_vectorstore(texts, metadatas)

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(ingest_confluence, "interval", minutes=config.SYNC_INTERVAL_MINUTES)
    scheduler.start()
    print(f"[SCHEDULER] Synchronisation toutes les {config.SYNC_INTERVAL_MINUTES} min.")

if __name__ == "__main__":
    ingest_confluence()
```

---

### 📄 `rag_chain.py`

```python
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma, FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.llms import LiteLLM
from sessions import get_session
import config, os

def load_vectorstore():
    embeddings = SentenceTransformerEmbeddings(model_name=config.EMBED_MODEL)
    if config.VECTOR_DB_TYPE.lower() == "chroma":
        return Chroma(
            persist_directory=config.VECTOR_DB_PATH,
            embedding_function=embeddings
        )
    elif config.VECTOR_DB_TYPE.lower() == "faiss":
        return FAISS.load_local(config.VECTOR_DB_PATH, embeddings, allow_dangerous_deserialization=True)
    else:
        raise ValueError("VECTOR_DB_TYPE doit être 'chroma' ou 'faiss'")

def get_llm():
    os.environ["LITELLM_API_KEY"] = config.LITELLM_API_KEY
    return LiteLLM(model=config.LITELLM_MODEL, api_base=config.LITELLM_API_BASE)

def get_rag_session(session_id: str):
    db = load_vectorstore()
    retriever = db.as_retriever(search_kwargs={"k": 5})
    session = get_session(session_id, retriever)
    return session

def ask_question(session_id: str, query: str):
    session = get_rag_session(session_id)
    llm = get_llm()

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=(
            "Tu es un assistant BNP spécialisé dans le wiki IV2.\n"
            "Réponds en utilisant uniquement le contexte fourni.\n"
            "Contexte:\n{context}\n\nQuestion: {question}\n\nRéponse:"
        )
    )

    qa = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=session["retriever"],
        memory=session["memory"],
        combine_docs_chain_kwargs={"prompt": prompt},
        verbose=False
    )

    response = qa.invoke({"question": query})
    answer = response["answer"]

    return {
        "session_id": session_id,
        "answer": answer,
        "history": [
            {"role": "user", "content": m.content}
            if m.type == "human"
            else {"role": "assistant", "content": m.content}
            for m in session["memory"].chat_memory.messages
        ]
    }
```

---

### 📄 `main.py`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ingest_confluence import ingest_confluence, start_scheduler
from rag_chain import ask_question
from sessions import reset_session

app = FastAPI(title="BNP RAG ChatBot (LangChain + LiteLLM + Mémoire)")

class QueryIn(BaseModel):
    session_id: str
    query: str

@app.on_event("startup")
def startup():
    start_scheduler()
    print("🚀 Serveur BNP RAG démarré avec gestion des sessions.")

@app.post("/query")
def query_endpoint(payload: QueryIn):
    try:
        result = ask_question(payload.session_id, payload.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset-session/{session_id}")
def reset_session_endpoint(session_id: str):
    reset_session(session_id)
    return {"status": "reset", "session_id": session_id}

@app.post("/ingest")
def manual_ingest():
    try:
        ingest_confluence()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 🎨 FRONTEND (Angular)

---

### 📄 `package.json`

```json
{
  "name": "bnp-chat",
  "version": "1.0.0",
  "dependencies": {
    "@angular/core": "^18.0.0",
    "@angular/common": "^18.0.0",
    "@angular/forms": "^18.0.0",
    "@angular/platform-browser": "^18.0.0",
    "@angular/platform-browser-dynamic": "^18.0.0",
    "@angular/router": "^18.0.0",
    "uuid": "^9.0.0",
    "rxjs": "^7.5.0"
  }
}
```

---

### 📄 `app.module.ts`

```typescript
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { ChatComponent } from './chat/chat.component';

@NgModule({
  declarations: [ChatComponent],
  imports: [BrowserModule, FormsModule, HttpClientModule],
  bootstrap: [ChatComponent]
})
export class AppModule {}
```

---

### 📄 `chat.component.ts`

```typescript
import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { v4 as uuidv4 } from 'uuid';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

@Component({
  selector: 'app-chat',
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css']
})
export class ChatComponent implements OnInit {
  sessionId: string = '';
  userInput: string = '';
  messages: Message[] = [];
  loading = false;
  apiUrl = 'http://localhost:8000/query';

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.sessionId = uuidv4();
  }

  sendMessage(): void {
    if (!this.userInput.trim()) return;
    const query = this.userInput.trim();

    this.messages.push({ role: 'user', content: query });
    this.userInput = '';
    this.loading = true;

    this.http.post<any>(this.apiUrl, {
      session_id: this.sessionId,
      query
    }).subscribe({
      next: (res) => {
        this.messages = res.history;
        this.loading = false;
      },
      error: (err) => {
        console.error(err);
        this.loading = false;
      }
    });
  }

  resetSession(): void {
    this.http.post(`http://localhost:8000/reset-session/${this.sessionId}`, {})
      .subscribe(() => {
        this.messages = [];
        this.sessionId = uuidv4();
      });
  }
}
```

---

### 📄 `chat.component.html`

```html
<div class="chat-container">
  <div class="chat-box">
    <div *ngFor="let msg of messages" [ngClass]="msg.role">
      <strong *ngIf="msg.role === 'user'">👤</strong>
      <strong *ngIf="msg.role === 'assistant'">🤖</strong>
      {{ msg.content }}
    </div>
  </div>

  <div class="chat-input">
    <input [(ngModel)]="userInput" placeholder="Pose ta question..." (keyup.enter)="sendMessage()" />
    <button (click)="sendMessage()" [disabled]="loading">Envoyer</button>
    <button (click)="resetSession()">🔄 Nouvelle session</button>
  </div>

  <div *ngIf="loading" class="loading">⏳ Génération...</div>
</div>
```

---

### 📄 `chat.component.css`

```css
.chat-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 700px;
  margin: 2rem auto;
  border: 1px solid #ddd;
  border-radius: 10px;
  padding: 1rem;
  background: #fafafa;
}

.chat-box {
  flex: 1;
  max-height: 70vh;
  overflow-y: auto;
  margin-bottom: 1rem;
}

.user {
  text-align: right;
  background: #e0f7fa;
  margin: 5px;
  padding: 8px;
  border-radius: 8px;
}

.assistant {
  text-align: left;
  background: #fff3e0;
  margin: 5px;
  padding: 8px;
  border-radius: 8px;
}

.chat-input {
  display: flex;
  gap: 0.5rem;
}

input {
  flex: 1;
  padding: 0.5rem;
  border-radius: 8px;
  border: 1px solid #ccc;
}

button {
  border: none;
  padding: 0.5rem 1rem;
  background: #1976d2;
  color: white;
  border-radius: 8px;
  cursor: pointer;
}

button:hover {
  background: #125ca3;
}

.loading {
  text-align: center;
  color: gray;
  margin-top: 1rem;
}
```

---

## ⚙️ DÉMARRAGE

### 🖥️ Backend

```bash
cd backend/app
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 💬 Frontend

```bash
cd frontend-angular
npm install
ng serve
```

Puis ouvre :
👉 [http://localhost:4200](http://localhost:4200)

---

Souhaites-tu que je t’ajoute une **persistance des sessions (SQLite)** pour que les conversations ne se perdent pas quand tu redémarres le backend ?
Sinon tout reste en mémoire RAM (plus rapide, mais volatile).
