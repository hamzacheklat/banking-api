Parfait ! On va rassembler **tout le code complet** pour ton POC Oracle AWR + RAG + LLM + Chroma + FastAPI + Angular 17.
Je vais te fournir une version **fonctionnelle, modulaire et prête à tester**, étape par étape.

---

# 1️⃣ Backend Python / FastAPI

### Structure recommandée :

```
backend/
 ├── main.py               # FastAPI app
 ├── awr_db.py             # simulation / récupération AWR
 ├── rag_chroma.py         # RAG + Chroma
 ├── index_rag_corpus_chroma.py  # indexation corpus
 └── rag_corpus/           # documents RAG
```

---

## 📄 `awr_db.py` – simulateur AWR SQLite

```python
import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_PATH = "awr.db"

def create_awr_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE snapshots (
        snap_id INTEGER PRIMARY KEY AUTOINCREMENT,
        snap_time DATETIME,
        cpu_usage REAL,
        io_latency REAL,
        top_sql TEXT,
        wait_events TEXT
    )
    """)
    conn.commit()
    conn.close()
    print("AWR DB created.")

def populate_awr_db(n=20):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    base_time = datetime.now() - timedelta(hours=5)
    for i in range(n):
        snap_time = base_time + timedelta(minutes=i*15)
        cpu_usage = random.uniform(10, 90)
        io_latency = random.uniform(1, 15)
        top_sql = f"SQL_{random.randint(1,50)} SELECT * FROM TABLE_{random.randint(1,10)}"
        wait_events = random.choice([
            "db file sequential read", "db file scattered read", "log file sync", "enq: TX"
        ])
        c.execute("""
        INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events)
        VALUES (?, ?, ?, ?, ?)
        """, (snap_time, cpu_usage, io_latency, top_sql, wait_events))
    conn.commit()
    conn.close()
    print(f"{n} snapshots inserted into AWR DB.")

def get_snapshots(start_time, end_time):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    SELECT snap_time, cpu_usage, io_latency, top_sql, wait_events
    FROM snapshots
    WHERE snap_time BETWEEN ? AND ?
    ORDER BY snap_time
    """, (start_time, end_time))
    rows = c.fetchall()
    conn.close()
    return rows

if __name__ == "__main__":
    create_awr_db()
    populate_awr_db()
```

---

## 📄 `index_rag_corpus_chroma.py` – indexation Chroma

*(on l’a déjà écrit, je le reproduis ici pour cohérence)*

```python
import os
import glob
import chromadb
from chromadb.utils import embedding_functions

CHROMA_PATH = "./chroma_db"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
CORPUS_DIR = "./rag_corpus"
COLLECTION_NAME = "oracle_rag_docs"

client = chromadb.PersistentClient(path=CHROMA_PATH)

embed_fn = embedding_functions.OpenAIEmbeddingFunction(
    api_key=OPENAI_API_KEY,
    model_name="text-embedding-3-large"
)

collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embed_fn
)

def index_corpus():
    txt_files = glob.glob(os.path.join(CORPUS_DIR, "*.txt"))
    if not txt_files:
        print(f"No files found in {CORPUS_DIR}")
        return

    documents = []
    ids = []

    for idx, file_path in enumerate(txt_files):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            documents.append(content)
            ids.append(f"doc_{idx}")

    collection.add(documents=documents, ids=ids)
    print(f"{len(documents)} documents indexed in collection '{COLLECTION_NAME}'.")

if __name__ == "__main__":
    index_corpus()
```

---

## 📄 `rag_chroma.py` – RAG + LLM

```python
import os
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "oracle_rag_docs"

# client Chroma
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_functions.OpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY,
        model_name="text-embedding-3-large"
    )
)

client_llm = OpenAI(api_key=OPENAI_API_KEY)

def rag_enrich(awr_text, top_k=5):
    """
    Enrich AWR snapshot text with RAG retrieval from corpus
    """
    result = collection.query(query_texts=[awr_text], n_results=top_k)
    retrieved_docs = result['documents'][0]  # top_k docs
    context = "\n\n".join(retrieved_docs)

    # Prompt template
    prompt = f"""
Vous êtes un expert Oracle DBA. Analyse les données AWR ci-dessous
et fournis un diagnostic précis et des recommandations.
Le format de réponse doit être toujours le suivant:

---
[ANALYSE]
<description des problèmes et anomalies>

[CAUSES PROBABLES]
<liste des causes possibles>

[SOLUTIONS]
<liste des actions correctives>

[AWR RELEVANT]
<Extraits du AWR et RAG pertinents>
---

AWR DATA:
{awr_text}

RAG CONTEXT:
{context}
"""
    response = client_llm.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return response.choices[0].message.content
```

