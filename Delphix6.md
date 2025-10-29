Parfait 🚀
Donc on part sur :

* **Chroma** comme vector store ✅
* **OpenAI `text-embedding-3-large`** comme modèle d’embedding (qualité top pour doc technique) ✅
* Accès Internet activé (donc scraping possible de docs.delphix.com et GitHub) ✅

Voici le **pipeline complet “multi-source Delphix”**, prêt à tourner directement dans ton environnement.
Tu peux le mettre dans un fichier `ingest_delphix_multisource.py`.

---

```python
import requests
import uuid
import json
import os
from tqdm import tqdm
import urllib3
from trafilatura import fetch_url, extract
from embedder import embed_texts
from vector_store import get_collection

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================
# ⚙️ SETTINGS
# ============================================================
DELPHIX_BASE_URL = "https://uk271.delphix.xmp.net.intra"
DELPHIX_USER = "admin"
DELPHIX_PASSWORD = "password"

# ============================================================
# 🧩 UTILS
# ============================================================

def chunk_text(text, chunk_size=800, overlap=100):
    """Split long text into overlapping chunks."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def json_to_text(obj, indent=2):
    """Convert any JSON recursively into structured readable text."""
    lines = []
    spacing = " " * indent
    if isinstance(obj, dict):
        for k, v in obj.items():
            key_name = k.upper() if isinstance(v, (dict, list)) else k
            if isinstance(v, (dict, list)):
                lines.append(f"{spacing}{key_name}:")
                lines.extend(json_to_text(v, indent + 2))
            else:
                lines.append(f"{spacing}{k}: {v}")
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            lines.append(f"{spacing}- item {idx + 1}:")
            lines.extend(json_to_text(item, indent + 2))
    else:
        lines.append(f"{spacing}{obj}")
    return lines

# ============================================================
# 🔐 LOGIN + API DOC
# ============================================================

def delphix_login():
    """Login to Delphix Engine."""
    sess = requests.Session()
    sess.verify = False
    sess.post(f"{DELPHIX_BASE_URL}/resources/json/delphix/session", json={
        "type": "APISession",
        "version": {"type": "APIVersion", "major": 1, "minor": 10, "micro": 0}
    })
    payload = {"type": "LoginRequest", "username": DELPHIX_USER, "password": DELPHIX_PASSWORD}
    r = sess.post(f"{DELPHIX_BASE_URL}/resources/json/delphix/login", json=payload)
    if r.status_code != 200:
        raise Exception(f"Login failed ({r.status_code}): {r.text}")
    print("✅ Connected to Delphix API")
    return sess

def fetch_api_doc(sess):
    """Fetch full API doc from best available endpoint."""
    urls = [
        f"{DELPHIX_BASE_URL}/api/json/delphix/latest.json",
        f"{DELPHIX_BASE_URL}/api/json/delphix.json",
        f"{DELPHIX_BASE_URL}/resources/json/delphix.json"
    ]
    for url in urls:
        r = sess.get(url)
        if r.status_code == 200:
            print(f"✅ API documentation fetched from {url}")
            return r.json()
    raise Exception("❌ Failed to fetch any Delphix API doc")

# ============================================================
# 🌐 SCRAPERS (Delphix Docs + GitHub)
# ============================================================

def scrape_page(url):
    """Fetch and extract text from a web page."""
    try:
        html = fetch_url(url)
        text = extract(html, include_comments=False, include_tables=True)
        return text
    except Exception as e:
        print(f"⚠️ Error scraping {url}: {e}")
        return None

def scrape_delphix_docs():
    """Scrape official public documentation from docs.delphix.com."""
    pages = [
        "https://docs.delphix.com/docs/delphix-engine",
        "https://docs.delphix.com/docs/delphix-engine-reference",
        "https://docs.delphix.com/docs/delphix-engine-api-guide",
        "https://docs.delphix.com/docs/delphix-masking-api-guide",
        "https://docs.delphix.com/docs/delphix-engine-cli-reference"
    ]
    docs = []
    for url in tqdm(pages, desc="🌐 Scraping Delphix Docs"):
        text = scrape_page(url)
        if text:
            docs.append((url, text))
    return docs

def scrape_github_repos():
    """Fetch README and docs from official Delphix GitHub repos."""
    repos = [
        "https://raw.githubusercontent.com/delphix/dxtoolkit/master/README.md",
        "https://raw.githubusercontent.com/delphix/delphixpy/master/README.md",
        "https://raw.githubusercontent.com/delphix/delphixpy-examples/master/README.md",
        "https://raw.githubusercontent.com/delphix/masking-api/master/README.md"
    ]
    docs = []
    for url in tqdm(repos, desc="🐙 Scraping Delphix GitHub"):
        try:
            r = requests.get(url)
            if r.status_code == 200:
                docs.append((url, r.text))
        except Exception as e:
            print(f"⚠️ Error fetching {url}: {e}")
    return docs

# ============================================================
# 🧠 INGESTION
# ============================================================

def ingest_delphix_multisource():
    """Ingest API + Docs + GitHub into Chroma vector store."""
    collection = get_collection()
    all_docs, metadatas, ids = [], [], []

    # ---- API Documentation ----
    sess = delphix_login()
    api_json = fetch_api_doc(sess)
    print(f"📘 {len(api_json)} API endpoints loaded")

    for endpoint, details in tqdm(api_json.items(), desc="📖 Parsing API JSON"):
        lines = [f"ENDPOINT: {endpoint}"]
        lines.extend(json_to_text(details))
        full_text = "\n".join(lines)
        for chunk in chunk_text(full_text):
            all_docs.append(chunk)
            ids.append(str(uuid.uuid4()))
            metadatas.append({"source": "delphix_api", "endpoint": endpoint})
    sess.close()

    # ---- Official Documentation ----
    for url, text in scrape_delphix_docs():
        for chunk in chunk_text(text):
            all_docs.append(chunk)
            ids.append(str(uuid.uuid4()))
            metadatas.append({"source": "delphix_docs", "url": url})

    # ---- GitHub Repos ----
    for url, text in scrape_github_repos():
        for chunk in chunk_text(text):
            all_docs.append(chunk)
            ids.append(str(uuid.uuid4()))
            metadatas.append({"source": "delphix_github", "url": url})

    print(f"🧾 Total {len(all_docs)} text chunks ready for embedding...")

    # ---- Embedding + Storage ----
    embeddings = embed_texts(all_docs)
    collection.add(ids=ids, documents=all_docs, embeddings=embeddings, metadatas=metadatas)
    print("✅ All sources successfully ingested into Chroma vector store!")

# ============================================================
# 🏁 ENTRY POINT
# ============================================================
if __name__ == "__main__":
    ingest_delphix_multisource()
```

