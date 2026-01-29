Parfait 👍
Je te donne **LE CODE COMPLET, COHÉRENT, PRÊT À L’EMPLOI**, pour un **RAG multi-livres Python**, avec :

✅ Lecture PDF
✅ Extraction **Table des Matières (chapitres / sections)**
✅ Extraction texte **par section réelle**
✅ Conversion **PDF → Markdown structuré**
✅ Chunking **1 section = 1 chunk (sans max_chars)**
✅ Vectorisation FAISS
✅ Prêt pour brancher un LLM derrière

Je te mets **TOUS les fichiers**, un par un, exactement comme dans l’arborescence.

---

# 📁 Arborescence finale

```
rag/
├── ingest/
│   ├── __init__.py
│   ├── toc_extractor.py
│   ├── pdf_loader.py
│   ├── pdf_to_markdown.py
│   ├── section_chunker.py
│   └── ingest_pipeline.py
│
├── embeddings/
│   ├── __init__.py
│   ├── embedder.py
│   └── vector_store.py
│
├── retriever/
│   ├── __init__.py
│   └── search.py
│
├── data/
│   ├── raw_pdfs/
│   └── chunks/
│
├── main.py
└── requirements.txt
```

---

# 📦 requirements.txt

```
pymupdf
sentence-transformers
faiss-cpu
numpy
```

---

# 📘 ingest/toc_extractor.py

👉 Extraction **Table des Matières réelle**

```python
import fitz  # PyMuPDF


def extract_toc(pdf_path: str):
    doc = fitz.open(pdf_path)
    toc = doc.get_toc(simple=True)

    if not toc:
        raise ValueError("No Table of Contents found in PDF")

    sections = []

    for i, (level, title, page) in enumerate(toc):
        start_page = page - 1
        end_page = (
            toc[i + 1][2] - 2
            if i + 1 < len(toc)
            else doc.page_count - 1
        )

        sections.append({
            "level": level,
            "title": title.strip(),
            "start_page": start_page,
            "end_page": end_page
        })

    return sections
```

---

# 📄 ingest/pdf_loader.py

👉 Extraction texte **par section**

```python
import fitz


def extract_section_text(pdf_path: str, section: dict) -> str:
    doc = fitz.open(pdf_path)
    texts = []

    for page_num in range(section["start_page"], section["end_page"] + 1):
        page = doc[page_num]
        texts.append(page.get_text("text"))

    return "\n".join(texts).strip()
```

---

# 🧾 ingest/pdf_to_markdown.py

👉 Conversion texte → Markdown propre

```python
import re


def to_markdown(title: str, text: str) -> str:
    md = f"# {title}\n\n"

    for line in text.splitlines():
        line = line.strip()

        if not line:
            md += "\n"
            continue

        # Detect numbered titles
        if re.match(r"^\d+(\.\d+)*\s+", line):
            md += f"## {line}\n"
        else:
            md += line + "\n"

    return md.strip()
```

---

# ✂️ ingest/section_chunker.py

👉 **1 section = 1 chunk (ce que tu veux)**

```python
def chunk_by_section(book: str, section: dict, markdown: str):
    return [{
        "book": book,
        "section": section["title"],
        "level": section["level"],
        "text": markdown,
        "metadata": {
            "start_page": section["start_page"],
            "end_page": section["end_page"]
        }
    }]
```

---

# 🔄 ingest/ingest_pipeline.py

👉 Pipeline complet PDF → chunks

```python
from ingest.toc_extractor import extract_toc
from ingest.pdf_loader import extract_section_text
from ingest.pdf_to_markdown import to_markdown
from ingest.section_chunker import chunk_by_section


def ingest_book(pdf_path: str, book_name: str):
    sections = extract_toc(pdf_path)
    chunks = []

    for section in sections:
        raw_text = extract_section_text(pdf_path, section)

        if not raw_text.strip():
            continue

        markdown = to_markdown(section["title"], raw_text)

        chunks.extend(
            chunk_by_section(book_name, section, markdown)
        )

    return chunks
```

---

# 🧠 embeddings/embedder.py

👉 Embeddings modernes (E5)

```python
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("intfloat/e5-large-v2")


def embed_texts(texts: list[str]):
    return _model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True
    )
```

---

# 📦 embeddings/vector_store.py

👉 FAISS simple et efficace

```python
import faiss
import numpy as np


class VectorStore:
    def __init__(self, dim: int):
        self.index = faiss.IndexFlatIP(dim)
        self.documents = []

    def add(self, embeddings, docs):
        self.index.add(np.array(embeddings).astype("float32"))
        self.documents.extend(docs)

    def search(self, query_embedding, k=5):
        scores, ids = self.index.search(
            np.array([query_embedding]).astype("float32"),
            k
        )
        return [self.documents[i] for i in ids[0]]
```

---

# 🔍 retriever/search.py

👉 Recherche sémantique

```python
from embeddings.embedder import embed_texts


def semantic_search(store, query: str, k=5):
    query_emb = embed_texts([query])[0]
    return store.search(query_emb, k)
```

---

# 🚀 main.py

👉 Multi-livres, prêt prod

```python
from ingest.ingest_pipeline import ingest_book
from embeddings.embedder import embed_texts
from embeddings.vector_store import VectorStore
from retriever.search import semantic_search


BOOKS = {
    "oracle_performance": "data/raw_pdfs/oracle_perf.pdf",
    "postgresql": "data/raw_pdfs/postgres.pdf"
}


def main():
    all_chunks = []

    for book, path in BOOKS.items():
        print(f"Ingesting {book}...")
        chunks = ingest_book(path, book)
        all_chunks.extend(chunks)

    texts = [c["text"] for c in all_chunks]
    embeddings = embed_texts(texts)

    store = VectorStore(dim=len(embeddings[0]))
    store.add(embeddings, all_chunks)

    # TEST
    results = semantic_search(
        store,
        "explain buffer cache contention",
        k=3
    )

    for r in results:
        print("\n---")
        print(r["book"], "->", r["section"])
        print(r["text"][:800])


if __name__ == "__main__":
    main()
```

---

# ✅ Ce que tu as maintenant

✔️ Chunking **100% sémantique**
✔️ Chapitres réels (TOC)
✔️ Multi-livres
✔️ Aucune limite `max_chars`
✔️ Contexte LLM propre
✔️ Architecture claire & extensible

---

## 🔥 Prochaines améliorations (je peux te les coder direct)

* Split automatique **par sous-sections Markdown**
* Fallback si le PDF **n’a pas de TOC**
* Docling / Nougat pour Markdown parfait
* Reranking cross-encoder
* Prompt RAG Oracle / DBA ultra-strict (comme tu aimes)

Dis-moi 👉 **quelle amélioration tu veux en premier** et je te donne le code direct.
