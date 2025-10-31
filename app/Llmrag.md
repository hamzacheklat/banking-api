Parfait — tu veux **supprimer l’accès direct à Mongo** et **tout reposer sur le LLM + ChromaDB** pour générer **la table des jobs failed** et les **statistiques**. Ça veut dire :

* on utilise l’embedding de la question pour récupérer les documents pertinents dans Chroma (historique),
* on fournit ces documents au LLM (prompt structuré),
* on demande explicitement au LLM de **retourner un JSON structuré** contenant :

  * `table`: liste d’objets `{DATE, FLOW, TASK, JOB_ID, SUB_ID, FAILURE_REASON, ORIGIN, WHAT_TO_DO, TOWER_URL, ...}`,
  * `stats`: totaux + topN flows/tasks/causes,
  * `answer`: texte synthétique (analyse + recommandations).
* on parse la réponse JSON et on renvoie un dict utilisable par ton front (table déjà serialisable en JSON).

Je te fournis une version complète de `app/rag.py` qui fait exactement ça. Elle suppose que :

* `embed_texts()` existe et renvoie embeddings (comme dans tes versions précédentes),
* `get_vanish_collection()` renvoie un objet Chroma compatible avec `.query(query_embeddings=[...], n_results=...)` qui renvoie `documents` et `metadatas`,
* `generate_with_litellm(messages)` appelle le LLM (litellm) et renvoie une string (ici on demande explicitement JSON).
* Tu veux continuer à fournir `top_k` docs depuis Chroma.

---

### ✅ `app/rag.py` (LLM + Chroma only — génère `table` et `stats` via le modèle)

