Parfait 👏 — tu veux avoir la version complète et propre du fichier `app/vector_store.py`,
celle qui s’intègre **avec Chroma**, **LangChain** et ton modèle d’embedding `mxbai-embed-large-v1`.

Je vais te donner la version **moderne, claire et compatible** avec ton pipeline RAG conversationnel.
Elle comprend deux méthodes :

* `get_vanish_collection()` → pour accéder à la collection brute Chroma (bas niveau)
* `get_vanish_vectorstore()` → pour l’utiliser dans LangChain comme `VectorStoreRetriever` (haut niveau)

---

## ⚙️ `app/vector_store.py` (version complète et à jour)

```python
import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from embedder import embed_texts
from langchain_community.embeddings import LiteLLMEmbeddings, HuggingFaceEmbeddings
import config
import os


# 🚀 1. Initialisation du client Chroma
chroma_client = chromadb.Client(
    Settings(
        persist_directory=config.CHROMA_DB_DIR,
        anonymized_telemetry=False
    )
)


# 🧩 2. Fonction pour récupérer ou créer la collection Chroma brute
def get_vanish_collection():
    """
    Retourne la collection Chroma brute utilisée pour vanish_flows.
    C’est l’interface bas-niveau (ajout direct d’embeddings).
    """
    return chroma_client.get_or_create_collection(
        name="mongo_vanish_flows",
        metadata={"description": "Index vectoriel pour la collection Mongo vanish_flows"},
        embedding_function=None  # Les embeddings sont gérés côté Python
    )


# 🧠 3. Définition du modèle d’embedding pour LangChain
def get_embedding_function():
    """
    Retourne le bon embedder (LiteLLM si API key présente, sinon HuggingFace local).
    """
    if config.LITELLM_API_KEY:
        print("🔗 Utilisation de LiteLLMEmbeddings (mxbai-embed-large-v1)")
        return LiteLLMEmbeddings(
            model="mxbai-embed-large-v1",
            api_key=config.LITELLM_API_KEY
        )
    else:
        print("⚙️ Utilisation de HuggingFaceEmbeddings local (mxbai-embed-large-v1)")
        return HuggingFaceEmbeddings(model_name="mxbai-embed-large-v1")


# 💾 4. Fonction haut-niveau pour LangChain (VectorStore)
def get_vanish_vectorstore():
    """
    Retourne un objet LangChain Chroma prêt à l’emploi
    pour être utilisé dans le RAG LangChain (ConversationalRetrievalChain).
    """
    embedding_fn = get_embedding_function()

    # Vérifie et crée le dossier d’index s’il n’existe pas
    os.makedirs(config.CHROMA_DB_DIR, exist_ok=True)

    # Initialisation du VectorStore LangChain
    vectorstore = Chroma(
        collection_name="mongo_vanish_flows",
        persist_directory=config.CHROMA_DB_DIR,
        embedding_function=embedding_fn
    )
    return vectorstore
```

---

## 🧩 Explications rapides

| Fonction                   | Rôle                                                                             |
| -------------------------- | -------------------------------------------------------------------------------- |
| `get_vanish_collection()`  | Interface directe avec ChromaDB (utilisée pour `mongo_ingest.py`)                |
| `get_embedding_function()` | Sélectionne automatiquement entre `LiteLLMEmbeddings` et `HuggingFaceEmbeddings` |
| `get_vanish_vectorstore()` | Interface LangChain (utilisée par ton `rag_langchain.py`)                        |

---

## ✅ Utilisation typique

### ➤ Dans `mongo_ingest.py`

```python
from vector_store import get_vanish_collection
chroma_col = get_vanish_collection()
chroma_col.add(ids=..., documents=..., embeddings=..., metadatas=...)
```

### ➤ Dans `rag_langchain.py`

```python
from vector_store import get_vanish_vectorstore
vectorstore = get_vanish_vectorstore()
retriever = vectorstore.as_retriever(search_kwargs={"k": 8})
```

---

## 💡 Bonus : commande utile pour “inspecter” ton Chroma

```python
from vector_store import get_vanish_collection

col = get_vanish_collection()
print("Nombre total de documents :", col.count())
print("Exemple de métadonnée :", col.get(limit=1))
```

---

Souhaites-tu que je t’ajoute aussi un **petit utilitaire `chroma_utils.py`**
→ pour faire des opérations pratiques comme :

* vider complètement l’index,
* supprimer des embeddings par `FLOW` ou par date (`ingested_at`),
* vérifier les tailles et stats du vector store ?
