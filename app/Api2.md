Parfait — je te fournis une **remplacement complet** de `embedder.py` (et une petite MAJ de `requirements.txt`) qui **n'utilise plus `sentence-transformers`** mais **transformers + torch** (tout en restant 100% local — pas d'API externe).
Ce code fait l'encodage en batch, utilise pooling (mean pooling + normalisation) et fonctionne avec n'importe quel modèle compatible `transformers` placé localement ou accessible depuis le cache HF.

Je donne aussi quelques conseils pratiques pour ton environnement BNP (pré-téléchargement du modèle, chemin local, variables d'environnement).

---

# ✅ Mise à jour `backend/requirements.txt`

Remplace la ligne `sentence-transformers` par `transformers` (si elle est déjà présente pas de souci). Exemple minimal :

```txt
fastapi
uvicorn[standard]
chromadb
transformers
torch
python-dotenv
pdfplumber
python-multipart
pydantic
tqdm
atlassian-python-api
requests
litellm
```

> Remarque : `transformers` + `torch` suffisent pour le nouvel embedder. Si tu veux accélérer le chargement sur CPU, tu peux ajouter `sentencepiece` si tu utilises certains tokenizers mais normalement pas obligatoire.

---

# ✅ Nouveau `app/embedder.py` (remplace l'ancien)

```python
# app/embedder.py
import os
from typing import List
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
import config

# Device selection
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

_model = None
_tokenizer = None
_model_name = os.getenv("LOCAL_EMB_MODEL", config.LOCAL_EMB_MODEL)

def get_tokenizer_and_model():
    global _model, _tokenizer
    if _model is None or _tokenizer is None:
        # Charger le tokenizer et le modèle (peut être un chemin local ou un hub id)
        _tokenizer = AutoTokenizer.from_pretrained(_model_name, use_fast=True)
        _model = AutoModel.from_pretrained(_model_name)
        _model.to(DEVICE)
        _model.eval()
    return _tokenizer, _model

def mean_pooling(model_output, attention_mask):
    """
    mean pooling of token embeddings (ignoring padding)
    model_output: BaseModelOutputWithPooling or tuple (last_hidden_state, ...)
    attention_mask: tensor
    """
    token_embeddings = model_output[0]  # first element is last_hidden_state
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    return sum_embeddings / sum_mask

def embed_texts(texts: List[str], batch_size: int = 64) -> List[List[float]]:
    """
    Encode a list of texts into embeddings (float32 lists).
    Works fully locally (no remote API calls). Returns list of vectors.
    """
    tokenizer, model = get_tokenizer_and_model()
    all_embs = []
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            enc = tokenizer(batch_texts, padding=True, truncation=True, return_tensors="pt", max_length=config.CHUNK_SIZE,)
            input_ids = enc["input_ids"].to(DEVICE)
            attention_mask = enc["attention_mask"].to(DEVICE)
            out = model(input_ids=input_ids, attention_mask=attention_mask, return_dict=False)
            pooled = mean_pooling(out, attention_mask)  # (batch, dim)
            # L2 normalize (common for vector stores)
            pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
            pooled = pooled.cpu().numpy().astype(np.float32)
            for v in pooled:
                all_embs.append(v.tolist())
    return all_embs

# convenience: single-text helper
def embed_text(text: str) -> List[float]:
    return embed_texts([text])[0]
```

### Explications courtes

* Utilise `transformers.AutoTokenizer` + `AutoModel`.
* `mean_pooling` sur le `last_hidden_state` (méthode simple, robuste — pas besoin de `sentence-transformers`).
* Normalisation L2 pour des comparaisons cosinus dans Chroma.
* Batch encoding pour la vitesse / mémoire.
* Compatible avec GPU si disponible (sinon CPU).

---

# 🛠️ Choix du modèle — recommandations

* Par défaut mets dans `.env` : `LOCAL_EMB_MODEL=distilbert-base-uncased` ou `LOCAL_EMB_MODEL=bert-base-uncased` (ces modèles sont standards et compatibles).
* Pour embeddings plus performants (si tu peux les télécharger) privilégie des modèles optimisés pour embeddings (par ex. `all-mpnet-base-v2`, `all-MiniLM-L6-v2`) — **mais** ces modèles sont souvent fournis par la family *sentence-transformers* ; ils restent utilisables via `transformers` si tu as les fichiers locaux.
* Si l'accès réseau est restreint : tu peux déposer le répertoire du modèle (téléchargé depuis un autre réseau) sous `/opt/models/my-emb-model` et mettre `LOCAL_EMB_MODEL=/opt/models/my-emb-model`.

---

# ⚙️ Conseils pour ton environnement BNP (sans accès internet)

1. **Pré-téléchargement** : Sur une machine avec accès internet, fais `from transformers import AutoModel, AutoTokenizer; AutoTokenizer.from_pretrained("distilbert-base-uncased"); AutoModel.from_pretrained("distilbert-base-uncased")` puis copie le dossier `~/.cache/huggingface/hub/...` sur la machine BNP dans un chemin accessible.
2. **Utiliser un chemin local** : mets `LOCAL_EMB_MODEL=/path/to/local/model` dans `.env`.
3. **Variables d'environnement utiles** :

   * `TRANSFORMERS_OFFLINE=1` pour forcer le mode hors-ligne si tu as placé les modèles en local.
   * `HF_HOME=/chemin/vers/cache_hf` si tu veux pointer le cache HF ailleurs.
4. **Memory / batch** : baisse `batch_size` si le serveur n'a pas beaucoup de RAM.
5. **Quantization** (optionnel) : si tu veux réduire l'empreinte mémoire, tu peux quantifier le modèle (ex : `bitsandbytes`) — à considérer si autorisé dans ton infra.

---

# 🔁 Intégration (remplacement rapide)

1. Remplace `app/embedder.py` par le fichier ci-dessus.
2. Mets à jour `requirements.txt` si nécessaire (`remove sentence-transformers`).
3. Dans `.env`, choisis `LOCAL_EMB_MODEL=distilbert-base-uncased` (ou un path local).
4. Relance `uvicorn` — pas besoin d'autres changements, le reste du code (ingestion / RAG) continue d'appeler `embed_texts()` / `embed_text()`.

---

Si tu veux, je peux aussi :

* Te fournir une **version quantifiée** (8-bit) de l’embedder si tu veux gagner de la RAM (nécessite `bitsandbytes` et config spécifique).
* Te générer un petit script `download_model.py` à lancer depuis une machine ayant accès au web pour préparer le dossier modèle à transférer en interne.

Tu veux que je te fournisse le script de téléchargement (prêt à lancer ailleurs) ou que j’ajoute la version 8-bit du loader ?
