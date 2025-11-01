Excellent 👌 — ton besoin est désormais **très clair** :

## Tu veux séparer **deux logiques distinctes** :

### 🧠 1️⃣ RAG = Chatbot analytique simple

* ❌ Ne touche **pas à la base Mongo**
* ✅ Travaille uniquement sur la base vectorielle (Chroma)
* ✅ Sert à interroger ton historique (1 an d’embeddings déjà indexés)
* ✅ Permet à l’utilisateur d’écrire :

  * “Quels sont les flows SQL les plus instables ?”
  * “Which VMware jobs failed repeatedly this month?”
  * “Analyse les erreurs Oracle Apex”
* ✅ Gère automatiquement la langue (fr/en)
* ✅ Renvoie un texte intelligent (pas de DataFrame, pas de stats internes)

---

### 📊 2️⃣ Rapport quotidien = Job automatisé (backend)

* ✅ S’exécute 1x par jour (cron ou task)
* ✅ Va chercher les **jobs échoués des dernières 24h** dans Mongo
* ✅ Produit un **fichier Excel** avec :

  * toutes les colonnes demandées (`DATE, FLOW, TASK, JOB_ID, SUB_ID, ORIGIN, FAILURE_REASON, WHAT_TO_DO, IS_SIMPLE_FIX, TOWER_URL`)
  * une **section en bas** avec une **analyse générée par le RAG** basée sur l’historique vectoriel (analyse synthétique)
* ✅ Peut être envoyé par mail (plus tard si tu veux l’intégrer)

---

Je te donne **le code complet**, propre et organisé, prêt à déployer.

---

## 📁 Structure finale

```
app/
├── config.py
├── embedder.py
├── vector_store.py
├── litellm_client.py
├── rag.py                # ✅ Chatbot simple basé sur embeddings
├── daily_report.py       # ✅ Job automatique pour le rapport Excel
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

# LLM
LITELLM_MODEL = os.getenv("LITELLM_MODEL", "mistral:latest")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", "")
```

---

## 💾 `app/vector_store.py`

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

