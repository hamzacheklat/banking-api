Parfait ! 🔥 On peut remplacer **`sentence-transformers`** par **`langchain`** pour l’ingestion et les embeddings. Je te propose une version backend mise à jour, prête à utiliser avec **Chroma + LangChain + LiteLLM**. Je vais te montrer uniquement les fichiers qui changent ou sont impactés.

---

## `backend/requirements.txt` (modifié)

```txt
fastapi
uvicorn[standard]
chromadb
langchain
transformers
torch
python-dotenv
pdfplumber
python-multipart
pydantic
tqdm
atlassian-python-api
requests
litellm
```

---

## `app/embedder.py` (remplacé par LangChain)

```python
from langchain.embeddings import HuggingFaceEmbeddings
import config

_model = None

def get_model():
    global _model
    if _model is None:
        _model = HuggingFaceEmbeddings(model_name=config.LOCAL_EMB_MODEL)
    return _model

def embed_texts(texts):
    model = get_model()
    return model.embed_documents(texts)
```

✅ Avec cette version :

* Les embeddings utilisent **LangChain**.
* L’interface des fonctions `embed_texts(texts)` reste identique.

---

Le reste du backend (**ingestion Confluence, Chroma, RAG, LiteLLM**) ne change pas.

Si tu veux, je peux te faire directement **la version complète `docker-compose.yml`** prête à lancer **backend + chroma + frontend Angular avec nginx**, en incluant LangChain.

Veux‑tu que je fasse ça maintenant ?
