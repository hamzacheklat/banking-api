Excellent choix 🔥 — c’est la **bonne pratique** pour les bases Mongo hétérogènes !
👉 En séparant chaque collection Mongo dans **sa propre collection Chroma**, tu obtiens :

* ✅ Meilleure pertinence (les embeddings d’une même nature restent ensemble)
* ✅ Plus facile à mettre à jour ou réindexer sélectivement
* ✅ Plus rapide lors des requêtes ciblées
* ✅ Plus propre pour le reporting (on peut demander “analyse la collection *logs_errors* uniquement”)

---

## 🧠 Nouvelle version : ingestion multi-collections → multi-Chroma

Voici le **nouveau `app/mongo_ingest.py` complet**, mis à jour pour créer **une collection Chroma par collection Mongo** automatiquement 👇

```python
# app/mongo_ingest.py
from pymongo import MongoClient
from tqdm import tqdm
import uuid, json
from embedder import embed_texts
from chromadb import Client
from chromadb.config import Settings
import config


def json_to_text(document: dict) -> str:
    """
    Convertit un document Mongo (dict) en texte lisible et stable pour l'embedding.
    """
    safe_doc = {}
    for k, v in document.items():
        if isinstance(v, (dict, list)):
            safe_doc[k] = json.dumps(v, ensure_ascii=False)
        elif isinstance(v, (str, int, float, bool)) or v is None:
            safe_doc[k] = v
        else:
            safe_doc[k] = str(v)
    text = "\n".join([f"{k}: {v}" for k, v in safe_doc.items()])
    return text


def get_chroma_client():
    return Client(Settings(persist_directory=config.CHROMA_DB_DIR, anonymized_telemetry=False))


def get_or_create_chroma_collection(client, name: str):
    """
    Retourne une collection Chroma spécifique à la collection Mongo.
    """
    return client.get_or_create_collection(
        name=f"mongo_{name}",
        metadata={"source": name, "description": f"Index vectoriel pour la collection Mongo {name}"},
        embedding_function=None
    )


def ingest_all_collections(sample_limit: int = None, include_collections=None, exclude_collections=None):
    """
    Parcourt toutes les collections Mongo et crée une collection Chroma par collection Mongo.
    """
    print("🚀 Ingestion MongoDB → Chroma (mode multi-collection)")

    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    chroma_client = get_chroma_client()

    mongo_collections = db.list_collection_names()

    if include_collections:
        mongo_collections = [c for c in mongo_collections if c in include_collections]
    if exclude_collections:
        mongo_collections = [c for c in mongo_collections if c not in exclude_collections]

    total_docs = 0

    for cname in mongo_collections:
        print(f"\n📂 Collection Mongo détectée : {cname}")

        mongo_col = db[cname]
        chroma_col = get_or_create_chroma_collection(chroma_client, cname)

        cursor = mongo_col.find()
        if sample_limit:
            cursor = cursor.limit(sample_limit)

        docs, ids, metas = [], [], []

        for doc in tqdm(cursor, desc=f"Traitement {cname}"):
            text = json_to_text(doc)
            docs.append(text)
            ids.append(str(uuid.uuid4()))
            metas.append({
                "collection": cname,
                "_id": str(doc.get("_id")),
            })

        if not docs:
            print(f"⚠️ Aucune donnée dans {cname}")
            continue

        print(f"🧠 Embedding de {len(docs)} documents depuis {cname}...")
        embeddings = embed_texts(docs)

        chroma_col.add(
            ids=ids,
            documents=docs,
            embeddings=embeddings,
            metadatas=metas
        )

        print(f"✅ {len(docs)} documents indexés dans Chroma ({cname})")
        total_docs += len(docs)

    print(f"\n🏁 Ingestion terminée : {total_docs} documents indexés dans {len(mongo_collections)} collections Chroma.")


if __name__ == "__main__":
    # Exemple d’appel : ingère toutes les collections sauf 'sessions'
    ingest_all_collections(sample_limit=1000, exclude_collections=["sessions"])
```