---

## 🧠 Ce que fait ce script

| Source                 | Description                                              |
| ---------------------- | -------------------------------------------------------- |
| **API JSON interne**   | Scrape via login + `/api/json/delphix.json`              |
| **Docs publiques**     | Extraits depuis `docs.delphix.com`                       |
| **GitHub open source** | Récupère les README des outils officiels                 |
| **Chunking**           | 800 tokens + overlap 100 pour meilleure précision        |
| **Embeddings**         | `text-embedding-3-large` (via ta fonction `embed_texts`) |
| **Vector store**       | Ingestion directe dans **Chroma**                        |
| **Metadata**           | Chaque chunk est tagué : `source` + `endpoint` ou `url`  |

---

### 🔍 Exemple de requêtes que ton RAG pourra bien gérer maintenant :

* “Comment provisionner un VDB via API Delphix ?”
* “Quelle commande CLI équivaut à un `POST /database/refresh` ?”
* “Exemple d’utilisation de delphixpy pour rafraîchir une source.”
* “Comment résoudre l’erreur DX-50005 ?”
* “Quelle différence entre un dSource et un VDB selon la doc officielle ?”

---

Souhaites-tu que je t’ajoute **un module complémentaire** pour tester ton RAG après ingestion ?
(genre `query_rag.py` → tu tapes une question, il te montre les passages retrouvés et la réponse générée)
👉 Très utile pour valider la qualité des embeddings et la pertinence des sources.