```python
# app/rag.py
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import json
import re

from embedder import embed_texts
from vector_store import get_vanish_collection
from litellm_client import generate_with_litellm
import config


# ------------------------------
# Helpers
# ------------------------------
def detect_language(text: str) -> str:
    text_lower = (text or "").lower()
    fr_score = len(re.findall(r"\b(le|la|les|est|erreur|flux|analyse|problème|cause|action)\b", text_lower))
    en_score = len(re.findall(r"\b(the|is|error|flow|analysis|problem|cause|action)\b", text_lower))
    return "fr" if fr_score >= en_score else "en"


def _extract_json(text: str) -> Optional[str]:
    """
    Try to extract the largest JSON object substring from text.
    """
    # try direct load first
    try:
        json.loads(text)
        return text
    except Exception:
        pass

    # find the first { and last } that form valid json
    starts = [m.start() for m in re.finditer(r'\{', text)]
    ends = [m.start() for m in re.finditer(r'\}', text)]
    if not starts or not ends:
        return None

    # attempt various candidate spans (greedy)
    for i in range(len(starts)):
        for j in range(len(ends)-1, -1, -1):
            if ends[j] <= starts[i]:
                continue
            candidate = text[starts[i]:ends[j]+1]
            try:
                json.loads(candidate)
                return candidate
            except Exception:
                continue
    return None


def safe_parse_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Try to parse JSON returned by the LLM. Returns dict or None.
    """
    if not text:
        return None
    # direct
    try:
        return json.loads(text)
    except Exception:
        pass
    # try to extract
    js = _extract_json(text)
    if not js:
        return None
    try:
        return json.loads(js)
    except Exception:
        return None


# ------------------------------
# Chroma retrieval
# ------------------------------
def retrieve_chroma_docs_for_query(query: str, top_k: int = 8) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Returns (documents, metadatas) for top_k results from Chroma.
    documents: list of text strings (document content)
    metadatas: list of corresponding metadata dicts
    """
    q_emb = embed_texts([query])[0]
    col = get_vanish_collection()
    res = col.query(query_embeddings=[q_emb], n_results=top_k)
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    # ensure same length
    docs = docs[: len(metas)]
    return docs, metas


# ------------------------------
# Prompt builder
# ------------------------------
def build_llm_prompt(query: str, docs: List[str], metas: List[Dict[str, Any]], date_range: str, lang: str) -> List[Dict[str, str]]:
    """
    Build messages for the LLM. We include raw docs + their metadatas,
    and a strict instruction asking for JSON output with schema.
    """
    # compact doc summary block (limit chars per doc)
    def compact(i, d, m):
        header = f"[Doc #{i+1}]"
        meta_str = " ".join([f"{k}={v}" for k, v in (m or {}).items()])
        content = (d or "")[:3500]  # safety limit
        return f"{header}\nMETA: {meta_str}\nCONTENT:\n{content}\n"

    docs_block = "\n\n".join([compact(i, docs[i], metas[i] if i < len(metas) else {}) for i in range(len(docs))])

    if lang == "fr":
        system = (
            "Tu es un assistant expert en analyse d'incidents de flows. "
            "On te fournit des extraits historiques (documents vectoriels) et une question. "
            "Ta tâche : synthétiser une TABLE des jobs 'failed' et des STATISTIQUES à partir des documents fournis, "
            "puis produire une ANALYSE (causes probables, actions recommandées)."
        )
        user = (
            f"Période ciblée : {date_range}\n\n"
            f"Documents pertinents (extraits vectoriels) :\n{docs_block}\n\n"
            "Produis **uniquement** un JSON valide (aucun commentaire hors JSON) avec la shape suivante :\n\n"
            "{\n"
            '  "table": [\n'
            "    {\"DATE\": \"YYYY-MM-DD\", \"FLOW\": \"...\", \"TASK\": \"...\", \"JOB_ID\": \"...\", \"SUB_ID\": \"...\", \"FAILURE_REASON\": \"...\", \"ORIGIN\": \"...\", \"WHAT_TO_DO\": \"...\", \"TOWER_URL\": \"...\"},\n"
            "    ...\n"
            "  ],\n"
            '  "stats": {\n'
            '    "total_failed": int,\n'
            '    "top_flows": [[\"FLOW_NAME\", count], ...],\n'
            '    "top_tasks": [[\"TASK_NAME\", count], ...],\n'
            '    "top_failures": [[\"FAILURE_REASON\", count], ...]\n'
            "  },\n"
            '  "answer": "Texte d\\u00e9taill\\u00e9 (analyse + recommandations)\"\n'
            "}\n\n"
            "Règles strictes :\n"
            "- Respecte exactement le JSON (pas de markdown, pas d'explications en dehors du JSON).\n"
            "- Si une valeur manque, mets une chaîne vide ou null pour respecter le schéma.\n"
            "- Table maximum 200 lignes (préférence : lignes les plus pertinentes)."
            f"\nQuestion: {query}"
        )
    else:
        system = (
            "You are an expert incident analysis assistant for batch flows. "
            "You will receive vector-retrieved documents and a question. "
            "Your task: build a TABLE of failed jobs and STATISTICS from the provided documents, "
            "and deliver an ANALYSIS (root causes, recommended actions)."
        )
        user = (
            f"Target period: {date_range}\n\n"
            f"Relevant documents (vector search results):\n{docs_block}\n\n"
            "Produce **only** a valid JSON with the following schema:\n\n"
            "{\n"
            '  "table": [\n'
            "    {\"DATE\": \"YYYY-MM-DD\", \"FLOW\": \"...\", \"TASK\": \"...\", \"JOB_ID\": \"...\", \"SUB_ID\": \"...\", \"FAILURE_REASON\": \"...\", \"ORIGIN\": \"...\", \"WHAT_TO_DO\": \"...\", \"TOWER_URL\": \"...\"},\n"
            "    ...\n"
            "  ],\n"
            '  "stats": {\n'
            '    "total_failed": int,\n'
            '    "top_flows": [[\"FLOW_NAME\", count], ...],\n'
            '    "top_tasks": [[\"TASK_NAME\", count], ...],\n'
            '    "top_failures": [[\"FAILURE_REASON\", count], ...]\n'
            "  },\n"
            '  "answer": "Analytical text (causes + recommendations)\"\n'
            "}\n\n"
            "Rules:\n"
            "- Return exactly one JSON object, nothing else.\n"
            "- If info is missing, use empty strings or nulls.\n"
            "- Limit table to 200 rows (prefer the most relevant).\n"
            f"\nQuestion: {query}"
        )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


# ------------------------------
# Main function (LLM + Chroma)
# ------------------------------
def answer_query_chroma_only(
    query: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    top_k: int = 12
) -> Dict[str, Any]:
    """
    Perform RAG using only vector DB + LLM:
      - retrieve top_k docs from Chroma (by embedding of query)
      - ask LLM to construct table + stats + analysis as JSON
      - parse and return structured data
    """
    date_range = f"{start_date or 'N/A'} → {end_date or start_date or 'N/A'}"
    lang = detect_language(query)

    # 1) retrieve from Chroma
    docs, metas = retrieve_chroma_docs_for_query(query, top_k=top_k)

    # 2) build prompt and call LLM
    messages = build_llm_prompt(query, docs, metas, date_range, lang)
    llm_raw = generate_with_litellm(messages)

    # 3) try to parse JSON from LLM
    parsed = safe_parse_json(llm_raw)

    # 4) fallback: if parse failed, attempt to ask the model again to output pure JSON (refine)
    if parsed is None:
        # minimal retry prompt asking to return only JSON
        retry_messages = [
            {"role": "system", "content": messages[0]["content"]},
            {"role": "user", "content": "The previous answer was invalid JSON. Please output ONLY a valid JSON object with the required schema (table, stats, answer)."}
        ]
        llm_retry = generate_with_litellm(retry_messages)
        parsed = safe_parse_json(llm_retry)
        # if still None, we'll return the raw text and empty table/stats as fallback

    # 5) normalize output
    result_table = []
    result_stats = {}
    result_answer = ""

    if parsed:
        result_table = parsed.get("table") or []
        result_stats = parsed.get("stats") or {}
        result_answer = parsed.get("answer") or ""
    else:
        # No JSON parsed: include raw text in 'answer' so front can display it
        result_answer = llm_raw or ""
        result_table = []
        result_stats = {}

    return {
        "answer": result_answer,
        "stats": result_stats,
        "table": result_table,          # list[dict] ready to json-serialize
        "raw_llm": llm_raw,             # raw llm content for debugging
        "chroma_docs": docs,
        "chroma_metas": metas,
        "query": query,
        "lang": lang,
        "date_range": date_range,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ------------------------------
# Example usage
# ------------------------------
if __name__ == "__main__":
    q = "Donne-moi la liste des jobs failed critiques et les causes récurrentes sur la semaine passée"
    out = answer_query_chroma_only(query=q, start_date="2025-10-20", end_date="2025-10-30", top_k=12)
    print("=== ANSWER ===")
    print(out["answer"][:1000])
    print("\n=== STATS ===")
    print(out["stats"])
    print("\n=== TABLE SAMPLE ===")
    print(out["table"][:5])
    print("\n=== RAW LLM (debug) ===")
    print(out["raw_llm"][:800])
```

