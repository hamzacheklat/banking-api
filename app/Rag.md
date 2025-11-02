Excellent 👏 — merci pour la précision, c’est **super important**.
Donc dans ta base, au lieu d’un champ `DATE`, tu as :

* `start_time` → moment où le job commence,
* `end_time` → moment où le job se termine.

C’est encore mieux, parce que ça te donne une **fenêtre temporelle précise** — parfaite pour un RAG “intelligent”.

---

## 🚀 Voici comment corriger et améliorer ton RAG & ton ingestion

### 🧩 Objectif

1. Ton ingestion doit indexer les champs `start_time` et `end_time` en clair.
2. Ton RAG doit comprendre que “aujourd’hui” = *compris entre 00:00 et 23:59 (UTC/local)*.
3. L’LLM doit utiliser ces informations temporelles **sans avoir besoin que tu tapes une date manuellement.**

---

## ✅ 1. Met à jour ton `json_to_text()` (dans `mongo_ingest.py`)

On veut que chaque document contienne une phrase temporelle **lisible et exploitable sémantiquement**.

```python
from datetime import datetime, timezone

def json_to_text(document: dict) -> str:
    ingestion_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    start_time = document.get("start_time", "")
    end_time = document.get("end_time", "")
    flow = document.get("FLOW", "")
    task = document.get("TASK", "")
    job_id = document.get("JOB_ID", "")
    sub_id = document.get("SUB_ID", "")
    status = document.get("STATUS", "")
    failure = document.get("FAILURE REASON", "")
    what_to_do = document.get("WHAT TO DO?", "")
    tower_url = document.get("TOWER_URL", "")

    text = (
        f"=== JOB EXECUTION RECORD ===\n"
        f"FLOW: {flow}\n"
        f"TASK: {task}\n"
        f"JOB_ID: {job_id}\n"
        f"SUB_ID: {sub_id}\n"
        f"STATUS: {status}\n"
        f"START_TIME: {start_time}\n"
        f"END_TIME: {end_time}\n"
        f"FAILURE_REASON: {failure}\n"
        f"WHAT_TO_DO: {what_to_do}\n"
        f"TOWER_URL: {tower_url}\n"
        f"INGESTION_DATE: {ingestion_date}\n"
        f"=============================\n"
    )

    return text
```

💡 Grâce à ça, ton embedding contiendra du texte comme :

> “START_TIME: 2025-11-02T03:25:10Z”
> “END_TIME: 2025-11-02T03:45:00Z”

Et donc le modèle pourra comprendre que ces jobs appartiennent “à aujourd’hui”.

---

## ✅ 2. Mets à jour les métadonnées (`batch_metas`)

Pour filtrer efficacement par date plus tard (dans Chroma), ajoute ceci :

```python
from datetime import datetime, timezone

batch_metas.append({
    "_id": doc_id,
    "FLOW": doc.get("FLOW", ""),
    "TASK": doc.get("TASK", ""),
    "JOB_ID": doc.get("JOB_ID", ""),
    "STATUS": doc.get("STATUS", ""),
    "START_TIME": str(doc.get("start_time", "")),
    "END_TIME": str(doc.get("end_time", "")),
    "INGESTION_TIMESTAMP": datetime.now(timezone.utc).isoformat()
})
```

👉 Si tes `start_time`/`end_time` sont des `datetime`, pense à les convertir en chaîne (`str()`) sinon Chroma plantera sur la sérialisation JSON.

---

## ✅ 3. Améliore ton `rag.py` pour qu’il comprenne le temps

On va injecter **la date du jour UTC** et indiquer au modèle comment raisonner sur les plages horaires :

```python
from datetime import datetime, timezone
from embedder import embed_texts
from vector_store import get_vanish_collection
from litellm_client import generate_with_litellm

def answer_query(query: str, top_k: int = 8):
    col = get_vanish_collection()
    q_emb = embed_texts([query])[0]

    # Recherche vectorielle
    res = col.query(query_embeddings=[q_emb], n_results=top_k)

    if not res["documents"] or not res["documents"][0]:
        return {"answer": "No results found.", "contexts": []}

    results = list(zip(res["documents"][0], res["metadatas"][0]))

    # Ajoute la date du jour dans le contexte du LLM
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    time_context = (
        f"Aujourd'hui, nous sommes le {today_str} (UTC).\n"
        f"Utilise les champs START_TIME et END_TIME pour déterminer si un job appartient à cette journée."
    )

    context_text = "\n---\n".join([r[0] for r in results])

    messages = [
        {
            "role": "system",
            "content": (
                "Tu es un assistant d'analyse de flux d'automatisation. "
                "Tu disposes d'un historique de jobs, chacun avec un start_time et end_time. "
                "Si l'utilisateur mentionne 'aujourd'hui' ou 'hier', interprète ces expressions selon la date du jour."
            ),
        },
        {
            "role": "user",
            "content": f"{time_context}\n\n{context_text}\n\nQUESTION:\n{query}"
        },
    ]

    answer = generate_with_litellm(messages)
    return {
        "answer": answer,
        "contexts": [{"content": r[0], "meta": r[1]} for r in results],
        "timestamp": now.isoformat()
    }
```

---

## ⚡ 4. Résultat

Quand tu poses :

> “Quels jobs ont échoué aujourd’hui ?”

Le modèle reçoit un contexte du type :

```
Aujourd'hui, nous sommes le 2025-11-02 (UTC).
Utilise les champs START_TIME et END_TIME pour déterminer si un job appartient à cette journée.

=== JOB EXECUTION RECORD ===
FLOW: sql_server_backup
TASK: create_backup
JOB_ID: 63df0a4
STATUS: FAILED
START_TIME: 2025-11-02T04:12:00Z
END_TIME: 2025-11-02T04:19:33Z
FAILURE_REASON: Timeout on backup client
WHAT_TO_DO: Retry backup or contact DBA
...
```

➡️ Le LLM sait alors que `START_TIME` et `END_TIME` appartiennent au jour courant, et te donne **les bons jobs échoués aujourd’hui** 🎯

---

## 🧠 Bonus : si tu veux un filtre optionnel “aujourd’hui”

Tu peux l’ajouter dans la requête Chroma :

```python
from datetime import datetime, timezone, timedelta

today = datetime.now(timezone.utc).date()
tomorrow = today + timedelta(days=1)

res = col.query(
    query_embeddings=[q_emb],
    n_results=top_k,
    where={
        "START_TIME": {"$gte": str(today), "$lt": str(tomorrow)}
    }
)
```

---

Souhaites-tu que je t’ajoute un **paramètre optionnel** `filter_by_today=True` dans la fonction `answer_query()`
pour que tu puisses facilement basculer entre “RAG global” et “RAG limité à la journée” ?