---

## ⚙️ Différences avec la version précédente

| Fonction                       | Avant                                            | Maintenant                                                            |
| ------------------------------ | ------------------------------------------------ | --------------------------------------------------------------------- |
| **Chroma unique**              | Tous les docs allaient dans une seule collection | ✅ 1 collection Chroma par collection Mongo                            |
| **Nom des collections Chroma** | `flow_logs` (fixe)                               | `mongo_<nom_collection>`                                              |
| **Sélection**                  | Toujours toutes les collections                  | ✅ Tu peux filtrer avec `include_collections` ou `exclude_collections` |
| **Structure des métadonnées**  | Simple                                           | `{collection, _id}` — ce qui permet de remonter l’origine du doc      |

---

## 🧩 Exemple d’utilisation via l’API

Tu peux mettre à jour ton endpoint FastAPI `/ingest_mongo` comme ceci 👇

```python
@app.post("/ingest_mongo")
def run_ingest_mongo(sample_limit: int = 1000, exclude: list[str] = None):
    try:
        from mongo_ingest import ingest_all_collections
        ingest_all_collections(sample_limit=sample_limit, exclude_collections=exclude)
        return {"status": "ok", "message": "Ingestion Mongo multi-collection terminée"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Exemple d’appel

```bash
curl -X POST http://localhost:8000/ingest_mongo \
     -H "Content-Type: application/json" \
     -d '{"sample_limit": 500, "exclude": ["temp", "cache"]}'
```

---

## 💬 Et pour les requêtes RAG (`/query`)

Tu peux maintenant préciser **de quelle collection Chroma tu veux tirer le contexte** (ou toutes si tu veux un RAG global) 👇

### ➕ Exemple : `app/rag.py` modifié

```python
from embedder import embed_texts
from chromadb import Client
from chromadb.config import Settings
from litellm_client import generate_with_litellm
import config
from datetime import datetime

def answer_query(query, collection_name=None, top_k=8):
    q_emb = embed_texts([query])[0]
    chroma_client = Client(Settings(persist_directory=config.CHROMA_DB_DIR, anonymized_telemetry=False))

    if collection_name:
        collections = [chroma_client.get_collection(f"mongo_{collection_name}")]
    else:
        # interroge toutes les collections
        collections = [chroma_client.get_collection(name) for name in chroma_client.list_collections()]

    results = []
    for col in collections:
        try:
            res = col.query(query_embeddings=[q_emb], n_results=top_k)
            if res["documents"][0]:
                results.extend(list(zip(res["documents"][0], res["metadatas"][0])))
        except Exception:
            continue

    if not results:
        return {"answer": "Aucun résultat trouvé.", "contexts": []}

    context_text = "\n---\n".join([r[0] for r in results])
    messages = [
        {"role": "system", "content": "Tu es un assistant de monitoring. Analyse les logs et explique les causes observées."},
        {"role": "user", "content": f"CONTEXT:\n{context_text}\n\nQUESTION:\n{query}\nRéponds en français."}
    ]

    answer = generate_with_litellm(messages)
    return {
        "answer": answer,
        "contexts": [{"content": r[0], "meta": r[1]} for r in results],
        "timestamp": datetime.utcnow().isoformat()
    }
```

Tu peux donc appeler :

```bash
curl -X POST http://localhost:8000/query \
     -H "Content-Type: application/json" \
     -d '{"query": "Quelles erreurs ont eu lieu ce matin ?", "collection_name": "flow_errors"}'
```

Ou sans préciser pour interroger tout :

```bash
-d '{"query": "Quels services ont échoué aujourd’hui ?"}'
```

---

Souhaites-tu que je t’ajoute **un endpoint `/list_collections`** pour que ton front puisse voir quelles collections sont dispo dans Chroma et Mongo ?
Ce serait pratique pour construire une UI dynamique où l’utilisateur choisit la collection à interroger.
