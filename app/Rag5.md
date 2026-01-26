Parfait 💪 — je te fais **la version RAG Oracle 23ai complète, prête pour prod**, **sans chapitres**, avec **tout : création de table, index vectoriel, embeddings, pipeline RAG complet et script d’indexation PDF/livres**, avec **source + topic** uniquement comme metadata.

On part **de zéro jusqu’au pipeline final**, cohérent et propre.

---

# 1️⃣ Création de la table Oracle RAG VECTOR

```sql
CREATE TABLE oracle_rag_docs (
    id            NUMBER GENERATED ALWAYS AS IDENTITY,
    topic         VARCHAR2(50),
    source        VARCHAR2(200),
    content       CLOB,
    embedding     VECTOR(384, FLOAT32),
    CONSTRAINT oracle_rag_docs_pk PRIMARY KEY (id)
);
```

---

# 2️⃣ Création de l’index VECTOR Oracle 23ai

```sql
CREATE VECTOR INDEX oracle_rag_vec_idx
ON oracle_rag_docs (embedding)
ORGANIZATION NEIGHBOR PARTITIONS
DISTANCE COSINE;
```

✅ Tout est natif Oracle 23ai, **pas de FAISS**, scalable RAC / Exadata.

---

# 3️⃣ Chunking intelligent avec LangChain

```python
# rag/chunking.py
from langchain.text_splitter import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len
)

def chunk_text(text):
    return text_splitter.split_text(text)
```

---

# 4️⃣ Embeddings HF locaux

```python
# rag/embeddings.py
from sentence_transformers import SentenceTransformer

MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def embed_text(text: str):
    return MODEL.encode(text).tolist()
```

---

# 5️⃣ Stockage et recherche Oracle VECTOR

```python
# rag/oracle_vector_store.py
import cx_Oracle

class OracleVectorStore:

    def __init__(self, dsn, user, pwd):
        self.conn = cx_Oracle.connect(user, pwd, dsn)

    def insert_doc(self, topic, source, content, embedding):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO oracle_rag_docs
            (topic, source, content, embedding)
            VALUES (:1, :2, :3, :4)
        """, [topic, source, content, embedding])
        self.conn.commit()

    def vector_search(self, embedding, topic, top_k=5):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT content, source
            FROM oracle_rag_docs
            WHERE topic = :topic
            ORDER BY VECTOR_DISTANCE(embedding, :vec, COSINE)
            FETCH FIRST :k ROWS ONLY
        """, {
            "topic": topic,
            "vec": embedding,
            "k": top_k
        })
        return [{"content": r[0], "source": r[1]} for r in cur.fetchall()]
```

---

# 6️⃣ Topic detection pour RAG

```python
# rag/topic_agent.py
from core.llm import call_llm

# Exemple ORACLE_TOPICS
ORACLE_TOPICS = [
    "sql_performance", "wait_events", "sessions_processes",
    "segments_storage", "memory", "io_performance",
    "latches_mutex", "statistics_optimizer", "ash_awr",
    "concurrency_tx", "parallelism", "resource_manager"
]

def detect_topics(question):
    prompt = f"""
Classify this Oracle DBA question.
Topics: {ORACLE_TOPICS}
Question: {question}
Return JSON list.
"""
    return eval(call_llm(prompt))
```

---

# 7️⃣ Récupérateur RAG

```python
# rag/retriever.py
from rag.embeddings import embed_text

class OracleRAGRetriever:

    def __init__(self, vector_store):
        self.store = vector_store

    def retrieve(self, question, topics):
        embedding = embed_text(question)
        docs = []
        for topic in topics:
            docs.extend(self.store.vector_search(embedding, topic))
        return docs
```

---

# 8️⃣ Summarizer token-safe

```python
# rag/summarizer.py
from core.llm import call_llm
from core.tokenizer import count_tokens

MAX_CONTEXT = 2800

def summarize_if_needed(question, docs):
    text = "\n\n".join([d["content"] for d in docs])
    if count_tokens(text) < MAX_CONTEXT:
        return text
    prompt = f"""
User question:
{question}

Summarize the following Oracle documentation:

{text}
"""
    return call_llm(prompt)
```

---

# 9️⃣ Pipeline RAG complet

```python
# rag/pipeline.py
from rag.topic_agent import detect_topics
from rag.retriever import OracleRAGRetriever
from rag.summarizer import summarize_if_needed

def rag_pipeline(question, retriever):
    topics = detect_topics(question)
    docs = retriever.retrieve(question, topics)
    return summarize_if_needed(question, docs)
```

---

# 🔥 10️⃣ Script d’indexation PDF / livres RAG complet

```python
# index_pdf_rag_final.py
import os
import glob
import fitz
from rag.chunking import chunk_text
from rag.embeddings import embed_text
from rag.oracle_vector_store import OracleVectorStore
from rag.topic_agent import detect_topics

# -------------------
# Config Oracle
# -------------------
DSN = "host:1521/ORCLCDB.localdomain"
USER = "your_user"
PWD = "your_password"

vector_store = OracleVectorStore(DSN, USER, PWD)

# -------------------
# PDF directory
# -------------------
PDF_DIR = "./oracle_docs"

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text

# -------------------
# Indexation PDF → Oracle VECTOR
# -------------------
for pdf_file in glob.glob(os.path.join(PDF_DIR, "*.pdf")):
    print(f"Indexing {pdf_file}...")
    text = extract_text_from_pdf(pdf_file)

    # Détection topic principal
    topics = detect_topics(text)
    main_topic = topics[0]

    # Chunking intelligent
    chunks = chunk_text(text)

    for chunk in chunks:
        embedding = embed_text(chunk)
        vector_store.insert_doc(
            topic=main_topic,
            source=os.path.basename(pdf_file),
            content=chunk,
            embedding=embedding
        )

print("✅ Indexation PDF RAG terminée !")
```

---

# ✅ Résultat

* **Table Oracle VECTOR + index** natif.
* **Embeddings HF locaux**.
* **Pipeline RAG complet** : topic → vector search → résumé.
* **Script d’indexation PDF/livres** prêt pour prod.
* **Metadata minimal** : source + topic (chapitre supprimé).

---

Si tu veux, je peux te faire **la version “tout-en-un” RAG Python** :

* Indexation multi-PDF
* Vector search avec topic
* Résumé automatique + consolidation multi-docs
* Tout dans **une seule classe RAG ultra-pro prête à l’usage**

Veux‑tu que je fasse cette version ?
