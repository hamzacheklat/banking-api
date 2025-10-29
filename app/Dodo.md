Parfait 👍
Voici le **script complet et prêt à exécuter** — corrigé pour **lister toutes les pages** de la documentation Delphix et **les ingérer entièrement** dans ton moteur d’embedding/vector store.

---

### 🧩 `ingest_delphix_docs.py`

```python
import requests
import uuid
from bs4 import BeautifulSoup
from tqdm import tqdm
from embedder import embed_texts
from vector_store import get_collection
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ⚙️ CONFIGURATION
DELPHIX_BASE_URL = "https://uk271.delphix.xmp.net.intra"
DELPHIX_USER = "admin"
DELPHIX_PASSWORD = "password"


# ============================================================
# 🔐 AUTHENTIFICATION
# ============================================================
def delphix_login():
    """Login to Delphix and return an authenticated session."""
    sess = requests.Session()
    sess.verify = False

    # Create API session
    sess.post(f"{DELPHIX_BASE_URL}/resources/json/delphix/session", json={
        "type": "APISession",
        "version": {"type": "APIVersion", "major": 1, "minor": 10, "micro": 0}
    })

    # User login
    payload = {"type": "LoginRequest", "username": DELPHIX_USER, "password": DELPHIX_PASSWORD}
    r = sess.post(f"{DELPHIX_BASE_URL}/resources/json/delphix/login", json=payload)
    if r.status_code != 200:
        raise Exception(f"❌ Login failed ({r.status_code}): {r.text}")

    print("✅ Connected to Delphix Engine")
    return sess


# ============================================================
# 📜 LISTER LES PAGES DE LA DOC
# ============================================================
def list_api_pages(sess):
    """
    Récupère toutes les URLs de documentation disponibles
    dans le menu latéral de la page principale /api/.
    """
    start_url = f"{DELPHIX_BASE_URL}/api"
    r = sess.get(start_url)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    links = []
    for a in soup.select("a[href]"):
        href = a["href"]
        # Filtrer uniquement les liens pertinents de la doc API
        if href.startswith("/api/") and not href.endswith(".json"):
            full_url = f"{DELPHIX_BASE_URL}{href}"
            if full_url not in links:
                links.append(full_url)

    print(f"🔍 Found {len(links)} API documentation pages.")
    return links


# ============================================================
# 🌐 SCRAPER LES PAGES HTML
# ============================================================
def scrape_api_html(sess):
    urls = list_api_pages(sess)
    results = []

    for url in tqdm(urls, desc="🌐 Scraping API HTML pages"):
        try:
            r = sess.get(url)
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            results.append((url, text))

        except Exception as e:
            print(f"⚠️ Error scraping {url}: {e}")

    print(f"✅ Scraped {len(results)} API HTML pages.")
    return results


# ============================================================
# ✂️ CHUNKING (Découpage du texte)
# ============================================================
def chunk_text(text, chunk_size=800, overlap=100):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks


# ============================================================
# 🧠 INGESTION DANS LA BASE VECTORIELLE
# ============================================================
def ingest_api_scraped_docs():
    """Scrape et ingère le contenu HTML de la documentation API Delphix."""
    sess = delphix_login()
    collection = get_collection()

    scraped_pages = scrape_api_html(sess)
    sess.close()

    all_docs, metadatas, ids = [], [], []

    for url, text in tqdm(scraped_pages, desc="📖 Processing scraped HTML"):
        for chunk in chunk_text(text):
            ids.append(str(uuid.uuid4()))
            all_docs.append(chunk)
            metadatas.append({"source": "delphix_api_html", "url": url})

    if not all_docs:
        print("⚠️ No scraped content found.")
        return

    print(f"🧠 Generating embeddings for {len(all_docs)} chunks...")
    embeddings = embed_texts(all_docs)

    collection.add(ids=ids, documents=all_docs, embeddings=embeddings, metadatas=metadatas)
    print("✅ HTML-based API documentation successfully ingested!")


# ============================================================
# 🏁 MAIN
# ============================================================
if __name__ == "__main__":
    ingest_api_scraped_docs()
```

---

### 🚀 Ce que fait cette version :

1. **Se connecte** à ton moteur Delphix via API REST (authentifié).
2. **Parcourt dynamiquement** tout le menu gauche de la doc (`/api`) pour extraire **toutes les sous-pages**.
3. **Scrape chaque page** HTML indépendamment (en ignorant le JavaScript).
4. **Découpe** les textes en chunks (800 mots avec 100 de recouvrement).
5. **Crée les embeddings** (via ta fonction `embed_texts`) et les stocke dans la collection Chroma ou autre backend (`get_collection`).

---

Souhaites-tu que je t’ajoute une **progress bar globale** avec estimation du temps total (pour suivre les ~100 pages plus facilement) ?
