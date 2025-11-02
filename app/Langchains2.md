Excellent 💪
On va tout assembler pour que tu aies **un projet complet RAG LangChain + Angular**, clé en main, sans rien manquer.

---

# 🧩 **STRUCTURE GLOBALE**

```
project/
├── app/                         # backend Python
│   ├── config.py
│   ├── embedder.py
│   ├── vector_store.py
│   ├── rag_langchain.py
│   └── main.py
└── frontend-angular/             # frontend Angular
    ├── src/
    │   └── app/
    │       ├── app.component.html
    │       ├── app.component.scss
    │       ├── app.component.ts
    │       └── app.module.ts
    ├── angular.json
    └── package.json
```

---

## 🧠 1. `app/config.py`

```python
import os

# MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "my_database")

# Chroma
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./chroma_data")

# LLM (Litellm / OpenAI / Mistral)
LITELLM_MODEL = os.getenv("LITELLM_MODEL", "mistral:latest")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", "")
```

---

## ⚙️ 2. `app/embedder.py`

```python
from langchain_community.embeddings import HuggingFaceEmbeddings

def get_embedder():
    """
    Retourne le modèle d'embedding configuré.
    """
    return HuggingFaceEmbeddings(model_name="mxbai-embed-large-v1")
```

---

## 💾 3. `app/vector_store.py`

```python
import config
from langchain_community.vectorstores import Chroma
from embedder import get_embedder

def get_vanish_vectorstore():
    """
    Retourne le vector store Chroma pour vanish_flows.
    """
    embeddings = get_embedder()
    return Chroma(
        persist_directory=config.CHROMA_DB_DIR,
        collection_name="mongo_vanish_flows",
        embedding_function=embeddings
    )
```

---

## 🧩 4. `app/rag_langchain.py`

```python
from datetime import datetime
from langchain_community.chat_models import ChatLiteLLM
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from vector_store import get_vanish_vectorstore
import config

# Initialisation des composants
vectorstore = get_vanish_vectorstore()
retriever = vectorstore.as_retriever(search_kwargs={"k": 8})
llm = ChatLiteLLM(model=config.LITELLM_MODEL, api_key=config.LITELLM_API_KEY)

# Prompt multilingue + contextuel
template = """
You are an assistant specialized in analyzing failed job flows from vanish_flows data.
Today's date is {today}.

Use the context below to answer precisely.
If the question is in French, respond in French.
If the question is in English, respond in English.

Each result corresponds to one job or flow from MongoDB with data such as:
FLOW, TASK, JOB_ID, FAILURE REASON, WHAT TO DO, START_TIME, END_TIME, ORIGIN, etc.

Summarize with:
- Key issues or repeated patterns
- Impact and origin
- Recommended actions if possible

-------------------
Context:
{context}
-------------------

Question:
{question}

Answer:
"""

PROMPT = PromptTemplate(
    input_variables=["today", "context", "question"],
    template=template
)

# Construction de la chaîne RAG
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff",
    chain_type_kwargs={"prompt": PROMPT}
)

def answer_query(query: str):
    """
    Pose une question à la base vectorielle Chroma via LangChain.
    """
    today = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    response = qa_chain.invoke({
        "today": today,
        "question": query
    })
    return {
        "query": query,
        "answer": response["result"],
        "date": today
    }

if __name__ == "__main__":
    q = "Quels jobs ont échoué aujourd'hui ?"
    res = answer_query(q)
    print("🧠 Question:", res["query"])
    print("💬 Réponse:", res["answer"])
```

---

## 🚀 5. `app/main.py`

```python
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from rag_langchain import answer_query

app = FastAPI(title="Vanish RAG API")

# Autoriser Angular à accéder à l’API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ à restreindre en prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/rag/query")
def rag_query(q: str = Query(..., description="User question")):
    """
    Endpoint du RAG chatbot
    """
    result = answer_query(q)
    return result
```

➡️ **Lancement :**

```bash
uvicorn app.main:app --reload --port 8000
```

---

# 🖥️ FRONTEND — Angular Chat

## 1️⃣ `src/app/app.component.html`

```html
<div class="chat-container">
  <mat-card class="chat-card">
    <h2>🧠 Vanish Flow Assistant</h2>

    <div class="messages">
      <div *ngFor="let m of messages" [ngClass]="m.sender">
        <strong *ngIf="m.sender === 'user'">Vous :</strong>
        <strong *ngIf="m.sender === 'bot'">Assistant :</strong>
        <p>{{ m.text }}</p>
      </div>
    </div>

    <div class="input-area">
      <mat-form-field class="input-full">
        <input matInput placeholder="Posez une question..." [(ngModel)]="userInput" (keyup.enter)="sendMessage()" />
      </mat-form-field>
      <button mat-flat-button color="primary" (click)="sendMessage()">Envoyer</button>
    </div>
  </mat-card>
</div>
```

---

## 2️⃣ `src/app/app.component.ts`

```typescript
import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';

interface Message {
  sender: 'user' | 'bot';
  text: string;
}

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {
  messages: Message[] = [];
  userInput = '';
  apiUrl = 'http://localhost:8000/rag/query';

  constructor(private http: HttpClient) {}

  sendMessage() {
    if (!this.userInput.trim()) return;

    const userMessage: Message = { sender: 'user', text: this.userInput };
    this.messages.push(userMessage);

    this.http.get<any>(`${this.apiUrl}?q=${encodeURIComponent(this.userInput)}`).subscribe({
      next: (res) => {
        const botMessage: Message = { sender: 'bot', text: res.answer };
        this.messages.push(botMessage);
      },
      error: () => {
        const errorMsg: Message = { sender: 'bot', text: "❌ Erreur lors de la communication avec le serveur." };
        this.messages.push(errorMsg);
      }
    });

    this.userInput = '';
  }
}
```

---

## 3️⃣ `src/app/app.component.scss`

```scss
.chat-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: #f3f4f6;
}

.chat-card {
  width: 600px;
  height: 80vh;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.messages {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 16px;
}

.user {
  text-align: right;
  background: #dbeafe;
  margin: 8px 0;
  padding: 8px;
  border-radius: 8px;
}

.bot {
  text-align: left;
  background: #e5e7eb;
  margin: 8px 0;
  padding: 8px;
  border-radius: 8px;
}

.input-area {
  display: flex;
  gap: 8px;
}

.input-full {
  flex: 1;
}
```

---

## 4️⃣ `src/app/app.module.ts`

```typescript
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';

import { AppComponent } from './app.component';

@NgModule({
  declarations: [AppComponent],
  imports: [
    BrowserModule,
    HttpClientModule,
    FormsModule,
    BrowserAnimationsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCardModule
  ],
  bootstrap: [AppComponent]
})
export class AppModule {}
```

---

## ⚡️ Lancement

### 1️⃣ Démarre ton **API FastAPI**

```bash
uvicorn app.main:app --reload --port 8000
```

### 2️⃣ Lance ton **Angular frontend**

```bash
ng serve --port 4200
```

Puis ouvre :
👉 [http://localhost:4200](http://localhost:4200)

---

Souhaites-tu que je t’ajoute maintenant :

* ✅ la **version avec mémoire conversationnelle (LangChain Memory)**
* ✅ un **mode sombre** dans le front Angular ?
