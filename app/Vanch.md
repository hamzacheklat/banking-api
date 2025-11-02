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
