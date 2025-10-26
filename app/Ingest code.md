Très bonne remarque 🔥
Tu mets le doigt sur deux points essentiels dans un RAG “engineering-grade” :

1. 🧠 **Quel modèle d’embedding est optimal pour analyser du code ?**
2. ⚙️ **Comment créer un ingesteur local** (par exemple pour ton code source, sans passer par Confluence) ?

---

## 🧩 1️⃣ — Le modèle d’embedding actuel (`all-MiniLM-L6-v2`) : excellent… mais pas pour le code

Ton `.env` utilise :

```env
LOCAL_EMB_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

Ce modèle est **très bon pour du texte** (Confluence, tickets, documentation).
Mais il **n’est pas entraîné sur du code source** → il ne comprend pas la sémantique du code (structures, noms de fonctions, API, etc.).

---

## 💡 Meilleurs modèles pour le code

Voici quelques modèles d’embedding **spécialement conçus pour le code**, compatibles avec `sentence-transformers` ou `transformers` :

| Modèle                                       | Type                         | Taille                                                   | Points forts                                 |
| -------------------------------------------- | ---------------------------- | -------------------------------------------------------- | -------------------------------------------- |
| 🧩 `microsoft/codebert-base`                 | HuggingFace                  | Moyen                                                    | Très bon pour comprendre du code + docstring |
| 🔍 `microsoft/unixcoder-base`                | HuggingFace                  | Moyen+                                                   | Multilang (Python, Java, JS, etc.)           |
| 🚀 `sentence-transformers/all-MiniLM-L12-v2` | Kaggle / SentenceTransformer | Petit                                                    | OK généraliste (si tu veux léger)            |
| 🧠 `BAAI/bge-small-en-v1.5`                  | HF / General + Code          | Léger, rapide, précis                                    |                                              |
| 🧰 `intfloat/e5-base-v2`                     | HF / English                 | Très performant pour retrieval, y compris code commenté  |                                              |
| 🧑‍💻 `jinaai/jina-embeddings-v2-base-code`  | JinaAI                       | Spécialement optimisé pour code (Python, JS, Java, etc.) |                                              |

👉 **Recommandé pour ton cas (RAG interne sur code source) :**

```env
LOCAL_EMB_MODEL=jinaai/jina-embeddings-v2-base-code
```

Ce modèle :

* comprend le code multi-langage, les classes, les imports, etc.
* fonctionne avec SentenceTransformers
* a un très bon rapport vitesse/précision pour la recherche sémantique de fonctions, classes, modules…

---

## ⚙️ 2️⃣ — Ajouter un **ingesteur local pour ton code source**

Tu veux un script qui :

* scanne un dossier (`./src/` ou autre)
* lit les fichiers `.py`, `.ts`, `.js`, `.java`, `.cpp`, etc.
* découpe proprement (chunks intelligents)
* et les insère dans Chroma avec les embeddings

Voici ton nouveau fichier :

---

### 📄 `app/ingest_local_code.py`

```python
import os
import uuid
from tqdm import tqdm
from embedder import embed_texts
from vector_store import get_collection
import config

# Extensions de code à indexer
CODE_EXTENSIONS = [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".html", ".css", ".json"]

def read_code_files(base_path="./src"):
    code_files = []
    for root, _, files in os.walk(base_path):
        for f in files:
            if any(f.endswith(ext) for ext in CODE_EXTENSIONS):
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as file:
                        content = file.read()
                        code_files.append({
                            "path": path,
                            "content": content
                        })
                except Exception as e:
                    print(f"⚠️ Erreur lecture {path}: {e}")
    return code_files

def chunk_code(text, max_lines=40, overlap=5):
    lines = text.splitlines()
    chunks = []
    i = 0
    while i < len(lines):
        chunk = "\n".join(lines[i:i+max_lines])
        if chunk.strip():
            chunks.append(chunk)
        i += max_lines - overlap
    return chunks

def ingest_local_code(base_path="./src"):
    files = read_code_files(base_path)
    collection = get_collection()
    all_chunks, metadatas, ids = [], [], []

    print(f"📂 {len(files)} fichiers trouvés dans {base_path}")

    for f in files:
        chunks = chunk_code(f["content"])
        for chunk in chunks:
            all_chunks.append(chunk)
            metadatas.append({"path": f["path"]})
            ids.append(str(uuid.uuid4()))

    batch = 128
    for i in tqdm(range(0, len(all_chunks), batch)):
        batch_texts = all_chunks[i:i+batch]
        batch_ids = ids[i:i+batch]
        batch_meta = metadatas[i:i+batch]
        embs = embed_texts(batch_texts)
        collection.add(
            ids=batch_ids,
            documents=batch_texts,
            embeddings=embs,
            metadatas=batch_meta
        )
    print("✅ Ingestion du code source terminée.")

if __name__ == "__main__":
    ingest_local_code("./src")
```

---

### ➕ Ajouter une route API

Dans `main.py`, ajoute :

```python
from ingest_local_code import ingest_local_code

@app.post("/ingest_local_code")
def run_ingest_local_code():
    try:
        ingest_local_code("./src")  # tu peux changer le chemin
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

### ⚡ Ajoute aussi dans le frontend

Dans `api.service.ts` :

```ts
ingestLocalCode(): Observable<any> {
  return this.http.post(`${this.base}/ingest_local_code`, {});
}
```

Et dans `chat.component.html`, ajoute un bouton :

```html
<button (click)="runIngestLocalCode()" [disabled]="loading">
  🧰 Ingest Code Local
</button>
```

Et dans `chat.component.ts` :

```ts
runIngestLocalCode() {
  if (this.loading) return;
  this.loading = true;
  this.api.ingestLocalCode().subscribe({
    next: () => {
      alert('✅ Ingestion du code terminée.');
      this.loading = false;
    },
    error: (e) => {
      alert('❌ Erreur ingestion code: ' + e.message);
      this.loading = false;
    }
  });
}
```

---

## ✅ Résumé

| Élément               | Avant                      | Après                                        |
| --------------------- | -------------------------- | -------------------------------------------- |
| Modèle d’embedding    | `all-MiniLM-L6-v2` (texte) | `jinaai/jina-embeddings-v2-base-code` (code) |
| Source RAG            | Confluence uniquement      | Confluence + Code local                      |
| Compréhension du code | ❌ très faible              | ✅ excellente                                 |
| Contexte du RAG       | Docs techniques            | + Fonctions, classes, APIs internes          |
| Utilisation           | `/ingest_confluence`       | + `/ingest_local_code`                       |

---

Souhaites-tu que je t’ajoute la version **Docker** complète (`docker-compose.yml`) qui lance :

* le backend FastAPI
* Chroma persistant
* le frontend Angular
* et qui monte un volume `./src` pour ingérer ton code automatiquement ?
