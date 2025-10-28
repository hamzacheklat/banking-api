import requests
import uuid
import json
from tqdm import tqdm
from embedder import embed_texts
from vector_store import get_collection
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ⚙️ Paramètres
DELPHIX_BASE_URL = "https://uk271.delphix.xmp.net.intra"
DELPHIX_USER = "admin"
DELPHIX_PASSWORD = "password"

def delphix_login():
    """Connexion à l'API Delphix et création de session."""
    sess = requests.Session()
    sess.verify = False

    # Création de session API
    sess.post(f"{DELPHIX_BASE_URL}/resources/json/delphix/session", json={
        "type": "APISession",
        "version": {"type": "APIVersion", "major": 1, "minor": 10, "micro": 0}
    })

    # Login utilisateur
    payload = {"type": "LoginRequest", "username": DELPHIX_USER, "password": DELPHIX_PASSWORD}
    r = sess.post(f"{DELPHIX_BASE_URL}/resources/json/delphix/login", json=payload)
    if r.status_code != 200:
        raise Exception(f"Erreur de login Delphix ({r.status_code}): {r.text}")

    print("✅ Connecté à Delphix API")
    return sess

def fetch_api_doc(sess):
    """Récupère la documentation complète des endpoints depuis /api/json/delphix.json"""
    doc_url = f"{DELPHIX_BASE_URL}/api/json/delphix.json"
    r = sess.get(doc_url)
    if r.status_code != 200:
        raise Exception(f"Impossible de récupérer la doc API ({r.status_code}): {r.text}")
    return r.json()

def ingest_delphix_doc():
    """Ingestion de la documentation Delphix API dans le vector store."""
    sess = delphix_login()
    collection = get_collection()

    doc_json = fetch_api_doc(sess)

    all_docs, metadatas, ids = [], [], []

    # Parcours des endpoints documentés
    for endpoint, details in tqdm(doc_json.items(), desc="📘 Récupération de la doc API"):
        # Crée un texte clair pour RAG : description + paramètres
        content_lines = [f"Endpoint: {endpoint}"]
        if "description" in details:
            content_lines.append(f"Description: {details['description']}")
        if "parameters" in details and details["parameters"]:
            content_lines.append("Paramètres:")
            for param in details["parameters"]:
                pname = param.get("name", "")
                pdesc = param.get("description", "")
                ptype = param.get("type", "")
                content_lines.append(f"  - {pname} ({ptype}): {pdesc}")
        if "response" in details:
            content_lines.append("Réponse JSON (schéma):")
            content_lines.append(json.dumps(details["response"], indent=2))
        content = "\n".join(content_lines)

        ids.append(str(uuid.uuid4()))
        all_docs.append(content)
        metadatas.append({
            "source": "delphix_api_doc",
            "endpoint": endpoint
        })

    if not all_docs:
        print("⚠️ Aucune documentation récupérée.")
        return

    print(f"🧠 Génération des embeddings pour {len(all_docs)} documents...")
    embeddings = embed_texts(all_docs)
    collection.add(
        ids=ids,
        documents=all_docs,
        embeddings=embeddings,
        metadatas=metadatas
    )
    print("✅ Ingestion complète de la documentation Delphix API terminée.")
    sess.close()

if __name__ == "__main__":
    ingest_delphix_doc()
