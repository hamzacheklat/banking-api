# test_sanitize.py
sample_meta = {"_id": None, "DATE": None, "FLOW": "INVOICE", "COUNT": 5, "EXTRA": {"a":1}}
print(sanitize_metadata_dict(sample_meta))


Excellente observation 👀 — et tu mets le doigt sur **le point le plus critique d’un RAG de logs/monitoring** :
si le modèle ne retrouve pas bien les *jobs échoués d’une date précise* ou un *flow spécifique*, ce n’est pas le LLM le problème — c’est souvent **l’embedding ou la structuration du texte avant l’indexation**.

Je vais t’expliquer **les 4 causes les plus probables** dans ton cas (avec ton ingestion Mongo → Chroma), puis te donner la **solution complète pour corriger** ton pipeline d’embedding 🔧.

---

## ⚠️ 1. Le texte indexé n’est pas structuré de manière discriminante

### Ce que tu fais actuellement :

Tu convertis tout le document Mongo en un gros bloc texte :

```python
text = "\n".join([f"{k}: {v}" for k, v in safe_doc.items()])
```

👉 Résultat :

* Les dates, les IDs, les statuts, les messages d’erreur sont “noyés” dans un texte.
* Le moteur vectoriel (Chroma) ne comprend pas bien les champs structurés.
* Le modèle d’embedding (MiniLM) encode mal les valeurs numériques, les dates et les clés techniques.

---

## ✅ Solution 1 : Embedding structuré “métadonnées + résumé lisible”

Fais un **préformatage clair et cohérent** avant embedding.

### Exemple concret à remplacer dans `mongo_ingest.py` :

```python
def json_to_text(document: dict) -> str:
    """
    Crée une représentation textuelle optimisée pour RAG.
    Chaque ligne est explicite et séquentielle, ce qui facilite la recherche.
    """
    date = str(document.get("DATE", ""))
    flow = document.get("FLOW", "")
    task = document.get("TASK", "")
    job_id = document.get("JOB_ID", "")
    sub_id = document.get("SUB_ID", "")
    origin = document.get("ORIGIN", document.get("SOURCE", ""))
    failure = document.get("FAILURE REASON", "")
    action = document.get("WHAT TO DO?", "")
    tower_url = document.get("TOWER_URL", "")
    status = document.get("STATUS", "")

    text = (
        f"DATE: {date}\n"
        f"FLOW: {flow}\n"
        f"TASK: {task}\n"
        f"JOB_ID: {job_id}\n"
        f"SUB_ID: {sub_id}\n"
        f"ORIGIN: {origin}\n"
        f"STATUS: {status}\n"
        f"FAILURE_REASON: {failure}\n"
        f"WHAT_TO_DO: {action}\n"
        f"TOWER_URL: {tower_url}\n"
    )

    return text
```

✅ Ce format rend les requêtes du type :

> “Quels jobs ont échoué le 29 octobre 2025 ?”
> ou
> “Montre les erreurs du flow INVOICE_EXPORT”
> beaucoup plus précises.

---

## ⚠️ 2. Le modèle d’embedding utilisé n’est pas optimal pour des données techniques/logs

Tu utilises :

```python
SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
```

Ce modèle est excellent pour du texte “naturel” (phrases),
mais **pas pour des logs ou du texte semi-structuré**.

---

## ✅ Solution 2 : Utiliser un modèle d’embedding spécialisé

👉 Deux options robustes :

1. **`mixedbread-ai/mxbai-embed-large-v1`** (open-source, top 1 des benchmarks RAG techniques)
2. **`text-embedding-3-large`** (si tu passes par OpenAI/LiteLLM)

Dans `embedder.py` :

```python
from sentence_transformers import SentenceTransformer

_model = None

def get_model():
    global _model
    if _model is None:
        # Option 1 : modèle open source
        _model = SentenceTransformer("mixedbread-ai/mxbai-embed-large-v1")
    return _model
```

⚙️ Ces modèles gèrent mieux :

* les tokens courts (dates, identifiants),
* les contextes logiques,
* les chaînes techniques (`FLOW=`, `JOB_ID=`, etc.).

---

## ⚠️ 3. L’interrogation RAG est trop floue

Ton `answer_query()` fait ceci :

```python
res = col.query(query_embeddings=[q_emb], n_results=top_k)
```

➡️ Si le query est “Analyse les jobs échoués le 29 octobre”,
le modèle vectoriel va chercher des vecteurs “similaires” à la phrase entière,
mais **pas forcément les bons champs** (ex : il ne comprend pas la date).

---

## ✅ Solution 3 : Reranking lexical + Requête reformulée

Avant de chercher, reformule la requête utilisateur en une version “data-oriented” :

Dans `rag.py`, juste avant `col.query()` :

```python
from datetime import datetime

def normalize_query(query: str) -> str:
    """
    Reformule la requête en style log pour améliorer le matching.
    """
    q = query.lower()
    # extraction simple de dates
    date_match = re.findall(r"\d{4}-\d{2}-\d{2}", q)
    if date_match:
        q += f" date:{date_match[0]}"
    # renforce les mots clés utiles
    q = q.replace("job", "JOB_ID").replace("flow", "FLOW").replace("task", "TASK")
    q = q.replace("failed", "STATUS: FAILED").replace("error", "FAILURE_REASON")
    return q

# ...
normalized_query = normalize_query(query)
q_emb = embed_texts([normalized_query])[0]
res = col.query(query_embeddings=[q_emb], n_results=top_k)
```

💡 Ça améliore drastiquement la précision de matching vectoriel.

---

## ⚠️ 4. Pas de dédoublonnage ou historique mal géré

Si tu as indexé plusieurs fois les mêmes flows sans métadonnées claires,
tu as peut-être du **bruit** dans ton Chroma.

---

## ✅ Solution 4 : Rebuild propre

Une fois ton ingestion corrigée :

1. Supprime le dossier Chroma existant :

   ```bash
   rm -rf ./chroma_data
   ```

2. Relance une ingestion complète (avec le format amélioré)

   ```bash
   python app/mongo_ingest.py --full
   ```

3. Puis active le mode **incrémental** (comme on l’a vu plus haut).

---

## 🧠 Résumé des optimisations à faire

| Zone                        | Action                                                 | Impact                     |
| --------------------------- | ------------------------------------------------------ | -------------------------- |
| **Format texte**            | Créer un format structuré (FLOW/TASK/DATE/STATUS/etc.) | +++ Précision des requêtes |
| **Modèle d’embedding**      | Passer à `mixedbread-ai/mxbai-embed-large-v1`          | ++ Compréhension des logs  |
| **Pré-traitement requêtes** | Normaliser les queries avec mots-clés & dates          | ++ Pertinence du RAG       |
| **Réindexation propre**     | Nettoyer les anciens embeddings mal formés             | + Cohérence globale        |

---

Si tu veux, je peux te faire un **script `rebuild_index.py`** qui :

* nettoie l’ancien Chroma,
* réindexe les données proprement,
* te donne un log de couverture (combien de jobs, combien d’erreurs par jour).

Souhaites-tu que je te le prépare ?
