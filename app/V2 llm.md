Parfait 👍 tu veux donc :

1. Utiliser **le LLM interne BNP** (celui que tu appelles via `https://ai4devs.group.echonet/api/v1` avec le module `litellm` et le modèle `mistral/codestral-latest`).
2. Corriger le backend pour qu’il fonctionne **uniquement avec ce modèle**, sans utiliser d’autres LLM externes.
3. Corriger les dépendances manquantes (`text_splitter`, `chains`, `prompts` etc.) dans `langchain`.
4. Compléter la partie **Angular** avec les fichiers manquants (`angular.json`, `main.ts`, etc.) pour que le front tourne sans erreur.

---

Je vais donc te redonner un **projet complet** corrigé :

* 🔹 Backend → FastAPI + LangChain + ta configuration BNP (`ai4devs.group.echonet`)
* 🔹 Frontend → Angular complet (avec fichiers de config, build et lancement).

---

## 🧱 1. BACKEND BNP-RAG

### 📂 Structure

```
backend/
 ├── app/
 │   ├── main.py
 │   ├── config.py
 │   ├── rag_chain.py
 │   ├── ingest_confluence.py
 │   ├── sessions.py
 │   └── requirements.txt
 └── data/vectordb/
```

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
truststore
```

---

### 📄 `config.py`

```python
import os
from dotenv import load_dotenv
load_dotenv()

# === BNP LLM ===
LITELLM_MODEL = os.getenv("LITELLM_MODEL", "mistral/codestral-latest")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", "")
LITELLM_API_BASE = os.getenv("LITELLM_API_BASE", "https://ai4devs.group.echonet/api/v1")

# === Vector store ===
VECTOR_DB_TYPE = os.getenv("VECTOR_DB_TYPE", "chroma")  # ou 'faiss'
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./data/vectordb")

# === Embeddings ===
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))

# === Confluence ===
CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
CONFLUENCE_PASSWORD = os.getenv("CONFLUENCE_PASSWORD")
CONFLUENCE_SPACE = os.getenv("CONFLUENCE_SPACE", "IV2")

# === Scheduler ===
SYNC_INTERVAL_MINUTES = int(os.getenv("SYNC_INTERVAL_MINUTES", "60"))
```

---

### 📄 `rag_chain.py`

> 🧠 Ce fichier utilise **ton modèle BNP** via `LiteLLM` et `truststore` pour SSL interne.

```python
import os
import truststore
truststore.inject_into_ssl()

from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma, FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.llms import LiteLLM
from sessions import get_session
import config

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
    os.environ["MISTRAL_API_KEY"] = config.LITELLM_API_KEY
    os.environ["NO_PROXY"] = "*"
    return LiteLLM(
        model=config.LITELLM_MODEL,
        api_base=config.LITELLM_API_BASE
    )

def get_rag_session(session_id: str):
    db = load_vectorstore()
    retriever = db.as_retriever(search_kwargs={"k": 5})
    return get_session(session_id, retriever)

