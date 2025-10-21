Excellent réflexe 🔥 — tu veux donc que ton chatbot **garde le contexte d’une conversation** (comme ChatGPT le fait), c’est-à-dire :

* le LLM **se souvient de l’historique** de la discussion,
* chaque nouvelle question est **liée aux précédentes**,
* chaque session (user/chat) garde son **contexte séparé**.

👉 On appelle ça une **mémoire de session**.

---

## ⚙️ Ce qu’on va faire

Je t’explique la logique, puis je te donne **tout le code mis à jour (backend + front)** :

### 🎯 Objectif

1. Chaque utilisateur (ou onglet Angular) a une **session_id** unique.
2. FastAPI stocke dans un **dictionnaire en mémoire** l’historique du chat pour cette session.
3. LangChain utilise une **mémoire conversationnelle** (`ConversationBufferMemory`) liée à chaque session.
4. À chaque appel `/query`, on renvoie la nouvelle réponse **et l’historique complet** pour affichage.

---

## 🧱 Nouveau backend

### 📂 Structure (inchangée)

```
backend/
 └── app/
      ├── main.py
      ├── rag_chain.py
      ├── ingest_confluence.py
      ├── config.py
      ├── requirements.txt
      └── sessions.py
```

---

### 🧠 `sessions.py`

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

### ⚙️ `rag_chain.py` (mise à jour pour mémoire + RAG)

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
            "Réponds en utilisant uniquement les informations du contexte.\n"
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

### ⚙️ `main.py` (mise à jour avec sessions)

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
    print("🚀 Serveur BNP RAG démarré avec sessions.")

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

## 🎨 FRONT-END (Angular)

Voici le code pour ton **composant de chat** qui gère le `session_id` automatiquement :

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
        this.messages = res.history; // l’historique complet
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

## ✅ Résumé

| Fonction   | Description                                           |
| ---------- | ----------------------------------------------------- |
| 🧠 Mémoire | Chaque `session_id` garde l’historique du chat        |
| 🔁 Reset   | `/reset-session/{session_id}` remet à zéro la mémoire |
| 🔒 Sécu    | Données et sessions uniquement en mémoire interne     |
| 💬 Front   | Angular gère le `session_id` automatiquement (UUID)   |
| ⚙️ Back    | FastAPI + LangChain + LiteLLM = full interne          |

---

Souhaites-tu que je te **ajoute une persistance des sessions** (ex. sauvegarde Redis ou SQLite pour ne pas perdre la mémoire après redémarrage du backend) ?
👉 Utile si ton chatbot doit “se souvenir” entre redémarrages.
