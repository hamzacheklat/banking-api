Merci — le message d’erreur sur ta capture est clair : **Chroma refuse des `metadatas` contenant des `None` ou des types non supportés**.
L’erreur explique que `NoneType` ne peut pas être converti en `Bool/Int/Float/Str/SparseVector`. En pratique il faut **nettoyer** les métadonnées avant de les envoyer à `chroma_col.add()`.

Je te donne :

1. une **explication rapide** des causes,
2. une **fonction utilitaire `sanitize_meta()`** (à coller dans ton `mongo_ingest.py`),
3. le **bloc `_process_batch`** mis à jour (batching + sanitizing),
4. quelques **bonnes pratiques** et tests rapides.

---

## Pourquoi ça casse

* Chroma attend dans `metadatas` des valeurs primaires (bool, int, float, str) ou `SparseVector`.
* Si une valeur est `None` (ou un dict/list non converti), Rust binding lève `TypeError: 'NoneType' object cannot be converted ...`.
* Il faut garantir que chaque metadata pour chaque document est une structure plate et sans `None`.

---

## Solution : sanitiser les métadatas avant ajout

Colle ceci dans ton `mongo_ingest.py` (ou remplace les fonctions existantes) :

```python
# utilitaire pour sanitiser les métadatas avant envoi à Chroma
def _sanitize_value(v):
    """
    Convertit la valeur en un type accepté par Chroma:
    - None -> "" (string vide)
    - bool/int/float/str -> inchangé
    - list/dict -> JSON string
    - autre -> str(v)
    """
    import json
    if v is None:
        return ""
    if isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (list, dict)):
        try:
            return json.dumps(v, ensure_ascii=False)
        except Exception:
            return str(v)
    # fallback
    return str(v)


def sanitize_metadata_dict(meta: dict) -> dict:
    """
    Retourne une copy du dict meta avec toutes les valeurs converties en types supportés.
    """
    return {k: _sanitize_value(v) for k, v in (meta.items() if meta else {})}
```

Et remplace / mets à jour ta fonction interne de traitement de batch `_process_batch` par ceci (extrait complet) :

```python
def _process_batch(chroma_col, docs, ids, metas):
    """
    Gère un batch complet : embedding + ajout à Chroma.
    S'assure que les metadatas sont nettoyées et alignées.
    """
    print(f"\n🧩 Traitement d’un batch de {len(docs)} documents...")

    # Embedding
    embeddings = embed_texts(docs)

    # Sanitize metadatas: must be a list of dicts with simple values
    safe_metas = []
    for meta in metas:
        safe_metas.append(sanitize_metadata_dict(meta))

    # Double-check lengths
    if not (len(ids) == len(docs) == len(embeddings) == len(safe_metas)):
        raise ValueError("Lengths mismatch between ids/documents/embeddings/metadatas")

    # Add to Chroma
    chroma_col.add(
        ids=ids,
        documents=docs,
        embeddings=embeddings,
        metadatas=safe_metas
    )
    print(f"✅ Batch ajouté ({len(docs)} docs).")
```

> Remarque : certains clients Chroma attendent `metadatas` sous la même structure (liste parallèle aux `documents`). Assure-toi que `safe_metas` est une `list[dict]` et que chaque dict est plat.

---

## Points supplémentaires / bonnes pratiques

* **Ne pas envoyer d’objets volumineux** (grand JSON) comme metadata : préfère mettre un `id` + éventuellement un petit résumé. Stocke le détail dans le `document` (texte indexé).
* **Limite la taille des metadata** — Chroma stocke aussi les metadatas; trop gros augmente l’I/O.
* Si tu utilises un champ `DATE` ou `_id` pour incrémental, assure-toi qu’ils existent et sont sérialisés en `str`.
* **Tester avec un petit batch** (e.g. 5 documents) avant de lancer 5000.
* Si tu veux conserver des booléens/nombres, garde-les tels quels (pas besoin de `str`) — mais surtout pas `None`.

---

## Test rapide à lancer

Avant de lancer un grand run, fais un petit test :

```python
# test_sanitize.py
sample_meta = {"_id": None, "DATE": None, "FLOW": "INVOICE", "COUNT": 5, "EXTRA": {"a":1}}
print(sanitize_metadata_dict(sample_meta))
```

Le print devrait donner quelque chose comme :

```py
{'_id': '', 'DATE': '', 'FLOW': 'INVOICE', 'COUNT': 5, 'EXTRA': '{"a": 1}'}
```

---

Si tu veux, je peux **te fournir la version complète du `mongo_ingest.py`** (avec batching) en y intégrant directement ces fonctions de sanitization et en m'assurant que tout est cohérent avec ta version précédente.
Veux-tu que je te renvoie le fichier complet prêt à remplacer celui en place ?
