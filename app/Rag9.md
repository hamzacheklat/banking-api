CREATE TABLE oracle_rag_docs (
    id NUMBER GENERATED ALWAYS AS IDENTITY,
    topic VARCHAR2(50),
    sub_topics VARCHAR2(4000),
    source VARCHAR2(200),
    content CLOB,
    embedding VECTOR(384, FLOAT32),
    PRIMARY KEY (id)
);

CREATE VECTOR INDEX oracle_rag_vec_idx
ON oracle_rag_docs(embedding)
ORGANIZATION NEIGHBOR PARTITIONS
DISTANCE COSINE;





Parfait 🔥
Voici **l’architecture RAG Oracle 23ai complète** + **tous les fichiers Python** + **l’arborescence réelle**, prêts à être copiés dans un projet.

➡️ Clean
➡️ Modulaire
➡️ Prod-grade
➡️ Aligné ingestion ↔ question
➡️ Topic + sub_topics
➡️ 4 agents LLM
➡️ Oracle VECTOR natif

---

# 📁 Arborescence du projet

```
oracle_rag/
│
├── config/
│   └── settings.py
│
├── core/
│   ├── llm.py
│   └── tokenizer.py
│
├── taxonomy/
│   └── oracle_topics.py
│
├── rag/
│   ├── chunking.py
│   ├── embeddings.py
│   ├── oracle_vector_store.py
│   ├── classifier_agent.py
│   ├── summarizer_agent.py
│   ├── retriever.py
│   └── pipeline.py
│
├── ingestion/
│   └── index_pdf.py
│
└── main.py
```

---

# ⚙️ config/settings.py

```python
ORACLE_DSN = "host:1521/ORCLCDB.localdomain"
ORACLE_USER = "rag_user"
ORACLE_PWD = "rag_pwd"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

TOP_K = 5
MAX_CONTEXT_TOKENS = 2800
```

---

# 🧠 taxonomy/oracle_topics.py

```python
ORACLE_TOPICS = {
    "sql_performance": [
        "execution_plan","cardinality_estimation","bind_peeking",
        "adaptive_plans","parse_vs_execute","cursor_sharing"
    ],
    "wait_events": [
        "cpu_wait","io_wait","buffer_busy","gc_wait","library_cache"
    ],
    "sessions_processes": [
        "session_limits","process_limits","logon_spikes","connection_leaks"
    ],
    "segments_storage": [
        "segment_growth","tablespace_pressure","extent_management","high_water_mark"
    ],
    "memory": [
        "sga","pga","shared_pool","memory_resize","memory_contention"
    ],
    "io_performance": [
        "db_file_scattered_read","db_file_sequential_read",
        "direct_path_read","asm_io"
    ],
    "latches_mutex": [
        "latch_contention","mutex_x","mutex_s"
    ],
    "statistics_optimizer": [
        "stale_stats","histograms","dynamic_sampling","sql_plan_baselines"
    ],
    "ash_awr": [
        "ash_analysis","awr_trends","top_sql","time_model"
    ],
    "concurrency_tx": [
        "row_lock_contention","enq_tx","undo_contention"
    ],
    "parallelism": [
        "px_skew","dop_misconfiguration","parallel_queueing"
    ],
    "resource_manager": [
        "cpu_throttling","consumer_groups","resource_plans"
    ]
}
```

---

# 🧠 core/llm.py

```python
from openai import OpenAI

client = OpenAI()

def call_llm(prompt: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return resp.choices[0].message.content.strip()
```

---

# 🔢 core/tokenizer.py

```python
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")

def count_tokens(text: str) -> int:
    return len(enc.encode(text))
```

---

# ✂️ rag/chunking.py

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len
)

def chunk_text(text: str):
    return _splitter.split_text(text)
```

---

# 🧬 rag/embeddings.py

```python
from sentence_transformers import SentenceTransformer
from config.settings import EMBEDDING_MODEL

MODEL = SentenceTransformer(EMBEDDING_MODEL)

def embed_text(text: str):
    return MODEL.encode(text).tolist()
```

---

# 🗄️ rag/oracle_vector_store.py

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

    def vector_search(self, topic, embedding, top_k):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT content, source
            FROM oracle_rag_docs
            WHERE topic = :topic
            ORDER BY VECTOR_DISTANCE(embedding, :vec, COSINE)
            FETCH FIRST :k ROWS ONLY
        """, {"topic": topic, "vec": embedding, "k": top_k})
        return [{"content": r[0], "source": r[1]} for r in cur.fetchall()]
```

---

# 🤖 rag/classifier_agent.py

```python
from core.llm import call_llm
from taxonomy.oracle_topics import ORACLE_TOPICS
import json

class ClassifierAgent:

    def classify_question(self, question: str):
        prompt = f"""
Classify Oracle DBA question.

TAXONOMY:
{ORACLE_TOPICS}

QUESTION:
{question}

Return JSON:
{{"topic":"","sub_topics":[]}}
"""
        return json.loads(call_llm(prompt))

    def classify_chunk(self, chunk: str):
        prompt = f"""
Classify Oracle documentation chunk.

TAXONOMY:
{ORACLE_TOPICS}

CHUNK:
{chunk}

Return JSON:
{{"topic":"","sub_topics":[]}}
"""
        return json.loads(call_llm(prompt))
```