---

### 🔎 Remarques importantes & recommandations

1. **Hallucinations** — quand tu demandes au LLM de *générer* des rows/table à partir de documents vectoriels, il peut **compléter** ou reécrire des champs.
   → **Toujours** marquer la réponse comme *proposition* et ajouter une validation (ex : vérifier `JOB_ID`/`DATE`/`FLOW` en base si possible) avant d’exploiter automatiquement les actions.

2. **Qualité des docs Chroma** — la pertinence des lignes produites dépendra fortement :

   * de la **qualité** des documents indexés (s’ils contiennent DATE/FLOW/TASK explicites),
   * du **top_k** que tu fournis (plus c’est grand, plus le LLM a de contexte, mais coût + risque d’incohérences).

3. **Contrainte JSON stricte** — on demande au LLM d’émettre **uniquement** du JSON. Malgré tout, on a mis un parser robuste (`safe_parse_json`) et une tentative de retry. Si tu veux zéro risque, tu peux :

   * demander au LLM de répondre en **formulaire CSV** que tu parsers toi-même,
   * ou demander un `table_html` prêt à afficher (moins structuré mais pratique).

4. **Performances** — pas de DB mais dépendance au vector DB + LLM appels. Pour builtin cron/reporting, considère mettre en cache les réponses pour un même `date_range` + `query`.

5. **Front** — ton front (le `chat.component.ts`/HTML que je t'ai envoyé précédemment) consomme un JSON avec `table` et `stats` : **compatible** — il suffit que ton backend renvoie exactement `table` comme liste d'objets. Si tu veux, je peux te fournir un endpoint FastAPI minimal qui appelle `answer_query_chroma_only()` et renvoie JSON.

---

Tu veux que je **génère aussi l’endpoint FastAPI** (ou Flask) qui expose `POST /api/rag/query` et renvoie ce JSON (avec option `top_k`, `start_date`, `end_date`) ? Ça me permettrait de te livrer la solution complète prête à brancher côté front.
