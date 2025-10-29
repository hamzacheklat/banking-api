import requests
import uuid
import os
from bs4 import BeautifulSoup
from tqdm import tqdm
from embedder import embed_texts
from vector_store import get_collection
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ⚙️ SETTINGS
DELPHIX_BASE_URL = "https://uk271.delphix.xmp.net.intra"
DELPHIX_USER = "admin"
DELPHIX_PASSWORD = "password"


# ============================================================
# 🔐 LOGIN
# ============================================================
def delphix_login():
    """Login to Delphix and return authenticated session."""
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
# 🌐 SCRAPE HTML DOC
# ============================================================
def scrape_api_html(sess):
    """
    Crawl the Delphix API documentation HTML pages (e.g., Swagger UI).
    Returns a list of (url, text_content).
    """
    start_url = f"{DELPHIX_BASE_URL}/api"
    visited, to_visit = set(), [start_url]
    results = []

    while to_visit:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            r = sess.get(url)
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "html.parser")

            # Extract visible text
            text = soup.get_text(separator=" ", strip=True)
            results.append((url, text))

            # Follow internal links under /api/
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("/api") and not href.endswith(".json"):
                    next_url = f"{DELPHIX_BASE_URL}{href}"
                    if next_url not in visited and next_url not in to_visit:
                        to_visit.append(next_url)

        except Exception as e:
            print(f"⚠️ Error scraping {url}: {e}")

    print(f"✅ Scraped {len(results)} API HTML pages.")
    return results


# ============================================================
# ✂️ CHUNKING
# ============================================================
def chunk_text(text, chunk_size=800, overlap=100):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks


# ============================================================
# 🧠 INGESTION
# ============================================================
def ingest_api_scraped_docs():
    """Scrape and ingest API documentation HTML content."""
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