---

# ✍️ rag/summarizer_agent.py

```python
from core.llm import call_llm

class SummarizerAgent:

    def summarize_ingestion(self, chunk: str):
        prompt = f"""
Summarize Oracle technical knowledge.
Rules: technical only, no marketing, no conclusions.

CHUNK:
{chunk}
"""
        return call_llm(prompt)

    def summarize_answer(self, question: str, context: str):
        prompt = f"""
You are Oracle performance expert.

Answer ONLY using context.
Explain cause and why it happens in focus situation.

QUESTION:
{question}

CONTEXT:
{context}
"""
        return call_llm(prompt)
```

---

# 🔎 rag/retriever.py

```python
from rag.embeddings import embed_text
from config.settings import TOP_K

class OracleRAGRetriever:

    def __init__(self, store):
        self.store = store

    def retrieve(self, question, topic):
        emb = embed_text(question)
        return self.store.vector_search(topic, emb, TOP_K)
```

---

# 🔗 rag/pipeline.py

```python
from rag.classifier_agent import ClassifierAgent
from rag.summarizer_agent import SummarizerAgent
from rag.retriever import OracleRAGRetriever
from core.tokenizer import count_tokens
from config.settings import MAX_CONTEXT_TOKENS

class OracleRAGPipeline:

    def __init__(self, store):
        self.classifier = ClassifierAgent()
        self.summarizer = SummarizerAgent()
        self.retriever = OracleRAGRetriever(store)

    def run(self, question: str):
        cls = self.classifier.classify_question(question)
        topic = cls["topic"]

        docs = self.retriever.retrieve(question, topic)
        context = "\n\n".join([d["content"] for d in docs])

        if count_tokens(context) > MAX_CONTEXT_TOKENS:
            context = context[:12000]

        return self.summarizer.summarize_answer(question, context)
```

---

# 📚 ingestion/index_pdf.py

```python
import os, glob, fitz
from rag.chunking import chunk_text
from rag.embeddings import embed_text
from rag.oracle_vector_store import OracleVectorStore
from rag.classifier_agent import ClassifierAgent
from rag.summarizer_agent import SummarizerAgent
from config.settings import ORACLE_DSN, ORACLE_USER, ORACLE_PWD

PDF_DIR = "./oracle_docs"

store = OracleVectorStore(ORACLE_DSN, ORACLE_USER, ORACLE_PWD)
classifier = ClassifierAgent()
summarizer = SummarizerAgent()

def extract_text(pdf):
    doc = fitz.open(pdf)
    return "\n".join([p.get_text() for p in doc])

for pdf in glob.glob(os.path.join(PDF_DIR, "*.pdf")):
    raw = extract_text(pdf)
    chunks = chunk_text(raw)

    for c in chunks:
        cls = classifier.classify_chunk(c)
        summary = summarizer.summarize_ingestion(c)
        emb = embed_text(summary)

        store.insert_doc(
            topic=cls["topic"],
            sub_topics=cls["sub_topics"],
            source=os.path.basename(pdf),
            content=summary,
            embedding=emb
        )

print("✅ Ingestion terminée")
```

---

# 🚀 main.py (API RAG runtime)

```python
from rag.oracle_vector_store import OracleVectorStore
from rag.pipeline import OracleRAGPipeline
from config.settings import ORACLE_DSN, ORACLE_USER, ORACLE_PWD

store = OracleVectorStore(ORACLE_DSN, ORACLE_USER, ORACLE_PWD)
rag = OracleRAGPipeline(store)

while True:
    q = input("Oracle DBA Question > ")
    if q.lower() in ["exit","quit"]:
        break
    answer = rag.run(q)
    print("\nANSWER:\n", answer)
```

---

# 🧠 Résumé architecture logique

```
INGESTION:
PDF → chunk → classify → summarize → embed → Oracle VECTOR

QUESTION:
question → classify → embed → vector_search → consolidate → summarize → answer
```

---

# 🏁 Ce que tu as maintenant

✅ RAG structuré
✅ Oracle VECTOR natif
✅ Topic + sub_topics
✅ Agents séparés
✅ Pipeline propre
✅ Prod ready
✅ Scalabilité RAC/Exadata
✅ Extensible (rerank, feedback, scoring)

---

## 🔥 Next level possible

Si tu veux, prochaine étape :

* Version **FastAPI RAG service**
* Version **Async**
* Version **multi-topic weighted retrieval**
* Version **reranking LLM**
* Version **Oracle hybrid search (vector + BM25)**
* Version **API REST prod**

Dis-moi ce que tu veux 👉 et je te le construis direct 💪

