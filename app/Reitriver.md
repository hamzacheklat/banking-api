Carrément 🔥 je vois exactement ce que tu veux :

✅ **RAG retrieval filtré par topic**
✅ **Résumé (summary) des résultats RAG** avant de répondre
✅ **Un nouvel agent “Router/Planner”** qui lit le résultat du **1er LLM call** et décide :

* **quel topic** viser
* **quel “contexte recherché”** (focus) tu veux retrouver dans le RAG
* et même **une requête reformulée** pour améliorer la recherche vectorielle

Je te propose une architecture propre en 2 phases :

---

# ✅ Nouvelle architecture (runtime)

### 1) First LLM Call = “Planner / Router”

Input : user question + history (optionnel)
Output JSON :

* `topic`
* `sub_topics`
* `rag_focus` (ce qu’on veut trouver dans le RAG)
* `search_query` (version optimisée pour embedding/retrieval)

### 2) Retrieve RAG (par topic)

On embed `search_query` et on fait `vector_search(topic=...)`

### 3) Summarize retrieved docs (agent dédié)

On fait un résumé des chunks récupérés (bullet points), ça sert de “clean context”.

### 4) Final Answer (agent final)

On répond à la question **uniquement** avec le contexte résumé.

---

# 🧠 1) Nouveau agent : `rag/router_agent.py`

````python
import json
from core.llm import call_llm
from taxonomy.oracle_topics import ORACLE_TOPICS

class RouterAgent:
    """
    Decide:
    - which topic to use
    - what we want to retrieve from RAG (focus)
    - optimized search query for embeddings
    """

    def route(self, question: str) -> dict:
        prompt = f"""
You are an Oracle DBA routing agent.

Your job:
1) Decide the best TOPIC + SUB_TOPICS from the taxonomy
2) Decide what specific context should be retrieved from the RAG (rag_focus)
3) Rewrite the question into an optimized search query for vector retrieval (search_query)

RULES:
- Use ONLY the provided taxonomy
- Output MUST be valid JSON only
- Be concise and technical

TAXONOMY:
{ORACLE_TOPICS}

USER QUESTION:
{question}

OUTPUT JSON FORMAT:
{{
  "topic": "<topic>",
  "sub_topics": ["<sub1>", "<sub2>"],
  "rag_focus": "what we want to find in the docs (symptoms, root cause, wait event, metric, parameter...)",
  "search_query": "rewritten query optimized for retrieval"
}}
"""
        raw = call_llm(prompt).strip()

        # robust extraction if model wraps json in markdown
        if "```" in raw and "json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()

        return json.loads(raw)
````

---

# 🔎 2) Retriever par topic + sub_topics (optionnel)

Tu veux “par topic”, donc on filtre **au minimum** sur `topic`.
Et si tu veux encore plus précis, on peut filtrer aussi sur `sub_topics` (LIKE).

### `rag/oracle_vector_store.py` (upgrade)

```python
import cx_Oracle

class OracleVectorStore:

    def __init__(self, dsn, user, pwd):
        self.conn = cx_Oracle.connect(user, pwd, dsn)

    def insert_doc(self, topic, sub_topics, source, content, embedding):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO oracle_rag_docs
            (topic, sub_topics, source, content, embedding)
            VALUES (:1, :2, :3, :4, :5)
        """, [topic, ",".join(sub_topics), source, content, embedding])
        self.conn.commit()

    def vector_search(self, topic, embedding, top_k, sub_topics=None):
        """
        Retrieval by topic (mandatory)
        Optional filtering by sub_topics (string match)
        """
        cur = self.conn.cursor()

        if sub_topics:
            # crude filter, can be improved with JSON array column later
            sub_filter = " AND (" + " OR ".join(
                [f"sub_topics LIKE '%' || :st{i} || '%'" for i in range(len(sub_topics))]
            ) + ")"

            binds = {"topic": topic, "vec": embedding, "k": top_k}
            for i, st in enumerate(sub_topics):
                binds[f"st{i}"] = st

            sql = f"""
                SELECT content, source, topic, sub_topics
                FROM oracle_rag_docs
                WHERE topic = :topic
                {sub_filter}
                ORDER BY VECTOR_DISTANCE(embedding, :vec, COSINE)
                FETCH FIRST :k ROWS ONLY
            """
            cur.execute(sql, binds)

        else:
            cur.execute("""
                SELECT content, source, topic, sub_topics
                FROM oracle_rag_docs
                WHERE topic = :topic
                ORDER BY VECTOR_DISTANCE(embedding, :vec, COSINE)
                FETCH FIRST :k ROWS ONLY
            """, {"topic": topic, "vec": embedding, "k": top_k})

        return [
            {"content": r[0], "source": r[1], "topic": r[2], "sub_topics": r[3]}
            for r in cur.fetchall()
        ]
```

---

# 🧾 3) Agent “RAG Results Summarizer”

### `rag/rag_results_summarizer_agent.py`