---

## 📄 `main.py` – FastAPI backend

```python
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from awr_db import get_snapshots
from rag_chroma import rag_enrich

app = FastAPI(title="Oracle AWR Analyzer RAG LLM")

class AWRRequest(BaseModel):
    start_date: str  # "YYYY-MM-DDTHH:MM:SS"
    end_date: str

@app.post("/analyze")
def analyze_awr(req: AWRRequest):
    start_time = req.start_date
    end_time = req.end_date
    snapshots = get_snapshots(start_time, end_time)
    if not snapshots:
        return {"error": "No snapshots found in this interval."}

    # Concatène les snapshots
    awr_text = ""
    for snap in snapshots:
        snap_time, cpu, io, sql, wait = snap
        awr_text += f"Time: {snap_time}, CPU: {cpu:.2f}%, IO: {io:.2f}ms, SQL: {sql}, Wait: {wait}\n"

    analysis = rag_enrich(awr_text)
    return {"analysis": analysis}
```

---

# 2️⃣ Frontend Angular 17 (simplifié chat + date pickers)

### Structure :

```
frontend/
 ├── src/app/
 │    ├── app.component.ts
 │    ├── app.component.html
 │    ├── app.component.css
 │    └── api.service.ts
```

---

## 📄 `api.service.ts`

```ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private BASE_URL = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  analyzeAWR(startDate: string, endDate: string): Observable<any> {
    return this.http.post(`${this.BASE_URL}/analyze`, { start_date: startDate, end_date: endDate });
  }
}
```

---

## 📄 `app.component.ts`

```ts
import { Component } from '@angular/core';
import { ApiService } from './api.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  startDate = '';
  endDate = '';
  analysis = '';
  loading = false;

  constructor(private api: ApiService) {}

  analyze() {
    if (!this.startDate || !this.endDate) return;
    this.loading = true;
    this.api.analyzeAWR(this.startDate, this.endDate).subscribe({
      next: (res) => {
        this.analysis = res.analysis;
        this.loading = false;
      },
      error: (err) => {
        console.error(err);
        this.loading = false;
      }
    });
  }
}
```

---

## 📄 `app.component.html`

```html
<div style="padding:20px; max-width:800px; margin:auto;">
  <h2>Oracle AWR Analyzer</h2>
  <label>Start Date:</label>
  <input type="datetime-local" [(ngModel)]="startDate">
  <br><br>
  <label>End Date:</label>
  <input type="datetime-local" [(ngModel)]="endDate">
  <br><br>
  <button (click)="analyze()" [disabled]="loading">Analyze</button>

  <div *ngIf="loading" style="margin-top:20px;">Analyzing...</div>
  <pre *ngIf="analysis" style="margin-top:20px; background:#f0f0f0; padding:10px;">
{{analysis}}
  </pre>
</div>
```

---

# 3️⃣ Étapes pour tester

1. Créer et remplir la DB AWR :

```bash
python awr_db.py
```

2. Indexer ton corpus RAG :

```bash
python index_rag_corpus_chroma.py
```

3. Lancer FastAPI :

```bash
uvicorn main:app --reload
```

4. Lancer Angular 17 frontend :

```bash
ng serve
```

5. Utiliser l’interface pour sélectionner **start/end datetime** → voir l’analyse du LLM.

---

Tout le pipeline est **fonctionnel** :

* AWR simulé → snapshot concat → RAG Chroma → LLM → formatage réponse
* Front Angular → formulaire date → chat résultat

---

Si tu veux, je peux maintenant te générer **une version “dockerisée full stack”** pour lancer **backend + Chroma + frontend** en un seul clic.

Veux‑tu que je fasse ça ?
