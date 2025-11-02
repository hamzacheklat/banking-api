from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.embeddings import LiteLLMEmbeddings
import numpy as np
import config


# Choisis ici la méthode d’embedding — selon ton infra :
# 👉 Si tu veux utiliser le modèle open-source localement :
# model_name = "mxbai-embed-large-v1"
# embeddings_model = HuggingFaceEmbeddings(model_name=model_name)

# 👉 Si tu veux utiliser un modèle hébergé via LiteLLM :
embeddings_model = LiteLLMEmbeddings(
    model="mxbai-embed-large-v1",
    api_key=config.LITELLM_API_KEY
)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Calcule les embeddings pour une liste de textes.
    Retourne une liste de vecteurs (list[list[float]]).
    """
    if not texts:
        return []

    # LangChain gère déjà le batching et la normalisation
    embeddings = embeddings_model.embed_documents(texts)

    # Convertit en format compatible Chroma (liste de listes)
    return np.array(embeddings).tolist()
