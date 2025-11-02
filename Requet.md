Parfait, là on peut le faire proprement. 😄

ChromaDB (ou tout vector store basé sur Chroma) te permet de **filtrer les documents par métadonnées** au moment de la recherche. Puisque tu as un champ `STATUS`, tu peux l’utiliser pour vérifier si tes flows failed sont bien indexés.

Voici comment faire :

---

### 1️⃣ Récupérer le collection / VectorStore

Si tu utilises ton `get_vanish_vectorstore()` ou `get_vanish_collection()` :

```python
from vector_store import get_vanish_collection

chroma_col = get_vanish_collection()  # ou ton vectorstore
```

---

### 2️⃣ Requête par métadonnée `STATUS`

```python
# Exemple : récupérer tous les flows FAILED
results = chroma_col.query(
    query_texts=[""],  # vide si on veut juste filtrer sur le metadata
    n_results=100,    # nombre max de résultats à retourner
    where={"STATUS": "FAILED"},  # filtre sur le champ STATUS
    include=["metadatas", "documents"]  # pour voir les données
)
```

* `query_texts=[""]` → tu ne fais pas de recherche vectorielle, juste un filtre sur les métadonnées.
* `where={"STATUS": "FAILED"}` → filtre uniquement les flows échoués.
* `include=["metadatas", "documents"]` → récupère le contenu stocké et les métadonnées pour inspection.

---

### 3️⃣ Afficher les résultats

```python
for doc, meta in zip(results["documents"], results["metadatas"]):
    print(f"FLOW: {meta['_id']} STATUS: {meta['STATUS']} START_TIME: {meta['START_TIME']}")
```

Ça te permet de **vérifier directement dans Chroma** si tes flows failed sont bien présents.

---

### 4️⃣ Astuce

* Si tu veux filtrer par date + status :

```python
where={"STATUS": "FAILED", "START_TIME": {"$regex": "^2025-10-01"}}
```

* `$regex` fonctionne si tes dates sont en ISO format (`YYYY-MM-DD...`).

---

💡 **En résumé** :

* Utilise `query_texts=[""]` pour juste filtrer sur métadatas.
* Mets `where={"STATUS": "FAILED"}` pour voir tes flows échoués.
* Tu peux ajouter d’autres filtres (`START_TIME`, `JOB_ID`, etc.) pour vérifier plus finement.

---

Si tu veux, je peux te donner **un petit snippet prêt à lancer** pour lister tous les flows failed du 01/10 dans Chroma et voir si tes données y sont vraiment.

Veux‑tu que je fasse ça ?
