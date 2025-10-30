Excellent ✅ — c’est une **amélioration très intelligente et naturelle** pour un RAG de production.
On va donc faire en sorte que le modèle **s’adapte automatiquement à la langue de la question** :

* si la question est en français → réponse en français,
* si la question est en anglais → réponse en anglais.

Cela se fera via une petite **détection linguistique légère** dans `rag.py` avant la génération du prompt.
Je te montre ci-dessous la version finale **améliorée et complète de `app/rag.py`**, avec cette logique intégrée proprement 👇

---

## 🧠 `app/rag.py` (version finale, contextualisée + multilingue auto)

```python
# app/rag.py
from datetime import datetime
from typing import List, Dict, Any, Optional
from embedder import embed_texts
from vector_store import get_vanish_collection
from litellm_client import generate_with_litellm  # module à part
import re


def detect_language(text: str) -> str:
    """
    Détection très simple de la langue (français ou anglais) selon les mots.
    """
    text_lower = text.lower()
    fr_score = len(re.findall(r"\b(le|la|les|est|erreur|flux|analyse|problème|cause|action)\b", text_lower))
    en_score = len(re.findall(r"\b(the|is|error|flow|analysis|problem|cause|action)\b", text_lower))
    return "fr" if fr_score >= en_score else "en"


def _build_system_prompt(date_str: str, lang: str) -> str:
    """
    Prompt système : rôle + contexte + date du jour, adapté à la langue détectée.
    """
    if lang == "fr":
        return (
            "Tu es un assistant expert en supervision et analyse des pipelines batch (Vanish Flows). "
            "Tu aides les équipes opérationnelles à diagnostiquer les échecs de jobs (SQL, Oracle, Postgres, "
            "VMWare, APEX, etc.), proposer des causes probables et des actions concrètes.\n\n"
            f"Date d'analyse : {date_str}\n"
            "Réponds en français, structuré avec : Erreurs récurrentes, Causes probables, Actions recommandées, Synthèse."
        )
    else:
        return (
            "You are an expert assistant specialized in analyzing batch pipelines (Vanish Flows). "
            "You help operations teams diagnose failed jobs (SQL, Oracle, Postgres, VMWare, APEX, etc.), "
            "identify likely causes and propose concrete corrective actions.\n\n"
            f"Analysis date: {date_str}\n"
            "Respond in English, structured with: Recurrent Errors, Probable Causes, Recommended Actions, Summary."
        )


def _build_user_prompt(query: str, contexts: List[Dict[str, Any]], date_str: str, lang: str) -> str:
    """
    Prompt utilisateur enrichi avec la date, les contextes et les consignes selon la langue.
    """
    context_blocks = []
    for i, ctx in enumerate(contexts):
        doc = ctx.get("document", "")
        meta = ctx.get("meta", {})
        id_info = meta.get("_id", "")
        context_blocks.append(f"[Context #{i+1} — _id: {id_info}]\n{doc}")

    joined_context = "\n\n---\n\n".join(context_blocks) if context_blocks else "No additional context available."

    if lang == "fr":
        return (
            f"Contrainte : date du rapport = {date_str}\n\n"
            f"QUESTION:\n{query}\n\n"
            f"CONTEXTES:\n{joined_context}\n\n"
            "Tâche :\n"
            "1️⃣ Liste les erreurs récurrentes observées.\n"
            "2️⃣ Indique les causes probables (réseau, permission, configuration...).\n"
            "3️⃣ Propose des actions concrètes et qui contacter.\n"
            "4️⃣ Termine par une synthèse concise.\n"
            "Réponds exclusivement en français."
        )
    else:
        return (
            f"Constraint: report date = {date_str}\n\n"
            f"QUESTION:\n{query}\n\n"
            f"CONTEXTS:\n{joined_context}\n\n"
            "Task:\n"
            "1️⃣ List recurrent errors observed.\n"
            "2️⃣ Explain probable causes (network, permission, config...).\n"
            "3️⃣ Suggest concrete actions and who should handle them.\n"
            "4️⃣ End with a concise summary.\n"
            "Answer strictly in English."
        )


def _format_chroma_result(res: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Transforme la réponse Chroma en une liste ordonnée de contextes { 'document': str, 'meta': {...} }.
    """
    contexts = []
    try:
        docs = res["documents"][0] if isinstance(res["documents"][0], list) else res["documents"]
        metas = res["metadatas"][0] if isinstance(res["metadatas"][0], list) else res["metadatas"]
    except Exception:
        docs = res.get("documents", [])
        metas = res.get("metadatas", [])

    for i in range(min(len(docs), len(metas))):
        contexts.append({"document": docs[i], "meta": metas[i]})
    return contexts


def answer_query(query: str, top_k: int = 8, date_str: Optional[str] = None) -> Dict[str, Any]:
    """
    RAG complet :
    - Détection de la langue du query
    - Recherche vectorielle Chroma
    - Génération contextualisée via LLM
    """
    if not date_str:
        date_str = datetime.utcnow().strftime("%d/%m/%Y")

    lang = detect_language(query)
    col = get_vanish_collection()
    q_emb = embed_texts([query])[0]

    try:
        res = col.query(query_embeddings=[q_emb], n_results=top_k)
    except Exception as e:
        msg = f"Index vectoriel indisponible : {e}"
        print(msg)
        res = {"documents": [[]], "metadatas": [[]]}

    contexts = _format_chroma_result(res)

    system_prompt = _build_system_prompt(date_str, lang)
    user_prompt = _build_user_prompt(query, contexts, date_str, lang)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    answer_text = generate_with_litellm(messages)

    return {
        "answer": answer_text,
        "contexts": contexts,
        "query": query,
        "lang": lang,
        "date": date_str,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Test rapide (tu peux lancer ce fichier directement)
if __name__ == "__main__":
    print("=== TEST FR ===")
    out_fr = answer_query("Analyse les erreurs critiques du jour et propose des actions.")
    print(out_fr["answer"], "\n")

    print("=== TEST EN ===")
    out_en = answer_query("Analyze today's failed flows and propose corrective actions.")
    print(out_en["answer"])
```

---

### 🧩 Points clés

| Fonction                 | Rôle                                               |
| ------------------------ | -------------------------------------------------- |
| `detect_language()`      | Détecte automatiquement la langue du prompt        |
| `_build_system_prompt()` | Définit le rôle et les règles selon la langue      |
| `_build_user_prompt()`   | Construit un prompt détaillé avec date et contexte |
| `answer_query()`         | Orchestration complète du RAG                      |

* Le prompt **ne force plus une seule langue**, mais s’adapte naturellement.
* Si tu poses une question en anglais, tout le raisonnement et la sortie se feront en anglais.
* Les contextes Chroma restent identiques (car ils sont neutres).

---

Souhaites-tu que je t’ajoute maintenant la version de `litellm_client.py` qui fonctionne directement avec ce RAG (gestion du modèle, API key, logs, timeouts, etc.) ?
Ça te permettrait d’avoir le pipeline complet RAG → analyse → rapport.
