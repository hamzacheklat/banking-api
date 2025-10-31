Excellent 💪 — là on passe ton **RAG** dans une vraie **phase “data observability / auto-diagnostic intelligent”**.
Tu veux qu’il combine **analyse vectorielle (RAG)** + **analyse historique structurée**.
C’est exactement ce qu’il faut pour produire des **rapports d’incidents exploitables et consolidés**.

Voici ce qu’on va faire :

---

## 🎯 Objectif

Créer un **`rag.py` enrichi** qui :

1. 🔍 Analyse les *jobs failed* du **période demandée** (ou du jour).
2. 🧠 Utilise les embeddings historiques (1 an d’historique) pour retrouver les **patterns similaires**.
3. 📊 Produit un **tableau récapitulatif** de *tous les jobs failed* (avec :
   `DATE`, `FLOW`, `TASK`, `JOB_ID`, `SUB_ID`, `FAILURE REASON`, `ORIGIN`, `WHAT TO DO`, `TOWER_URL`, etc.).
4. 💬 Génère une **analyse intelligente** (via RAG) avec stats + recommandations.

---

## ⚙️ Nouvelle version complète : `app/rag.py`

> 🧩 Cette version lit Mongo + Chroma, calcule les stats globales, extrait les docs pertinents de l’historique et te retourne à la fois :
>
> * une **analyse RAG enrichie**
> * un **DataFrame Pandas prêt à être exporté en Excel ou PDF**

---