def get_vanish_collection():
    return chroma_client.get_or_create_collection(
        name="mongo_vanish_flows",
        metadata={"description": "Index vectoriel des flux vanish"},
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

## 🤖 `app/litellm_client.py`

```python
import litellm
import config

def generate_with_litellm(messages: list[dict]) -> str:
    response = litellm.completion(
        model=config.LITELLM_MODEL,
        messages=messages,
        api_key=config.LITELLM_API_KEY,
        temperature=0.3,
    )
    return response["choices"][0]["message"]["content"].strip()
```

---

## 💬 `app/rag.py` — **Chatbot intelligent générique**

> 🔹 Ne lit **pas Mongo**
> 🔹 Utilise uniquement la base vectorielle (embedding historique)
> 🔹 Répond dynamiquement selon la langue du prompt

```python
from datetime import datetime
import re
from embedder import embed_texts
from vector_store import get_vanish_collection
from litellm_client import generate_with_litellm


def detect_language(text: str) -> str:
    text_lower = text.lower()
    fr_score = len(re.findall(r"\b(le|la|les|est|erreur|flux|analyse|problème|cause|action)\b", text_lower))
    en_score = len(re.findall(r"\b(the|is|error|flow|analysis|problem|cause|action)\b", text_lower))
    return "fr" if fr_score >= en_score else "en"


def answer_query(query: str, top_k: int = 8):
    lang = detect_language(query)
    q_emb = embed_texts([query])[0]
    col = get_vanish_collection()
    res = col.query(query_embeddings=[q_emb], n_results=top_k)

    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]

    if not docs:
        return {"answer": "Aucun résultat pertinent trouvé." if lang == "fr" else "No relevant results found."}

    context_text = "\n---\n".join([docs[i] for i in range(min(len(docs), 5))])

    if lang == "fr":
        system_prompt = (
            "Tu es un assistant d'analyse des flux Vanish. "
            "Interprète les anomalies et fournis une réponse analytique et structurée en français."
        )
        user_prompt = f"Voici le contexte :\n{context_text}\n\nQuestion : {query}\n"
    else:
        system_prompt = (
            "You are an analytical assistant specialized in Vanish Flows. "
            "Interpret anomalies and provide a structured, English answer."
        )
        user_prompt = f"Context:\n{context_text}\n\nQuestion:\n{query}\n"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    answer = generate_with_litellm(messages)
    return {
        "answer": answer,
        "contexts": [{"content": docs[i], "meta": metas[i]} for i in range(len(docs))],
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    result = answer_query("Analyse les erreurs SQL les plus fréquentes.")
    print(result["answer"])
```

---

## 📊 `app/daily_report.py` — **Job quotidien avec Excel**

> 🔹 Se connecte à Mongo
> 🔹 Récupère les jobs `FAILED` des dernières 24h
> 🔹 Crée un fichier `.xlsx` clair
> 🔹 En bas de l’Excel → résumé analytique généré via RAG

```python
from datetime import datetime, timedelta
from pymongo import MongoClient
import pandas as pd
from rag import answer_query
import config

def fetch_failed_jobs_last_24h():
    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    col = db["vanish_flows"]

    now = datetime.utcnow()
    start = now - timedelta(hours=24)

    query = {
        "DATE": {"$gte": start.strftime("%Y-%m-%d"), "$lte": now.strftime("%Y-%m-%d")},
        "$or": [{"STATUS": "FAILED"}, {"FAILURE REASON": {"$ne": None}}],
    }

    docs = list(col.find(query))
    if not docs:
        return pd.DataFrame()

    records = []
    for d in docs:
        records.append({
            "DATE": d.get("DATE"),
            "FLOW": d.get("FLOW"),
            "TASK": d.get("TASK"),
            "JOB_ID": d.get("JOB_ID"),
            "SUB_ID": d.get("SUB_ID"),
            "ORIGIN": d.get("ORIGIN") or d.get("SOURCE"),
            "FAILURE_REASON": d.get("FAILURE REASON"),
            "WHAT_TO_DO": d.get("WHAT TO DO?"),
            "IS_SIMPLE_FIX": "✅" if d.get("WHAT TO DO?") and "restart" in str(d.get("WHAT TO DO?")).lower() else "❌",
            "TOWER_URL": d.get("TOWER_URL") or d.get("URL"),
        })

    df = pd.DataFrame(records)
    df.sort_values(by="DATE", ascending=False, inplace=True)
    return df


def generate_excel_report():
    df = fetch_failed_jobs_last_24h()
    if df.empty:
        print("Aucun job échoué dans les dernières 24h.")
        return

    # Générer résumé analytique via RAG
    summary_prompt = "Analyse les tendances et causes principales des jobs échoués récents."
    rag_result = answer_query(summary_prompt)
    summary_text = rag_result["answer"]

    # Ajout d'une feuille “Summary” en bas
    output_path = f"rapport_flows_{datetime.now().strftime('%Y%m%d')}.xlsx"
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Failed Jobs")
        summary_df = pd.DataFrame({"Synthèse RAG": [summary_text]})
        summary_df.to_excel(writer, index=False, sheet_name="Résumé")

    print(f"✅ Rapport généré : {output_path}")


if __name__ == "__main__":
    generate_excel_report()
```

---

## 🚀 Résumé

| Fichier                           | Rôle                                                     |
| --------------------------------- | -------------------------------------------------------- |
| `rag.py`                          | Chatbot intelligent sur la base vectorielle uniquement   |
| `daily_report.py`                 | Job automatique quotidien (Mongo → Excel + synthèse RAG) |
| `embedder.py` / `vector_store.py` | Infrastructure RAG                                       |
| `litellm_client.py`               | Interface LLM générique                                  |

---

Souhaites-tu que je t’ajoute aussi un **mini front web (React)** avec un chat interface propre pour `rag.py` (input → réponse + historique de conversation) ?
Je peux te le donner clé-en-main avec Tailwind et une API Flask.
