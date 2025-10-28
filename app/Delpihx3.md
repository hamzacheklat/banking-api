import requests
import uuid
import json
from tqdm import tqdm
from embedder import embed_texts
from vector_store import get_collection
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ⚙️ Paramètres (tu peux ensuite les déplacer dans config.py)
DELPHIX_BASE_URL = "https://uk271.delphix.xmp.net.intra"
DELPHIX_USER = "admin"
DELPHIX_PASSWORD = "password"

# ✅ Endpoints connus et stables de Delphix
DELPHIX_ENDPOINTS = [
    "environment",
    "repository",
    "sourceconfig",
    "source",
    "database",
    "snapshot",
    "system",
    "job",
    "type"  # <-- option 4 ajoutée ici
]

def delphix_login():
    sess = requests.Session()
    sess.verify = False

    # 1️⃣ Création de session API
    sess.post(f"{DELPHIX_BASE_URL}/resources/json/delphix/session", json={
        "type": "APISession",
        "version": {"type": "APIVersion", "major": 1, "minor": 10, "micro": 0}
    })

    # 2️⃣ Login utilisateur
    payload = {"type": "LoginRequest", "username": DELPHIX_USER, "password": DELPHIX_PASSWORD}
    r = sess.post(f"{DELPHIX_BASE_URL}/resources/json/delphix/login", json=payload)
    if r.status_code != 200:
        raise Exception(f"Erreur de login Delphix ({r.status_code}): {r.text}")

    print("✅ Connecté à Delphix API")
    return sess

def fetch_endpoint(sess, endpoint):
    """Appelle un endpoint Delphix, renvoie le JSON brut (ou None si non dispo)."""
    url = f"{DELPHIX_BASE_URL}/resources/json/delphix/{endpoint}"
    r = sess.get(url)
    if r.status_code == 404:
        print(f"⚠️ Endpoint '{endpoint}' introuvable (404).")
        return None
    if r.status_code >= 400:
        print(f"⚠️ Erreur sur {endpoint}: {r.status_code}")
        return None
    try:
        return json.dumps(r.json(), indent=2)
    except Exception:
        return r.text

def ingest_delphix_api():
    """Ingestion complète de la documentation et des objets Delphix."""
    sess = delphix_login()
    collection = get_collection()

    all_docs, metadatas, ids = [], [], []

    for ep in tqdm(DELPHIX_ENDPOINTS, desc="📘 Récupération des endpoints Delphix"):
        content = fetch_endpoint(sess, ep)
        if not content:
            continue
        ids.append(str(uuid.uuid4()))
        all_docs.append(content)
        metadatas.append({
            "source": "delphix_api",
            "endpoint": ep
        })

    if not all_docs:
        print("⚠️ Aucune donnée récupérée depuis Delphix.")
        return

    print(f"🧠 Génération des embeddings pour {len(all_docs)} documents...")
    embeddings = embed_texts(all_docs)
    collection.add(
        ids=ids,
        documents=all_docs,
        embeddings=embeddings,
        metadatas=metadatas
    )
    print("✅ Ingestion complète Delphix (API + Types) terminée.")
    sess.close()

if __name__ == "__main__":
    ingest_delphix_api()