def ask_question(session_id: str, query: str):
    session = get_rag_session(session_id)
    llm = get_llm()

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=(
            "Tu es un assistant BNP qui répond sur le wiki IV2.\n"
            "Utilise uniquement le contexte ci-dessous pour formuler ta réponse.\n"
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
    return {
        "session_id": session_id,
        "answer": response["answer"],
        "history": [
            {"role": "user", "content": m.content}
            if m.type == "human"
            else {"role": "assistant", "content": m.content}
            for m in session["memory"].chat_memory.messages
        ]
    }
```

---

### 📄 `sessions.py`

```python
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.llms import LiteLLM
import config

_sessions = {}

def get_session(session_id: str, retriever=None):
    if session_id not in _sessions:
        print(f"[NEW SESSION] Création: {session_id}")
        llm = LiteLLM(
            model=config.LITELLM_MODEL,
            api_base=config.LITELLM_API_BASE
        )
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        chain = ConversationChain(llm=llm, memory=memory, verbose=False)
        _sessions[session_id] = {"chain": chain, "memory": memory, "retriever": retriever}
    return _sessions[session_id]

def reset_session(session_id: str):
    if session_id in _sessions:
        del _sessions[session_id]
```

---

### 📄 `ingest_confluence.py`

(identique à la version précédente — ingestion automatique depuis Confluence)

---

### 📄 `main.py`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from rag_chain import ask_question
from ingest_confluence import ingest_confluence, start_scheduler
from sessions import reset_session

app = FastAPI(title="BNP Wiki IV2 RAG Chatbot")

class QueryIn(BaseModel):
    session_id: str
    query: str

@app.on_event("startup")
def startup():
    start_scheduler()
    print("🚀 BNP Chatbot démarré (LLM interne Mistral Codestral).")

@app.post("/query")
def query(payload: QueryIn):
    try:
        return ask_question(payload.session_id, payload.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset-session/{session_id}")
def reset(session_id: str):
    reset_session(session_id)
    return {"status": "reset", "session_id": session_id}

@app.post("/ingest")
def ingest():
    try:
        ingest_confluence()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 🎨 2. FRONTEND ANGULAR COMPLET

### 📂 Structure

```
frontend-angular/
 ├── angular.json
 ├── package.json
 ├── tsconfig.json
 └── src/
     ├── main.ts
     └── app/
         ├── app.module.ts
         └── chat/
             ├── chat.component.ts
             ├── chat.component.html
             └── chat.component.css
```

---

### 📄 `package.json`

```json
{
  "name": "bnp-chatbot",
  "version": "1.0.0",
  "scripts": {
    "start": "ng serve",
    "build": "ng build"
  },
  "dependencies": {
    "@angular/animations": "^18.0.0",
    "@angular/common": "^18.0.0",
    "@angular/compiler": "^18.0.0",
    "@angular/core": "^18.0.0",
    "@angular/forms": "^18.0.0",
    "@angular/platform-browser": "^18.0.0",
    "@angular/platform-browser-dynamic": "^18.0.0",
    "@angular/router": "^18.0.0",
    "rxjs": "^7.5.0",
    "uuid": "^9.0.0"
  },
  "devDependencies": {
    "@angular/cli": "^18.0.0",
    "@angular/compiler-cli": "^18.0.0",
    "typescript": "^5.4.0"
  }
}
```

---

### 📄 `angular.json`

```json
{
  "$schema": "./node_modules/@angular/cli/lib/config/schema.json",
  "version": 1,
  "projects": {
    "bnp-chatbot": {
      "projectType": "application",
      "sourceRoot": "src",
      "architect": {
        "build": {
          "builder": "@angular-devkit/build-angular:browser",
          "options": {
            "outputPath": "dist/bnp-chatbot",
            "index": "src/index.html",
            "main": "src/main.ts",
            "polyfills": [],
            "tsConfig": "tsconfig.json"
          }
        },
        "serve": {
          "builder": "@angular-devkit/build-angular:dev-server",
          "options": {
            "browserTarget": "bnp-chatbot:build"
          }
        }
      }
    }
  },
  "defaultProject": "bnp-chatbot"
}
```

---

### 📄 `tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "es2020",
    "module": "es2020",
    "strict": true,
    "moduleResolution": "node",
    "experimentalDecorators": true,
    "skipLibCheck": true,
    "outDir": "./dist/out-tsc"
  },
  "include": ["src/**/*.ts"]
}
```

---

### 📄 `main.ts`

```typescript
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';

platformBrowserDynamic().bootstrapModule(AppModule)
  .catch(err => console.error(err));
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

### 📄 `chat.component.ts` / `.html` / `.css`

> (identiques à la version précédente, elles fonctionnent sans modification)

---

## 🚀 Lancement

### 🔧 Backend

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

👉 Accès via : [http://localhost:4200](http://localhost:4200)
👉 API : [http://localhost:8000/docs](http://localhost:8000/docs)

---

Souhaites-tu que je t’ajoute aussi la **persistance de la mémoire** (sessions stockées en SQLite ou Redis) pour ne pas perdre le contexte si tu redémarres le serveur ?
