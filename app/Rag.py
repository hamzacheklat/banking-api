# app/rag.py
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import Counter
from pymongo import MongoClient
from embedder import embed_texts
from vector_store import get_vanish_collection
from litellm_client import generate_with_litellm
import re
import config


# ------------------------------
# 🔤 Langue & contexte
# ------------------------------

def detect_language(text: str) -> str:
    """
    Détection simple de la langue (français ou anglais) selon les mots clés.
    """
    text_lower = text.lower()
    fr_score = len(re.findall(r"\b(le|la|les|est|erreur|flux|analyse|problème|cause|action)\b", text_lower))
    en_score = len(re.findall(r"\b(the|is|error|flow|analysis|problem|cause|action)\b", text_lower))
    return "fr" if fr_score >= en_score else "en"


def _build_system_prompt(date_range: str, lang: str) -> str:
    """
    Prompt système enrichi avec contexte temporel.
    """
    if lang == "fr":
        return (
            "Tu es un assistant expert en supervision et analyse des flux batch (Vanish Flows). "
            "Tu aides à diagnostiquer les échecs récurrents et à proposer des actions correctives. "
            f"Analyse les données de la période : {date_range}. "
            "Réponds en français, structuré avec : Erreurs récurrentes, Causes probables, Actions recommandées, Synthèse."
        )
    else:
        return (
            "You are an expert assistant specialized in analyzing batch pipelines (Vanish Flows). "
            "You help identify recurring failures and propose corrective actions. "
            f"Analyze data for the period: {date_range}. "
            "Respond in English, structured with: Recurrent Errors, Probable Causes, Recommended Actions, Summary."
        )


# ------------------------------
# 📊 Construction du contexte Mongo
# ------------------------------

def fetch_failed_jobs(start_date: str, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Récupère les jobs échoués entre deux dates dans Mongo vanish_flows.
    """
    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    col = db["vanish_flows"]

    # Normalisation des dates
    if not end_date:
        end_date = start_date

    query = {
        "DATE": {"$gte": start_date, "$lte": end_date},
        "$or": [
            {"STATUS": "FAILED"},
            {"FAILURE REASON": {"$ne": None}}
        ]
    }

    return list(col.find(query))


def build_context_from_flows(flow_docs: List[Dict[str, Any]]) -> str:
    """
    Construit le contexte textuel enrichi pour le RAG :
    - Détail de chaque job échoué
    - Statistiques agrégées par FLOW, TASK, FAILURE
    """
    if not flow_docs:
        return "Aucun job échoué pour cette période."

    # 1️⃣ Détails ligne à ligne
    lines = [
        f"FLOW: {d.get('FLOW', '')}\n"
        f"TASK: {d.get('TASK', '')}\n"
        f"JOB_ID: {d.get('JOB_ID', '')}\n"
        f"FAILURE: {d.get('FAILURE REASON', '')}\n"
        f"ACTION: {d.get('WHAT TO DO?', '')}\n"
        for d in flow_docs
    ]

    # 2️⃣ Statistiques agrégées
    flow_counts = Counter([d.get("FLOW") for d in flow_docs if d.get("FLOW")])
    task_counts = Counter([d.get("TASK") for d in flow_docs if d.get("TASK")])
    failure_counts = Counter([d.get("FAILURE REASON") for d in flow_docs if d.get("FAILURE REASON")])

    stats = [
        "📊 Statistiques globales :",
        f"- Total jobs en échec : {len(flow_docs)}",
        "- Top 5 FLOW les plus en erreur : " + ", ".join([f"{k} ({v})" for k, v in flow_counts.most_common(5)]),
        "- Top 5 TASK les plus en erreur : " + ", ".join([f"{k} ({v})" for k, v in task_counts.most_common(5)]),
        "- Top 5 causes fréquentes : " + ", ".join([f"{k} ({v})" for k, v in failure_counts.most_common(5)]),
    ]

    return "\n".join(stats) + "\n\n---\n\n" + "\n".join(lines)


# ------------------------------
# 🧠 RAG principal
# ------------------------------

def answer_query_with_date(
    query: str,
    start_date: str,
    end_date: Optional[str] = None,
    top_k: int = 8
) -> Dict[str, Any]:
    """
    RAG complet avec génération de contexte Mongo enrichi.
    """
    if not end_date:
        end_date = start_date

    lang = detect_language(query)
    date_range = f"{start_date} → {end_date}"

    # 1️⃣ Récupération des jobs échoués
    flows = fetch_failed_jobs(start_date, end_date)
    context_text = build_context_from_flows(flows)

    # 2️⃣ Recherche vectorielle complémentaire dans Chroma
    q_emb = embed_texts([query])[0]
    col = get_vanish_collection()
    res = col.query(query_embeddings=[q_emb], n_results=top_k)
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    chroma_context = "\n\n---\n\n".join([
        f"[Chroma Context #{i+1}] {docs[i]}" for i in range(min(len(docs), 3))
    ])

    # 3️⃣ Construction du prompt complet
    system_prompt = _build_system_prompt(date_range, lang)
    if lang == "fr":
        user_prompt = (
            f"Voici les logs des jobs échoués pour la période {date_range} :\n\n"
            f"{context_text}\n\n---\n\n"
            f"Informations additionnelles depuis la base vectorielle :\n{chroma_context}\n\n"
            f"Question : {query}\n"
            "Analyse ces informations et produis une réponse complète et structurée."
        )
    else:
        user_prompt = (
            f"Here are the failed jobs logs for the period {date_range}:\n\n"
            f"{context_text}\n\n---\n\n"
            f"Additional context from the vector database:\n{chroma_context}\n\n"
            f"Question: {query}\n"
            "Analyze the information and provide a structured, complete answer."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # 4️⃣ Génération finale
    answer_text = generate_with_litellm(messages)

    return {
        "answer": answer_text,
        "stats": {
            "total_failed": len(flows),
            "flows": Counter([d.get("FLOW") for d in flows if d.get("FLOW")]),
            "tasks": Counter([d.get("TASK") for d in flows if d.get("TASK")]),
            "failures": Counter([d.get("FAILURE REASON") for d in flows if d.get("FAILURE REASON")]),
        },
        "query": query,
        "lang": lang,
        "date_range": date_range,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ------------------------------
# 🧪 Exemple d’utilisation
# ------------------------------
if __name__ == "__main__":
    result = answer_query_with_date(
        query="Analyse les erreurs critiques et les causes principales pour la journée.",
        start_date="2025-10-30"
    )
    print("=== RÉPONSE RAG ===")
    print(result["answer"])
    print("\n=== STATS ===")
    for k, v in result["stats"].items():
        print(k, ":", v)