```python
from core.llm import call_llm

class RAGResultsSummarizerAgent:
    """
    Summarize retrieved RAG docs into a compact technical context.
    """

    def summarize_retrieval(self, question: str, rag_focus: str, retrieved_docs: list) -> str:
        joined = "\n\n".join(
            [f"[SOURCE={d['source']}]\n{d['content']}" for d in retrieved_docs]
        )

        prompt = f"""
You are an Oracle performance tuning expert.

TASK:
Summarize the retrieved documentation into a clean technical context
that will be used to answer the question.

RULES:
- Keep ONLY information relevant to the question + rag_focus
- Output bullet points
- Mention the most important cause/evidence/mechanism
- Do NOT invent anything
- If context is weak, say "INSUFFICIENT CONTEXT"

USER QUESTION:
{question}

RAG FOCUS:
{rag_focus}

RETRIEVED DOCS:
{joined}
"""
        return call_llm(prompt).strip()
```

---

# ✍️ 4) Summarizer final (Answer Agent) — version stricte

Tu as déjà un prompt très bon (dans ta capture) :
👉 je le garde, mais je l’alimente avec **le contexte résumé**, pas brut.

### `rag/final_answer_agent.py`

```python
from core.llm import call_llm

class FinalAnswerAgent:

    def answer(self, question: str, context: str) -> str:
        prompt = f"""
You are a senior Oracle performance tuning expert.

Answer the USER QUESTION using ONLY the provided CONTEXT.

RULES:
- Base your answer strictly on the context
- Explain WHY the issue occurs
- Explain WHY it appears in the focus situation
- Do NOT give generic Oracle advice
- Do NOT list unrelated bottlenecks
- If the context is insufficient, say it clearly
- Be precise, technical, and concise

USER QUESTION:
{question}

CONTEXT:
{context}
"""
        return call_llm(prompt).strip()
```

---

# 🔗 5) Pipeline complet (Router → Retrieve(topic) → Summarize → Answer)

### `rag/pipeline.py` (nouvelle version)

```python
from rag.router_agent import RouterAgent
from rag.retriever import OracleRAGRetriever
from rag.rag_results_summarizer_agent import RAGResultsSummarizerAgent
from rag.final_answer_agent import FinalAnswerAgent
from config.settings import TOP_K

class OracleRAGPipeline:

    def __init__(self, store):
        self.router = RouterAgent()
        self.retriever = OracleRAGRetriever(store)
        self.rag_summarizer = RAGResultsSummarizerAgent()
        self.answer_agent = FinalAnswerAgent()

    def run(self, question: str):
        # 1) PLAN / ROUTE
        plan = self.router.route(question)

        topic = plan["topic"]
        sub_topics = plan.get("sub_topics", [])
        rag_focus = plan.get("rag_focus", "")
        search_query = plan.get("search_query", question)

        # 2) RETRIEVE by topic (+ optional sub_topics)
        docs = self.retriever.retrieve(
            query=search_query,
            topic=topic,
            sub_topics=sub_topics
        )

        # 3) Summarize retrieved docs
        rag_context = self.rag_summarizer.summarize_retrieval(
            question=question,
            rag_focus=rag_focus,
            retrieved_docs=docs
        )

        # 4) Final answer using only summarized context
        final = self.answer_agent.answer(question, rag_context)

        return {
            "plan": plan,
            "retrieved": docs,
            "rag_context": rag_context,
            "answer": final
        }
```

---

# 🔎 6) Retriever modifié pour accepter `query` et `sub_topics`

### `rag/retriever.py`

```python
from rag.embeddings import embed_text
from config.settings import TOP_K

class OracleRAGRetriever:

    def __init__(self, store):
        self.store = store

    def retrieve(self, query: str, topic: str, sub_topics=None):
        emb = embed_text(query)
        return self.store.vector_search(
            topic=topic,
            embedding=emb,
            top_k=TOP_K,
            sub_topics=sub_topics
        )
```

---

# 🧩 7) Intégration dans ton `ChatAgent` (ton code screenshot)

Dans ton `ChatAgent.chat()`, aujourd’hui tu fais :

* first LLM call
* parse JSON tools
* execute tools
* second LLM call

👉 Là tu peux ajouter **un tool `rag_retrieve()`** qui exécute le pipeline ci-dessus.

### Exemple tool function

```python
def rag_retrieve(question: str):
    result = rag_pipeline.run(question)
    return {
        "topic": result["plan"]["topic"],
        "sub_topics": result["plan"]["sub_topics"],
        "rag_focus": result["plan"]["rag_focus"],
        "rag_context": result["rag_context"],
        "answer": result["answer"]
    }
```

Et ton LLM 1 peut décider d’appeler ce tool.

---

# ✅ Résultat final attendu (ce que tu obtiens)

Quand l’utilisateur pose une question :

1. **RouterAgent** décide :

* Topic : `sql_performance`
* Sub topics : `execution_plan`, `cardinality_estimation`
* Focus : “why full table scan appears / wrong cardinality”
* Search query : reformulation propre

2. Retrieval dans Oracle VECTOR **uniquement dans ce topic**
3. Résumé des docs récupérés
4. Réponse finale strictement basée sur ce résumé

---

# Si tu veux je te fais la V2 encore plus “prod”

🔥 Ajouts possibles :

* **multi-topic retrieval pondéré** (si Router hésite)
* **hybrid search** (vector + keyword)
* **reranker LLM** (top_k=20 → rerank → top_k=5)
* stockage `sub_topics` en **JSON** au lieu de VARCHAR2
* logs + traces “why retrieved”

Si tu veux, envoie-moi ton fichier `llm.py` + ton `chat_agent.py` complet (copier/coller), et je te l’intègre exactement dans TON framework sans casser ton flow 🔥