```python
# app/rag.py
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import Counter
from pymongo import MongoClient
import pandas as pd
from embedder import embed_texts
from vector_store import get_vanish_collection
from litellm_client import generate_with_litellm
import config
import re


# ------------------------------
# 🔤 Détection de langue
# ------------------------------
def detect_language(text: str) -> str:
    text_lower = text.lower()
    fr_score = len(re.findall(r"\b(le|la|les|est|erreur|flux|analyse|problème|cause|action)\b", text_lower))
    en_score = len(re.findall(r"\b(the|is|error|flow|analysis|problem|cause|action)\b", text_lower))
    return "fr" if fr_score >= en_score else "en"


# ------------------------------
# 🧩 Mongo : récupération des jobs échoués
# ------------------------------
def fetch_failed_jobs(start_date: str, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    col = db["vanish_flows"]

    if not end_date:
        end_date = start_date

    query = {
        "DATE": {"$gte": start_date, "$lte": end_date},
        "$or": [{"STATUS": "FAILED"}, {"FAILURE REASON": {"$ne": None}}],
    }

    return list(col.find(query))


# ------------------------------
# 📊 Tableau récapitulatif complet
# ------------------------------
def build_failed_jobs_table(flow_docs: List[Dict[str, Any]]) -> pd.DataFrame:
    if not flow_docs:
        return pd.DataFrame()

    records = []
    for d in flow_docs:
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
            "TOWER_URL": d.get("TOWER_URL") or d.get("URL") or "",
        })

    df = pd.DataFrame(records)

    # Tri par date descendante
    df.sort_values(by="DATE", ascending=False, inplace=True)
    return df


# ------------------------------
# 🧠 Construction du contexte RAG enrichi
# ------------------------------
def build_context(flow_docs: List[Dict[str, Any]]) -> str:
    if not flow_docs:
        return "Aucun job échoué pour cette période."

    # Détails des erreurs
    lines = [
        f"DATE: {d.get('DATE', '')}\n"
        f"FLOW: {d.get('FLOW', '')}\n"
        f"TASK: {d.get('TASK', '')}\n"
        f"JOB_ID: {d.get('JOB_ID', '')}\n"
        f"SUB_ID: {d.get('SUB_ID', '')}\n"
        f"ORIGIN: {d.get('ORIGIN', '') or d.get('SOURCE', '')}\n"
        f"FAILURE: {d.get('FAILURE REASON', '')}\n"
        f"WHAT_TO_DO: {d.get('WHAT TO DO?', '')}\n"
        f"TOWER_URL: {d.get('TOWER_URL', '') or d.get('URL', '')}\n"
        "----"
        for d in flow_docs
    ]

    # Statistiques globales
    flow_counts = Counter([d.get("FLOW") for d in flow_docs if d.get("FLOW")])
    failure_counts = Counter([d.get("FAILURE REASON") for d in flow_docs if d.get("FAILURE REASON")])
    origin_counts = Counter([d.get("ORIGIN") or d.get("SOURCE") for d in flow_docs if d.get("ORIGIN") or d.get("SOURCE")])

    stats = [
        f"📊 Total jobs en échec : {len(flow_docs)}",
        "🔁 Top 5 flows en erreur : " + ", ".join([f"{k} ({v})" for k, v in flow_counts.most_common(5)]),
        "💥 Top 5 causes fréquentes : " + ", ".join([f"{k} ({v})" for k, v in failure_counts.most_common(5)]),
        "🌍 Origines principales : " + ", ".join([f"{k} ({v})" for k, v in origin_counts.most_common(5)]),
    ]

    return "\n".join(stats) + "\n\n---\n\n" + "\n".join(lines)


# ------------------------------
# ⚙️ RAG complet
# ------------------------------
def answer_query_with_history(
    query: str,
    start_date: str,
    end_date: Optional[str] = None,
    top_k: int = 8
) -> Dict[str, Any]:
    """
    RAG enrichi :
      - Contexte Mongo (jobs failed)
      - Historique vectoriel (embeddings)
      - Tableau récapitulatif complet
      - Analyse multilingue automatique
    """
    if not end_date:
        end_date = start_date

    lang = detect_language(query)
    date_range = f"{start_date} → {end_date}"

    # 1️⃣ Mongo : extraction des jobs failed
    flows = fetch_failed_jobs(start_date, end_date)
    df_jobs = build_failed_jobs_table(flows)
    context_text = build_context(flows)

    # 2️⃣ Recherche vectorielle : patterns similaires dans l’historique
    q_emb = embed_texts([query])[0]
    col = get_vanish_collection()
    res = col.query(query_embeddings=[q_emb], n_results=top_k)
    docs = res.get("documents", [[]])[0]
    chroma_context = "\n\n---\n\n".join(docs[:3]) if docs else ""

    # 3️⃣ Construction du prompt
    if lang == "fr":
        system_prompt = (
            f"Tu es un assistant d'analyse des flux Vanish. "
            f"Ta tâche est d'analyser les erreurs survenues entre {date_range}, "
            f"en t'appuyant sur l'historique des embeddings (1 an de logs). "
            f"Réponds en français, structuré avec sections : Erreurs récurrentes, Causes, Actions, Synthèse."
        )
        user_prompt = (
            f"Voici les logs récents et les statistiques :\n{context_text}\n\n"
            f"---\n\nContexte historique trouvé dans la base vectorielle :\n{chroma_context}\n\n"
            f"Question : {query}\n"
            "Donne une réponse analytique et hiérarchisée, orientée supervision."
        )
    else:
        system_prompt = (
            f"You are an analytical assistant specialized in Vanish Flows. "
            f"Analyze all failed jobs between {date_range}, "
            f"using historical embeddings (1 year of logs). "
            f"Respond in English, with sections: Recurrent Errors, Causes, Actions, Summary."
        )
        user_prompt = (
            f"Here are the recent failed jobs and statistics:\n{context_text}\n\n"
            f"---\n\nHistorical context from vector DB:\n{chroma_context}\n\n"
            f"Question: {query}\n"
            "Provide a structured, analytical answer."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # 4️⃣ Génération
    answer_text = generate_with_litellm(messages)

    return {
        "answer": answer_text,
        "table": df_jobs,  # ✅ DataFrame prêt à être exporté
        "stats": {
            "total_failed": len(flows),
            "flows": Counter([d.get("FLOW") for d in flows if d.get("FLOW")]),
            "failures": Counter([d.get("FAILURE REASON") for d in flows if d.get("FAILURE REASON")]),
            "origins": Counter([d.get("ORIGIN") or d.get("SOURCE") for d in flows if d.get("ORIGIN") or d.get("SOURCE")]),
        },
        "query": query,
        "lang": lang,
        "date_range": date_range,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ------------------------------
# 🧪 Exemple d'utilisation
# ------------------------------
if __name__ == "__main__":
    result = answer_query_with_history(
        query="Analyse les jobs échoués SQL et VMWare de la semaine",
        start_date="2025-10-20",
        end_date="2025-10-30"
    )

    print("=== 🔍 ANALYSE RAG ===")
    print(result["answer"])

    print("\n=== 📊 STATS ===")
    for k, v in result["stats"].items():
        print(k, ":", v)

    print("\n=== 🧾 TABLEAU JOBS FAILD ===")
    print(result["table"].head())
```

---

## 🔎 Résultat

### 1️⃣ Sortie RAG

* Analyse textuelle intelligente
* Synthèse par catégories et historique

### 2️⃣ Tableau `pandas.DataFrame`

Contient toutes les colonnes utiles :

| DATE | FLOW | TASK | JOB_ID | SUB_ID | ORIGIN | FAILURE_REASON | WHAT_TO_DO | IS_SIMPLE_FIX | TOWER_URL |
| ---- | ---- | ---- | ------ | ------ | ------ | -------------- | ---------- | ------------- | --------- |

Tu pourras ensuite :

```python
result["table"].to_excel("rapport_flows_failed.xlsx", index=False)
```

ou

```python
result["table"].to_html("rapport_flows_failed.html", index=False)
```

---

Souhaites-tu que je te fasse la **version PDF automatique** du rapport avec :

* Le résumé RAG
* Le tableau complet
* Les stats agrégées
  👉 Prêt à être envoyé par mail tous les matins ?
